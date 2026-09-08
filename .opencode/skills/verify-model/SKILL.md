---
name: verify-model
description: "Audita y optimiza únicamente el modelo actualmente cargado en llama.cpp. Verifica YAML vs llama-server, logs, VRAM, RAM, GPU layers, contexto, KV cache, batch, vision y opciones avanzadas. Objetivo: hacer que el modelo entre de forma estable, mantener margen suficiente de VRAM/RAM y maximizar velocidad dentro de ese margen, evitando degradaciones de calidad innecesarias. Use ONLY when user says verifica modelo, verifica config, verifica Agents, analiza VRAM, optimiza GPU, revisa yaml, o menciona Agents A1 4B, llama-server, context, cache."
---

# Verify Model — Auditor y Optimizador de llama.cpp

Skill para auditar y optimizar **solo el modelo actualmente cargado** en `llama.cpp`.

Debe comparar:

* configuración YAML;
* comando real de `llama-server`;
* logs reales;
* uso actual de VRAM;
* uso actual de RAM;
* GPU layers;
* contexto;
* KV cache;
* batch / micro-batch;
* vision encoder;
* prompt cache;
* opciones avanzadas de llama.cpp;
* rendimiento cuando existan benchmarks disponibles.

La skill debe detectar discrepancias entre configuración declarada y configuración real, identificar riesgos de memoria y seleccionar una configuración recomendada.

---

# 1. Objetivo de optimización

La skill debe optimizar la configuración siguiendo esta prioridad:

## Prioridad 1 — Encajar y funcionar

El modelo debe poder cargarse y ejecutarse sin:

* OOM;
* crashes;
* presión extrema de memoria;
* swap/pagefile excesivo;
* errores recurrentes de `llama-server`;
* configuración incompatible.

Si el modelo no entra, la prioridad absoluta es encontrar una configuración que permita ejecutarlo.

---

## Prioridad 2 — Mantener margen de memoria

Una configuración que apenas entra no debe considerarse óptima.

Debe existir margen suficiente para:

* Windows;
* `llama-server`;
* otras aplicaciones;
* variaciones de uso;
* crecimiento del KV cache;
* operaciones temporales de llama.cpp.

### VRAM objetivo

Para una RTX 3070 Laptop de 8 GB:

* `<300 MiB libres` → 🔴 crítico
* `300–500 MiB` → 🟠 margen bajo
* `500–1000 MiB` → 🟢 margen recomendado
* `>1000 MiB` → 🟢 margen amplio

El objetivo normal es aproximadamente **500–1000 MiB libres**.

No reducir memoria innecesariamente si el modelo ya funciona con un margen razonable.

### RAM

Usar la siguiente clasificación:

* `<70%` → 🟢 cómoda
* `70–80%` → 🟢 aceptable
* `80–90%` → 🟠 presión
* `>90%` → 🔴 crítica
* swap/pagefile activo de forma relevante → 🔴 crítico

La RAM disponible puede utilizarse como recurso de compensación cuando liberar VRAM sea necesario.

---

# 2. Objetivo de rendimiento

Una vez que el modelo entra y existe margen suficiente, la prioridad pasa a ser:

**maximizar velocidad dentro del presupuesto de memoria.**

Analizar, cuando existan datos:

* prompt processing tok/s;
* generation tok/s;
* latencia;
* throughput;
* VRAM;
* RAM.

No asumir que menor uso de memoria siempre significa mayor velocidad.

La configuración recomendada debe buscar el mejor equilibrio entre:

```text
estabilidad
    ↓
margen de memoria
    ↓
velocidad
    ↓
calidad
```

La calidad debe preservarse siempre que sea razonable, pero no debe obligar a utilizar una configuración lenta, inestable o peligrosamente cercana al límite de memoria.

---

# 3. Tradeoffs — Datos medidos (Agents-A1-4B, RTX 3070 8GB)

La skill debe reconocer explícitamente que existen configuraciones con distintos compromisos.

## Datos reales de benchmark (sept 2026)

