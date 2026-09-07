from __future__ import annotations

from pathlib import Path

from app.core.config_loader import (
    ConfigError,
    create_default_config,
    get_variant_overrides,
    load_model_config,
    load_yaml,
    update_variant_profile,
    write_model_config,
)
from app.models.model_definition import ModelDefinition, ModelHealth, ModelStatus


class ModelManager:
    def __init__(self, models_dir: Path) -> None:
        self._models_dir = models_dir
        self._models: list[ModelDefinition] = []
        self._unconfigured: list[tuple[Path, list[str]]] = []

    @property
    def models(self) -> list[ModelDefinition]:
        return self._models

    @property
    def unconfigured_folders(self) -> list[tuple[Path, list[str]]]:
        return self._unconfigured

    def _find_model_yamls(self, entry: Path) -> list[Path]:
        """Encuentra todos los YAMLs que son configs de modelo en una carpeta.

        Soporta:
        - model.yaml (legacy)
        - model.<variant>.yaml / <variant>.yaml (per-variante)
        - cualquier *.yaml que contenga 'model' y 'name'
        """
        yamls: list[Path] = []
        # Buscar todos los yaml en la carpeta (no recursivo)
        for p in sorted(entry.glob("*.yaml")):
            # Evitar backups
            if p.name.endswith(".bak") or p.name.endswith(".backup"):
                continue
            try:
                data = load_yaml(p)
                if isinstance(data, dict) and "model" in data:
                    yamls.append(p)
            except ConfigError:
                continue
            except Exception:
                continue
        for p in sorted(entry.glob("*.yml")):
            if p.name.endswith(".bak"):
                continue
            try:
                data = load_yaml(p)
                if isinstance(data, dict) and "model" in data:
                    yamls.append(p)
            except ConfigError:
                continue
            except Exception:
                continue
        # Ordenar: model.yaml primero si existe
        yamls_sorted: list[Path] = []
        primary = entry / "model.yaml"
        if primary in yamls:
            yamls_sorted.append(primary)
            for y in yamls:
                if y != primary:
                    yamls_sorted.append(y)
        else:
            yamls_sorted = yamls
        return yamls_sorted

    def scan(self) -> list[ModelDefinition]:
        self._models.clear()
        self._unconfigured.clear()
        if not self._models_dir.is_dir():
            return self._models

        for entry in sorted(self._models_dir.iterdir()):
            if not entry.is_dir():
                continue

            yaml_files = self._find_model_yamls(entry)
            gguf_files = self._find_gguf_files(entry)

            if yaml_files:
                # Si hay múltiples YAMLs por carpeta => modo per-variante agrupado (un card con dropdown)
                if len(yaml_files) > 1:
                    # Cargar cada YAML per-variante temporalmente
                    per_variant_temp: list[ModelDefinition] = []
                    for yp in yaml_files:
                        try:
                            tmp = load_model_config(yp)
                            per_variant_temp.append(tmp)
                        except ConfigError:
                            continue
                    if not per_variant_temp:
                        continue
                    # Elegir base: model.yaml si existe, si no el primero
                    base_model: ModelDefinition | None = None
                    primary = entry / "model.yaml"
                    for tmp in per_variant_temp:
                        if tmp.config_path and tmp.config_path.resolve() == primary.resolve():
                            base_model = tmp
                            break
                    if base_model is None:
                        base_model = per_variant_temp[0]
                    # Descubrir mains/drafts/mmprojs para la familia (usando base)
                    mains, drafts, mmprojs = self._collect_variants(base_model._gguf_dir(), entry)
                    if not mains and not drafts and not mmprojs:
                        mains2, drafts2, mmprojs2 = self._collect_variants(entry / "gguf", entry)
                        if mains2 or drafts2 or mmprojs2:
                            mains, drafts, mmprojs = mains2, drafts2, mmprojs2
                    # Construir mapa variante -> yaml path
                    variant_yaml_map: dict[str, Path] = {}
                    variant_files: list[str] = []
                    for tmp in per_variant_temp:
                        # Normalizar model.file del tmp
                        f = tmp.model.file
                        # Si el tmp tiene file que no está en mains por subcarpeta, normalizar
                        if f and f not in mains:
                            bn = Path(f).name
                            for rel in mains:
                                if Path(rel).name == bn:
                                    f = rel
                                    break
                        if f:
                            # Si f ya está en mains, usarlo; si no, usar f tal cual si existe
                            if f in mains or tmp.model_path.is_file():
                                variant_files.append(f)
                                variant_yaml_map[f] = tmp.config_path
                            else:
                                # Fallback: usar mains
                                pass
                    # Si no se pudo mapear, usar mains descubiertos
                    if not variant_files:
                        variant_files = mains
                        # Mapear cada main a su yaml si existe uno que apunte a él
                        for main in mains:
                            for tmp in per_variant_temp:
                                if tmp.model.file == main or Path(tmp.model.file).name == Path(main).name:
                                    variant_yaml_map[main] = tmp.config_path
                                    break
                    # Ordenar variant_files según mains original para consistencia
                    ordered_variants: list[str] = []
                    for main in mains:
                        if main in variant_files:
                            ordered_variants.append(main)
                    # Añadir cualquier variante que no esté en mains pero sí en mapa (por si hay)
                    for vf in variant_files:
                        if vf not in ordered_variants:
                            ordered_variants.append(vf)
                    # Si base_model.file no está en ordered, asegurarse
                    if base_model.model.file and base_model.model.file not in ordered_variants:
                        # Normalizar base file
                        bf = base_model.model.file
                        if bf not in mains:
                            bn = Path(bf).name
                            for rel in mains:
                                if Path(rel).name == bn:
                                    bf = rel
                                    break
                        if bf not in ordered_variants:
                            ordered_variants.insert(0, bf)
                            variant_yaml_map[bf] = base_model.config_path
                    # Normalizar base_model.file si es basename
                    if base_model.model.file and base_model.model.file not in ordered_variants:
                        bn = Path(base_model.model.file).name
                        for rel in ordered_variants:
                            if Path(rel).name == bn:
                                base_model.model.file = rel
                                break
                    # Asignar a familia
                    base_model.available_main_files = ordered_variants if ordered_variants else mains
                    base_model.available_draft_files = drafts
                    base_model.available_mmproj_files = mmprojs
                    base_model.variant_yaml_paths = variant_yaml_map
                    # Asegurar draft y vision normalizados para familia
                    if base_model.model.draft_model and base_model.model.draft_model not in drafts:
                        bn = Path(base_model.model.draft_model).name
                        for rel in drafts:
                            if Path(rel).name == bn:
                                base_model.model.draft_model = rel
                                break
                    if base_model.vision and base_model.vision.encoder and base_model.vision.encoder not in mmprojs:
                        bn = Path(base_model.vision.encoder).name
                        for rel in mmprojs:
                            if Path(rel).name == bn:
                                base_model.vision.encoder = rel
                                break
                    if not base_model.server.port:
                        base_model.server.port = 18765
                    base_model.check_health()
                    self._models.append(base_model)
                else:
                    # Single YAML legacy (o per-variante único)
                    config_path = yaml_files[0]
                    try:
                        model = load_model_config(config_path)
                        mains, drafts, mmprojs = self._collect_variants(model._gguf_dir(), entry)
                        if not mains and not drafts and not mmprojs:
                            mains2, drafts2, mmprojs2 = self._collect_variants(entry / "gguf", entry)
                            if mains2 or drafts2 or mmprojs2:
                                mains, drafts, mmprojs = mains2, drafts2, mmprojs2
                        if model.model.file and model.model.file not in mains:
                            base_name = Path(model.model.file).name
                            for rel in mains:
                                if Path(rel).name == base_name:
                                    model.model.file = rel
                                    break
                        if model.model.draft_model and model.model.draft_model not in drafts:
                            base_name = Path(model.model.draft_model).name
                            for rel in drafts:
                                if Path(rel).name == base_name:
                                    model.model.draft_model = rel
                                    break
                        if model.vision and model.vision.encoder and model.vision.encoder not in mmprojs:
                            base_name = Path(model.vision.encoder).name
                            for rel in mmprojs:
                                if Path(rel).name == base_name:
                                    model.vision.encoder = rel
                                    break
                        if not mains and model.model.file:
                            if model.model_path.is_file():
                                model.available_main_files = [model.model.file]
                            else:
                                model.available_main_files = mains
                        else:
                            model.available_main_files = mains
                        model.available_draft_files = drafts
                        model.available_mmproj_files = mmprojs
                        if not model.server.port:
                            model.server.port = 18765
                        model.check_health()
                        self._models.append(model)
                    except ConfigError:
                        pass
                # Resolver colisiones de nombre dentro de la misma carpeta
                seen: dict[str, int] = {}
                for m in [x for x in self._models if x.directory == entry]:
                    base = m.name
                    if base not in seen:
                        seen[base] = 1
                    else:
                        seen[base] += 1
                        # Añadir sufijo con nombre de archivo o variante
                        suffix = Path(m.model.file).stem if m.model.file else m.config_path.stem if m.config_path else f"v{seen[base]}"
                        # Evitar duplicar sufijo si ya lo tiene
                        if suffix not in m.name:
                            m.name = f"{base} ({suffix})"
                            # También actualizar alias si es igual al base
                            if m.server.alias == base:
                                m.server.alias = m.name.replace(" ", "_")
            elif gguf_files:
                self._unconfigured.append((entry, gguf_files))

        return self._models

    def _collect_variants(self, gguf_base: Path, folder: Path) -> tuple[list[str], list[str], list[str]]:
        """Descubre recursivamente todos los GGUFs bajo gguf_base y los clasifica.

        Returns:
            (mains, drafts, mmprojs) como listas de paths relativos a gguf_base.
            Si gguf_base no existe, intenta buscar bajo folder.
        """
        mains: list[str] = []
        drafts: list[str] = []
        mmprojs: list[str] = []

        base = gguf_base if gguf_base.is_dir() else (folder / "gguf" if (folder / "gguf").is_dir() else folder)
        if not base.is_dir():
            return mains, drafts, mmprojs

        for p in sorted(base.rglob("*.gguf")):
            # Evitar cache de huggingface
            if ".cache" in p.parts:
                continue
            try:
                rel = p.relative_to(base).as_posix()
            except ValueError:
                rel = p.name
            lower_name = p.name.lower()
            if "mmproj" in lower_name:
                mmprojs.append(rel)
            elif "mtp" in lower_name or "draft" in lower_name:
                drafts.append(rel)
            elif lower_name.endswith(".gguf"):
                mains.append(rel)
        return mains, drafts, mmprojs

    def get_by_name(self, name: str) -> ModelDefinition | None:
        for m in self._models:
            if m.name == name:
                return m
        return None

    def get_running(self) -> list[ModelDefinition]:
        return [m for m in self._models if m.status == ModelStatus.RUNNING]

    def get_by_port(self, port: int) -> ModelDefinition | None:
        for m in self._models:
            if m.server.port == port and m.status == ModelStatus.RUNNING:
                return m
        return None

    def create_config_for_folder(
        self, folder: Path, gguf_files: list[str], port: int = 18765
    ) -> ModelDefinition:
        # Siempre usar 18765 por defecto a menos que se especifique otro
        if not port:
            port = 18765
        # Si hay múltiples GGUFs principales, crear YAML por variante (per-variante)
        # Clasificar ggufs para detectar mains
        mains: list[str] = []
        drafts: list[str] = []
        mmprojs: list[str] = []
        for f in gguf_files:
            bn = Path(f).name.lower()
            if "mmproj" in bn:
                mmprojs.append(f)
            elif "mtp" in bn or "draft" in bn:
                drafts.append(f)
            elif f.lower().endswith(".gguf"):
                mains.append(f)
        # Si hay múltiples mains, crear un YAML por cada main (per-variante)
        if len(mains) > 1:
            # Usar el mismo draft para todas las cuantizaciones (MTP compartido)
            draft_file = drafts[0] if drafts else ""
            created: list[ModelDefinition] = []
            for main in mains:
                # Crear config base para este main + draft compartido
                single_ggufs = [main]
                if draft_file:
                    single_ggufs.append(draft_file)
                if mmprojs:
                    single_ggufs.extend(mmprojs)
                config = create_default_config(folder.name, single_ggufs, folder)
                # Asegurar file correcto y draft compartido
                config["model"]["file"] = main
                if draft_file:
                    config["model"]["draft_model"] = draft_file
                    # Asegurar speculative habilitado si hay draft
                    config.setdefault("speculative", {})["enabled"] = True
                    config["speculative"].setdefault("spec_type", "draft-mtp")
                    config["speculative"].setdefault("draft_n_max", 3)
                # Nombre único por variante
                variant_stem = Path(main).stem
                # Si el nombre base es igual al folder, añadir sufijo
                base_name = folder.name
                # Crear nombre como "Base (variant)"
                config["name"] = f"{base_name} ({variant_stem})"
                config["server"]["port"] = port
                config["server"]["alias"] = f"{base_name}_{variant_stem}".replace(" ", "_").replace("-", "_")[:32]
                # Escribir en archivo por variante: model.<variant>.yaml
                safe_variant = variant_stem.replace(" ", "_").replace("/", "_")
                out_path = folder / f"model.{safe_variant}.yaml"
                # Evitar colisión, si existe añadir sufijo
                counter = 1
                orig = out_path
                while out_path.exists():
                    out_path = folder / f"model.{safe_variant}_{counter}.yaml"
                    counter += 1
                from app.core.config_loader import write_model_config_to_path

                write_model_config_to_path(out_path, config)
                model = load_model_config(out_path)
                m2, d2, mm2 = self._collect_variants(model._gguf_dir(), folder)
                model.available_main_files = m2
                model.available_draft_files = d2
                model.available_mmproj_files = mm2
                model.check_health()
                self._models.append(model)
                created.append(model)
            self._unconfigured = [(p, f) for p, f in self._unconfigured if p != folder]
            # Retornar el primero por compatibilidad
            return created[0] if created else None
        # Caso single GGUF: comportamiento clásico
        config = create_default_config(folder.name, gguf_files, folder)
        config["server"]["port"] = port
        write_model_config(folder, config)
        model = load_model_config(folder / "model.yaml")
        mains, drafts, mmprojs = self._collect_variants(model._gguf_dir(), folder)
        if not mains and not drafts and not mmprojs:
            mains2, drafts2, mmprojs2 = self._collect_variants(folder / "gguf", folder)
            if mains2 or drafts2 or mmprojs2:
                mains, drafts, mmprojs = mains2, drafts2, mmprojs2
        model.available_main_files = mains
        model.available_draft_files = drafts
        model.available_mmproj_files = mmprojs
        model.check_health()
        self._models.append(model)
        self._unconfigured = [(p, f) for p, f in self._unconfigured if p != folder]
        return model

    def save_variant_profile(
        self, model: ModelDefinition, variant_file: str, overrides: dict | None
    ) -> bool:
        """Guarda perfil para una variante.

        - Per-variante agrupado: si variant_file tiene YAML específico en variant_yaml_paths,
          edita ese YAML directamente.
        - Per-variante individual (múltiples yamls): edita su propio config_path.
        - Legacy: single model.yaml con variants dict.
        """
        try:
            # Caso agrupado: variant_file tiene YAML per-variante
            target_yaml: Path | None = None
            if variant_file and variant_file in model.variant_yaml_paths:
                target_yaml = model.variant_yaml_paths[variant_file]
            elif variant_file:
                # Buscar por basename
                base = Path(variant_file).name
                for k, v in model.variant_yaml_paths.items():
                    if Path(k).name == base:
                        target_yaml = v
                        break
            # Si es familia con múltiples yamls y hay target, editar ese YAML
            if target_yaml and target_yaml.is_file():
                from app.core.config_loader import load_yaml
                import yaml

                data = load_yaml(target_yaml)
                if overrides is None or not overrides:
                    return True
                for section, values in overrides.items():
                    if not isinstance(values, dict):
                        continue
                    if section not in data or not isinstance(data[section], dict):
                        data[section] = {}
                    for k, v in values.items():
                        data[section][k] = v
                with open(target_yaml, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                # Recargar familia y actualizar cache per-variante
                # Invalidar cache
                if variant_file in model.per_variant_cache:
                    del model.per_variant_cache[variant_file]
                # Recargar el per-variante específico para verificar
                from app.core.config_loader import load_model_config

                # No reemplazar toda la familia, solo invalidar cache; la familia sigue igual
                # Pero para UI, actualizar familia con nuevos datos si es el base
                return True
            # Detectar si es per-variante individual (múltiples yamls pero modelo es uno de ellos)
            yamls = self._find_model_yamls(model.directory)
            is_per_variant = len(yamls) > 1 or (model.config_path and model.config_path.name != "model.yaml")
            if is_per_variant and model.config_path and model.config_path.is_file():
                # Si variant_file == model.file o es el mismo, editar su propio YAML
                if variant_file == model.model.file or Path(variant_file).name == Path(model.model.file).name:
                    from app.core.config_loader import load_yaml
                    import yaml

                    data = load_yaml(model.config_path)
                    if overrides is None or not overrides:
                        return True
                    for section, values in overrides.items():
                        if not isinstance(values, dict):
                            continue
                        if section not in data or not isinstance(data[section], dict):
                            data[section] = {}
                        for k, v in values.items():
                            data[section][k] = v
                    with open(model.config_path, "w", encoding="utf-8") as f:
                        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                    new_model = load_model_config(model.config_path)
                    new_model.available_main_files = list(model.available_main_files)
                    new_model.available_draft_files = list(model.available_draft_files)
                    new_model.available_mmproj_files = list(model.available_mmproj_files)
                    new_model.variant_yaml_paths = dict(model.variant_yaml_paths)
                    new_model.per_variant_cache = dict(model.per_variant_cache)
                    new_model.status = model.status
                    new_model.health = model.health
                    new_model.pid = model.pid
                    for i, m in enumerate(self._models):
                        if m.config_path == model.config_path:
                            self._models[i] = new_model
                            break
                        if m.name == model.name and m.directory == model.directory and m.config_path == model.config_path:
                            self._models[i] = new_model
                            break
                    return True
            # Legacy: single model.yaml con variants
            update_variant_profile(model.directory, variant_file, overrides)
            cfg_path = model.config_path if model.config_path and model.config_path.is_file() else model.directory / "model.yaml"
            new_model = load_model_config(cfg_path)
            new_model.available_main_files = list(model.available_main_files)
            new_model.available_draft_files = list(model.available_draft_files)
            new_model.available_mmproj_files = list(model.available_mmproj_files)
            new_model.variant_yaml_paths = dict(model.variant_yaml_paths)
            new_model.per_variant_cache = dict(model.per_variant_cache)
            new_model.status = model.status
            new_model.health = model.health
            new_model.pid = model.pid
            for i, m in enumerate(self._models):
                if m.name == model.name:
                    self._models[i] = new_model
                    break
            return True
        except Exception:
            return False

    def save_backend_path(self, model: ModelDefinition, llama_path: str | None) -> bool:
        """Guarda backend.llama_server_path.

        Per-variante: guarda solo en el YAML de esa variante.
        Legacy: guarda en model.yaml.
        """
        try:
            from app.core.config_loader import update_model_backend_path

            target_path = model.config_path if model.config_path and model.config_path.is_file() else model.directory / "model.yaml"
            # Si es per-variante, editar solo ese archivo
            yamls = self._find_model_yamls(model.directory)
            is_per_variant = len(yamls) > 1 or (model.config_path and model.config_path.name != "model.yaml")
            if is_per_variant and model.config_path and model.config_path.is_file():
                from app.core.config_loader import load_yaml
                import yaml

                data = load_yaml(model.config_path)
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
                if "backend" in data and "type" not in data["backend"]:
                    data["backend"]["type"] = "llama.cpp"
                with open(model.config_path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                new_model = load_model_config(model.config_path)
                new_model.available_main_files = list(model.available_main_files)
                new_model.available_draft_files = list(model.available_draft_files)
                new_model.available_mmproj_files = list(model.available_mmproj_files)
                new_model.variant_yaml_paths = dict(model.variant_yaml_paths)
                new_model.per_variant_cache = dict(model.per_variant_cache)
                new_model.status = model.status
                new_model.health = model.health
                new_model.pid = model.pid
                for i, m in enumerate(self._models):
                    if m.config_path == model.config_path:
                        self._models[i] = new_model
                        break
                return True
            # Legacy
            update_model_backend_path(model.directory, llama_path or "")
            new_model = load_model_config(target_path)
            new_model.available_main_files = list(model.available_main_files)
            new_model.available_draft_files = list(model.available_draft_files)
            new_model.available_mmproj_files = list(model.available_mmproj_files)
            new_model.variant_yaml_paths = dict(model.variant_yaml_paths)
            new_model.per_variant_cache = dict(model.per_variant_cache)
            new_model.status = model.status
            new_model.health = model.health
            new_model.pid = model.pid
            for i, m in enumerate(self._models):
                if m.name == model.name:
                    self._models[i] = new_model
                    break
            return True
        except Exception:
            return False

    def get_effective_model(self, model: ModelDefinition, variant_file: str | None = None) -> ModelDefinition:
        """Retorna modelo efectivo para una variante.

        Prioridad:
        1. YAML per-variante (variant_yaml_paths)
        2. Perfil variants dict (legacy)
        3. Copia con solo file cambiado
        """
        v = variant_file or model.model.file
        # Per-variante YAML primero
        if model.variant_yaml_paths:
            # Búsqueda exacta
            if v in model.variant_yaml_paths:
                return model.get_for_variant_yaml(v)
            # Por basename
            base = Path(v).name if v else ""
            for k in model.variant_yaml_paths:
                if Path(k).name == base:
                    return model.get_for_variant_yaml(k)
        if model.has_variant_profile(v):
            return model.get_for_variant(v)
        if v != model.model.file:
            return model.get_for_variant(v)
        return model

    def validate_model(self, model: ModelDefinition) -> list[str]:
        errors: list[str] = []
        if not model.model_path.is_file():
            errors.append(f"Archivo del modelo no encontrado:\n{model.model_path}")
        if model.capabilities.vision and model.vision:
            enc = model.vision_encoder_path
            if enc is None or not enc.is_file():
                errors.append(f"Encoder de visión no encontrado:\n{enc}")
        if model.model.draft_model:
            draft = model.draft_model_path
            if draft is None or not draft.is_file():
                errors.append(f"Modelo draft no encontrado:\n{draft}")
        return errors

    def _find_gguf_files(self, folder: Path) -> list[str]:
        """Encuentra todos los .gguf de forma recursiva para mostrar carpetas sin config.

        Retorna lista de paths relativos (incluye subcarpetas) para que create_default_config
        pueda clasificar correctamente. Filtra .cache.
        """
        gguf_files: list[str] = []
        gguf_dir = folder / "gguf"
        base = gguf_dir if gguf_dir.is_dir() else folder
        if not base.is_dir():
            return gguf_files
        for p in sorted(base.rglob("*.gguf")):
            if ".cache" in p.parts:
                continue
            try:
                rel = p.relative_to(base).as_posix()
            except ValueError:
                rel = p.name
            gguf_files.append(rel)
        return gguf_files
