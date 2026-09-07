from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.models.model_definition import (
    AdvancedConfig,
    BackendConfig,
    CacheConfig,
    CapabilitiesConfig,
    HardwareConfig,
    ModelDefinition,
    ModelFileConfig,
    ModelHealth,
    ModelStatus,
    SamplingConfig,
    ServerConfig,
    SpeculativeConfig,
    VisionConfig,
)


class ConfigError(Exception):
    pass


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Archivo no encontrado: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ConfigError(f"Formato inválido en: {path}")
    return data


def _parse_backend(raw: dict[str, Any] | None) -> BackendConfig:
    if raw is None:
        return BackendConfig()
    # Soporta múltiples keys para compatibilidad: llama_server_path, server_path, path
    custom = (
        raw.get("llama_server_path")
        or raw.get("server_path")
        or raw.get("path")
        or raw.get("binary")
        or ""
    )
    return BackendConfig(
        backend_type=raw.get("type", "llama.cpp"),
        llama_server_path=str(custom).strip() if custom else "",
    )


def _parse_model_file(raw: dict[str, Any] | None) -> ModelFileConfig:
    if raw is None:
        return ModelFileConfig()
    return ModelFileConfig(
        file=raw.get("file", ""),
        format=raw.get("format", "gguf"),
        draft_model=raw.get("draft_model", ""),
        gguf_directory=raw.get("gguf_directory", ""),
    )


def _parse_server(raw: dict[str, Any] | None) -> ServerConfig:
    if raw is None:
        return ServerConfig()
    return ServerConfig(
        host=raw.get("host", "127.0.0.1"),
        port=raw.get("port", 18765),
        alias=raw.get("alias", ""),
        protocol=raw.get("protocol", "http"),
    )


def _parse_hardware(raw: dict[str, Any] | None) -> HardwareConfig:
    if raw is None:
        return HardwareConfig()
    gpu = raw.get("gpu_layers", 0)
    if isinstance(gpu, str) and gpu.lower() == "all":
        gpu = -1
    return HardwareConfig(
        gpu_layers=gpu,
        context_size=raw.get("context_size", 2048),
        batch_size=raw.get("batch_size", 2048),
        threads=raw.get("threads", 0),
        micro_batch=raw.get("micro_batch", 0),
    )


def _parse_cache(raw: dict[str, Any] | None) -> CacheConfig:
    if raw is None:
        return CacheConfig()
    return CacheConfig(
        type_k=raw.get("type_k", ""),
        type_v=raw.get("type_v", ""),
        type_k_draft=raw.get("type_k_draft", ""),
        type_v_draft=raw.get("type_v_draft", ""),
        unified=raw.get("unified", False),
    )


def _parse_speculative(raw: dict[str, Any] | None) -> SpeculativeConfig:
    if raw is None:
        return SpeculativeConfig()
    return SpeculativeConfig(
        enabled=raw.get("enabled", False),
        spec_type=raw.get("spec_type", ""),
        draft_n_max=raw.get("draft_n_max", 0),
    )


def _parse_sampling(raw: dict[str, Any] | None) -> SamplingConfig:
    if raw is None:
        return SamplingConfig()
    return SamplingConfig(
        temperature=raw.get("temperature", 0.7),
        top_p=raw.get("top_p", 0.9),
        top_k=raw.get("top_k", 0),
        min_p=raw.get("min_p", 0.0),
        presence_penalty=raw.get("presence_penalty", 0.0),
        repeat_penalty=raw.get("repeat_penalty", 1.0),
    )


def _parse_capabilities(raw: dict[str, Any] | None) -> CapabilitiesConfig:
    if raw is None:
        return CapabilitiesConfig()
    return CapabilitiesConfig(
        vision=raw.get("vision", False),
        tool_calling=raw.get("tool_calling", False),
    )


def _parse_vision(raw: dict[str, Any] | None) -> VisionConfig | None:
    if raw is None:
        return None
    encoder = raw.get("encoder", "")
    if not encoder:
        return None
    return VisionConfig(
        encoder=encoder,
        image_min_tokens=raw.get("image_min_tokens", 0),
    )


def _parse_advanced(raw: dict[str, Any] | None) -> AdvancedConfig:
    if raw is None:
        return AdvancedConfig()
    dgl = raw.get("draft_gpu_layers", -1)
    if isinstance(dgl, str) and dgl.lower() == "all":
        dgl = -1
    return AdvancedConfig(
        flash_attention=raw.get("flash_attention", False),
        reasoning=raw.get("reasoning", False),
        fit=raw.get("fit", ""),
        ncmoe=raw.get("ncmoe", 0),
        parallel=raw.get("parallel", 1),
        log_verbosity=raw.get("log_verbosity", 0),
        draft_gpu_layers=dgl,
        cache_ram=raw.get("cache_ram", 8192),
    )


