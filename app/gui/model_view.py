from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models.model_definition import ModelDefinition, ModelHealth, ModelStatus


def _style_card(frame: QFrame, bg: str, border: str, hover_border: str | None = None) -> None:
    frame.setObjectName("ModelCard")
    hover = hover_border or border
    frame.setStyleSheet(
        f"#ModelCard {{ background-color: {bg}; border: 1px solid {border}; "
        f"border-radius: 12px; padding: 12px; }}"
        f"#ModelCard:hover {{ border: 1px solid {hover}; background-color: {bg}; }}"
    )


def _set_label(label: QLabel, text: str, size: int = 11, bold: bool = False) -> None:
    label.setText(text)
    font = label.font()
    font.setPointSize(size)
    font.setBold(bold)
    label.setFont(font)
    label.setStyleSheet("color: #e8e8e8; background-color: transparent; border: none;")
    label.setWordWrap(True)


def _set_label_dim(label: QLabel, text: str, size: int = 11) -> None:
    label.setText(text)
    font = label.font()
    font.setPointSize(size)
    label.setFont(font)
    label.setStyleSheet("color: #a0a0a0; background-color: transparent; border: none;")
    label.setWordWrap(True)


def _set_label_info(label: QLabel, text: str) -> None:
    label.setText(text)
    font = label.font()
    font.setPointSize(10)
    label.setFont(font)
    label.setStyleSheet("color: #b8b8b8; background-color: transparent; border: none;")
    label.setWordWrap(True)


def _set_status(label: QLabel, text: str, color: str) -> None:
    label.setText(text)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    label.setStyleSheet(f"color: {color}; background-color: transparent; border: none;")


