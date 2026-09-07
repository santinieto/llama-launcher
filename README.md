# Local LLM Manager

Aplicación de escritorio para administrar y ejecutar modelos de inteligencia artificial localmente mediante [`llama.cpp`](https://github.com/ggml-org/llama.cpp).

Centraliza la gestión de modelos GGUF, evita múltiples `.bat` y permite lanzar `llama-server` con la configuración correcta desde una GUI.

La aplicación detecta automáticamente los modelos disponibles en `models/`, lee su `model.yaml` (y variantes) y construye el comando de `llama-server`.

---

## Objetivo

Cada modelo de `llama.cpp` puede requerir configuración distinta:

* Archivo y cuantización (`Q4_K_M`, `IQ1_M`, `Q2_K_XL`, etc.)
* `gpu_layers`, `context_size`, `batch_size`, `micro_batch`
* MoE (`n_expert_used`), `ncmoe`
* MTP / draft model (`spec_type: draft-mtp`, `draft_n_max`)
* Vision encoder (`mmproj`)
* Chat template / `system_prompt`
* Sampling (`temperature`, `top_p`, `top_k`, `min_p`)
* Puerto `host:port`

Sin un gestor, esa configuración queda dispersa en `.bat` y es difícil de mantener. Este proyecto la centraliza en YAML por modelo.

---

## Características actuales

Implementado en `app/`:

* **Auto-discovery** recursivo en `models/` (`app/core/model_manager.py:62`). Soporta:
  * `model.yaml` único (legacy)
  * Múltiples `model.<variant>.yaml` / `model.<cuantización>.yaml` en la misma carpeta → una sola tarjeta con dropdown de variantes (`app/core/model_manager.py:89`)
  * `gguf/`, `gguf/mtp/`, `gguf/nomtp/` con detección de `mains` vs `drafts` vs `mmproj` (`model_manager.py:262`)
* **Per-variante YAML + perfiles**: cada cuantización puede tener su propio YAML (`variant_yaml_paths` `model_manager.py:180`). Además, botón `⚙` por variante permite guardar overrides sin editar manualmente (`save_variant_profile` `model_manager.py:398`).
* **MTP auto-detectado**: si existe draft o `nextn_predict_layers`, se envía `--spec-type draft-mtp` y `--model-draft` solo cuando corresponde (`app/core/command_builder.py:112`). Evita el error `failed to create MTP context` de variantes `nomtp`.
* **Backend por modelo**: `backend.llama_server_path` permite usar un `llama-server.exe` distinto por modelo (`command_builder.py:11`, `main_window.py:267`, `model_manager.py:505`).
* **GUI PySide6** (`app/gui/main_window.py:30`):
  * Header con `Settings` (rutas globales) y `↻ Recargar Configs` (F5) (`main_window.py:100`)
  * Panel izquierdo: tarjetas de modelos con dropdown de variantes, estado `READY/ERROR/RUNNING`, `MTP: on/off`, botón `Launch/Stop`, `⚙` perfil y `Runtime`
  * Panel derecho: `Terminal — Logs` en vivo (`LogViewer` `app/gui/log_viewer.py:1`) + indicador `LIVE/RUNNING/ERROR`
  * Status bar con `VRAM/RAM` y contador `X configurados • Y nuevos • MTP en Z`
* **Validación** antes de lanzar: existe `model_path`, `llama-server.exe`, puerto libre, `draft` y `vision` (`model_manager.py:598`).
* **Construcción de comando** completa: `--n-gpu-layers`, `-c`, `-b`, `-ub`, `--cache-type-k/v`, `--spec-type`, `--cache-ram`, `-ncmoe`, `sampling`, `--host/--port`, `--reasoning`, `--chat-template-file` si hay `system_prompt` (`command_builder.py:44`).
* **Gestión de proceso**: `start/stop`, captura `stdout/stderr` a `logs/<modelo>/YYYY-MM-DD_HH-MM-SS.log`, detección `model loaded` y `server listening` (`app/core/process_manager.py`).

---

## Estructura del proyecto

```text
.
├── app/
│   ├── main.py                 # entry point, resuelve config/app.yaml
│   ├── core/
│   │   ├── model_manager.py    # discovery + variantes + health
│   │   ├── config_loader.py    # YAML loader/validator
│   │   ├── command_builder.py  # YAML → args llama-server
│   │   └── process_manager.py  # spawn/monitor llama-server
│   ├── gui/
│   │   ├── main_window.py      # ventana principal
│   │   ├── model_view.py       # ModelCard + VariantProfileDialog
│   │   ├── log_viewer.py
│   │   └── settings_view.py    # diálogo rutas globales
│   └── models/
│       └── model_definition.py
├── models/                     # NO se sube *.gguf (225GB) - ver .gitignore
│   ├── Qwen3.5-32B-A3B/
│   │   ├── model.yaml                          # base
│   │   ├── model.mtp_Qwen3.6-35B-A3B-UD-IQ1_M.yaml  # per-variante
│   │   ├── model.mtp_...IQ3_S.yaml
│   │   └── gguf/
│   │       ├── mtp/Qwen3.6-35B-...IQ1_M.gguf
│   │       ├── mtp/...Q4_K_XL.gguf
│   │       └── nomtp/...Q2_K_XL.gguf
│   ├── Qwen3.8-27B/
│   └── ...
├── llama.cpp/                  # binarios NO incluidos (ver Instalación)
│   └── llama-server.exe
├── config/
│   ├── app.yaml                # rutas relativas (para repo)
│   └── app.local.yaml          # tu local con rutas absolutas (ignorado)
├── logs/                       # generado en ejecución (ignorado)
├── build.py                    # PyInstaller
├── pyproject.toml
└── requirements.txt
```

> `llama.cpp/` es dependencia externa. La app permite configurar la ruta en `config/app.yaml` o por modelo en `backend.llama_server_path`.

---

## Modelos

Cada modelo vive en su carpeta. Ejemplo real:

```text
models/Qwen3.5-32B-A3B/
  gguf/mtp/Qwen3.6-35B-A3B-UD-IQ1_M.gguf
  gguf/mtp/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf
  gguf/nomtp/Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf
  model.yaml
  model.mtp_Qwen3.6-35B-A3B-UD-IQ1_M.yaml
  model.mtp_Qwen3.6-35B-A3B-UD-Q4_K_XL.yaml
```

La app agrupa todos los `model*.yaml` de la carpeta en una sola tarjeta. El dropdown lista `available_main_files` y el YAML seleccionado es el efectivo.

Agregar un modelo:
1. Crear `models/mi-modelo/`
2. Copiar `.gguf` (en `gguf/` o directo)
3. Copiar/crear `model.yaml` (o dejar que la GUI lo cree para carpetas sin config → tarjeta "sin configurar")
4. Abrir la app → aparece automáticamente → `Launch`

---

## Configuración de modelos

Formato YAML (ejemplo real de `models/Qwen3.5-32B-A3B/model.mtp_Qwen3.6-35B-A3B-UD-IQ1_M.yaml`):

```yaml
name: Qwen 3.5 35B A3B (Qwen3.6-35B-A3B-UD-IQ1_M)
description: Qwen 3.5 35B A3B
backend:
  type: llama.cpp
  # llama_server_path: D:/custom/llama-server.exe  # opcional por modelo
model:
  file: mtp/Qwen3.6-35B-A3B-UD-IQ1_M.gguf
  format: gguf
server:
  host: 127.0.0.1
  port: 18765
  alias: Qwen3.5_35B_A3B_Qwen3.6_35B_A3B_UD_IQ1_M
hardware:
  gpu_layers: all
  context_size: 32768
  batch_size: 2048
cache:
  type_k: q4_0
  type_v: q4_0
speculative:
  enabled: true
  spec_type: draft-mtp
  draft_n_max: 2
sampling:
  temperature: 1.0
  top_p: 0.95
  top_k: 64
  min_p: 0.0
  presence_penalty: 0.0
  repeat_penalty: 1.0
capabilities:
  vision: false
advanced:
  reasoning: true
  cache_ram: 4096
  ncmoe: 32
  parallel: 1
  log_verbosity: 4
```

La app lo traduce a:

```text
llama-server.exe -m models/Qwen3.5-32B-A3B/gguf/mtp/Qwen3.6-35B-A3B-UD-IQ1_M.gguf
  -a Qwen3.5_35B_A3B_Qwen3.6_35B_A3B_UD_IQ1_M --n-gpu-layers all --fit off
  -c 32768 -b 2048 --reasoning on --cache-type-k q4_0 --cache-type-v q4_0
  --spec-type draft-mtp --spec-draft-n-max 2 -ncmoe 32 --temp 1.0 --top-p 0.95
  --top-k 64 -np 1 --log-verbosity 4 --cache-ram 4096 --host 127.0.0.1 --port 18765
```

### Vision

```yaml
capabilities:
  vision: true
vision:
  encoder: mmproj-model-f16.gguf
  image_min_tokens: 0
```
Se añade automáticamente `-mm <encoder>` si existe.

---

## Interfaz gráfica

* **Header**: `Local LLM Manager • llama.cpp • gestión local de modelos GGUF • MTP auto-detectado` + `Settings` + `Recargar Configs`
* **Lista de modelos**: cada tarjeta muestra `nombre`, `cuantización`, `context`, `GPU layers`, `MTP`, `health`, dropdown de variantes y botones `Launch/Stop` + `⚙` para perfil por variante.
* **Logs**: `Terminal — Logs` con streaming `stdout/stderr` de `llama-server`, indicador `● LIVE / ◐ STARTING / ● RUNNING / ● ERROR`.
* **Atajos**: `F5` recarga configs desde disco sin reiniciar.

Al lanzar se valida: archivo existe, `llama-server` existe, puerto libre (`app/gui/main_window.py:410`).

---

## Configuración global

`config/app.yaml` (rutas relativas para el repo):

```yaml
llama_server_path: "./llama.cpp/llama-server.exe"
models_directory: "./models"
logs_directory: "./logs"
default_host: "127.0.0.1"
default_port: 18765
```

Para uso local con rutas absolutas, edita `config/app.local.yaml` (ignorado por git). `app/main.py:28` resuelve ambas.

También se puede configurar desde la GUI: `Settings` → `llama-server` y `models_dir` (`main_window.py:513`).

---

## Instalación

Requisitos: `Python >=3.12`, `llama.cpp` build con CUDA (según tu GPU).

```powershell
git clone https://github.com/santinieto/llama-launcher.git
Set-Location llama-launcher
pip install -r requirements.txt
# o pip install -e .

# 1. Descarga llama.cpp binarios (ej. release) a llama.cpp/llama-server.exe
#    https://github.com/ggml-org/llama.cpp/releases
# 2. Copia modelos GGUF a models/<nombre>/gguf/
# 3. Ajusta config/app.yaml si es necesario
python -m app.main
# o local-llm-manager (si instalaste via pyproject.toml)
```

Build ejecutable:

```powershell
python build.py  # genera dist/LocalLLMManager/
```

> Modelos `*.gguf` (225GB), `llama.cpp/*.dll` (`cublas`, `ggml-cuda` ~1GB), `logs/` y `dist/build/` están ignorados en `.gitignore:1`.

---

## Arquitectura

```text
GUI (main_window, model_view, log_viewer)
  │
  ├─ ModelManager  (discovery, per-variante agrupado, _collect_variants, health)
  ├─ ConfigLoader  (load_yaml, load_model_config, variant profiles)
  ├─ CommandBuilder (YAML efectivo → args, MTP/draft, backend por modelo, -mm)
  └─ ProcessManager (spawn llama-server, logs, ready/error signals)
          │
          └─ llama-server.exe
```

* `GUI` solo interacción.
* `ModelManager` escanea `models/` y expone `models` + `unconfigured_folders`.
* `CommandBuilder` respeta `variant_has_mtp` para no enviar `--spec-type` en variantes `nomtp`.
* `ProcessManager` captura salida y escribe `logs/<modelo>/YYYY-MM-DD_HH-MM-SS.log`.

---

## Tecnologías

* **Python 3.12+**
* **PySide6 >=6.6.0** (Qt)
* **PyYAML >=6.0**
* **llama.cpp** (`llama-server`)

---

## Roadmap

### Fase 1 — MVP

* [x] Estructura del proyecto
* [x] Detección automática de modelos (incl. per-variante y `gguf/mtp|nomtp`)
* [x] Leer `model.yaml` / `model.<variant>.yaml`
* [x] Validar configuraciones (`ModelHealth`)
* [x] Detectar `llama-server.exe` (global y por modelo)
* [x] Construir comandos automáticamente (incl. MTP, cache, ncmoe, vision)
* [x] Lanzar/detener `llama-server`
* [x] Mostrar logs en tiempo real
* [x] GUI básica (split, tarjetas, logs)

### Fase 2 — Gestión avanzada

* [x] Info detallada por modelo (cuantización, MTP, health, variantes, perfiles)
* [x] Estado del servidor (`RUNNING/STARTING/ERROR`)
* [x] Validar conflictos de puerto y proceso único
* [x] Reiniciar / F5 recarga
* [x] Configuración global (`config/app.yaml` + Settings)
* [ ] Mostrar VRAM/RAM en vivo (actualmente solo logs de `llama-server`)
* [ ] Historial de ejecuciones

### Fase 3 — Experiencia de usuario

* [x] Editor visual por variante (`⚙` VariantProfileDialog)
* [x] Detección automática de GGUF y creación de `model.yaml` para carpetas sin config
* [x] Perfiles por variante (hereda base)
* [ ] Favoritos / búsqueda / filtros
* [ ] Métricas tokens/s en GUI

### Fase 4 — Integración

* [x] MTP / draft models
* [x] Vision `mmproj`
* [x] MoE (`ncmoe`, `n_expert`)
* [ ] Múltiples servidores simultáneos (actual: uno a la vez)
* [ ] Actualización de `llama.cpp` desde la app
* [ ] API OpenAI-compatible integrada

---

## Principio de diseño

> **Agregar un modelo no debe requerir modificar el código.**

1. Crear carpeta `models/mi-modelo/`
2. Copiar `.gguf`
3. Crear `model.yaml` (o dejar que la app lo sugiera)
4. Abrir Local LLM Manager → aparece automáticamente → `Launch`

---

## Licencia

Por definir. Distinguir: código propio, `llama.cpp` (MIT), modelos (licencia de cada modelo) y dependencias. Los modelos no se incluyen en el repo.