def _parse_system_prompt(raw: Any | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw.strip()
    return str(raw).strip()


def _parse_variants(raw: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    # Normalizar keys a posix, valores deben ser dict
    out: dict[str, dict[str, Any]] = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            out[str(k)] = v
    return out


def load_model_config(path: Path) -> ModelDefinition:
    data = load_yaml(path)

    name = data.get("name", path.parent.name)
    description = data.get("description", "")
    system_prompt = _parse_system_prompt(data.get("system_prompt"))

    return ModelDefinition(
        name=name,
        description=description,
        system_prompt=system_prompt,
        directory=path.parent,
        backend=_parse_backend(data.get("backend")),
        model=_parse_model_file(data.get("model")),
        server=_parse_server(data.get("server")),
        hardware=_parse_hardware(data.get("hardware")),
        cache=_parse_cache(data.get("cache")),
        speculative=_parse_speculative(data.get("speculative")),
        sampling=_parse_sampling(data.get("sampling")),
        capabilities=_parse_capabilities(data.get("capabilities")),
        vision=_parse_vision(data.get("vision")),
        advanced=_parse_advanced(data.get("advanced")),
        status=ModelStatus.STOPPED,
        health=ModelHealth.READY,
        pid=None,
        config_path=path,
        variant_profiles=_parse_variants(data.get("variants")),
    )


def load_app_config(path: Path) -> dict[str, Any]:
    return load_yaml(path)


def create_default_config(
    name: str,
    gguf_files: list[str],
    directory: Path,
) -> dict[str, Any]:
    main_file = ""
    vision_file = ""
    draft_file = ""

    for f in gguf_files:
        # Usar solo el nombre del archivo para clasificar, no el path completo
        # (evita que "mtp/model.gguf" se clasifique como draft por el directorio)
        basename_lower = Path(f).name.lower()
        lower = f.lower()
        if "mmproj" in basename_lower:
            vision_file = f
        elif "mtp" in basename_lower or "draft" in basename_lower:
            draft_file = f
        elif lower.endswith(".gguf"):
            main_file = f

    has_vision = bool(vision_file)
    has_draft = bool(draft_file)

    config: dict[str, Any] = {
        "name": name,
        "description": "",
        "backend": {"type": "llama.cpp"},
        "model": {"file": main_file, "format": "gguf"},
        "server": {"host": "127.0.0.1", "port": 18765, "alias": name},
        "hardware": {
            "gpu_layers": "all",
            "context_size": 8192,
            "batch_size": 2048,
        },
        "cache": {
            "type_k": "q8_0",
            "type_v": "q8_0",
        },
        "sampling": {
            "temperature": 0.7,
            "top_p": 0.9,
        },
        "capabilities": {
            "vision": has_vision,
            "tool_calling": False,
        },
        "advanced": {
            "reasoning": False,
        },
    }

    if has_vision:
        config["vision"] = {"encoder": vision_file}

    if has_draft:
        config["model"]["draft_model"] = draft_file
        config["speculative"] = {
            "enabled": True,
            "spec_type": "draft-mtp",
            "draft_n_max": 3,
        }
        config["cache"]["type_k_draft"] = "q8_0"
        config["cache"]["type_v_draft"] = "q8_0"

    return config


def write_model_config(directory: Path, config: dict[str, Any]) -> Path:
    config_path = directory / "model.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return config_path


def write_model_config_to_path(path: Path, config: dict[str, Any]) -> Path:
    """Escribe config en un path específico (per-variante).

    Asegura que server.port sea 18765 por defecto y que draft_model
    sea consistente si se especifica.
    """
    # Normalizar puerto por defecto 18765 si no se especifica
    if "server" in config and isinstance(config["server"], dict):
        if "port" not in config["server"] or not config["server"]["port"]:
            config["server"]["port"] = 18765
    else:
        config.setdefault("server", {})["port"] = 18765
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return path


def update_variant_profile(
    directory: Path, variant_file: str, overrides: dict[str, Any] | None
) -> Path:
    """Crea/actualiza o elimina (si overrides is None) el perfil de una variante.

    Guarda en model.yaml bajo clave variants: { variant_file: overrides }
    Si overrides es None o vacío, elimina la entrada.
    """
    config_path = directory / "model.yaml"
    data = load_yaml(config_path) if config_path.is_file() else {}
    variants = data.get("variants")
    if not isinstance(variants, dict):
        variants = {}
    if overrides is None or not overrides:
        variants.pop(variant_file, None)
        # También probar por basename
        base = Path(variant_file).name
        for k in list(variants.keys()):
            if Path(k).name == base:
                variants.pop(k, None)
    else:
        variants[variant_file] = overrides
    if variants:
        data["variants"] = variants
    else:
        data.pop("variants", None)
    # Escribir de vuelta preservando orden
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return config_path


def get_variant_overrides(directory: Path, variant_file: str) -> dict[str, Any] | None:
    config_path = directory / "model.yaml"
    if not config_path.is_file():
        return None
    data = load_yaml(config_path)
    variants = data.get("variants")
    if not isinstance(variants, dict):
        return None
    if variant_file in variants:
        return variants[variant_file]
    base = Path(variant_file).name
    for k, v in variants.items():
        if Path(k).name == base:
            return v
    return None


def update_model_backend_path(directory: Path, llama_path: str) -> Path:
    """Actualiza backend.llama_server_path del modelo base en model.yaml.

    Si llama_path es vacío o None, elimina la clave (vuelve a global).
    """
    config_path = directory / "model.yaml"
    data = load_yaml(config_path) if config_path.is_file() else {}
    backend = data.get("backend")
    if not isinstance(backend, dict):
        backend = {}
    if not llama_path or not str(llama_path).strip():
        backend.pop("llama_server_path", None)
        backend.pop("server_path", None)
        backend.pop("path", None)
    else:
        backend["llama_server_path"] = str(llama_path).strip()
    if backend:
        data["backend"] = backend
    else:
        data.pop("backend", None)
    # Asegurar type
    if "backend" in data and "type" not in data["backend"]:
        data["backend"]["type"] = "llama.cpp"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return config_path