class VariantProfileDialog(QDialog):
    """Editor simple para perfil por variante.

    Permite editar hardware.context_size, batch_size, cache type, speculative, etc.
    Si se guarda vacío, elimina el perfil (vuelve a heredar del base).
    """

    def __init__(self, model: ModelDefinition, variant: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._variant = variant
        # Usar YAML per-variante si existe, sino perfil legacy
        if hasattr(model, "get_effective_model"):
            eff = model.get_effective_model(variant)
        else:
            eff = model.get_for_variant(variant) if model.has_variant_profile(variant) else model.get_for_variant(variant)
        # Si no hay perfil, eff es copia con base; si hay, eff tiene overrides
        # Para mostrar valores actuales efectivos:
        self._eff = eff
        self.setWindowTitle(f"Perfil variante — {Path(variant).name}")
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        info = QLabel(f"Variante: <b>{self._variant}</b><br>Deja vacío para heredar del perfil base.")
        info.setStyleSheet("color: #a0a0a0; background: transparent; border: none; font-size: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(8)

        # Context size
        self._ctx_spin = QSpinBox()
        self._ctx_spin.setRange(0, 1000000)
        self._ctx_spin.setSingleStep(1024)
        self._ctx_spin.setValue(self._eff.hardware.context_size)
        self._ctx_spin.setSpecialValueText("heredar")
        self._ctx_spin.setToolTip("0 = heredar del base")
        form.addRow("Context size:", self._ctx_spin)

        # Batch size
        self._batch_spin = QSpinBox()
        self._batch_spin.setRange(0, 1000000)
        self._batch_spin.setSingleStep(256)
        self._batch_spin.setValue(self._eff.hardware.batch_size)
        self._batch_spin.setSpecialValueText("heredar")
        form.addRow("Batch size:", self._batch_spin)

        # Threads
        self._threads_spin = QSpinBox()
        self._threads_spin.setRange(0, 128)
        self._threads_spin.setValue(self._eff.hardware.threads)
        self._threads_spin.setSpecialValueText("heredar (auto)")
        form.addRow("Threads:", self._threads_spin)

        # Cache type
        self._cache_k_edit = QLineEdit(self._eff.cache.type_k)
        self._cache_k_edit.setPlaceholderText("heredar (ej: q8_0, q4_0, q4_0)")
        form.addRow("Cache K:", self._cache_k_edit)

        self._cache_v_edit = QLineEdit(self._eff.cache.type_v)
        self._cache_v_edit.setPlaceholderText("heredar")
        form.addRow("Cache V:", self._cache_v_edit)

        # Speculative
        self._spec_enabled_check = QSpinBox()
        # Usar checkbox simulado? Usaremos QSpinBox 0/1 para simplicidad, pero mejor usar checkbox
        from PySide6.QtWidgets import QCheckBox

        self._spec_check = QCheckBox("Habilitar speculative (MTP)")
        self._spec_check.setChecked(self._eff.speculative.enabled)
        form.addRow(self._spec_check)

        self._spec_type_edit = QLineEdit(self._eff.speculative.spec_type)
        self._spec_type_edit.setPlaceholderText("ej: draft-mtp")
        form.addRow("Spec type:", self._spec_type_edit)

        self._draft_n_spin = QSpinBox()
        self._draft_n_spin.setRange(0, 10)
        self._draft_n_spin.setValue(self._eff.speculative.draft_n_max)
        form.addRow("draft_n_max:", self._draft_n_spin)

        # Advanced: flash, reasoning, parallel
        from PySide6.QtWidgets import QCheckBox

        self._flash_check = QCheckBox("Flash Attention")
        self._flash_check.setChecked(self._eff.advanced.flash_attention)
        form.addRow(self._flash_check)

        self._reason_check = QCheckBox("Reasoning")
        self._reason_check.setChecked(self._eff.advanced.reasoning)
        form.addRow(self._reason_check)

        # Backend: llama_server_path por variante (per-model override)
        from PySide6.QtWidgets import QFileDialog

        self._llama_path_edit = QLineEdit(self._eff.backend.llama_server_path)
        self._llama_path_edit.setPlaceholderText("heredar (global: config/app.yaml)")
        self._llama_path_edit.setToolTip("Ruta al exe de llama-server para esta variante.\nVacío = usa global de config/app.yaml\nEj: D:/llama.cpp/versions/b4567/llama-server.exe")
        llama_row = QHBoxLayout()
        llama_row.addWidget(self._llama_path_edit, stretch=1)
        browse_btn = QPushButton("…")
        browse_btn.setFixedWidth(28)
        browse_btn.setToolTip("Buscar llama-server.exe")
        def _browse():
            p, _ = QFileDialog.getOpenFileName(self, "Seleccionar llama-server.exe", "", "Executable (*.exe);;All (*)")
            if p:
                self._llama_path_edit.setText(p)
        browse_btn.clicked.connect(_browse)
        llama_row.addWidget(browse_btn)
        llama_container = QWidget()
        llama_container.setLayout(llama_row)
        form.addRow("llama-server:", llama_container)

        layout.addLayout(form)

        # Botones
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        # Añadir botón para eliminar perfil
        del_btn = QPushButton("Eliminar perfil (heredar)")
        del_btn.setStyleSheet("background-color: #5a2a2a; color: #e0e0e0; border: 1px solid #7a3a3a; border-radius: 4px; padding: 4px 8px;")
        del_btn.clicked.connect(self._on_delete)
        btns.addButton(del_btn, QDialogButtonBox.ButtonRole.ActionRole)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_delete(self) -> None:
        self._delete_requested = True
        self.accept()

    def get_overrides(self) -> dict | None:
        # Si se pidió eliminar, retornar None
        if getattr(self, "_delete_requested", False):
            return None
        # Construir dict solo con valores que difieren del base o que el usuario quiere override
        # Para simplificar, siempre guardar hardware/cache/spec si el usuario cambió algo
        base = self._model
        eff = self._eff
        overrides: dict = {}
        hw = {}
        if self._ctx_spin.value() != base.hardware.context_size:
            hw["context_size"] = self._ctx_spin.value()
        if self._batch_spin.value() != base.hardware.batch_size:
            hw["batch_size"] = self._batch_spin.value()
        if self._threads_spin.value() != base.hardware.threads:
            hw["threads"] = self._threads_spin.value()
        if hw:
            overrides["hardware"] = hw

        cache = {}
        if self._cache_k_edit.text().strip() != base.cache.type_k:
            cache["type_k"] = self._cache_k_edit.text().strip()
        if self._cache_v_edit.text().strip() != base.cache.type_v:
            cache["type_v"] = self._cache_v_edit.text().strip()
        if cache:
            overrides["cache"] = cache

        spec = {}
        if self._spec_check.isChecked() != base.speculative.enabled:
            spec["enabled"] = self._spec_check.isChecked()
        if self._spec_type_edit.text().strip() != base.speculative.spec_type:
            spec["spec_type"] = self._spec_type_edit.text().strip()
        if self._draft_n_spin.value() != base.speculative.draft_n_max:
            spec["draft_n_max"] = self._draft_n_spin.value()
        if spec:
            overrides["speculative"] = spec

        adv = {}
        if self._flash_check.isChecked() != base.advanced.flash_attention:
            adv["flash_attention"] = self._flash_check.isChecked()
        if self._reason_check.isChecked() != base.advanced.reasoning:
            adv["reasoning"] = self._reason_check.isChecked()
        if adv:
            overrides["advanced"] = adv

        # Backend: llama_server_path por variante
        llama_path = self._llama_path_edit.text().strip()
        base_path = (base.backend.llama_server_path or "").strip()
        if llama_path != base_path:
            # Solo guardar si es no vacío o si quiere forzar heredar global (vacío) cuando base tenía custom
            if llama_path:
                overrides["backend"] = {"llama_server_path": llama_path}
            else:
                # Usuario borró para heredar → si base tenía custom, guardar vacío para indicar override a global
                # En update_variant_profile, vacío se maneja como heredar (no guardar)
                # Para variante, guardar vacío significa eliminar override
                # No hacemos nada, se manejará como no override
                pass

        # Si overrides vacío, considerar que no hay cambios → eliminar
        if not overrides:
            return {}
        return overrides


class ModelCard(QFrame):
    launch_clicked = Signal(str)
    stop_clicked = Signal(str)
    create_config_clicked = Signal(str, list)
    variant_changed = Signal(str, str)  # name, new_file
    edit_variant_profile = Signal(str, str)  # name, variant
    edit_backend_requested = Signal(str)  # name
    copy_command_clicked = Signal(str)  # name
    dry_run_clicked = Signal(str)  # name
    open_browser_clicked = Signal(str)  # name

    def __init__(
        self,
        model: ModelDefinition | None = None,
        unconfigured: tuple | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._model = model
        self._unconfigured = unconfigured
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setMinimumHeight(260)
        from PySide6.QtWidgets import QSizePolicy

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        self.setMouseTracking(True)
        self._init_ui()
        self._apply_style()

    def _apply_style(self) -> None:
        if self._model and self._model.health == ModelHealth.MISSING_MODEL:
            bg, border, hover = "#2d1e1e", "#5c3333", "#7a4444"
        elif self._unconfigured:
            bg, border, hover = "#1e2d2d", "#335c5c", "#4a7a7a"
        elif self._model and (
            getattr(self._model, "has_variant_profile", lambda x: False)(self._model.model.file)
            or (getattr(self._model, "get_variant_yaml_path", lambda x: None)(self._model.model.file) is not None)
        ):
            bg, border, hover = "#1e2a3a", "#3a5a8a", "#4a6a9a"
        else:
            bg, border, hover = "#1e1e2e", "#2d2d44", "#3a3a5a"
        _style_card(self, bg, border, hover)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)
        if self._model:
            self._init_model_ui(layout)
        elif self._unconfigured:
            self._init_unconfigured_ui(layout)

    def _init_model_ui(self, layout: QVBoxLayout) -> None:
        m = self._model
        assert m is not None

        # Header con nombre y alias
        header_row = QHBoxLayout()
        self._name_label = QLabel()
        _set_label(self._name_label, m.name, 13, bold=True)
        header_row.addWidget(self._name_label)
        header_row.addStretch()
        # Alias badge
        if m.server.alias:
            alias_lbl = QLabel(f"@{m.server.alias}")
            alias_lbl.setStyleSheet("color: #7a7aff; background-color: #2a2a4a; border: 1px solid #3a3a6a; border-radius: 8px; padding: 2px 6px; font-size: 9px;")
            header_row.addWidget(alias_lbl)
        layout.addLayout(header_row)

        self._desc_label = QLabel()
        if m.description:
            _set_label_dim(self._desc_label, m.description)
            layout.addWidget(self._desc_label)

        # Selector de variante
        self._variant_combo: QComboBox | None = None
        self._variant_profile_btn: QPushButton | None = None
        variants = m.variants_display() if hasattr(m, "variants_display") else []
        is_multi = getattr(m, "is_multivariant", False) or len(getattr(m, "available_main_files", [])) > 1
        if is_multi and len(variants) > 1:
            var_row = QHBoxLayout()
            var_label = QLabel("Versión:")
            var_label.setStyleSheet("color: #a0a0a0; background: transparent; border: none; font-size: 10px; font-weight: bold;")
            var_label.setFixedWidth(55)
            var_row.addWidget(var_label)
            self._variant_combo = QComboBox()
            self._variant_combo.addItems(variants)
            idx = -1
            try:
                idx = variants.index(m.model.file)
            except ValueError:
                base = Path(m.model.file).name if m.model.file else ""
                for i, v in enumerate(variants):
                    if Path(v).name == base:
                        idx = i
                        break
                if idx == -1:
                    idx = 0
            self._variant_combo.setCurrentIndex(idx)
            if variants and idx >= 0 and idx < len(variants):
                selected = variants[idx]
                if selected != m.model.file and Path(selected).name == Path(m.model.file).name:
                    m.model.file = selected
            self._variant_combo.setStyleSheet(
                "QComboBox { background-color: #2a2a3a; color: #e0e0e0; border: 1px solid #3a3a5a; "
                "border-radius: 6px; padding: 4px 8px; font-size: 10px; }"
                "QComboBox::drop-down { border: none; width: 20px; }"
                "QComboBox QAbstractItemView { background-color: #1e1e2e; color: #e0e0e0; selection-background-color: #3a3a6a; border: 1px solid #3a3a5a; }"
                "QComboBox:disabled { background-color: #1a1a2a; color: #777; }"
            )
            self._variant_combo.setToolTip("Selecciona qué archivo GGUF cargar.\nCada variante puede tener su propio perfil de configuración.")
            self._variant_combo.currentTextChanged.connect(self._on_variant_changed)
            var_row.addWidget(self._variant_combo, stretch=1)
            count_lbl = QLabel(f"({len(variants)})")
            count_lbl.setStyleSheet("color: #777; background: transparent; border: none; font-size: 9px;")
            count_lbl.setToolTip(f"{len(variants)} versiones disponibles")
            var_row.addWidget(count_lbl)

            # Botón editar perfil por variante
            self._variant_profile_btn = QPushButton("⚙")
            self._variant_profile_btn.setFixedSize(28, 28)
            self._variant_profile_btn.setToolTip("Editar perfil de esta variante (context, batch, cache, MTP...)\nCada variante puede tener configuración propia.")
            self._variant_profile_btn.setStyleSheet(
                "QPushButton { background-color: #2a2a4a; color: #a0a0ff; border: 1px solid #3a3a6a; border-radius: 6px; font-size: 12px; }"
                "QPushButton:hover { background-color: #3a3a6a; color: #fff; border-color: #5a5aaa; }"
                "QPushButton:pressed { background-color: #1a1a3a; }"
            )
            self._variant_profile_btn.clicked.connect(self._on_edit_profile)
            var_row.addWidget(self._variant_profile_btn)

            layout.addLayout(var_row)
            # Indicador de perfil custom para variante actual
            self._profile_indicator = QLabel()
            self._update_profile_indicator()
            layout.addWidget(self._profile_indicator)
        else:
            self._profile_indicator = None

        # MTP + Vision row
        self._mtp_label = QLabel()
        mtp_text, mtp_color = m.mtp_status_label() if hasattr(m, "mtp_status_label") else ("MTP: --", "#888")
        _set_status(self._mtp_label, mtp_text, mtp_color)
        self._mtp_label.setStyleSheet(f"color: {mtp_color}; background-color: transparent; border: none; font-size: 10px; font-weight: bold; padding: 2px 0;")
        self._mtp_label.setToolTip(
            "MTP (Multi-Token Prediction):\n• Sí (activo): draft externo\n• Sí (integrado): nextn en GGUF\n• No: variante sin MTP (ej nomtp/)\n• Sí (desactivado): disponible pero spec off"
        )
        mtp_row = QHBoxLayout()
        mtp_row.setSpacing(8)
        # Icono MTP con fondo
        mtp_container = QWidget()
        mtp_container.setStyleSheet(f"background-color: {mtp_color}22; border: 1px solid {mtp_color}44; border-radius: 6px; padding: 1px;")
        mtp_layout = QHBoxLayout(mtp_container)
        mtp_layout.setContentsMargins(6, 2, 6, 2)
        mtp_layout.addWidget(self._mtp_label)
        mtp_row.addWidget(mtp_container)

        if m.capabilities.vision:
            vis_lbl = QLabel("● Vision")
            vis_lbl.setStyleSheet("color: #4fc3f7; background-color: #1e3a4a; border: 1px solid #2a5a6a; border-radius: 6px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
            vis_lbl.setToolTip("Soporte de visión habilitado")
            mtp_row.addWidget(vis_lbl)
        mtp_row.addStretch()
        if getattr(m, "available_draft_files", []):
            draft_info = QLabel(f"draft: {m.available_draft_files[0]}" if len(m.available_draft_files)==1 else f"drafts: {len(m.available_draft_files)}")
            draft_info.setStyleSheet("color: #888; background: transparent; border: none; font-size: 9px;")
            draft_info.setToolTip("Archivos draft/mtp: " + ", ".join(m.available_draft_files))
            mtp_row.addWidget(draft_info)
        layout.addLayout(mtp_row)

        # Backend runtime row (per-model llama version)
        self._backend_label = QLabel()
        self._backend_btn: QPushButton | None = None
        backend_row = QHBoxLayout()
        backend_row.setSpacing(6)
        # Determinar runtime efectivo para la variante actual (per-variante YAML o perfil)
        try:
            if hasattr(m, "get_effective_model"):
                eff_backend = m.get_effective_model(m.model.file).backend.llama_server_path
            elif hasattr(m, "get_for_variant") and m.has_variant_profile(m.model.file):
                eff_backend = m.get_for_variant(m.model.file).backend.llama_server_path
            else:
                eff_backend = m.backend.llama_server_path
            if not eff_backend and hasattr(m, "has_variant_profile") and m.has_variant_profile(m.model.file):
                eff_backend = m.backend.llama_server_path
            # Fallback si per-variante no tiene backend pero base sí
            if not eff_backend and hasattr(m, "get_variant_yaml_path") and m.get_variant_yaml_path(m.model.file):
                eff_backend = m.backend.llama_server_path
        except Exception:
            eff_backend = m.backend.llama_server_path
        if eff_backend and eff_backend.strip():
            backend_text = f"🖥 Runtime: {Path(eff_backend).name}"
            backend_color = "#7aaaff"
            backend_bg = "#1e2a4a"
            tip = f"Binario custom para este modelo:\n{eff_backend}\nClick ✎ para cambiar"
        else:
            backend_text = "🖥 Runtime: global"
            backend_color = "#888888"
            backend_bg = "#1a1a2a"
            tip = "Usa binario global de config/app.yaml\nClick ✎ para asignar uno custom a este modelo"
        _set_status(self._backend_label, backend_text, backend_color)
        self._backend_label.setStyleSheet(f"color: {backend_color}; background-color: {backend_bg}; border: 1px solid {backend_color}44; border-radius: 6px; padding: 2px 6px; font-size: 9px; font-weight: bold;")
        self._backend_label.setToolTip(tip)
        self._backend_label.setWordWrap(False)
        backend_row.addWidget(self._backend_label)

        self._backend_btn = QPushButton("✎")
        self._backend_btn.setFixedSize(28, 22)
        self._backend_btn.setToolTip("Cambiar binario llama-server para este modelo\nDeja vacío para volver al global")
        self._backend_btn.setStyleSheet(
            "QPushButton { background-color: #1e2a4a; color: #7aaaff; border: 1px solid #3a4a6a; border-radius: 6px; font-size: 10px; }"
            "QPushButton:hover { background-color: #2a3a5a; color: #fff; }"
        )
        self._backend_btn.clicked.connect(self._on_edit_backend)
        backend_row.addWidget(self._backend_btn)
        backend_row.addStretch()
        # Indicador de variante custom para backend
        has_custom_backend = (m.has_variant_profile(m.model.file) if hasattr(m, "has_variant_profile") else False) or (m.get_variant_yaml_path(m.model.file) is not None if hasattr(m, "get_variant_yaml_path") else False)
        if has_custom_backend and eff_backend:
            var_backend_lbl = QLabel("variante")
            var_backend_lbl.setStyleSheet("color: #7aaaff; background: transparent; border: none; font-size: 8px;")
            var_backend_lbl.setToolTip("Este runtime es específico de la variante seleccionada")
            backend_row.addWidget(var_backend_lbl)
        layout.addLayout(backend_row)

        # Info estético — grid con chips (reemplaza bloque de texto plano)
        self._info_container = QWidget()
        self._info_container.setStyleSheet("background-color: #141420; border: 1px solid #2a2a3a; border-radius: 8px;")
        self._info_layout = QVBoxLayout(self._info_container)
        self._info_layout.setContentsMargins(8, 8, 8, 8)
        self._info_layout.setSpacing(6)
        self._rebuild_info()
        layout.addWidget(self._info_container)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 6, 0, 0)
        btn_layout.addStretch()

        self._status_label = QLabel()
        btn_layout.addWidget(self._status_label)

        self._dry_run_btn = QPushButton("👁")
        self._dry_run_btn.setFixedSize(32, 32)
        self._dry_run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dry_run_btn.setToolTip("Ver comando — dry run sin iniciar el modelo\nMuestra el comando completo que se ejecutaría al hacer Launch (copiable)")
        self._dry_run_btn.setStyleSheet(
            "QPushButton { background-color: #2a2a1a; color: #ffb74d; border: 1px solid #5a4a2a; border-radius: 8px; font-size: 13px; }"
            "QPushButton:hover { background-color: #3a2a1a; color: #ffcc80; border-color: #8a6a3a; }"
            "QPushButton:pressed { background-color: #1a1a0a; }"
        )
        self._dry_run_btn.clicked.connect(self._on_dry_run)
        btn_layout.addWidget(self._dry_run_btn)

        self._open_browser_btn = QPushButton("🌐")
        self._open_browser_btn.setFixedSize(32, 32)
        self._open_browser_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_browser_btn.setToolTip("Abrir servidor en navegador")
        self._open_browser_btn.setStyleSheet(
            "QPushButton { background-color: #1a2a4a; color: #7aaaff; border: 1px solid #3a3a6a; border-radius: 8px; font-size: 13px; }"
            "QPushButton:hover { background-color: #2a3a6a; color: #fff; border-color: #5a6aaa; }"
            "QPushButton:pressed { background-color: #1a1a3a; }"
        )
        self._open_browser_btn.clicked.connect(self._on_open_browser)
        btn_layout.addWidget(self._open_browser_btn)

        self._action_btn = QPushButton()
        self._action_btn.setFixedHeight(32)
        self._action_btn.setFixedWidth(110)
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_btn.clicked.connect(self._on_action_clicked)
        btn_layout.addWidget(self._action_btn)

        layout.addLayout(btn_layout)
        self._update_state()
        self._refresh_mtp_label()

    def _init_unconfigured_ui(self, layout: QVBoxLayout) -> None:
        folder, gguf_files = self._unconfigured

        self._name_label = QLabel()
        _set_label(self._name_label, folder.name, 12, bold=True)
        layout.addWidget(self._name_label)

        self._desc_label = QLabel("No configuration found")
        font = self._desc_label.font()
        font.setPointSize(10)
        self._desc_label.setFont(font)
        self._desc_label.setStyleSheet(
            "color: #ffb74d; background-color: #2a2a1a; border: 1px solid #5a4a2a; border-radius: 6px; padding: 4px 6px;"
        )
        layout.addWidget(self._desc_label)

        files_text = f"GGUF files found: {len(gguf_files)}"
        for f in gguf_files[:5]:
            files_text += f"\n  • {f}"
        if len(gguf_files) > 5:
            files_text += f"\n  ... and {len(gguf_files) - 5} more"

        self._info_label = QLabel()
        _set_label_info(self._info_label, files_text)
        self._info_label.setStyleSheet("color: #b8b8b8; background-color: #1a2a1a; border: 1px solid #2a3a2a; border-radius: 6px; padding: 6px; font-size: 10px;")
        layout.addWidget(self._info_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._status_label = QLabel()
        _set_status(self._status_label, "No config", "#ffb74d")
        btn_layout.addWidget(self._status_label)

        self._action_btn = QPushButton("✚ Create config")
        self._action_btn.setFixedHeight(32)
        self._action_btn.setFixedWidth(130)
        self._action_btn.setStyleSheet(
            "QPushButton { background-color: #2a4a3a; color: #e0e0e0; border: 1px solid #3a6a4a; border-radius: 8px; font-weight: bold; }"
            "QPushButton:hover { background-color: #3a6a5a; border-color: #4a8a6a; }"
        )
        self._action_btn.clicked.connect(self._on_create_config)
        btn_layout.addWidget(self._action_btn)

        layout.addLayout(btn_layout)

    def _update_profile_indicator(self) -> None:
        if not hasattr(self, "_profile_indicator") or self._profile_indicator is None or not self._model:
            return
        m = self._model
        has_profile = m.has_variant_profile(m.model.file) if hasattr(m, "has_variant_profile") else False
        has_yaml = m.get_variant_yaml_path(m.model.file) is not None if hasattr(m, "get_variant_yaml_path") else False
        # Considerar per-variante YAML como perfil custom
        is_custom = has_profile or has_yaml
        if is_custom:
            self._profile_indicator.setText("⚙ Perfil custom activo para esta variante")
            self._profile_indicator.setStyleSheet("color: #7aaaff; background-color: #1e2a4a; border: 1px solid #3a4a6a; border-radius: 6px; padding: 3px 6px; font-size: 9px; font-weight: bold;")
            self._profile_indicator.setVisible(True)
            if hasattr(self, "_variant_profile_btn") and self._variant_profile_btn:
                self._variant_profile_btn.setStyleSheet(
                    "QPushButton { background-color: #3a4a8a; color: #fff; border: 1px solid #5a6aaa; border-radius: 6px; font-size: 12px; }"
                    "QPushButton:hover { background-color: #4a5aaa; }"
                )
        else:
            self._profile_indicator.setVisible(False)
            if hasattr(self, "_variant_profile_btn") and self._variant_profile_btn:
                self._variant_profile_btn.setStyleSheet(
                    "QPushButton { background-color: #2a2a4a; color: #a0a0ff; border: 1px solid #3a3a6a; border-radius: 6px; font-size: 12px; }"
                    "QPushButton:hover { background-color: #3a3a6a; color: #fff; border-color: #5a5aaa; }"
                )

    def _update_state(self) -> None:
        if not self._model:
            return
        m = self._model

        if hasattr(self, "_variant_combo") and self._variant_combo is not None:
            is_running = m.status in (ModelStatus.RUNNING, ModelStatus.STARTING)
            self._variant_combo.setEnabled(not is_running)
            if hasattr(self, "_variant_profile_btn") and self._variant_profile_btn:
                self._variant_profile_btn.setEnabled(not is_running)
            if hasattr(self, "_backend_btn") and self._backend_btn is not None:
                self._backend_btn.setEnabled(not is_running)
                if is_running:
                    self._backend_btn.setToolTip("No se puede cambiar runtime mientras el modelo está en ejecución")
                else:
                    self._backend_btn.setToolTip("Cambiar binario llama-server para este modelo")
            if is_running:
                self._variant_combo.setToolTip("No se puede cambiar versión mientras el modelo está en ejecución")
            else:
                self._variant_combo.setToolTip("Selecciona versión. Cada variante puede tener su propio perfil (⚙).")

        # Visibilidad del botón abrir navegador (solo RUNNING)
        if hasattr(self, "_open_browser_btn"):
            is_running_visible = m.status == ModelStatus.RUNNING
            self._open_browser_btn.setVisible(is_running_visible)
            if is_running_visible:
                try:
                    if hasattr(m, "get_effective_model"):
                        eff = m.get_effective_model(m.model.file)
                    else:
                        eff = m
                    host = eff.server.host or "127.0.0.1"
                    if host == "0.0.0.0":
                        host = "127.0.0.1"
                    url = f"http://{host}:{eff.server.port}"
                    self._open_browser_btn.setToolTip(f"Abrir {url} en navegador")
                except Exception:
                    self._open_browser_btn.setToolTip("Abrir servidor en navegador")

        # Estilo del botón según estado
        if m.status == ModelStatus.RUNNING:
            _set_status(self._status_label, "● Running", "#4caf50")
            self._action_btn.setText("⏹ Stop")
            self._action_btn.setStyleSheet(
                "QPushButton { background-color: #4a2a2a; color: #ff8a80; border: 1px solid #6a3a3a; border-radius: 8px; font-weight: bold; }"
                "QPushButton:hover { background-color: #6a3a3a; color: #fff; }"
            )
            self._action_btn.setVisible(True)
        elif m.status == ModelStatus.STARTING:
            _set_status(self._status_label, "◐ Starting...", "#ff9800")
            self._action_btn.setText("⏹ Stop")
            self._action_btn.setStyleSheet(
                "QPushButton { background-color: #4a3a1a; color: #ffb74d; border: 1px solid #6a4a1a; border-radius: 8px; font-weight: bold; }"
                "QPushButton:hover { background-color: #6a4a2a; }"
            )
            self._action_btn.setVisible(True)
        elif m.health == ModelHealth.MISSING_MODEL:
            _set_status(self._status_label, "✖ Model missing", "#f44336")
            self._action_btn.setVisible(False)
        elif m.health == ModelHealth.MISSING_VISION:
            _set_status(self._status_label, "✖ Vision missing", "#f44336")
            self._action_btn.setVisible(False)
        elif m.health == ModelHealth.MISSING_DRAFT:
            _set_status(self._status_label, "✖ Draft missing", "#f44336")
            self._action_btn.setVisible(False)
        elif m.status == ModelStatus.ERROR:
            _set_status(self._status_label, "✖ Error", "#f44336")
            self._action_btn.setText("↻ Retry")
            self._action_btn.setStyleSheet(
                "QPushButton { background-color: #4a2a2a; color: #ff8a80; border: 1px solid #6a3a3a; border-radius: 8px; font-weight: bold; }"
                "QPushButton:hover { background-color: #6a3a3a; }"
            )
            self._action_btn.setVisible(True)
        else:
            _set_status(self._status_label, "○ Ready", "#888888")
            self._action_btn.setText("▶ Launch")
            self._action_btn.setStyleSheet(
                "QPushButton { background-color: #2a4a3a; color: #81c784; border: 1px solid #3a6a4a; border-radius: 8px; font-weight: bold; font-size: 11px; }"
                "QPushButton:hover { background-color: #3a6a4a; color: #fff; border-color: #4caf50; }"
                "QPushButton:pressed { background-color: #1e3a2a; }"
            )
            self._action_btn.setVisible(True)

    def _on_action_clicked(self) -> None:
        if not self._model:
            return
        if self._model.status in (ModelStatus.RUNNING, ModelStatus.STARTING):
            self.stop_clicked.emit(self._model.name)
        else:
            self.launch_clicked.emit(self._model.name)

    def _on_variant_changed(self, new_file: str) -> None:
        if not self._model or not new_file:
            return
        old_file = self._model.model.file
        if new_file == old_file:
            return
        self._model.model.file = new_file
        self._model.check_health()
        self._rebuild_info()
        self._update_profile_indicator()
        self._update_backend_label()
        self._refresh_mtp_label()
        self._update_state()
        self._apply_style()
        self.variant_changed.emit(self._model.name, new_file)

    def _on_edit_profile(self) -> None:
        if not self._model:
            return
        variant = self._model.model.file
        self.edit_variant_profile.emit(self._model.name, variant)

    def _on_edit_backend(self) -> None:
        if not self._model:
            return
        self.edit_backend_requested.emit(self._model.name)

    def _on_copy_command(self) -> None:
        if not self._model:
            return
        self.copy_command_clicked.emit(self._model.name)

    def _on_dry_run(self) -> None:
        if not self._model:
            return
        self.dry_run_clicked.emit(self._model.name)

    def _on_open_browser(self) -> None:
        if not self._model:
            return
        self.open_browser_clicked.emit(self._model.name)

    def _update_backend_label(self) -> None:
        if not hasattr(self, "_backend_label") or self._backend_label is None or not self._model:
            return
        m = self._model
        try:
            if hasattr(m, "get_effective_model"):
                eff_backend = m.get_effective_model(m.model.file).backend.llama_server_path
            elif hasattr(m, "get_for_variant") and m.has_variant_profile(m.model.file):
                eff_backend = m.get_for_variant(m.model.file).backend.llama_server_path
            else:
                eff_backend = m.backend.llama_server_path
            if not eff_backend and hasattr(m, "has_variant_profile") and m.has_variant_profile(m.model.file):
                eff_backend = m.backend.llama_server_path
        except Exception:
            eff_backend = m.backend.llama_server_path
        if eff_backend and eff_backend.strip():
            backend_text = f"🖥 Runtime: {Path(eff_backend).name}"
            backend_color = "#7aaaff"
            backend_bg = "#1e2a4a"
            tip = f"Binario custom para este modelo:\n{eff_backend}\nClick ✎ para cambiar"
        else:
            backend_text = "🖥 Runtime: global"
            backend_color = "#888888"
            backend_bg = "#1a1a2a"
            tip = "Usa binario global de config/app.yaml\nClick ✎ para asignar uno custom a este modelo"
        _set_status(self._backend_label, backend_text, backend_color)
        self._backend_label.setStyleSheet(f"color: {backend_color}; background-color: {backend_bg}; border: 1px solid {backend_color}44; border-radius: 6px; padding: 2px 6px; font-size: 9px; font-weight: bold;")
        self._backend_label.setToolTip(tip)

    def _rebuild_info(self) -> None:
        if not hasattr(self, "_info_layout") or not self._model:
            return
        while self._info_layout.count():
            child = self._info_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                # Limpiar layout anidado
                while child.layout().count():
                    sub = child.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
        m = self._model
        if hasattr(m, "get_effective_model"):
            eff = m.get_effective_model(m.model.file)
        else:
            eff = m.get_for_variant(m.model.file) if hasattr(m, "get_for_variant") and m.has_variant_profile(m.model.file) else m
        if m.health != ModelHealth.READY:
            err = QLabel()
            if m.health == ModelHealth.MISSING_MODEL:
                err.setText(f"✖ File NOT found: {Path(m.model.file).name}")
            elif m.health == ModelHealth.MISSING_VISION:
                err.setText(f"✖ Vision encoder NOT found: {m.vision.encoder if m.vision else '?'}")
            elif m.health == ModelHealth.MISSING_DRAFT:
                err.setText(f"✖ Draft NOT found: {m.model.draft_model}")
            else:
                err.setText(f"Estado: {m.health.value}")
            err.setStyleSheet("color: #ff6b6b; background: transparent; border: none; font-size: 10px; font-weight: bold;")
            err.setWordWrap(True)
            self._info_layout.addWidget(err)
            return

        def _fmt_gpu(v) -> str:
            return "all" if v == -1 or str(v).lower() == "all" else str(v)
        def _fmt_quant(fname: str) -> str:
            import re
            mm = re.search(r"(Q\d[_\w]*|IQ\d[_\w]*|BF16|F16)", fname, re.IGNORECASE)
            return mm.group(1).upper() if mm else "GGUF"
        def _fmt_size(path: Path) -> str:
            try:
                sz = path.stat().st_size
                return f"{sz/1024**3:.1f}GB" if sz > 1024**3 else f"{sz/1024**2:.0f}MB"
            except:
                return ""
        def _chip(text: str, color: str = "#b8b8b8", bg: str = "#1a1a2e", border: str = "#2a2a3a") -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {color}; background-color: {bg}; border: 1px solid {border}; border-radius: 6px; padding: 2px 6px; font-size: 9px; font-weight: 600;")
            return lbl
        def _kv_row(label: str, value: str) -> QHBoxLayout:
            row = QHBoxLayout()
            row.setSpacing(4)
            row.setContentsMargins(0, 0, 0, 0)
            l = QLabel(label)
            l.setStyleSheet("color: #6a6a8a; background: transparent; border: none; font-size: 9px; min-width: 78px;")
            l.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            v = QLabel(value)
            v.setStyleSheet("color: #e0e0e0; background: transparent; border: none; font-size: 9px; font-weight: 600;")
            v.setWordWrap(True)
            v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(l)
            row.addWidget(v, stretch=1)
            return row

        # Header archivo
        file_row = QHBoxLayout()
        file_row.setSpacing(6)
        quant = _fmt_quant(eff.model.file)
        quant_lbl = QLabel(f"⬢ {quant}")
        quant_lbl.setStyleSheet("color: #a0a0ff; background-color: #1e1e3a; border: 1px solid #2a2a5a; border-radius: 6px; padding: 2px 6px; font-size: 9px; font-weight: bold;")
        file_row.addWidget(quant_lbl)
        fname = Path(eff.model.file).name
        name_lbl = QLabel(fname if len(fname) < 30 else fname[:27] + "…")
        name_lbl.setStyleSheet("color: #e0e0e0; background: transparent; border: none; font-size: 10px; font-weight: 600;")
        name_lbl.setToolTip(f"{eff.model.file}  •  {eff.model.format.upper()}")
        file_row.addWidget(name_lbl, stretch=1)
        sz_txt = _fmt_size(m.model_path)
        if sz_txt:
            size_lbl = QLabel(sz_txt)
            size_lbl.setStyleSheet("color: #8a8aaa; background-color: #1a1a2e; border: 1px solid #2a2a3a; border-radius: 6px; padding: 2px 6px; font-size: 9px;")
            file_row.addWidget(size_lbl)
        self._info_layout.addLayout(file_row)

        # Grid ordenado en filas y columnas (2 columnas)
        from PySide6.QtWidgets import QGridLayout, QFrame
        grid_frame = QFrame()
        grid_frame.setStyleSheet("QFrame { background-color: #0f0f1e; border: 1px solid #1e1e2e; border-radius: 6px; }")
        grid = QGridLayout(grid_frame)
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        # Helpers para añadir fila
        row_idx = 0
        def _add_section(title: str):
            nonlocal row_idx
            sec = QLabel(title)
            sec.setStyleSheet("color: #7aaaff; background: transparent; border: none; font-size: 8px; font-weight: 700; letter-spacing: 0.6px; text-transform: uppercase; padding-top: 4px;")
            grid.addWidget(sec, row_idx, 0, 1, 4)
            row_idx += 1
            # Línea divisoria
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("color: #1e1e2e; background-color: #1e1e2e; border: none; max-height: 1px;")
            grid.addWidget(line, row_idx, 0, 1, 4)
            row_idx += 1

        def _add_pair(c: int, label: str, value: str):
            # c = columna base (0 o 2)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #6a6a8a; background: transparent; border: none; font-size: 9px;")
            val = QLabel(value)
            val.setStyleSheet("color: #e0e0e0; background: transparent; border: none; font-size: 9px; font-weight: 600;")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(lbl, row_idx, c)
            grid.addWidget(val, row_idx, c+1)

        # Sección Hardware
        _add_section("Hardware")
        _add_pair(0, "Context", f"{eff.hardware.context_size//1024}K  ({eff.hardware.context_size})")
        _add_pair(2, "GPU Layers", _fmt_gpu(eff.hardware.gpu_layers))
        row_idx += 1
        _add_pair(0, "Batch", str(eff.hardware.batch_size))
        _add_pair(2, "Micro Batch", str(eff.hardware.micro_batch) if eff.hardware.micro_batch else "—")
        row_idx += 1
        threads_txt = str(eff.hardware.threads) if eff.hardware.threads else "auto"
        _add_pair(0, "Threads", threads_txt)
        # Cache en la misma fila derecha si no hay threads extra
        cache_txt = f"{eff.cache.type_k or '—'} / {eff.cache.type_v or '—'}"
        if eff.cache.unified:
            cache_txt += "  • unified"
        _add_pair(2, "Cache K/V", cache_txt)
        row_idx += 1

        # Sección Servidor
        _add_section("Servidor")
        _add_pair(0, "Host", eff.server.host)
        _add_pair(2, "Port", str(eff.server.port))
        row_idx += 1
        alias_txt = f"@{eff.server.alias}" if eff.server.alias else "—"
        _add_pair(0, "Alias", alias_txt)
        # Mostrar host:port completo como valor secundario a la derecha
        url_txt = f"http://{eff.server.host}:{eff.server.port}"
        _add_pair(2, "URL", url_txt)
        row_idx += 1

        # Sección Capacidades
        _add_section("Capacidades")
        has_mtp = eff.variant_has_mtp(eff.model.file) if hasattr(eff, "variant_has_mtp") else False
        mtp_val = eff.speculative.spec_type if eff.speculative.enabled and has_mtp else "—"
        if eff.speculative.enabled and has_mtp:
            mtp_val = f"{eff.speculative.spec_type}  n={eff.speculative.draft_n_max}"
        elif eff.speculative.enabled and not has_mtp:
            mtp_val = "— (variante sin MTP)"
        _add_pair(0, "Speculative", mtp_val)
        _add_pair(2, "Reasoning", "Sí" if eff.advanced.reasoning else "No")
        row_idx += 1
        _add_pair(0, "Vision", "Sí" if eff.capabilities.vision else "No")
        vision_txt = eff.vision.encoder if eff.vision and eff.vision.encoder else "—"
        if eff.capabilities.vision and eff.vision and eff.vision.image_min_tokens:
            vision_txt += f"  ({eff.vision.image_min_tokens} tok)"
        _add_pair(2, "Encoder", vision_txt)
        row_idx += 1
        _add_pair(0, "Tool calling", "Sí" if eff.capabilities.tool_calling else "No")
        flash_txt = "Sí" if eff.advanced.flash_attention else "No"
        _add_pair(2, "Flash Attn", flash_txt)
        row_idx += 1

        # Sección Muestreo
        _add_section("Muestreo")
        _add_pair(0, "Temp", str(eff.sampling.temperature))
        _add_pair(2, "Top-P", str(eff.sampling.top_p))
        row_idx += 1
        _add_pair(0, "Top-K", str(eff.sampling.top_k))
        _add_pair(2, "Min-P", str(eff.sampling.min_p))
        row_idx += 1
        _add_pair(0, "Repeat penalty", str(eff.sampling.repeat_penalty))
        _add_pair(2, "Presence", str(eff.sampling.presence_penalty))
        row_idx += 1

        # Sección Avanzado / Variantes
        _add_section("Avanzado")
        _add_pair(0, "Parallel", str(eff.advanced.parallel))
        _add_pair(2, "Cache RAM", f"{eff.advanced.cache_ram} MB")
        row_idx += 1
        ncmoe_txt = str(eff.advanced.ncmoe) if eff.advanced.ncmoe else "—"
        _add_pair(0, "NCMoE", ncmoe_txt)
        fit_txt = eff.advanced.fit or "—"
        _add_pair(2, "Fit", fit_txt)
        row_idx += 1
        is_multi = getattr(m, "is_multivariant", False) or len(getattr(m, "available_main_files", [])) > 1
        if is_multi:
            variants = m.variants_display() if hasattr(m, "variants_display") else []
            _add_pair(0, "Versiones", f"{len(variants)} disponibles")
            has_profile = m.has_variant_profile(m.model.file) if hasattr(m, "has_variant_profile") else False
            has_yaml = m.get_variant_yaml_path(m.model.file) is not None if hasattr(m, "get_variant_yaml_path") else False
            if has_yaml:
                profile_txt = "YAML"
            elif has_profile:
                profile_txt = "Sí"
            else:
                profile_txt = "hereda base"
            _add_pair(2, "Perfil", profile_txt)
            row_idx += 1

        self._info_layout.addWidget(grid_frame)

    def _refresh_mtp_label(self) -> None:
        if not self._model or not hasattr(self, "_mtp_label"):
            return
        mtp_text, mtp_color = self._model.mtp_status_label() if hasattr(self._model, "mtp_status_label") else ("MTP: --", "#888")
        _set_status(self._mtp_label, mtp_text, mtp_color)
        self._mtp_label.setStyleSheet(f"color: {mtp_color}; background-color: transparent; border: none; font-size: 10px; font-weight: bold;")
        # Actualizar contenedor
        if hasattr(self, "_mtp_label") and self._mtp_label.parent():
            try:
                container = self._mtp_label.parent()
                container.setStyleSheet(f"background-color: {mtp_color}22; border: 1px solid {mtp_color}44; border-radius: 6px; padding: 1px;")
            except:
                pass

    def _on_create_config(self) -> None:
        if self._unconfigured:
            folder, gguf_files = self._unconfigured
            self.create_config_clicked.emit(str(folder), gguf_files)

    def refresh_status(self) -> None:
        if self._model:
            self._model.check_health()
            self._rebuild_info()
            self._update_state()
            self._refresh_mtp_label()
            self._update_profile_indicator()
            self._update_backend_label()
            self._apply_style()

