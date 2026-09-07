from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.core.command_builder import CommandBuilder
from app.core.config_loader import load_app_config
from app.core.model_manager import ModelManager
from app.core.process_manager import ProcessManager
from app.gui.main_window import MainWindow


def _exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _find_config(exe_base: Path) -> Path:
    candidates = [
        exe_base / "config" / "app.yaml",
        exe_base / "_internal" / "config" / "app.yaml",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return candidates[0]


def _resolve_path(value: str, base: Path) -> Path:
    p = Path(value)
    if not p.is_absolute():
        p = base / p
    return p.resolve()


def main() -> None:
    exe_base = _exe_dir()
    config_path = _find_config(exe_base)

    if config_path.is_file():
        app_config = load_app_config(config_path)
    else:
        app_config = {}

    server_path = _resolve_path(
        app_config.get("llama_server_path", "./llama.cpp/llama-server.exe"),
        exe_base,
    )
    models_dir = _resolve_path(
        app_config.get("models_directory", "./models"),
        exe_base,
    )
    logs_dir = _resolve_path(
        app_config.get("logs_directory", "./logs"),
        exe_base,
    )
    logs_dir.mkdir(parents=True, exist_ok=True)

    cmd_builder = CommandBuilder(server_path)
    model_manager = ModelManager(models_dir)
    process_manager = ProcessManager(cmd_builder, logs_dir)

    qt_app = QApplication(sys.argv)
    # No usar stylesheet global aquí: MainWindow ya define "background-color: #1e1e1e"
    # y un QSS global tipo "QWidget { ... }" interfiere con el cálculo de sizeHint
    # dentro de QScrollArea (comprimía las tarjetas a 120px).

    window = MainWindow(model_manager, process_manager, cmd_builder, app_config)
    window.show()

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
