from __future__ import annotations

import re
from pathlib import Path

from app.models.model_definition import ModelDefinition


class CommandBuilder:
    def __init__(self, server_path: Path) -> None:
        self._server_path = server_path

    def get_effective_server_path(self, model: ModelDefinition) -> Path:
        """Resuelve el binario a usar para este modelo (per-model override)."""
        try:
            eff = model
            # Prioridad: YAML per-variante > perfil variants legacy
            if hasattr(model, "get_effective_model"):
                try:
                    eff = model.get_effective_model(model.model.file)
                except Exception:
                    eff = model
            elif hasattr(model, "has_variant_profile") and model.has_variant_profile(model.model.file):
                eff = model.get_for_variant(model.model.file)
            if hasattr(eff, "get_effective_llama_server_path"):
                return eff.get_effective_llama_server_path(self._server_path)
        except Exception:
            pass
        return self._server_path

    def build(self, model: ModelDefinition) -> list[str]:
        # Resolver binario por modelo (soporta backend.llama_server_path per-model/variant)
        eff_model = model
        try:
            if hasattr(model, "get_effective_model"):
                eff_model = model.get_effective_model(model.model.file)
            elif hasattr(model, "has_variant_profile") and model.has_variant_profile(model.model.file):
                eff_model = model.get_for_variant(model.model.file)
        except Exception:
            eff_model = model
        server_path = self.get_effective_server_path(eff_model)
        args: list[str] = [str(server_path)]
        # Usar eff_model para el resto de la configuración si tiene perfil por variante
        model = eff_model

        args.extend(["-m", str(model.model_path)])

        if model.server.alias:
            args.extend(["-a", model.server.alias])

        hw = model.hardware
        gpu = hw.gpu_layers
        if gpu == -1:
            args.extend(["--n-gpu-layers", "all"])
        elif isinstance(gpu, int) and gpu > 0:
            args.extend(["--n-gpu-layers", str(gpu)])

        args.extend(["--fit", "off"])

        if hw.context_size > 0:
            args.extend(["-c", str(hw.context_size)])

        if hw.batch_size > 0:
            args.extend(["-b", str(hw.batch_size)])

        if hw.micro_batch > 0:
            args.extend(["-ub", str(hw.micro_batch)])

        if hw.tensor_split:
            args.extend(["--tensor-split", hw.tensor_split])

        adv = model.advanced

        if adv.reasoning:
            args.extend(["--reasoning", "on"])

        cache = model.cache
        if cache.type_k:
            args.extend(["--cache-type-k", cache.type_k])
        if cache.type_v:
            args.extend(["--cache-type-v", cache.type_v])

        spec = model.speculative
        draft_path = model.draft_model_path
        has_valid_draft = draft_path is not None and draft_path.is_file()
        # Determinar si la VARIANTE seleccionada realmente tiene MTP
        # Usa variant_has_mtp para que nomtp/ no intente usar spec y pueda bootear
        has_mtp = False
        try:
            # Preferir chequeo por variante específica
            if hasattr(model, "variant_has_mtp"):
                has_mtp = bool(model.variant_has_mtp(model.model.file))
                # Si variante no tiene MTP pero el modelo global sí, respetar variante
                # (ej Qwen 35B nomtp debe bootear sin spec)
                if not has_mtp:
                    has_mtp = False
                else:
                    # Variante tiene MTP, verificar que spec esté habilitado si es integrado
                    # has_mtp ya incluye chequeo de spec para integrado via variant_has_mtp fallback
                    pass
            else:
                has_mtp = bool(getattr(model, "mtp_enabled", False))
            # Fallback adicional por si variant_has_mtp no detecta integrado pero spec está activo
            if not has_mtp and spec.enabled and "mtp" in (spec.spec_type or "").lower():
                # Solo considerar integrado si la variante no es explícitamente nomtp
                if hasattr(model, "variant_has_mtp"):
                    if model.variant_has_mtp(model.model.file):
                        has_mtp = True
                else:
                    has_mtp = has_valid_draft or bool(getattr(model, "has_mtp_available", False))
        except Exception:
            has_mtp = has_valid_draft

        # Solo enviar --model-draft si hay MTP real en la variante y draft válido.
        if has_mtp and has_valid_draft:
            args.extend(["--model-draft", str(draft_path)])
            if cache.type_k_draft:
                args.extend(["--cache-type-k-draft", cache.type_k_draft])
            if cache.type_v_draft:
                args.extend(["--cache-type-v-draft", cache.type_v_draft])
            dgl = getattr(adv, "draft_gpu_layers", -1)
            if isinstance(dgl, str) and dgl.lower() == "all":
                dgl = -1
            if isinstance(dgl, int):
                if dgl == 0:
                    args.extend(["--n-gpu-layers-draft", "0"])
                elif dgl > 0:
                    args.extend(["--n-gpu-layers-draft", str(dgl)])

        # MTP / speculative: solo si el modelo tiene MTP real.
        # Si no tiene MTP, se obvian --spec-type y --spec-draft-n-max para permitir boot.
        # Para MTP integrado (sin draft file) sigue siendo válido enviar --spec-type sin --model-draft.
        if has_mtp:
            if spec.enabled and spec.spec_type:
                args.extend(["--spec-type", spec.spec_type])
            if spec.enabled and spec.draft_n_max > 0:
                args.extend(["--spec-draft-n-max", str(spec.draft_n_max)])
        else:
            # Debug opcional: si yaml tenía spec habilitado pero modelo no tiene MTP, lo ignoramos silenciosamente
            # Para trazabilidad, podríamos loguear
            pass

        if adv.fit:
            args.extend(["--fit", adv.fit])

        if adv.ncmoe > 0:
            args.extend(["-ncmoe", str(adv.ncmoe)])

        if cache.unified:
            args.append("--kv-unified")

        sp = model.sampling
        args.extend(["--temp", str(sp.temperature)])
        args.extend(["--top-p", str(sp.top_p)])
        if sp.top_k > 0:
            args.extend(["--top-k", str(sp.top_k)])
        if sp.min_p > 0:
            args.extend(["--min-p", str(sp.min_p)])
        args.extend(["--presence-penalty", str(sp.presence_penalty)])
        args.extend(["--repeat-penalty", str(sp.repeat_penalty)])

        if adv.parallel > 1:
            args.extend(["--parallel", str(adv.parallel)])
        elif adv.parallel == 1:
            args.extend(["-np", "1"])

        if adv.log_verbosity > 0:
            args.extend(["--log-verbosity", str(adv.log_verbosity)])
        elif adv.log_verbosity == 0 and model.server.port:
            args.extend(["-lv", "4"])

        if model.capabilities.vision and model.vision:
            enc = model.vision_encoder_path
            if enc:
                args.extend(["-mm", str(enc)])
            if model.vision.image_min_tokens > 0:
                args.extend(["--image-min-tokens", str(model.vision.image_min_tokens)])

        if adv.flash_attention:
            args.extend(["--flash-attn", "on"])

        # cache-ram limita RAM del prompt cache (default 8192) - baja a 4096 para 32GB con 83% uso
        if hasattr(adv, "cache_ram") and adv.cache_ram is not None:
            args.extend(["--cache-ram", str(adv.cache_ram)])

        # System prompt: parchea chat_template para que default_system_prompt use el YAML
        # llama-server no tiene --system-prompt, se inyecta vía --chat-template-file
        if model.system_prompt:
            tpl_path = self._ensure_patched_template(model)
            if tpl_path and tpl_path.is_file():
                args.extend(["--chat-template-file", str(tpl_path)])

        args.extend(["--host", model.server.host])
        args.extend(["--port", str(model.server.port)])

        return args

    def validate_server(self) -> bool:
        return self._server_path.is_file()

    def validate_server_for_model(self, model: ModelDefinition) -> tuple[bool, Path]:
        """Valida el binario efectivo para un modelo específico.

        Retorna (existe, path_efectivo).
        """
        eff_path = self.get_effective_server_path(model)
        return eff_path.is_file(), eff_path

    def _ensure_patched_template(self, model: ModelDefinition) -> Path | None:
        """Genera un archivo Jinja parcheado con system_prompt del YAML.

        Extrae el chat_template del GGUF y reemplaza el bloque
        {%- set default_system_prompt -%}...{%- endset -%} por el
        system_prompt del YAML. Si no se encuentra el bloque, intenta
        un reemplazo genérico de fecha o crea un wrapper mínimo.
        Retorna Path al archivo generado o None si falla.
        """
        try:
            prompt = model.system_prompt.strip()
            if not prompt:
                return None
            out_path = model.directory / f".chat_template.{model.server.alias}.jinja"
            # Si ya existe y coincide, reusar (evita reescribir si no cambió)
            if out_path.is_file():
                try:
                    existing = out_path.read_text(encoding="utf-8")
                    if prompt in existing:
                        return out_path
                except Exception:
                    pass
            raw = self._extract_template_from_gguf(model.model_path)
            patched: str | None = None
            if raw and "default_system_prompt" in raw:
                # Reemplaza bloque default_system_prompt
                pattern = re.compile(
                    r"{%- set default_system_prompt -%}.*?{%- endset -%}",
                    re.DOTALL,
                )
                replacement = "{%- set default_system_prompt -%}\n" + prompt + "\n{%- endset -%}"
                patched, n = pattern.subn(replacement, raw, count=1)
                if n == 0:
                    # Fallback: intenta reemplazar solo el contenido entre set/endset con split
                    patched = None
            if patched is None and raw:
                # Fallback genérico: reemplaza fecha vieja si existe
                # GGUF trae 2026-07-14, YAML trae 2026-09-04
                if "2026-07-14" in raw and "2026-09-04" in prompt:
                    patched = raw.replace("2026-07-14", "2026-09-04")
                    # Además inyecta prompt completo si no coincide
                    if prompt not in patched:
                        # Intenta reemplazar bloque igualmente
                        m = re.search(r"You are Intern-A1.*?(?={%- endset)", raw, re.DOTALL)
                        if m:
                            patched = raw.replace(m.group(0), prompt + "\n")
                else:
                    # Si no hay default_system_prompt, crea wrapper que prepend system
                    # Usa raw como base pero prepende lógica de inyección
                    # Minimal: anteponer set default_system_prompt
                    patched = "{%- set default_system_prompt -%}\n" + prompt + "\n{%- endset -%}\n" + raw
            if patched is None:
                # Último fallback: genera template mínimo funcional
                # No intenta replicar tool logic completo, solo system + messages
                patched = (
                    "{%- set default_system_prompt -%}\n"
                    + prompt
                    + "\n{%- endset -%}\n"
                    "{%- set system_content = default_system_prompt %}\n"
                    "{%- if messages and messages[0].role == 'system' %}\n"
                    "  {%- set system_content = messages[0].content %}\n"
                    "{%- endif %}\n"
                    "{%- if system_content %}<|im_start|>system\n{{ system_content }}<|im_end|>\n{%- endif %}\n"
                    "{%- for message in messages %}\n"
                    "  {%- if message.role != 'system' %}<|im_start|>{{ message.role }}\n{{ message.content }}<|im_end|>\n{%- endif %}\n"
                    "{%- endfor %}\n"
                    "{%- if add_generation_prompt %}<|im_start|>assistant\n{%- endif %}\n"
                )
            out_path.write_text(patched, encoding="utf-8")
            return out_path
        except Exception as e:
            # No romper el build si falla parcheo; log a stdout para diagnóstico
            try:
                print(f"[CommandBuilder] system_prompt patch failed: {e}")
            except Exception:
                pass
            return None

    def _extract_template_from_gguf(self, gguf_path: Path) -> str | None:
        """Extrae chat_template del GGUF leyendo bytes crudos.

        Busca la clave 'chat_template' y luego el primer '{%' posterior.
        Lee ventana de 32KB que suele contener el template completo (~8K).
        """
        try:
            if not gguf_path.is_file():
                return None
            data = gguf_path.read_bytes()
            idx = data.find(b"chat_template")
            if idx == -1:
                return None
            # Ventana de búsqueda amplia (32K)
            window = data[idx : idx + 32768]
            # Busca inicio Jinja
            start = window.find(b"{%")
            if start == -1:
                start = window.find(b"{{")
                if start == -1:
                    return None
            # Extrae desde start hasta posible terminador (busca null o hasta 20K)
            snippet = window[start : start + 20000]
            # Corta en primer null byte si existe (fin de string GGUF)
            null = snippet.find(b"\x00")
            if null != -1:
                snippet = snippet[:null]
            # Decodifica
            try:
                txt = snippet.decode("utf-8", errors="ignore")
            except Exception:
                txt = snippet.decode("utf-8", errors="replace")
            # Valida que contenga marcadores esperados
            if "<|im_start|>" in txt or "messages" in txt:
                # Limpia caracteres de relleno al final (puede traer basura)
                # Jinja termina típicamente con 'endif' o similar; corta en último '%}' o '}}'
                # Busca último '%}' significativo
                last = txt.rfind("%}")
                if last != -1 and last > len(txt) - 500:
                    txt = txt[: last + 2]
                # También intenta encontrar fin coherente para Agents-A1 (observado 8114 chars)
                return txt.strip()
            return txt.strip() if txt.strip().startswith("{%") else None
        except Exception:
            return None