| Config | Gen tok/s | VRAM libre | Velocidad | Calidad |
|--------|----------:|----------:|-----------|---------|
| 128K q8_0 | 64.9 | 565 MiB | Baseline | Baseline |
| **65K q8_0** | **64.4** | **1,972 MiB** | **=** | **=** |
| 128K q4_0 | 63.7 | 1,587 MiB | -1.7% | = |
| 65K q4_0 | 62.3 | 2,482 MiB | -4.0% | = |

## Hallazgos clave

1. **Reducir contexto 128K→65K NO mejora velocidad** (misma generación tok/s)
2. **KV cache Q4 es más lento que Q8** (dequantización overhead)
3. **La calidad es idéntica** en todas las configs (mismo reasoning process)
4. **65K q8_0 gana 3.5x más VRAM libre** con la misma velocidad

## Tradeoffs generales

| Cambio             |       VRAM | RAM |    Velocidad |     Calidad |
| ------------------ | ---------: | --: | -----------: | ----------: |
| ↑ GPU layers       |          ↑ |   ↓ |            ↑ |           = |
| ↓ GPU layers       |          ↓ |   ↑ |            ↓ |           = |
| ↑ context          |          ↑ |   ↑ |            ↔ | ↑ ventana |
| ↓ context          |          ↓ |   ↓ |            ↔ | ↓ ventana |
| KV Q8 → Q4         |         ↓↓ |   = |          ↓ |      = |
| ↑ batch            |          ↑ |   ↑ | ↑ throughput |           = |
| ↓ batch            |          ↓ |   ↓ | ↓ throughput |           = |
| cuantización menor |         ↓↓ |   ↓ |          ↔/↑ |           ↓ |
| cuantización mayor |         ↑↑ |   ↑ |          ↔/↓ |           ↑ |
| prompt cache menor | ↓ VRAM/RAM |   ↓ |  ↓ cache hit |           = |

**Nota**: La velocidad de generación depende del tamaño del modelo y memory bandwidth, no del contexto o KV cache. Reducir contexto solo libera VRAM.

No mostrar necesariamente esta tabla en el reporte final.

Debe utilizarse como modelo mental para tomar decisiones.

---

# 4. Concepto de configuración óptima

La configuración óptima NO es:

> la que utiliza menos memoria.

Tampoco es:

> la de mayor calidad posible.

Ni necesariamente:

> la que obtiene el máximo benchmark.

La configuración óptima es:

> **la configuración más rápida que mantiene el modelo estable y deja suficiente margen de VRAM/RAM, evitando pérdidas de calidad innecesarias.**

Por lo tanto:

* no reducir GPU layers si todavía hay margen y hacerlo empeora significativamente la velocidad;
* no aumentar GPU layers si deja VRAM en estado crítico;
* no aumentar contexto simplemente porque el modelo lo soporta;
* no reducir contexto innecesariamente si el usuario necesita una ventana grande;
* no cambiar cuantización si no aporta una ventaja real;
* no utilizar RAM como overflow si provoca una caída importante de rendimiento cuando todavía existe una alternativa mejor.

---

# 5. Detectar modelo cargado

## Fuente primaria

Detectar el proceso vivo:

```powershell
Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" |
    Select-Object ProcessId, CommandLine, CreationDate |
    Format-List
```

Extraer:

* `-a <alias>`;
* `-m <model_path>`;
* puerto;
* GPU layers;
* contexto;
* demás flags relevantes.

La línea de comando del proceso vivo es la **fuente de verdad**.

---

## Fallback

Si no existe proceso vivo, buscar el log más reciente:

```powershell
Get-ChildItem D:\llama.cpp\logs -Recurse -Filter *.log |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 FullName, LastWriteTime, Length |
    Format-List
```

Si no existe proceso ni log identificable:

```text
Ningún modelo cargado actualmente.
```

Abortar el workflow.

No analizar modelos que no estén cargados.

---

# 6. Escanear YAML — SOLO MODELO CARGADO

Usar:

```text
D:\llama.cpp\models\<LOADED>\model.yaml
```

Comparar:

* `model.file`;
* `hardware.context_size`;
* `hardware.gpu_layers`;
* `hardware.batch_size`;
* `hardware.micro_batch`;
* `cache.type_k`;
* `cache.type_v`;
* prompt cache;
* vision;
* system prompt;
* opciones avanzadas.

