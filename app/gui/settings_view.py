from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    settings_saved = Signal(Path, Path)

    def __init__(
        self,
        server_path: Path,
        models_dir: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self._server_path = server_path
        self._models_dir = models_dir
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("llama-server path:"))
        srv_row = QHBoxLayout()
        self._server_edit = QLineEdit(str(self._server_path))
        srv_row.addWidget(self._server_edit)
        srv_btn = QPushButton("Browse")
        srv_btn.clicked.connect(self._browse_server)
        srv_row.addWidget(srv_btn)
        layout.addLayout(srv_row)

        layout.addWidget(QLabel("Models directory:"))
        mdl_row = QHBoxLayout()
        self._models_edit = QLineEdit(str(self._models_dir))
        mdl_row.addWidget(self._models_edit)
        mdl_btn = QPushButton("Browse")
        mdl_btn.clicked.connect(self._browse_models)
        mdl_row.addWidget(mdl_btn)
        layout.addLayout(mdl_row)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _browse_server(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select llama-server", "", "Executable (*.exe);;All (*)"
        )
        if path:
            self._server_edit.setText(path)

    def _browse_models(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select models directory")
        if path:
            self._models_edit.setText(path)

    def _save(self) -> None:
        self.settings_saved.emit(
            Path(self._server_edit.text()),
            Path(self._models_edit.text()),
        )
        self.accept()
