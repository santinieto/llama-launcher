from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# Cache para detección de MTP integrado (nextn) por archivo
_nextn_cache: dict[str, bool] = {}


def _gguf_supports_integrated_mtp(path: Path) -> bool:
    """Detecta si un GGUF tiene soporte MTP integrado buscando tensor 'nextn'.

    Lee solo los primeros 8MB para evitar cargar archivos grandes.
    Se cachea por path.
    """
    key = str(path)
    if key in _nextn_cache:
        return _nextn_cache[key]
    try:
        if not path.is_file():
            _nextn_cache[key] = False
            return False
        with open(path, "rb") as f:
            data = f.read(8_000_000)
        # 'nextn' es el nombre del tensor de MTP integrado en Qwen3/Qwen3.5
        has = b"nextn" in data
        _nextn_cache[key] = has
        return has
    except Exception:
        _nextn_cache[key] = False
        return False


class ModelStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


class ModelHealth(str, Enum):
    READY = "ready"
    NO_CONFIG = "no_config"
    MISSING_MODEL = "missing_model"
    MISSING_VISION = "missing_vision"
    MISSING_DRAFT = "missing_draft"


@dataclass(slots=True)
class BackendConfig:
    backend_type: str = "llama.cpp"
    llama_server_path: str = ""  # per-model override, vacío = usa global de config/app.yaml


@dataclass(slots=True)
class ModelFileConfig:
    file: str = ""
    format: str = "gguf"
    draft_model: str = ""
    gguf_directory: str = ""