No analizar ni modificar otros modelos.

---

# 7. Validar GGUF

Verificar:

* existencia del GGUF;
* tamaño;
* path;
* integridad mediante `ModelManager.validate_model`;
* vision encoder si corresponde.

Si el modelo tiene vision:

* verificar existencia del encoder;
* tamaño;
* configuración;
* tokens mínimos;
* correspondencia con los logs.

---

# 8. Comparar YAML contra llama-server

El proceso vivo tiene prioridad sobre el YAML.

Comparar:

### Modelo

```text
YAML model.file
vs
loading model '...'
```

### Contexto

```text
hardware.context_size
vs
n_ctx
```

### Batch

```text
hardware.batch_size
vs
n_batch
```

### Micro batch

```text
hardware.micro_batch
vs
n_ubatch
```

### KV cache

```text
cache.type_k / type_v
vs
KV buffer / cache type
```

### GPU layers

```text
hardware.gpu_layers
vs
offloaded X/X layers
```

### Vision

```text
capabilities.vision
vs
has vision encoder
```

### System prompt

Comparar YAML con el comando y el comportamiento real de `llama-server`.

### Slot

Buscar:

```text
W find_slot: non-consecutive
```

Si aparece repetidamente:

* comprobar batch;
* comprobar versión de llama.cpp;
* recomendar actualización si corresponde.

---

# 9. Medir memoria real

Usar:

```bash
nvidia-smi --query-gpu=memory.total,memory.used,memory.free --format=csv
```

Y:

```powershell
Get-CimInstance Win32_OperatingSystem |
    Select-Object TotalVisibleMemorySize, FreePhysicalMemory
```

La memoria real tiene prioridad sobre las estimaciones.

---

# 10. Estimación de VRAM

Cuando no existan mediciones suficientes, estimar:

```text
model buffer
+ vision
+ KV cache
+ compute buffers
+ recurrent state
+ overhead
≈ VRAM total
```

No presentar las fórmulas como valores exactos.

Las estimaciones deben etiquetarse como:

```text
estimado
```

y las mediciones reales como:

```text
medido
```

Nunca confundir ambos.

---

# 11. Fase A — determinar si entra

Antes de optimizar velocidad, determinar el estado:

### 🔴 NO ENTRA

* OOM;
* crash;
* VRAM insuficiente;
* RAM insuficiente.

### 🟠 ENTRA CON RIESGO

* margen VRAM <300–500 MiB;
* RAM >90%;
* swap relevante.

### 🟢 ESTABLE

* margen VRAM ≥500 MiB;
* RAM ≤80%;
* sin errores relevantes.

### 🟢 ÓPTIMO

* margen suficiente;
* RAM cómoda;
* configuración estable;
* velocidad adecuada.

No realizar optimizaciones de rendimiento agresivas mientras el estado sea 🔴 o 🟠.

---

# 12. Fase B — optimizar memoria

Si el modelo NO entra o tiene margen insuficiente, aplicar cambios en orden de menor impacto.

## 12.1 Corregir configuración

Primero corregir discrepancias entre:

* YAML;
* comando;
* modelo;
* logs.

Impacto normalmente nulo.

---

## 12.2 Contexto

Reducir contexto solo cuando sea necesario para liberar VRAM.

```text
131K → 65K libera ~1,088 MiB de KV cache
```

**Hallazgo importante**: Reducir contexto NO mejora velocidad de generación. La generación tok/s depende del tamaño del modelo y memory bandwidth, no del tamaño del KV cache.

Informar siempre:

```text
VRAM ahorrada: ~X MiB
ventana perdida: X tokens
velocidad: sin cambio significativo
```

No afirmar que reducir contexto mejora velocidad.

Es una reducción de capacidad de contexto que libera VRAM.

### Guía de contextos

| Contexto | KV cache (q8_0) | VRAM libre aprox | Uso recomendado |
|----------|----------------:|-----------------:|-----------------|
| 32K | ~544 MiB | ~2,500 MiB | Tareas cortas |
| 65K | ~1,088 MiB | ~1,972 MiB | Uso general (recomendado) |
| 96K | ~1,632 MiB | ~1,100 MiB | Conversaciones largas |
| 128K | ~2,176 MiB | ~565 MiB | Sesiones ultra-largas |

