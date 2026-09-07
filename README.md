# Local LLM Manager

Aplicación de escritorio para administrar y ejecutar modelos de inteligencia artificial localmente mediante [`llama.cpp`](https://github.com/ggml-org/llama.cpp).

El objetivo del proyecto es centralizar la gestión de modelos locales y evitar la necesidad de mantener múltiples archivos `.bat` con configuraciones específicas para cada modelo.

La aplicación detectará automáticamente los modelos disponibles, cargará su configuración y permitirá iniciarlos mediante una interfaz gráfica.

---

## 🎯 Objetivo

Actualmente, cada modelo utilizado con `llama.cpp` puede requerir una configuración diferente:

* Modelo utilizado.
* Quantización.
* Número de capas descargadas a GPU.
* Context size.
* Batch size.
* Número de CPU threads.
* Número de GPU layers.
* Configuración MoE.
* Modelos draft para MTP.
* Encoders de visión.
* Chat templates.
* Parámetros de sampling.
* Puerto del servidor.
* Otros argumentos específicos de `llama-server`.

La configuración suele terminar distribuida entre diferentes scripts `.bat`, haciendo más difícil:

* Agregar nuevos modelos.
* Recordar qué configuración utiliza cada modelo.
* Cambiar parámetros.
* Comparar configuraciones.
* Iniciar modelos rápidamente.
* Mantener una configuración reproducible.

Este proyecto busca resolverlo mediante una aplicación centralizada.

---

## 🧠 Concepto

La aplicación funcionará como un **administrador local de modelos para `llama.cpp`**.

La idea principal es:

```text
                 ┌──────────────────────┐
                 │   Local LLM Manager   │
                 │       GUI            │
                 └──────────┬───────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
       Detectar modelos              Leer configuración
              │                           │
              ▼                           ▼
       ┌──────────────┐            ┌──────────────┐
       │   models/    │            │  model.yaml  │
       └──────────────┘            └──────────────┘
              │                           │
              └─────────────┬─────────────┘
                            ▼
                    Construir comando
                            │
                            ▼
                    llama-server.exe
                            │
                            ▼
                     Modelo ejecutándose
```

La aplicación no debería necesitar conocer previamente qué modelos existen.

**Agregar un modelo debería consistir simplemente en agregar sus archivos y su configuración.**

---

# 📁 Estructura del proyecto

Una estructura inicial propuesta sería:

```text
local-llm-manager/
│
├── README.md
├── requirements.txt
├── pyproject.toml
│
├── app/
│   ├── main.py
│   │
│   ├── gui/
│   │   ├── main_window.py
│   │   ├── model_view.py
│   │   └── settings_view.py
│   │
│   ├── core/
│   │   ├── model_manager.py
│   │   ├── config_loader.py
│   │   ├── command_builder.py
│   │   └── process_manager.py
│   │
│   └── models/
│       └── model_definition.py
│
├── models/
│   ├── qwen3.5-9b/
│   │   ├── model.gguf
│   │   └── model.yaml
│   │
│   ├── gemma-4-e4b/
│   │   ├── model.gguf
│   │   └── model.yaml
│   │
│   └── ...
│
├── llama.cpp/
│   ├── llama-server.exe
│   ├── ...
│   └── ...
│
├── scripts/
│   ├── install.bat
│   ├── update-llama.cpp.bat
│   └── ...
│
├── logs/
│   └── ...
│
└── config/
    └── app.yaml
```

> La carpeta `llama.cpp/` debería considerarse una dependencia externa del proyecto. Idealmente, la aplicación debería permitir especificar dónde se encuentra el ejecutable en lugar de asumir una ubicación fija.

---

# 🤖 Modelos

Cada modelo tendrá su propia carpeta.

Ejemplo:

```text
models/
└── qwen3.5-9b/
    ├── qwen3.5-9b-Q4_K_M.gguf
    └── model.yaml
```

Esto permite que toda la información necesaria para ejecutar el modelo permanezca junto al modelo.

---

# ⚙️ Configuración de modelos

Se propone utilizar **YAML** para las configuraciones.

La razón principal es que resulta más legible y editable manualmente que JSON, especialmente cuando la configuración contiene muchos parámetros opcionales.

Ejemplo:

```yaml
name: Qwen 3.5 9B
description: Qwen 3.5 9B local model

backend:
  type: llama.cpp

model:
  file: qwen3.5-9b-Q4_K_M.gguf

server:
  host: 127.0.0.1
  port: 8080

hardware:
  gpu_layers: all
  context_size: 24576
  batch_size: 2048
  threads: 8

sampling:
  temperature: 0.7
  top_p: 0.8

capabilities:
  vision: false
  tool_calling: true

advanced:
  flash_attention: true
```

La aplicación utilizará esta información para construir automáticamente el comando correspondiente.

Por ejemplo:

```text
llama-server.exe
    --model models/qwen3.5-9b/qwen3.5-9b-Q4_K_M.gguf
    --host 127.0.0.1
    --port 8080
    --ctx-size 24576
    --batch-size 2048
    --n-gpu-layers all
    --threads 8
    --temp 0.7
    --top-p 0.8
    --flash-attn
```

---

# 👁️ Modelos con Vision

El proyecto debería contemplar modelos que utilicen componentes adicionales para procesamiento visual.

Por ejemplo:

```yaml
capabilities:
  vision: true

vision:
  encoder: mmproj-model-f16.gguf
```

La aplicación deberá poder detectar que un modelo requiere un encoder y agregar automáticamente los argumentos correspondientes al comando de `llama-server`.

Esto permitiría tener configuraciones como:

```text
models/
└── qwen-vl/
    ├── model.gguf
    ├── mmproj-model.gguf
    └── model.yaml
```

---

# 📦 Formatos de modelos

El proyecto estará inicialmente orientado a modelos compatibles con `llama.cpp`.

El formato principal será:

```text
GGUF
```

Sin embargo, la arquitectura debería evitar asumir que todos los modelos utilizan exclusivamente GGUF.

La aplicación podría representar el formato mediante:

```yaml
model:
  format: gguf
  file: model.gguf
```

Esto permitiría incorporar soporte para otros formatos en el futuro si `llama.cpp` o el backend utilizado los soporta directamente.

---

# 🖥️ Interfaz gráfica

La interfaz debería proporcionar una vista simple de los modelos disponibles.

Por ejemplo:

```text
┌─────────────────────────────────────────────────────┐
│ Local LLM Manager                              [⚙] │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Available Models                                    │
│                                                     │
│ ┌───────────────────────────────────────────────┐   │
│ │ Qwen 3.5 9B                                  │   │
│ │ Q4_K_M                                       │   │
│ │ Context: 24K                                 │   │
│ │ GPU: All                                     │   │
│ │                                               │   │
│ │                         [ Launch ]            │   │
│ └───────────────────────────────────────────────┘   │
│                                                     │
│ ┌───────────────────────────────────────────────┐   │
│ │ Gemma 4 E4B                                  │   │
│ │ Q4_K_M                                       │   │
│ │ Context: 32K                                 │   │
│ │ GPU: All                                     │   │
│ │                                               │   │
│ │                         [ Launch ]            │   │
│ └───────────────────────────────────────────────┘   │
│                                                     │
├─────────────────────────────────────────────────────┤
│ Status: No model running                            │
└─────────────────────────────────────────────────────┘
```

Al seleccionar un modelo, la aplicación debería mostrar:

* Nombre.
* Descripción.
* Formato.
* Tamaño.
* Quantización.
* Context size.
* Uso de GPU.
* Soporte de Vision.
* Estado actual.
* Puerto.
* Configuración relevante.

---

# 🚀 Ejecución

Al presionar **Launch**, la aplicación deberá:

1. Validar la configuración.
2. Verificar que el archivo del modelo exista.
3. Verificar que `llama-server.exe` exista.
4. Construir el comando.
5. Iniciar `llama-server`.
6. Mostrar el estado del proceso.
7. Capturar stdout/stderr.
8. Mostrar los logs en la interfaz.
9. Detectar cuando el servidor está listo.
10. Permitir detener el modelo.

Ejemplo:

```text
Model: Qwen 3.5 9B

Status:
🟢 Running

Server:
http://127.0.0.1:8080

PID:
12345

GPU:
RTX 3070 Laptop GPU

VRAM:
7.2 GB / 8 GB
```

---

# 🛑 Gestión del proceso

La aplicación deberá administrar los procesos iniciados.

Como mínimo:

```text
[ Launch ]
[ Stop ]
[ Restart ]
```

También debería ser posible impedir que se ejecuten accidentalmente dos modelos que requieran el mismo puerto o demasiados recursos.

En el futuro podría incorporarse detección automática de:

* VRAM disponible.
* RAM disponible.
* GPU disponible.
* Procesos de `llama-server` existentes.

---

# 📋 Detección automática de modelos

Al iniciar la aplicación se deberá escanear:

```text
models/
```

Cada subcarpeta que contenga un `model.yaml` será considerada un modelo válido.

Ejemplo:

```text
models/
├── qwen3.5-9b/
│   └── model.yaml
│
├── gemma-4-e4b/
│   └── model.yaml
│
└── llama-3.1-8b/
    └── model.yaml
```

La aplicación encontrará automáticamente:

```text
Qwen 3.5 9B
Gemma 4 E4B
Llama 3.1 8B
```

Sin necesidad de modificar el código fuente.

---

# 🔧 Validación de configuración

Antes de ejecutar un modelo, la aplicación deberá validar:

* Que exista el archivo del modelo.
* Que el formato sea compatible.
* Que `llama-server` exista.
* Que los parámetros sean válidos.
* Que los archivos auxiliares existan.
* Que el puerto esté disponible.
* Que la configuración YAML sea válida.

Ejemplo de error:

```text
Unable to launch model.

Model file not found:

models/qwen3.5-9b/qwen3.5-9b-Q4_K_M.gguf
```

---

# 📊 Logs

Cada ejecución debería generar logs.

Ejemplo:

```text
logs/
├── qwen3.5-9b/
│   ├── 2026-09-04_10-30-12.log
│   └── 2026-09-04_14-21-45.log
│
└── gemma-4-e4b/
    └── 2026-09-04_11-10-32.log
```

La interfaz también debería permitir visualizar el output de `llama-server` en tiempo real.

---

# 🧩 Arquitectura

Se busca mantener una arquitectura desacoplada:

```text
GUI
 │
 ▼
Model Manager
 │
 ├── Model Discovery
 │
 ├── Configuration Loader
 │
 ├── Command Builder
 │
 └── Process Manager
          │
          ▼
    llama-server
```

### GUI

Responsable exclusivamente de la interacción con el usuario.

### Model Discovery

Busca modelos disponibles en `models/`.

### Configuration Loader

Carga y valida los archivos `model.yaml`.

### Command Builder

Transforma la configuración YAML en argumentos de `llama-server`.

### Process Manager

Inicia, detiene y monitorea los procesos.

---

# 🛠️ Tecnologías

La implementación inicial estará basada en:

* **Python**
* **llama.cpp**
* **YAML**
* **PyYAML**

Para la interfaz gráfica se evaluarán alternativas como:

* PySide6 / Qt
* Tkinter
* CustomTkinter

La opción preferida inicialmente sería **PySide6**, debido a que permite construir una interfaz más completa y escalable.

---

# 🔮 Roadmap

## Fase 1 — MVP

* [ ] Crear estructura del proyecto.
* [ ] Detectar automáticamente modelos.
* [ ] Leer `model.yaml`.
* [ ] Validar configuraciones.
* [ ] Detectar `llama-server.exe`.
* [ ] Construir comandos automáticamente.
* [ ] Lanzar `llama-server`.
* [ ] Detener procesos.
* [ ] Mostrar logs.
* [ ] Crear GUI básica.

## Fase 2 — Gestión avanzada

* [ ] Mostrar información detallada de cada modelo.
* [ ] Mostrar estado del servidor.
* [ ] Detectar GPU.
* [ ] Mostrar VRAM disponible.
* [ ] Validar conflictos de puertos.
* [ ] Reiniciar modelos.
* [ ] Guardar historial de ejecuciones.
* [ ] Configuración global de la aplicación.

## Fase 3 — Experiencia de usuario

* [ ] Editor visual de `model.yaml`.
* [ ] Importación de nuevos modelos.
* [ ] Detección automática de archivos GGUF.
* [ ] Perfiles de configuración.
* [ ] Favoritos.
* [ ] Búsqueda y filtros.
* [ ] Métricas de rendimiento.
* [ ] Estadísticas de tokens/s.

## Fase 4 — Integración

* [ ] Actualización de `llama.cpp`.
* [ ] Integración con APIs OpenAI-compatible.
* [ ] Integración con clientes externos.
* [ ] Soporte para múltiples servidores simultáneos.
* [ ] Gestión de modelos Vision.
* [ ] Soporte para configuraciones avanzadas de MoE.
* [ ] Soporte para MTP / draft models.

---

# 💡 Principio de diseño

El principio fundamental del proyecto es:

> **Agregar un modelo no debería requerir modificar el código de la aplicación.**

Idealmente, el proceso debería ser:

```text
1. Crear carpeta del modelo
2. Copiar el modelo
3. Crear model.yaml
4. Abrir Local LLM Manager
5. El modelo aparece automáticamente
6. Presionar Launch
```

Esto permite que la aplicación evolucione independientemente de los modelos instalados.

---

# 📌 Ejemplo completo

Un modelo podría quedar definido de esta manera:

```yaml
name: Gemma 4 E4B
description: Google Gemma 4 E4B local model

backend:
  type: llama.cpp

model:
  file: gemma-4-e4b-Q4_K_M.gguf
  format: gguf

server:
  host: 127.0.0.1
  port: 8080

hardware:
  gpu_layers: all
  context_size: 32768
  batch_size: 2048
  threads: 8

sampling:
  temperature: 0.7
  top_p: 0.9

capabilities:
  vision: false
  tool_calling: true

advanced:
  flash_attention: true
```

La aplicación transformará esta configuración en la invocación correspondiente de `llama-server`.

---

# 📜 Licencia

La licencia del proyecto deberá definirse antes de la primera publicación.

Se deberá tener especial cuidado en distinguir:

* Código propio del proyecto.
* `llama.cpp`.
* Modelos descargados.
* Licencias individuales de los modelos.
* Dependencias Python.

Los modelos no deberían incluirse dentro del repositorio Git.
