from __future__ import annotations

import subprocess
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from app.core.command_builder import CommandBuilder
from app.models.model_definition import ModelDefinition, ModelStatus


class ProcessManager(QObject):
    output_received = Signal(str)
    process_started = Signal(int)
    process_ready = Signal(int)  # emitido cuando el servidor está escuchando (RUNNING)
    process_stopped = Signal()
    process_error = Signal(str)

    def __init__(self, command_builder: CommandBuilder, logs_dir: Path) -> None:
        super().__init__()
        self._cmd_builder = command_builder
        self._logs_dir = logs_dir
        self._process: subprocess.Popen[bytes] | None = None
        self._log_file = None
        self._current_model: ModelDefinition | None = None
        self._reader_thread: threading.Thread | None = None
        self._output_buffer: list[str] = []
        self._stop_requested: bool = False
        self._ready_emitted: bool = False

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(50)
        self._poll_timer.timeout.connect(self._flush_buffer)

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self, model: ModelDefinition) -> bool:
        if self.is_running:
            self.process_error.emit("Ya hay un proceso en ejecución.")
            return False

        # Validar binario por modelo (soporta backend.llama_server_path)
        try:
            ok, eff_path = self._cmd_builder.validate_server_for_model(model)
            if not ok:
                self.process_error.emit(
                    f"llama-server no encontrado para {model.name}:\n{eff_path}\n"
                    f"Verifica backend.llama_server_path en model.yaml o config/app.yaml"
                )
                return False
        except Exception:
            if not self._cmd_builder.validate_server():
                self.process_error.emit(
                    f"llama-server no encontrado:\n{self._cmd_builder._server_path}"
                )
                return False

        # Si la variante seleccionada tiene YAML per-variante o perfil custom, usar config efectiva
        effective = model
        try:
            if hasattr(model, "get_effective_model"):
                effective = model.get_effective_model(model.model.file)
            elif hasattr(model, "has_variant_profile") and model.has_variant_profile(model.model.file):
                effective = model.get_for_variant(model.model.file)
            elif hasattr(model, "variant_has_mtp"):
                pass
        except Exception:
            effective = model

        errors = self._validate(effective)
        if errors:
            for e in errors:
                self.process_error.emit(e)
            return False

        cmd = self._cmd_builder.build(effective)

        log_dir = self._logs_dir / _safe_dir_name(model.name)
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_path = log_dir / f"{timestamp}.log"

        try:
            self._log_file = open(log_path, "wb")
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
            )
        except OSError as e:
            self.process_error.emit(f"Error al iniciar proceso:\n{e}")
            self._cleanup()
            return False

        self._current_model = model
        model.status = ModelStatus.STARTING
        model.pid = self._process.pid
        self._stop_requested = False
        self._ready_emitted = False

        self._reader_thread = threading.Thread(
            target=self._read_output, daemon=True
        )
        self._reader_thread.start()
        self._poll_timer.start()
        self.process_started.emit(self._process.pid)
        return True

    def stop(self) -> None:
        self._stop_requested = True
        self._poll_timer.stop()
        if self._process is None:
            # Aun así emitir stopped para que la UI se actualice
            if self._current_model:
                self._current_model.status = ModelStatus.STOPPED
                self._current_model.pid = None
            self.process_stopped.emit()
            return
        try:
            self._process.terminate()
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.kill()
        except Exception:
            pass
        finally:
            if self._current_model:
                self._current_model.status = ModelStatus.STOPPED
                self._current_model.pid = None
            self._cleanup()
            # Evitar doble emit: _read_output también emite process_stopped al terminar
            # Solo emitir si el thread ya terminó o no existe
            if self._reader_thread is None or not self._reader_thread.is_alive():
                self.process_stopped.emit()
            else:
                # El thread emitirá process_stopped; marcar para que no ponga ERROR
                pass

    def _validate(self, model: ModelDefinition) -> list[str]:
        errors: list[str] = []
        if not model.model_path.is_file():
            errors.append(f"Archivo del modelo no encontrado:\n{model.model_path}")
        if model.capabilities.vision:
            enc = model.vision_encoder_path
            if enc is None or not enc.is_file():
                errors.append(f"Encoder de visión no encontrado:\n{enc}")
        if model.model.draft_model:
            draft = model.draft_model_path
            if draft is None or not draft.is_file():
                errors.append(f"Modelo draft no encontrado:\n{draft}")
        return errors

    def _read_output(self) -> None:
        proc = self._process
        if proc is None or proc.stdout is None:
            return
        try:
            while True:
                chunk = proc.stdout.read(4096)
                if not chunk:
                    break
                try:
                    text = chunk.decode("utf-8", errors="replace")
                except Exception:
                    text = str(chunk)
                self._output_buffer.append(text)
                if self._log_file:
                    self._log_file.write(chunk)
                    self._log_file.flush()
                # Detección temprana de READY (sin esperar flush)
                self._check_ready(text)
        except Exception:
            pass
        finally:
            proc.wait()
            self._poll_timer.stop()
            if self._current_model:
                if self._stop_requested:
                    # Usuario pidió detener → siempre STOPPED, no ERROR
                    self._current_model.status = ModelStatus.STOPPED
                elif proc.returncode == 0:
                    self._current_model.status = ModelStatus.STOPPED
                elif proc.returncode is None:
                    self._current_model.status = ModelStatus.STOPPED
                else:
                    # Si nunca llegó a READY y falla rápido, es ERROR real
                    # Si ya estaba RUNNING, un crash también es ERROR
                    # pero si fue stop_requested ya está manejado
                    self._current_model.status = ModelStatus.ERROR
                    if proc.returncode is not None:
                        self.process_error.emit(f"Proceso terminó con código {proc.returncode}")
                self._current_model.pid = None
            self._flush_buffer()
            self._cleanup()
            self.process_stopped.emit()

    def _check_ready(self, text: str) -> None:
        if self._ready_emitted or self._current_model is None:
            return
        lower = text.lower()
        # Patrones que indican que el servidor ya está escuchando
        ready_markers = [
            "listening on",
            "model loaded",
            "server is listening",
            "llama_server: listening",
            "http server listening",
        ]
        for marker in ready_markers:
            if marker in lower:
                self._ready_emitted = True
                self._current_model.status = ModelStatus.RUNNING
                # Emitir desde thread → queued connection, thread-safe
                try:
                    self.process_ready.emit(self._current_model.pid or 0)
                except Exception:
                    pass
                break

    def _flush_buffer(self) -> None:
        if self._output_buffer:
            text = "".join(self._output_buffer)
            self._output_buffer.clear()
            for line in text.splitlines():
                self.output_received.emit(line)

    def _cleanup(self) -> None:
        self._process = None
        if self._log_file:
            try:
                self._log_file.close()
            except Exception:
                pass
            self._log_file = None


def _safe_dir_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
