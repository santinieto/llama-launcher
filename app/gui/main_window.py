from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QInputDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.command_builder import CommandBuilder
from app.core.config_loader import load_app_config
from app.core.model_manager import ModelManager
from app.core.process_manager import ProcessManager
from app.gui.log_viewer import LogViewer
from app.gui.model_view import ModelCard, VariantProfileDialog
from app.gui.settings_view import SettingsDialog
from app.models.model_definition import ModelHealth, ModelStatus


class MainWindow(QWidget):
    def __init__(
        self,
        model_manager: ModelManager,
        process_manager: ProcessManager,
        command_builder: CommandBuilder,
        app_config: dict,
    ) -> None:
        super().__init__()
        self._model_manager = model_manager
        self._process_manager = process_manager
        self._command_builder = command_builder
        self._app_config = app_config
        self._model_cards: dict[str, ModelCard] = {}
        self._unconfigured_cards: dict[str, ModelCard] = {}
        self._init_ui()
        self._connect_signals()
        self._refresh_models()

    def _init_ui(self) -> None:
        self.setWindowTitle("Local LLM Manager — llama.cpp")
        self.setMinimumSize(1150, 740)
        self.resize(1280, 780)

        # Estilo global pulido
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', Inter, sans-serif; }
            QToolTip { background-color: #2a2a3a; color: #e0e0e0; border: 1px solid #3a3a5a; border-radius: 6px; padding: 6px; font-size: 10px; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header con gradiente y branding
        header = QFrame()
        header.setObjectName("Header")
        header.setStyleSheet("""
            #Header { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #12121a, stop:1 #1e1e2e);
                      border-bottom: 1px solid #2d2d44; }
        """)
        header.setFixedHeight(62)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(12)

        # Logo + título
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("⟡  Local LLM Manager")
        title.setStyleSheet("font-size: 19px; font-weight: 800; color: #e8e8ff; background: transparent; border: none; letter-spacing: 0.5px;")
        subtitle = QLabel("llama.cpp  •  gestión local de modelos GGUF  •  MTP auto-detectado")
        subtitle.setStyleSheet("font-size: 10px; color: #8a8aaa; background: transparent; border: none;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # Botones header
        settings_btn = QPushButton("⚙  Settings")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet("""
            QPushButton { background-color: #1e1e2e; color: #a0a0b8; border: 1px solid #2d2d44; border-radius: 8px; padding: 7px 14px; font-size: 11px; font-weight: 600; }
            QPushButton:hover { background-color: #2a2a3a; color: #e0e0e0; border-color: #3a3a5a; }
            QPushButton:pressed { background-color: #1a1a2a; }
        """)
        settings_btn.setToolTip("Configurar rutas de llama-server y directorio de modelos")
        settings_btn.clicked.connect(self._open_settings)
        header_layout.addWidget(settings_btn)

        refresh_btn = QPushButton("↻  Recargar Configs")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton { background-color: #2d5a3d; color: #e0ffe0; border: 1px solid #3a7a4a; border-radius: 8px; padding: 7px 16px; font-size: 11px; font-weight: 700; }
            QPushButton:hover { background-color: #357a4a; border-color: #4caf50; }
            QPushButton:pressed { background-color: #1e3a2a; }
        """)
        refresh_btn.setToolTip("Recarga todas las configuraciones (model.yaml) desde disco\nsin reiniciar. Detecta variantes y MTP.\nAtajo: F5")
        refresh_btn.clicked.connect(self._refresh_models)
        self._refresh_btn = refresh_btn
        header_layout.addWidget(refresh_btn)

        main_layout.addWidget(header)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #2d2d44; }")
        splitter.setChildrenCollapsible(False)

        # Panel izquierdo
        left_panel = QWidget()
        left_panel.setStyleSheet("background-color: #0f0f14;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        left_header = QHBoxLayout()
        left_label = QLabel("Modelos Disponibles")
        left_label.setStyleSheet("color: #e0e0ff; font-size: 11px; font-weight: 700; background: transparent; border: none; letter-spacing: 0.8px; text-transform: uppercase;")
        left_header.addWidget(left_label)
        left_header.addStretch()
        # Contador
        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color: #6a6a8a; background: #1a1a2a; border: 1px solid #2a2a3a; border-radius: 10px; padding: 2px 8px; font-size: 10px;")
        left_header.addWidget(self._count_label)
        left_layout.addLayout(left_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea { border: 1px solid #1e1e2e; border-radius: 10px; background-color: #0f0f14; }
            QScrollBar:vertical { background: #0f0f14; width: 8px; margin: 2px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #2a2a3a; border-radius: 4px; min-height: 24px; }
            QScrollBar::handle:vertical:hover { background: #3a3a5a; }
            QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
        """)

        self._models_container = QWidget()
        self._models_container.setStyleSheet("background-color: transparent;")
        from PySide6.QtWidgets import QSizePolicy

        self._models_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._models_layout = QVBoxLayout(self._models_container)
        self._models_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._models_layout.setSpacing(10)
        self._models_layout.setContentsMargins(6, 6, 12, 6)
        scroll.setWidget(self._models_container)
        left_layout.addWidget(scroll, stretch=1)

        # Panel derecho
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #0f0f14;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        logs_header = QHBoxLayout()
        logs_label = QLabel("◆  Terminal — Logs")
        logs_label.setStyleSheet("color: #e0e0ff; font-size: 11px; font-weight: 700; background: transparent; border: none; letter-spacing: 0.8px;")
        logs_header.addWidget(logs_label)
        logs_header.addStretch()
        # Indicador vivo
        self._live_dot = QLabel("● LIVE")
        self._live_dot.setStyleSheet("color: #4caf50; background: #1a2a1a; border: 1px solid #2a5a3a; border-radius: 10px; padding: 2px 8px; font-size: 9px; font-weight: 700;")
        logs_header.addWidget(self._live_dot)
        right_layout.addLayout(logs_header)

        self._log_viewer = LogViewer()
        self._log_viewer.setMinimumWidth(440)
        right_layout.addWidget(self._log_viewer, stretch=1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([560, 720])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, stretch=1)

        # Status bar pulida
        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #12121a; border-top: 1px solid #1e1e2e;")
        status_frame.setFixedHeight(28)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(12, 0, 12, 0)
        status_layout.setSpacing(8)
        dot = QLabel("●")
        dot.setStyleSheet("color: #4caf50; font-size: 10px; background: transparent; border: none;")
        status_layout.addWidget(dot)
        self._status_bar = QLabel("Listo — ningún modelo en ejecución")
        self._status_bar.setStyleSheet("color: #8a8aaa; font-size: 10px; background: transparent; border: none;")
        status_layout.addWidget(self._status_bar)
        status_layout.addStretch()
        hint = QLabel("F5 recarga  •  ⚙ por variante = perfil custom")
        hint.setStyleSheet("color: #5a5a6a; font-size: 9px; background: transparent; border: none;")
        status_layout.addWidget(hint)
        main_layout.addWidget(status_frame)

        self.setStyleSheet(self.styleSheet() + "background-color: #0f0f14; color: #e0e0e0;")

    def _connect_signals(self) -> None:
        pm = self._process_manager
        pm.output_received.connect(self._log_viewer.append_line)
        pm.process_started.connect(self._on_process_started)
        try:
            pm.process_ready.connect(self._on_process_ready)
        except Exception:
            pass
        pm.process_stopped.connect(self._on_process_stopped)
        pm.process_error.connect(self._on_process_error)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F5:
            self._refresh_models()
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_variant_changed(self, model_name: str, new_file: str) -> None:
        self._log_viewer.append_line(f"[UI] {model_name}: versión → {Path(new_file).name}")
        # Actualizar contador de perfil custom si existe
        m = self._model_manager.get_by_name(model_name)
        if m and m.has_variant_profile(new_file):
            self._status_bar.setText(f"Variante {Path(new_file).name} — perfil custom activo")
            self._status_bar.setStyleSheet("color: #7aafff; font-size: 10px; background: transparent; border: none; font-weight: bold;")
        else:
            self._status_bar.setText(f"Variante seleccionada: {Path(new_file).name}")
            self._status_bar.setStyleSheet("color: #64b5f6; font-size: 10px; background: transparent; border: none;")

    def _on_edit_variant_profile(self, model_name: str, variant: str) -> None:
        model = self._model_manager.get_by_name(model_name)
        if not model:
            return
        dlg = VariantProfileDialog(model, variant, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            overrides = dlg.get_overrides()
            # overrides is None → eliminar perfil
            if overrides is None:
                ok = self._model_manager.save_variant_profile(model, variant, None)
                msg = f"Perfil eliminado para {Path(variant).name} — ahora hereda base"
            elif not overrides:
                QMessageBox.information(self, "Sin cambios", "No se detectaron cambios respecto al base.\nNo se guardó perfil.")
                return
            else:
                ok = self._model_manager.save_variant_profile(model, variant, overrides)
                msg = f"Perfil guardado para {Path(variant).name}"
            if ok:
                self._log_viewer.append_line(f"[System] {msg}")
                self._status_bar.setText(msg)
                self._status_bar.setStyleSheet("color: #4caf50; font-size: 10px; background: transparent; border: none; font-weight: bold;")
                self._refresh_models()
            else:
                QMessageBox.warning(self, "Error", "No se pudo guardar el perfil.")

    def _on_edit_backend(self, model_name: str) -> None:
        model = self._model_manager.get_by_name(model_name)
        if not model:
            return
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QLabel

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Runtime llama-server — {model.name}")
        dlg.setMinimumWidth(500)
        layout = QVBoxLayout(dlg)
        info = QLabel(
            f"Modelo: <b>{model.name}</b><br>"
            f"Actual: <code>{model.backend.llama_server_path or 'global (config/app.yaml)'}</code><br>"
            f"Global: <code>{self._command_builder._server_path}</code><br><br>"
            "Selecciona un binario específico para este modelo.<br>"
            "Vacío = usa el global. Útil para modelos que requieren una versión particular de llama.cpp."
        )
        info.setStyleSheet("color: #a0a0b8; font-size: 10px; background: transparent; border: none;")
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        edit = QLineEdit(model.backend.llama_server_path)
        edit.setPlaceholderText("Vacío = global, ej: D:/llama.cpp/versions/b1234/llama-server.exe")
        browse = QPushButton("…")
        browse.setFixedWidth(30)
        row = QHBoxLayout()
        row.addWidget(edit, stretch=1)
        row.addWidget(browse)
        container = QWidget()
        container.setLayout(row)
        form.addRow("llama-server:", container)
        layout.addLayout(form)

        def _browse():
            p, _ = QFileDialog.getOpenFileName(dlg, "Seleccionar llama-server.exe", str(Path(model.backend.llama_server_path).parent if model.backend.llama_server_path else self._command_builder._server_path.parent), "Executable (*.exe);;All (*)")
            if p:
                edit.setText(p)

        browse.clicked.connect(_browse)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        clear_btn = QPushButton("Usar global")
        clear_btn.setToolTip("Borrar custom y volver al global de config/app.yaml")
        clear_btn.setStyleSheet("background-color: #2a2a3a; color: #a0a0b8; border: 1px solid #3a3a5a; border-radius: 6px; padding: 4px 8px;")
        def _clear():
            edit.setText("")
        clear_btn.clicked.connect(_clear)
        btns.addButton(clear_btn, QDialogButtonBox.ButtonRole.ActionRole)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_path = edit.text().strip()
        # Validar si no vacío
        if new_path:
            p = Path(new_path)
            # Resolver relativo a modelo o global
            if not p.is_absolute():
                p = (model.directory / p).resolve()
                if not p.is_file():
                    p = (self._command_builder._server_path.parent / Path(new_path)).resolve()
            if not p.is_file():
                QMessageBox.warning(self, "No encontrado", f"El archivo no existe:\n{p}\n\nSe guardará igual, pero el modelo no iniciará hasta que el archivo exista.")
        ok = self._model_manager.save_backend_path(model, new_path if new_path else None)
        if ok:
            msg = f"Runtime guardado para {model.name}: {new_path or 'global'}"
            self._log_viewer.append_line(f"[System] {msg}")
            self._status_bar.setText(msg)
            self._status_bar.setStyleSheet("color: #4caf50; font-size: 10px; background: transparent; border: none; font-weight: bold;")
            self._refresh_models()
        else:
            QMessageBox.warning(self, "Error", "No se pudo guardar el runtime.")

    def _refresh_models(self) -> None:
        running_map: dict[str, tuple[ModelStatus, int | None]] = {}
        for m in self._model_manager.models:
            if m.status in (ModelStatus.RUNNING, ModelStatus.STARTING):
                running_map[m.name] = (m.status, m.pid)

        self._model_manager.scan()

        for model in self._model_manager.models:
            if model.name in running_map:
                status, pid = running_map[model.name]
                model.status = status
                model.pid = pid

        for card in list(self._model_cards.values()) + list(self._unconfigured_cards.values()):
            card.setParent(None)
            card.deleteLater()
        self._model_cards.clear()
        self._unconfigured_cards.clear()

        for model in self._model_manager.models:
            card = ModelCard(model=model)
            card.launch_clicked.connect(self._launch_model)
            card.stop_clicked.connect(self._stop_model)
            card.variant_changed.connect(self._on_variant_changed)
            card.edit_variant_profile.connect(self._on_edit_variant_profile)
            card.edit_backend_requested.connect(self._on_edit_backend)
            card.copy_command_clicked.connect(self._on_copy_command)
            card.dry_run_clicked.connect(self._on_dry_run)
            self._model_cards[model.name] = card
            self._models_layout.addWidget(card)

        for folder, gguf_files in self._model_manager.unconfigured_folders:
            card = ModelCard(unconfigured=(folder, gguf_files))
            card.create_config_clicked.connect(self._create_config)
            self._unconfigured_cards[folder.name] = card
            self._models_layout.addWidget(card)

        if not self._model_manager.models and not self._model_manager.unconfigured_folders:
            empty = QLabel("No models found.\nAñade carpetas con GGUF a models/ y usa ↻ Recargar.")
            empty.setStyleSheet("color: #6a6a7a; padding: 24px; font-size: 13px; background: #1a1a2a; border: 1px dashed #2a2a3a; border-radius: 10px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._models_layout.addWidget(empty)

        total = len(self._model_manager.models)
        unc = len(self._model_manager.unconfigured_folders)
        self._count_label.setText(f"{total} configurados" + (f" • {unc} nuevos" if unc else ""))
        msg = f"Configs recargadas: {total} modelo(s)"
        if unc:
            msg += f", {unc} sin configurar"
        mtp_count = sum(1 for m in self._model_manager.models if getattr(m, "has_mtp_available", False) or getattr(m, "has_mtp_configured", False) or getattr(m, "mtp_enabled", False))
        if mtp_count:
            msg += f" • MTP en {mtp_count}"
        # Contar perfiles por variante
        custom = sum(len(getattr(m, "variant_profiles", {})) for m in self._model_manager.models)
        if custom:
            msg += f" • {custom} perfil(es) por variante"
        self._status_bar.setText(msg)
        self._status_bar.setStyleSheet("color: #8a8aaa; font-size: 10px; background: transparent; border: none;")
        self._log_viewer.append_line(f"[System] {msg} (F5)")
        for m in self._model_manager.models:
            try:
                mtp_txt, _ = m.mtp_status_label() if hasattr(m, "mtp_status_label") else ("MTP: ?", "")
                var_info = f" variantes={len(getattr(m, 'available_main_files', []))}" if getattr(m, "available_main_files", []) else ""
                custom_info = f" perfiles={len(getattr(m, 'variant_profiles', {}))}" if getattr(m, "variant_profiles", {}) else ""
                self._log_viewer.append_line(f"  - {m.name}: {mtp_txt} | {Path(m.model.file).name}{var_info}{custom_info} | {m.health.value}")
            except Exception:
                pass

    def _launch_model(self, name: str) -> None:
        model = self._model_manager.get_by_name(name)
        if model is None:
            return
        # Validar con perfil efectivo de la variante seleccionada (per-variante YAML o legacy)
        if hasattr(model, "get_effective_model"):
            eff = model.get_effective_model(model.model.file)
        elif hasattr(model, "get_for_variant"):
            eff = model.get_for_variant(model.model.file)
        else:
            eff = model
        if eff.check_health() != ModelHealth.READY:
            QMessageBox.warning(self, "No se puede iniciar", f"Modelo no listo.\nEstado: {eff.health.value}\nArchivo: {eff.model.file}")
            return
        running = self._model_manager.get_running()
        if running:
            names = ", ".join(m.name for m in running)
            QMessageBox.warning(self, "Modelo en ejecución", f"Detén primero:\n{names}")
            return
        port_conflict = self._model_manager.get_by_port(eff.server.port)
        if port_conflict and port_conflict.name != name:
            QMessageBox.warning(self, "Puerto en uso", f"Puerto {eff.server.port} en uso por {port_conflict.name}.")
            return
        # Mostrar qué perfil se usa
        is_per_variant = bool(getattr(model, "variant_yaml_paths", {}).get(model.model.file) or getattr(model, "variant_yaml_paths", {}))
        has_profile = model.has_variant_profile(model.model.file) if hasattr(model, "has_variant_profile") else False
        if has_profile or is_per_variant:
            # Verificar si hay YAML per-variante específico
            yaml_path = model.get_variant_yaml_path(model.model.file) if hasattr(model, "get_variant_yaml_path") else None
            if yaml_path and yaml_path.name != "model.yaml":
                self._log_viewer.append_line(f"[System] Lanzando {name} [{Path(model.model.file).name}] con YAML per-variante {yaml_path.name}")
            elif has_profile:
                self._log_viewer.append_line(f"[System] Lanzando {name} [{Path(model.model.file).name}] con perfil custom")
        self._log_viewer.clear()
        self._log_viewer.append_line(f"[System] Lanzando {name} — variante {Path(model.model.file).name} — MTP {eff.mtp_status_label()[0] if hasattr(eff, 'mtp_status_label') else ''}")
        # Mostrar comando final (related to #2)
        try:
            cmd = self._command_builder.build(eff)
            cmd_str = self._format_command(cmd)
            self._log_viewer.append_line(f"[CMD] {cmd_str}")
            self._log_viewer.append_line(f"[CMD] Variante: {Path(eff.model.file).name} | {len(cmd)} args | {eff.server.host}:{eff.server.port}")
        except Exception as e:
            self._log_viewer.append_line(f"[CMD] (error al construir comando: {e})")
        self._process_manager.start(model)  # pasa original, ProcessManager aplicará perfil internamente
        self._update_card(name)

    def _format_command(self, cmd: list[str]) -> str:
        """Formatea lista de args a string copiable para consola Windows."""
        parts: list[str] = []
        for c in cmd:
            if " " in c or '"' in c or "'" in c:
                # escapar comillas internas
                esc = c.replace('"', '\\"')
                parts.append(f'"{esc}"')
            else:
                parts.append(c)
        return " ".join(parts)

    def _on_copy_command(self, name: str) -> None:
        model = self._model_manager.get_by_name(name)
        if model is None:
            return
        if hasattr(model, "get_effective_model"):
            eff = model.get_effective_model(model.model.file)
        elif hasattr(model, "has_variant_profile") and model.has_variant_profile(model.model.file):
            eff = model.get_for_variant(model.model.file)
        else:
            eff = model
        try:
            cmd = self._command_builder.build(eff)
            cmd_str = self._format_command(cmd)
            QApplication.clipboard().setText(cmd_str)
            self._log_viewer.append_line(f"[CMD] {cmd_str}")
            self._log_viewer.append_line(f"[CMD] Copiado al portapapeles — variante {Path(eff.model.file).name} — {eff.server.host}:{eff.server.port}")
            self._status_bar.setText(f"[CMD] Copiado: {Path(eff.model.file).name}")
            self._status_bar.setStyleSheet("color: #4caf50; font-size: 10px; background: transparent; border: none; font-weight: bold;")
            QMessageBox.information(self, "Comando copiado", f"Comando de {name} copiado al portapapeles:\n\n{cmd_str[:800]}{'...' if len(cmd_str) > 800 else ''}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo construir el comando:\n{e}")

    def _on_dry_run(self, name: str) -> None:
        model = self._model_manager.get_by_name(name)
        if model is None:
            return
        if hasattr(model, "get_effective_model"):
            eff = model.get_effective_model(model.model.file)
        elif hasattr(model, "has_variant_profile") and model.has_variant_profile(model.model.file):
            eff = model.get_for_variant(model.model.file)
        else:
            eff = model
        try:
            cmd = self._command_builder.build(eff)
            cmd_str = self._format_command(cmd)
            self._log_viewer.append_line(f"[DRY-RUN] {name} — variante {Path(eff.model.file).name}")
            self._log_viewer.append_line(f"[DRY-RUN] {cmd_str}")
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Dry run — {name} [{Path(eff.model.file).name}]")
            dlg.setMinimumSize(720, 380)
            layout = QVBoxLayout(dlg)
            info = QLabel(
                f"Modelo: <b>{name}</b> — variante <code>{Path(eff.model.file).name}</code><br>"
                f"Servidor: <code>{eff.server.host}:{eff.server.port}</code> — alias <code>{eff.server.alias}</code><br>"
                f"Este es el comando <b>exacto</b> que se ejecutaría al hacer <b>Launch</b> (no inicia el modelo)."
            )
            info.setStyleSheet("color: #a0a0b8; font-size: 10px; background: transparent; border: none;")
            info.setWordWrap(True)
            layout.addWidget(info)
            edit = QTextEdit()
            edit.setReadOnly(True)
            edit.setPlainText(cmd_str)
            edit.setStyleSheet("background-color: #1e1e2e; color: #e0e0e0; border: 1px solid #2d2d44; border-radius: 6px; font-family: Consolas, monospace; font-size: 9px;")
            layout.addWidget(edit)
            btns = QDialogButtonBox()
            copy_btn = QPushButton("⧉ Copiar")
            copy_btn.setToolTip("Copiar comando al portapapeles")
            launch_btn = QPushButton("▶ Launch")
            launch_btn.setToolTip("Cerrar este diálogo e iniciar el modelo")
            launch_btn.setStyleSheet("background-color: #2a4a3a; color: #81c784; border: 1px solid #3a6a4a; border-radius: 6px; padding: 6px 12px; font-weight: bold;")
            close_btn = QPushButton("Cerrar")
            btns.addButton(copy_btn, QDialogButtonBox.ButtonRole.ActionRole)
            btns.addButton(launch_btn, QDialogButtonBox.ButtonRole.ActionRole)
            btns.addButton(close_btn, QDialogButtonBox.ButtonRole.RejectRole)
            def _copy():
                QApplication.clipboard().setText(cmd_str)
                self._log_viewer.append_line(f"[DRY-RUN] Copiado: {Path(eff.model.file).name}")
                self._status_bar.setText(f"[DRY-RUN] Copiado: {Path(eff.model.file).name}")
                self._status_bar.setStyleSheet("color: #4caf50; font-size: 10px; background: transparent; border: none; font-weight: bold;")
            copy_btn.clicked.connect(_copy)
            close_btn.clicked.connect(dlg.reject)
            def _launch():
                dlg.accept()
                self._launch_model(name)
            launch_btn.clicked.connect(_launch)
            layout.addWidget(btns)
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo construir el comando:\n{e}")

    def _stop_model(self, name: str) -> None:
        self._log_viewer.append_line(f"[System] Deteniendo {name}…")
        self._process_manager.stop()

    def _create_config(self, folder_path: str, gguf_files: list[str]) -> None:
        folder = Path(folder_path)
        # Todos los modelos usan 18765 por defecto a menos que se especifique lo contrario
        port = 18765
        port, ok = QInputDialog.getInt(self, "Puerto para nuevo modelo", f"Puerto para {folder.name}:", port, 1024, 65535)
        if not ok:
            return
        self._model_manager.create_config_for_folder(folder, gguf_files, port)
        self._refresh_models()

    def _update_card(self, name: str) -> None:
        card = self._model_cards.get(name)
        if card:
            card.refresh_status()

    def _update_all_cards(self) -> None:
        for card in self._model_cards.values():
            card.refresh_status()

    @Slot(int)
    def _on_process_started(self, pid: int) -> None:
        self._status_bar.setText(f"● Starting (PID {pid})…")
        self._status_bar.setStyleSheet("color: #ffb74d; font-size: 10px; background: transparent; border: none; font-weight: bold;")
        self._live_dot.setText("◐ STARTING")
        self._live_dot.setStyleSheet("color: #ffb74d; background: #2a2a1a; border: 1px solid #5a4a1a; border-radius: 10px; padding: 2px 8px; font-size: 9px; font-weight: 700;")
        self._update_all_cards()

    @Slot(int)
    def _on_process_ready(self, pid: int) -> None:
        self._status_bar.setText(f"● Running (PID {pid}) ✓")
        self._status_bar.setStyleSheet("color: #4caf50; font-size: 10px; background: transparent; border: none; font-weight: bold;")
        self._live_dot.setText("● RUNNING")
        self._live_dot.setStyleSheet("color: #4caf50; background: #1a2a1a; border: 1px solid #2a5a3a; border-radius: 10px; padding: 2px 8px; font-size: 9px; font-weight: 700;")
        self._log_viewer.append_line(f"[System] ✓ Modelo listo (PID {pid})")
        self._update_all_cards()

    @Slot()
    def _on_process_stopped(self) -> None:
        has_error = any(m.status == ModelStatus.ERROR for m in self._model_manager.models)
        if has_error:
            self._status_bar.setText("✖ Error")
            self._status_bar.setStyleSheet("color: #f44336; font-size: 10px; background: transparent; border: none; font-weight: bold;")
            self._live_dot.setText("● ERROR")
            self._live_dot.setStyleSheet("color: #f44336; background: #2a1a1a; border: 1px solid #5a2a2a; border-radius: 10px; padding: 2px 8px; font-size: 9px; font-weight: 700;")
        else:
            self._status_bar.setText("○ Stopped")
            self._status_bar.setStyleSheet("color: #8a8aaa; font-size: 10px; background: transparent; border: none;")
            self._live_dot.setText("● IDLE")
            self._live_dot.setStyleSheet("color: #8a8aaa; background: #1a1a2a; border: 1px solid #2a2a3a; border-radius: 10px; padding: 2px 8px; font-size: 9px; font-weight: 700;")
            self._log_viewer.append_line("[System] Modelo detenido")
        self._update_all_cards()

    @Slot(str)
    def _on_process_error(self, error: str) -> None:
        self._status_bar.setText("✖ Error")
        self._status_bar.setStyleSheet("color: #f44336; font-size: 10px; background: transparent; border: none; font-weight: bold;")
        self._live_dot.setText("● ERROR")
        self._live_dot.setStyleSheet("color: #f44336; background: #2a1a1a; border: 1px solid #5a2a2a; border-radius: 10px; padding: 2px 8px; font-size: 9px; font-weight: 700;")
        self._log_viewer.append_line(f"ERROR: {error}")
        self._update_all_cards()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(server_path=self._command_builder._server_path, models_dir=self._model_manager._models_dir, parent=self)
        dialog.settings_saved.connect(self._apply_settings)
        dialog.exec()

    @Slot(Path, Path)
    def _apply_settings(self, server_path, models_dir) -> None:
        self._command_builder = CommandBuilder(server_path)
        self._process_manager = ProcessManager(self._command_builder, self._app_config.get("logs_directory", Path("./logs")))
        self._model_manager = ModelManager(models_dir)
        self._connect_signals()
        self._refresh_models()