---

## 12.3 KV cache

Evaluar:

```text
Q8_0 → Q6_K → Q5_K → Q4_0
```

según compatibilidad.

**Hallazgo importante**: Q4_0 es más lento que Q8_0 (dequantización overhead durante attention). Q4_0 libera ~50% del KV cache pero la generación es ~2-4% más lenta.

La skill debe evitar afirmar porcentajes de pérdida de calidad sin evidencia.

En su lugar:

```text
impacto esperado: bajo / medio / alto
```

Si existen benchmarks o documentación específica, utilizarlos.

No recomendar automáticamente `q2`, `iq1` u opciones extremadamente agresivas.

### Datos medidos (Agents-A1-4B)

| KV cache | VRAM KV | Gen tok/s | Velocidad |
|----------|--------:|----------:|-----------|
| q8_0 | 2,176 MiB | 64.9 | Baseline |
| q4_0 | ~1,088 MiB | 63.7 | -1.7% |

**Conclusión**: Q4_0 no mejora velocidad, solo libera VRAM. Usar solo si el modelo no entra con Q8_0.

---

## 12.4 GPU layers

Si VRAM es el recurso limitante:

```text
↑ gpu_layers
```

consume más VRAM y normalmente aumenta velocidad.

```text
↓ gpu_layers
```

libera VRAM pero puede aumentar uso de CPU/RAM y reducir velocidad.

Buscar el máximo número de GPU layers que mantenga:

```text
VRAM margin >= target
RAM margin >= target
```

Si la diferencia de velocidad es significativa, recomendar la configuración con más GPU layers aunque utilice más memoria, siempre que permanezca dentro del margen seguro.

---

## 12.5 Batch / micro-batch

Evaluar:

* `n_batch`;
* `n_ubatch`;
* `batch_size`;
* `micro_batch`.

Mayor batch puede:

* aumentar throughput;
* aumentar VRAM/RAM.

Menor batch:

* reduce memoria;
* puede reducir throughput.

No modificar batch únicamente para ahorrar memoria si ya existe margen suficiente.

---

# 13. Overlap RAM/VRAM

La skill puede utilizar RAM como recurso de compensación.

Ejemplo:

```text
VRAM:
7.7 / 8 GB → margen crítico

RAM:
21 / 32 GB → margen amplio
```

Puede recomendar una configuración con más trabajo en CPU/RAM si:

* evita OOM;
* mantiene RAM por debajo de niveles críticos;
* el impacto de velocidad es aceptable.

Debe explicar el tradeoff:

```text
VRAM: -700 MiB
RAM: +700 MiB
velocidad: potencialmente -X%
```

No utilizar RAM adicional si esto provoca swap o presión crítica.

---

# 14. Fase C — optimizar velocidad

Una vez que el modelo entra con margen suficiente:

## Buscar

1. máximo GPU offload seguro;
2. batch adecuado;
3. micro-batch adecuado;
4. Flash Attention si corresponde;
5. KV cache apropiada;
6. configuración de contexto razonable;
7. prompt cache cuando realmente aporta;
8. otras optimizaciones soportadas por la versión actual de llama.cpp.

El objetivo es maximizar:

```text
generation tok/s
```

y, cuando corresponda:

```text
prompt processing tok/s
```

No asumir que una optimización mejora ambos.

---

# 15. Benchmark — Framework de testing completo

Cuando sea posible, ejecutar tests comparativos entre configuraciones.

## 15.1 Configuraciones a testear

Probar al menos estas combinaciones:

| Config | Contexto | KV cache | Nota |
|--------|----------|----------|------|
| Baseline | Actual | Actual | Punto de referencia |
| Reduced context | 50-75% del actual | Igual | Testea impacto de contexto |
| Q4 KV | Igual | q4_0 | Testea impacto de cuantización |
| Mínima | 32K | q4_0 | Máximo ahorro VRAM |

## 15.2 Métricas a capturar por cada config