@dataclass(slots=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 18765
    alias: str = ""
    protocol: str = "http"


@dataclass(slots=True)
class HardwareConfig:
    gpu_layers: int | str = 0
    context_size: int = 2048
    batch_size: int = 2048
    threads: int = 0
    micro_batch: int = 0


@dataclass(slots=True)
class CacheConfig:
    type_k: str = ""
    type_v: str = ""
    type_k_draft: str = ""
    type_v_draft: str = ""
    unified: bool = False


@dataclass(slots=True)
class SpeculativeConfig:
    enabled: bool = False
    spec_type: str = ""
    draft_n_max: int = 0


@dataclass(slots=True)
class SamplingConfig:
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 0
    min_p: float = 0.0
    presence_penalty: float = 0.0
    repeat_penalty: float = 1.0


@dataclass(slots=True)
class CapabilitiesConfig:
    vision: bool = False
    tool_calling: bool = False


@dataclass(slots=True)
class VisionConfig:
    encoder: str = ""
    image_min_tokens: int = 0


@dataclass(slots=True)
class AdvancedConfig:
    flash_attention: bool = False
    reasoning: bool = False
    fit: str = ""
    ncmoe: int = 0
    parallel: int = 1
    log_verbosity: int = 0
    draft_gpu_layers: int | str = -1
    cache_ram: int = 8192


@dataclass(slots=True)
class ModelDefinition:
    name: str
    description: str
    system_prompt: str
    directory: Path
    backend: BackendConfig
    model: ModelFileConfig
    server: ServerConfig
    hardware: HardwareConfig
    cache: CacheConfig
    speculative: SpeculativeConfig
    sampling: SamplingConfig
    capabilities: CapabilitiesConfig
    vision: VisionConfig | None
    advanced: AdvancedConfig
    status: ModelStatus = ModelStatus.STOPPED
    health: ModelHealth = ModelHealth.READY
    pid: int | None = None
    # Ruta al YAML que define este modelo (per-variante)
    config_path: Path | None = None
    # --- variantes descubiertas en disco (rellenadas por ModelManager.scan) ---
    available_main_files: list[str] = field(default_factory=list)
    available_draft_files: list[str] = field(default_factory=list)
    available_mmproj_files: list[str] = field(default_factory=list)
    # --- perfiles por variante: file -> overrides dict (del YAML variants:) ---
    # Deprecado: se mantiene por compatibilidad, preferir YAML por variante.
    variant_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    # --- per-variante YAMLs: main file -> Path del YAML específico ---
    # Si hay múltiples YAMLs por carpeta, este dict mapea cada variante a su YAML.
    variant_yaml_paths: dict[str, Path] = field(default_factory=dict)
    # Cache interna de ModelDefinition per-variante (no serializar)
    per_variant_cache: dict[str, "ModelDefinition"] = field(default_factory=dict, repr=False)

    def _gguf_dir(self) -> Path:
        if self.model.gguf_directory:
            p = Path(self.model.gguf_directory)
            if p.is_absolute():
                return p
            return self.directory / p
        return self.directory / "gguf"

    def get_effective_llama_server_path(self, global_path: Path) -> Path:
        """Resuelve el binario a usar para este modelo.

        Prioridad: backend.llama_server_path del model.yaml/variant si está seteado,
        si no usa global_path de config/app.yaml.
        Soporta rutas absolutas y relativas (relativas al directorio del modelo
        o al directorio del exe).
        """
        raw = (self.backend.llama_server_path or "").strip()
        if not raw:
            return global_path
        p = Path(raw)
        if p.is_absolute():
            return p
        # Relativo al directorio del modelo
        cand = (self.directory / p).resolve()
        if cand.is_file():
            return cand
        # Relativo al directorio del ejecutable (global_path parent)
        try:
            cand2 = (global_path.parent / p).resolve()
            if cand2.is_file():
                return cand2
        except Exception:
            pass
        # Fallback: devolver tal cual (puede ser relativo al exe base)
        # Normalizar contra global base para mensaje claro
        try:
            return (global_path.parent / p).resolve()
        except Exception:
            return p

    @property
    def has_custom_llama_server(self) -> bool:
        return bool((self.backend.llama_server_path or "").strip())

    def _resolve_gguf_file(self, filename: str) -> Path | None:
        """Resuelve un archivo GGUF contra el directorio gguf con soporte para subcarpetas.

        Soporta:
        - filename con subpath relativo (ej: "mtp/model.gguf")
        - filename solo basename donde el archivo puede estar en subcarpeta recursiva
        - fallback a directorio del modelo si no hay gguf/
        """
        if not filename:
            return None
        # 1. Intento directo relativo a gguf_dir
        gguf_dir = self._gguf_dir()
        direct = gguf_dir / filename
        if direct.is_file():
            return direct
        # 2. Intento directo relativo a directory (caso sin gguf/)
        alt = self.directory / filename
        if alt.is_file():
            return alt
        # 3. Búsqueda recursiva por basename bajo gguf_dir
        basename = Path(filename).name
        if gguf_dir.is_dir():
            # evitar escanear .cache innecesariamente pero rglob igual lo hace; filtrar
            for p in gguf_dir.rglob("*.gguf"):
                # evitar .cache
                if ".cache" in p.parts:
                    continue
                if p.name == basename:
                    # si filename tiene subdir, intentar match por sufijo también
                    # pero por ahora primera coincidencia por nombre es suficiente
                    return p
                # si filename incluye subdir, comparar sufijo relativo
                try:
                    rel = p.relative_to(gguf_dir).as_posix()
                    if rel == filename or rel.endswith("/" + filename):
                        return p
                except Exception:
                    pass
        # 4. Búsqueda recursiva bajo directory
        if self.directory.is_dir():
            for p in self.directory.rglob("*.gguf"):
                if ".cache" in p.parts:
                    continue
                if p.name == basename:
                    return p
        # 5. No encontrado, devolver el path directo esperado para mensajes de error
        return direct

    @property
    def model_path(self) -> Path:
        resolved = self._resolve_gguf_file(self.model.file)
        return resolved if resolved is not None else self._gguf_dir() / self.model.file

    @property
    def draft_model_path(self) -> Path | None:
        if self.model.draft_model:
            resolved = self._resolve_gguf_file(self.model.draft_model)
            return resolved if resolved is not None else self._gguf_dir() / self.model.draft_model
        return None

    @property
    def vision_encoder_path(self) -> Path | None:
        if self.vision and self.vision.encoder:
            resolved = self._resolve_gguf_file(self.vision.encoder)
            return resolved if resolved is not None else self._gguf_dir() / self.vision.encoder
        return None

    # --- Helpers MTP / variantes ---

    @property
    def has_mtp_available(self) -> bool:
        """True si hay algún archivo draft/mtp descubierto en disco."""
        return len(self.available_draft_files) > 0

    @property
    def has_mtp_configured(self) -> bool:
        """True si el model.yaml tiene draft_model y ese archivo existe."""
        if not self.model.draft_model:
            return False
        dp = self.draft_model_path
        return dp is not None and dp.is_file()

    @property
    def mtp_enabled(self) -> bool:
        """True si speculative está habilitado (con draft externo o integrado)."""
        if not self.speculative.enabled:
            return False
        # Con draft externo válido o MTP integrado sin archivo draft
        if self.has_mtp_configured:
            return True
        # MTP integrado: spec_type draft-mtp sin draft file (ej. Qwen3.5)
        if "mtp" in (self.speculative.spec_type or "").lower():
            return True
        return bool(self.speculative.spec_type)

    @property
    def is_multivariant(self) -> bool:
        return len(self.available_main_files) > 1

    def variant_has_mtp(self, variant: str | None = None) -> bool:
        """Determina si una variante específica tiene soporte MTP.

        Heurística mejorada con inspección de GGUF:
        - Si path contiene 'nomtp' => No (variantes sin MTP, ej Qwen 35B nomtp/)
        - Si contiene 'mtp' (y no es nomtp) => Sí (draft externo)
        - Si has_mtp_configured/available => Sí (draft externo)
        - Si el GGUF contiene tensor 'nextn' => Sí (MTP integrado)
        - Fallback: usa mtp_enabled solo si el archivo realmente tiene nextn
        """
        file = variant if variant is not None else self.model.file
        if not file:
            return False
        lower = file.lower()
        if "nomtp" in lower or "no_mtp" in lower or "without_mtp" in lower:
            return False
        if "mtp" in lower or "draft" in Path(file).name.lower():
            if "mmproj" not in lower:
                return True
        if self.has_mtp_configured or self.has_mtp_available:
            return True
        # MTP integrado: verificar tensor 'nextn' en el GGUF (independiente de spec.enabled para mostrar capacidad)
        try:
            path = self._resolve_gguf_file(file)
            if path and path.is_file() and _gguf_supports_integrated_mtp(path):
                # Si contiene nextn, tiene MTP integrado (aunque spec esté deshabilitado, mostrar como disponible)
                return True
        except Exception:
            pass
        # Si spec está habilitado con tipo mtp pero el archivo no tiene nextn, no considerar con MTP
        if self.speculative.enabled and "mtp" in (self.speculative.spec_type or "").lower():
            try:
                path = self._resolve_gguf_file(file)
                if path and path.is_file():
                    # Ya verificamos nextn arriba y no lo tiene
                    return False
            except Exception:
                pass
            if self.mtp_enabled:
                return True
        if self.mtp_enabled:
            return True
        return False

    def mtp_status_label(self, variant: str | None = None) -> tuple[str, str]:
        """Retorna (texto, color) para mostrar estado MTP en la UI.

        Si se pasa variant, evalúa MTP para esa variante específica.
        Maneja tanto MTP con archivo draft externo como MTP integrado.
        """
        # Si se especifica variante y esa variante no tiene MTP (ej nomtp/), forzar No
        if variant is not None and not self.variant_has_mtp(variant):
            return ("MTP: No", "#888888")
        # También verificar variante actual si no se pasa
        if variant is None and not self.variant_has_mtp(self.model.file):
            # Si la variante seleccionada es nomtp, mostrar No aunque el modelo global tenga MTP
            # Solo si el archivo actual es nomtp
            if "nomtp" in self.model.file.lower():
                return ("MTP: No", "#888888")

        is_spec_mtp = self.speculative.enabled and "mtp" in (self.speculative.spec_type or "").lower()
        # Caso 1: draft externo configurado y activo
        if self.has_mtp_configured and self.speculative.enabled:
            # Si variante actual es nomtp, no mostrar activo
            if not self.variant_has_mtp(variant or self.model.file):
                return ("MTP: No", "#888888")
            return ("MTP: Sí (activo)", "#4caf50")
        if self.has_mtp_configured and not self.speculative.enabled:
            return ("MTP: Sí (desactivado)", "#ff9800")
        # Caso 2: MTP integrado (spec habilitado sin draft externo, como Qwen3.5)
        if self.speculative.enabled and not self.model.draft_model:
            if not self.variant_has_mtp(variant or self.model.file):
                return ("MTP: No", "#888888")
            if is_spec_mtp or self.speculative.spec_type == "draft-mtp":
                return ("MTP: Sí (integrado)", "#4caf50")
            return ("MTP: Spec activo", "#4caf50")
        # Caso 3: hay archivo draft en disco pero no está referenciado en yaml
        if self.has_mtp_available and not self.has_mtp_configured:
            if self.speculative.enabled:
                if not self.variant_has_mtp(variant or self.model.file):
                    return ("MTP: No", "#888888")
                return ("MTP: Disponible (integrado)", "#2196F3")
            return ("MTP: Disponible (no configurado)", "#2196F3")
        # Caso 3b: MTP integrado disponible pero spec deshabilitado (ej Qwen3.8 con nextn)
        if not self.speculative.enabled:
            if self.variant_has_mtp(variant or self.model.file):
                # Tiene capacidad MTP pero está desactivado en YAML
                return ("MTP: Sí (desactivado)", "#ff9800")
        # Caso 4: spec habilitado pero draft configurado no existe
        if self.speculative.enabled and not self.has_mtp_configured:
            if self.model.draft_model:
                return ("MTP: Falta draft", "#f44336")
            # Si variante no tiene MTP pero spec intenta habilitarlo, ya se manejó arriba con No
            return ("MTP: Spec sin draft", "#f44336")
        return ("MTP: No", "#888888")

    def variants_display(self) -> list[str]:
        """Lista ordenada de variantes para mostrar en ComboBox."""
        if self.available_main_files:
            files = list(self.available_main_files)
            if self.model.file in files:
                files.remove(self.model.file)
                files.insert(0, self.model.file)
                return files
            # Si file no está exacto pero coincide por basename (ej: plain vs subcarpeta)
            base_name = Path(self.model.file).name if self.model.file else ""
            for f in files:
                if Path(f).name == base_name:
                    files.remove(f)
                    files.insert(0, f)
                    return files
            # Si no hay coincidencia por basename, agregar el file configurado al frente
            # para que el usuario vea la selección actual aunque no esté entre variantes descubiertas
            if self.model.file:
                files.insert(0, self.model.file)
            return files
        if self.model.file:
            return [self.model.file]
        return []

    # --- Per-variant profiles ---

    def has_variant_profile(self, variant: str | None = None) -> bool:
        """True si la variante tiene perfil custom en variants:"""
        key = variant if variant is not None else self.model.file
        if not key:
            return False
        # Normalizar: probar exacto, luego basename
        if key in self.variant_profiles:
            return True
        base = Path(key).name
        for k in self.variant_profiles:
            if k == key or Path(k).name == base:
                return True
        return False

    def get_variant_profile(self, variant: str | None = None) -> dict[str, Any] | None:
        key = variant if variant is not None else self.model.file
        if not key:
            return None
        if key in self.variant_profiles:
            return self.variant_profiles[key]
        base = Path(key).name
        for k, v in self.variant_profiles.items():
            if Path(k).name == base:
                return v
        return None

    def get_for_variant(self, variant: str) -> "ModelDefinition":
        """Retorna una copia con overrides de variants: aplicados.

        Si no hay perfil para la variante, retorna copia con solo model.file cambiado.
        No muta el original. La copia mantiene variant_profiles y available_*.
        """
        import copy

        # Clonar base (shallow copy de configs, deep para variant_profiles)
        eff: ModelDefinition = copy.copy(self)
        # Necesario para slots: copy.copy funciona con slots=True
        # Pero variant_profiles debe ser copia
        eff.variant_profiles = dict(self.variant_profiles)
        eff.available_main_files = list(self.available_main_files)
        eff.available_draft_files = list(self.available_draft_files)
        eff.available_mmproj_files = list(self.available_mmproj_files)

        # Cambiar archivo seleccionado
        eff.model = ModelFileConfig(
            file=variant,
            format=self.model.format,
            draft_model=self.model.draft_model,
            gguf_directory=self.model.gguf_directory,
        )
        # Aplicar overrides si existen
        profile = self.get_variant_profile(variant)
        if not profile:
            return eff
        # Helper para mergear
        def _apply_hardware(base: HardwareConfig, raw: dict[str, Any]) -> HardwareConfig:
            gpu = raw.get("gpu_layers", base.gpu_layers)
            if isinstance(gpu, str) and gpu.lower() == "all":
                gpu = -1
            return HardwareConfig(
                gpu_layers=gpu,
                context_size=raw.get("context_size", base.context_size),
                batch_size=raw.get("batch_size", base.batch_size),
                threads=raw.get("threads", base.threads),
                micro_batch=raw.get("micro_batch", base.micro_batch),
            )

        def _apply_cache(base: CacheConfig, raw: dict[str, Any]) -> CacheConfig:
            return CacheConfig(
                type_k=raw.get("type_k", base.type_k),
                type_v=raw.get("type_v", base.type_v),
                type_k_draft=raw.get("type_k_draft", base.type_k_draft),
                type_v_draft=raw.get("type_v_draft", base.type_v_draft),
                unified=raw.get("unified", base.unified),
            )

        def _apply_spec(base: SpeculativeConfig, raw: dict[str, Any]) -> SpeculativeConfig:
            return SpeculativeConfig(
                enabled=raw.get("enabled", base.enabled),
                spec_type=raw.get("spec_type", base.spec_type),
                draft_n_max=raw.get("draft_n_max", base.draft_n_max),
            )

        def _apply_sampling(base: SamplingConfig, raw: dict[str, Any]) -> SamplingConfig:
            return SamplingConfig(
                temperature=raw.get("temperature", base.temperature),
                top_p=raw.get("top_p", base.top_p),
                top_k=raw.get("top_k", base.top_k),
                min_p=raw.get("min_p", base.min_p),
                presence_penalty=raw.get("presence_penalty", base.presence_penalty),
                repeat_penalty=raw.get("repeat_penalty", base.repeat_penalty),
            )

        def _apply_advanced(base: AdvancedConfig, raw: dict[str, Any]) -> AdvancedConfig:
            dgl = raw.get("draft_gpu_layers", base.draft_gpu_layers)
            if isinstance(dgl, str) and dgl.lower() == "all":
                dgl = -1
            return AdvancedConfig(
                flash_attention=raw.get("flash_attention", base.flash_attention),
                reasoning=raw.get("reasoning", base.reasoning),
                fit=raw.get("fit", base.fit),
                ncmoe=raw.get("ncmoe", base.ncmoe),
                parallel=raw.get("parallel", base.parallel),
                log_verbosity=raw.get("log_verbosity", base.log_verbosity),
                draft_gpu_layers=dgl,
                cache_ram=raw.get("cache_ram", base.cache_ram),
            )

        def _apply_server(base: ServerConfig, raw: dict[str, Any]) -> ServerConfig:
            return ServerConfig(
                host=raw.get("host", base.host),
                port=raw.get("port", base.port),
                alias=raw.get("alias", base.alias),
            )

        def _apply_vision(base: VisionConfig | None, raw: dict[str, Any] | None) -> VisionConfig | None:
            if raw is None:
                return base
            if base is None:
                base = VisionConfig()
            return VisionConfig(
                encoder=raw.get("encoder", base.encoder),
                image_min_tokens=raw.get("image_min_tokens", base.image_min_tokens),
            )

        def _apply_cap(base: CapabilitiesConfig, raw: dict[str, Any]) -> CapabilitiesConfig:
            return CapabilitiesConfig(
                vision=raw.get("vision", base.vision),
                tool_calling=raw.get("tool_calling", base.tool_calling),
            )

        # Aplicar cada sección si existe en profile
        if "backend" in profile and isinstance(profile["backend"], dict):
            braw = profile["backend"]
            eff.backend = BackendConfig(
                backend_type=braw.get("type", self.backend.backend_type),
                llama_server_path=braw.get("llama_server_path", self.backend.llama_server_path) or braw.get("server_path", self.backend.llama_server_path) or braw.get("path", self.backend.llama_server_path),
            )
        if "hardware" in profile and isinstance(profile["hardware"], dict):
            eff.hardware = _apply_hardware(self.hardware, profile["hardware"])
        if "cache" in profile and isinstance(profile["cache"], dict):
            eff.cache = _apply_cache(self.cache, profile["cache"])
        if "speculative" in profile and isinstance(profile["speculative"], dict):
            eff.speculative = _apply_spec(self.speculative, profile["speculative"])
        if "sampling" in profile and isinstance(profile["sampling"], dict):
            eff.sampling = _apply_sampling(self.sampling, profile["sampling"])
        if "advanced" in profile and isinstance(profile["advanced"], dict):
            eff.advanced = _apply_advanced(self.advanced, profile["advanced"])
        if "server" in profile and isinstance(profile["server"], dict):
            eff.server = _apply_server(self.server, profile["server"])
        if "vision" in profile:
            eff.vision = _apply_vision(self.vision, profile["vision"])
        if "capabilities" in profile and isinstance(profile["capabilities"], dict):
            eff.capabilities = _apply_cap(self.capabilities, profile["capabilities"])
        if "model" in profile and isinstance(profile["model"], dict):
            # Permitir override de draft_model por variante (útil si cada quant tiene su draft)
            mraw = profile["model"]
            eff.model = ModelFileConfig(
                file=variant,
                format=mraw.get("format", eff.model.format),
                draft_model=mraw.get("draft_model", eff.model.draft_model),
                gguf_directory=mraw.get("gguf_directory", eff.model.gguf_directory),
            )
        return eff

    def get_variant_yaml_path(self, variant: str | None = None) -> Path | None:
        """Retorna el Path del YAML específico para una variante si existe."""
        key = variant if variant is not None else self.model.file
        if not key:
            return self.config_path
        # Búsqueda exacta
        if key in self.variant_yaml_paths:
            return self.variant_yaml_paths[key]
        # Por basename
        base = Path(key).name
        for k, v in self.variant_yaml_paths.items():
            if Path(k).name == base:
                return v
        return None

    def get_for_variant_yaml(self, variant: str) -> "ModelDefinition":
        """Retorna ModelDefinition cargado desde el YAML per-variante si existe.

        Si hay un YAML específico para esa variante (variant_yaml_paths), lo carga
        y retorna esa definición (con su propio hardware, cache, etc.).
        Si no existe, fallback a get_for_variant (legacy variants dict).
        """
        # Verificar si hay YAML per-variante
        yaml_path = self.get_variant_yaml_path(variant)
        if yaml_path and yaml_path.is_file() and yaml_path != self.config_path:
            # Usar cache si ya cargado
            if variant in self.per_variant_cache:
                cached = self.per_variant_cache[variant]
                # Actualizar available_* para consistencia
                cached.available_main_files = list(self.available_main_files)
                cached.available_draft_files = list(self.available_draft_files)
                cached.available_mmproj_files = list(self.available_mmproj_files)
                return cached
            try:
                from app.core.config_loader import load_model_config

                per = load_model_config(yaml_path)
                per.available_main_files = list(self.available_main_files)
                per.available_draft_files = list(self.available_draft_files)
                per.available_mmproj_files = list(self.available_mmproj_files)
                per.variant_yaml_paths = dict(self.variant_yaml_paths)
                # Guardar en cache
                self.per_variant_cache[variant] = per
                return per
            except Exception:
                pass
        # Fallback legacy
        return self.get_for_variant(variant)

    def get_effective_model(self, variant: str | None = None) -> "ModelDefinition":
        """Retorna el modelo efectivo para una variante.

        Prioridad:
        1. YAML per-variante (variant_yaml_paths)
        2. Perfil variants dict (legacy)
        3. Copia con solo file cambiado
        """
        v = variant if variant is not None else self.model.file
        # Intentar per-variante YAML primero
        if self.variant_yaml_paths:
            yaml_path = self.get_variant_yaml_path(v)
            if yaml_path and yaml_path.is_file():
                return self.get_for_variant_yaml(v)
        # Fallback a perfil legacy
        if self.has_variant_profile(v):
            return self.get_for_variant(v)
        if v != self.model.file:
            return self.get_for_variant(v)
        return self

    def check_health(self) -> ModelHealth:
        if not self.model.file:
            self.health = ModelHealth.NO_CONFIG
            return self.health

        if not self.model_path.is_file():
            self.health = ModelHealth.MISSING_MODEL
            return self.health

        if self.capabilities.vision and self.vision:
            enc = self.vision_encoder_path
            if enc is None or not enc.is_file():
                self.health = ModelHealth.MISSING_VISION
                return self.health

        if self.model.draft_model:
            draft = self.draft_model_path
            if draft is None or not draft.is_file():
                self.health = ModelHealth.MISSING_DRAFT
                return self.health

        self.health = ModelHealth.READY
        return self.health

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "directory": str(self.directory),
            "model_file": self.model.file,
            "model_format": self.model.format,
            "draft_model": self.model.draft_model,
            "host": self.server.host,
            "port": self.server.port,
            "alias": self.server.alias,
            "gpu_layers": self.hardware.gpu_layers,
            "context_size": self.hardware.context_size,
            "batch_size": self.hardware.batch_size,
            "threads": self.hardware.threads,
            "micro_batch": self.hardware.micro_batch,
            "cache_type_k": self.cache.type_k,
            "cache_type_v": self.cache.type_v,
            "cache_type_k_draft": self.cache.type_k_draft,
            "cache_type_v_draft": self.cache.type_v_draft,
            "cache_unified": self.cache.unified,
            "spec_enabled": self.speculative.enabled,
            "spec_type": self.speculative.spec_type,
            "draft_n_max": self.speculative.draft_n_max,
            "temperature": self.sampling.temperature,
            "top_p": self.sampling.top_p,
            "top_k": self.sampling.top_k,
            "min_p": self.sampling.min_p,
            "presence_penalty": self.sampling.presence_penalty,
            "repeat_penalty": self.sampling.repeat_penalty,
            "vision": self.capabilities.vision,
            "tool_calling": self.capabilities.tool_calling,
            "flash_attention": self.advanced.flash_attention,
            "reasoning": self.advanced.reasoning,
            "fit": self.advanced.fit,
            "ncmoe": self.advanced.ncmoe,
            "parallel": self.advanced.parallel,
            "log_verbosity": self.advanced.log_verbosity,
            "draft_gpu_layers": self.advanced.draft_gpu_layers,
            "cache_ram": self.advanced.cache_ram,
        }