```text
VRAM baseline (sin modelo)
VRAM after load (idle)
VRAM after inference (active)
RAM used / free
Generation tok/s (promedio de 3-5 tests)
Prompt tok/s (promedio)
```

## 15.3 Tests de calidad (mismos prompts en todas las configs)

```powershell
# Test matemático
"What is 15 * 7 + 23? Show your work."

# Test de razonamiento
"If all roses are flowers, and some flowers fade quickly, can we conclude that some roses fade quickly? Explain step by step."

# Test de instrucción
"Respond ONLY with a JSON object containing name and age for a person named Juan who is 30 years old. No extra text."

# Test de definición
"Explain what a neural network is in exactly 3 sentences."

# Test de coding
"Write a Python function that checks if a string is a palindrome. Include docstring."
```

## 15.4 API de testing

Usar el endpoint de chat completions:

```powershell
$body = @{
    model = "<alias>"
    messages = @(@{ role="user"; content="<prompt>" })
    temperature = 0.85
    top_p = 0.95
    top_k = 20
    min_p = 0.0
    presence_penalty = 1.1
    repeat_penalty = 1.0
    max_tokens = 200
    stream = $false
} | ConvertTo-Json -Depth 3

$resp = Invoke-RestMethod -Uri "http://127.0.0.1:<port>/v1/chat/completions" `
    -Method Post -ContentType "application/json" -Body $body

# Métricas
$resp.timings.prompt_per_second   # Prompt processing
$resp.timings.predicted_per_second  # Generation
$resp.choices[0].message.content    # Output (para comparar calidad)
$resp.choices[0].message.reasoning_content  # Thinking (si reasoning=true)
```

## 15.5 Tabla comparativa de resultados

Generar tabla al final de los tests:

| Config | Gen tok/s | VRAM libre | Velocidad vs baseline | Calidad |
|--------|----------:|----------:|----------------------|---------|
| Baseline (X) | X | X | — | Baseline |
| Reduced ctx (Y) | Y | Y | +/-% | =/↓ |
| Q4 KV (Z) | Z | Z | +/-% | =/↓ |

## 15.6 Análisis de calidad

Comparar outputs entre configs:
- Mismos tokens de razonamiento (thinking process)
- Mismas respuestas factuales
- Misma cadena lógica
- Mismo formato de output

**Regla**: Si los outputs son idénticos o prácticamente idénticos, marcar calidad como "=".

## 15.7 Veredicto

Al final de los tests,给出 una recomendación clara:

```text
RECOMENDACIÓN: <config> es la mejor porque...
- Velocidad: X tok/s (vs Y tok/s baseline)
- VRAM: X MiB libres (vs Y MiB baseline)
- Calidad: idéntica / ↓ leve / ↓ significativa
- Ventana: X tokens (suficiente para / limitada para...)
```

---

# 16. Cuantización

La cuantización es una herramienta de optimización, no el primer recurso.

Antes de cambiarla:

1. comprobar si existen otras formas de liberar memoria;
2. comprobar si existen cuantizaciones alternativas;
3. comparar tamaño;
4. comparar calidad esperada;
5. comparar impacto en velocidad;
6. verificar que realmente resuelve el problema.

Buscar alternativas en Hugging Face cuando corresponda.

Preferir la cuantización con mejor relación:

```text
calidad / memoria / velocidad
```

No utilizar simplemente:

```text
Q6 > Q5 > Q4
```

como regla absoluta.

Por ejemplo, si:

```text
Q6:
7.7 GB VRAM
250 MB libres
40 tok/s

Q5:
7.1 GB VRAM
900 MB libres
47 tok/s

Q4:
6.5 GB VRAM
1.5 GB libres
53 tok/s
```

Q5 puede ser la configuración óptima aunque Q6 tenga mayor calidad.

La decisión debe considerar estabilidad, margen y velocidad.

---

# 17. Opciones avanzadas de llama.cpp

La skill puede consultar:

```text
llama-server --help
```

y documentación oficial de llama.cpp.

Puede investigar opciones como:

* `--flash-attn`;
* `--cache-ram`;
* `--mlock`;
* `--no-mmap`;
* `--split-mode`;
* `--offload-kqv`;
* `--rope-freq-base`;
* `--rope-freq-scale`;
* `--swa-*`;
* otras disponibles en la versión instalada.

Antes de recomendar una opción:

1. verificar que exista en la versión instalada;
2. verificar si ya está implementada en YAML;
3. verificar si ya está implementada en `CommandBuilder`;
4. evaluar RAM;
5. evaluar VRAM;
6. evaluar velocidad;
7. evaluar posibles efectos sobre calidad/compatibilidad.

Nunca asumir que una opción tiene un impacto fijo.

Los porcentajes de velocidad/memoria deben ser:

* medidos;
* documentados por la fuente;
* o expresados como estimaciones.

---

# 18. Sistema de decisión

Para cada configuración candidata evaluar:

```text
STABILITY
VRAM margin
RAM margin
GENERATION SPEED
PROMPT SPEED
QUALITY
```

Primero eliminar configuraciones que:

* no entran;
* generan OOM;
* dejan memoria críticamente baja;
* provocan swap;
* producen errores graves.

Entre las configuraciones restantes:

1. preferir mayor velocidad;
2. preferir mayor margen cuando la diferencia de velocidad sea pequeña;
3. preferir mayor calidad cuando el rendimiento sea similar;
4. evitar cambios innecesarios.

---

# 19. Ventanas de tradeoff

Cuando existan varias configuraciones razonables, presentar como máximo:

### Recomendada

La mejor combinación global.

### Más rápida

Usa más memoria para maximizar velocidad.

### Más segura

Deja mayor margen de VRAM/RAM sacrificando algo de velocidad.

Ejemplo:

```text
RECOMENDADA
VRAM: 7.2 GB
RAM: 24 GB
Generation: 52 tok/s

MÁS RÁPIDA
VRAM: 7.55 GB
RAM: 23 GB
Generation: ~57 tok/s
Margen VRAM: bajo

MÁS SEGURA
VRAM: 6.8 GB
RAM: 25 GB
Generation: ~48 tok/s
Margen VRAM: amplio
```

No mostrar alternativas si la configuración recomendada es claramente superior.

---

# 20. Regla de no modificar por modificar

Si la configuración actual:

* entra;
* tiene margen suficiente;
* es estable;
* y tiene buen rendimiento;

entonces:

```text
NO CAMBIAR
```

No recomendar:

* menor cuantización;
* menor contexto;
* menor GPU offload;
* menor batch;

simplemente porque existe una configuración que utiliza menos memoria.

El objetivo no es minimizar recursos.

El objetivo es **utilizar los recursos disponibles de forma eficiente**.

---

# 21. Reporte final

El reporte debe ser técnico pero legible.

Debe poder entenderse rápidamente sin leer todos los detalles internos.

No narrar el proceso.

Evitar frases como:

```text
Se procedió a analizar...
Se verificó inicialmente...
Luego se realizó...
```

Mostrar directamente:

```text
qué se encontró
qué recomienda
por qué
qué tradeoff existe
qué acción tomar
```

## Formato

### Resultado

```text
Modelo: <nombre>
Estado: 🟢 ESTABLE
```

Tabla:

| Recurso    |       Uso | Margen | Estado |
| ---------- | --------: | -----: | ------ |
| VRAM       |  X / 8 GB |   X MB | 🟢     |
| RAM        | X / 32 GB |   X GB | 🟢     |
| GPU layers |     X / N |      — | 🟢     |

### Recomendación

Indicar **una configuración concreta**.

Ejemplo:

```text
Recomendación: mantener Q4_K_M + 61 GPU layers + 64K context.

Motivo:
Es la configuración más rápida encontrada que mantiene
≥500 MiB de VRAM libre y RAM en zona segura.
```

### Cambios

Solo listar cambios necesarios:

```text
model.yaml:13
gpu_layers: all → 61

model.yaml:27
context_size: 131072 → 65536
```

### Impacto

```text
VRAM: -1.0 GB
RAM: +0.2 GB
Generation: potencialmente +X%
Context: -65K tokens
Calidad: sin cambio de cuantización
```

Separar claramente:

```text
medido
```

de:

```text
estimado
```

### Tradeoff

Mostrar solo si es relevante.

```text
Más rápido:
+400 MiB VRAM
+~8% generation
margen VRAM queda en ~400 MiB

Más seguro:
-400 MiB VRAM
-~7% generation
margen VRAM ~1.2 GB
```

### Acción

Indicar claramente:

```text
Acción requerida: reiniciar llama-server.
```

o:

```text
Acción requerida: ninguna.
```

### Verificación posterior

Solo si hubo cambios:

```text
Después del reinicio verificar:
- VRAM libre
- RAM libre
- GPU layers
- n_ctx
- generation tok/s
```

### Detalle técnico

Solo incluirlo cuando:

* existe una discrepancia;
* una decisión necesita justificación;
* hay una estimación importante;
* hay un comportamiento anómalo;
* se utilizó una opción avanzada.

No volcar logs completos ni comandos innecesarios.

---

# 22. Ejemplo de reporte ideal

```text
## Resultado

Modelo: Qwen3.8-27B Q4_K_M
Estado: 🟢 ESTABLE

| Recurso | Uso | Margen | Estado |
|---|---:|---:|---|
| VRAM | 7.18 / 8.0 GB | 820 MB | 🟢 |
| RAM | 24.1 / 31.6 GB | 7.5 GB | 🟢 |
| GPU layers | 61 / 61 | — | 🟢 |

## Recomendación

**Mantener la configuración actual.**

Es la mejor relación entre memoria y velocidad dentro del margen
seguro detectado.

No se recomienda reducir cuantización ni GPU layers.

## Tradeoff

**Más segura**
- reducir GPU layers a 55
- ~400 MB menos de VRAM
- menor velocidad esperada

**Más rápida**
- aumentar GPU offload si existe margen real
- mayor VRAM
- potencialmente mayor generation tok/s
- solo recomendable si conserva ≥500 MB libres

## Acción

Ninguna.

## Verificación

No necesaria.
```

---

# 23. Archivos y fuentes

Fuentes principales:

```text
D:\llama.cpp\models\<LOADED>\model.yaml
D:\llama.cpp\logs\<LOADED_UNDERSCORE>\
D:\llama.cpp\app\core\command_builder.py
D:\llama.cpp\app\core\model_manager.py
```

Para configuración real, priorizar:

```text
1. proceso vivo llama-server
2. logs
3. YAML
```

Para implementación:

```text
app/core/command_builder.py
```

Para validación:

```text
app/core/model_manager.py
```

Para estado de GPU:

```text
nvidia-smi
```

Para documentación de llama.cpp:

```text
https://github.com/ggml-org/llama.cpp
```

---

# 24. Restricciones

* Analizar únicamente el modelo cargado.
* No modificar otros modelos.
* No recomendar cambios sin explicar su objetivo.
* No presentar estimaciones como mediciones.
* No inventar porcentajes de calidad o velocidad.
* No asumir que una configuración que usa menos memoria es mejor.
* No sacrificar calidad si no es necesario.
* No sacrificar velocidad innecesariamente.
* No dejar VRAM/RAM en estado crítico.
* No reducir GPU layers si existe suficiente margen y la reducción empeora significativamente el rendimiento.
* No aumentar GPU layers si deja la VRAM por debajo del margen seguro.
* No reducir contexto sin indicar cuánta ventana se pierde.
* No cambiar cuantización sin justificar el beneficio.
* No utilizar cuantizaciones extremadamente agresivas como primera opción.
* No realizar cambios cosméticos que no mejoren estabilidad, memoria o rendimiento.
* No pedir confirmación: ejecutar el análisis completo sobre el modelo cargado y proponer cambios concretos.

---

# 25. Resultado esperado

La skill debe terminar siempre tomando una posición clara:

```text
MANTENER
```

o:

```text
MODIFICAR → <configuración recomendada>
```

y, cuando sea útil:

```text
TRADEOFF → <alternativa más rápida>
TRADEOFF → <alternativa más segura>
```

La respuesta final debe dejar claro:

## **qué configuración usar, por qué, cuánto margen deja y qué se sacrifica a cambio.**
