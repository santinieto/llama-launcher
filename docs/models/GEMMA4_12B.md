# Gemma 4 12B — Referencia del modelo

## Arquitectura

| Propiedad | Valor |
|-----------|-------|
| Arquitectura | gemma4 (SSM + attention hybrid) |
| Parámetros | 11.91 B |
| Capas | 48 (40 SWA + 8 full attention) |
| Embedding | 3840 |
| Contexto máximo | 262,144 tokens |
| Tokenizer | BPE, 262,144 tokens |
| Special tokens | `<bos>`, `<eos>`, `<turn|>`, `<\|tool_response\|>` |
| EOT token | `<turn\|>` (106) |
| Reasoning | DeepSeek-style (`<think>...</think>`) |

### Attention heads

- **Full attention layers** (8): 16 Q heads, 8 KV heads, head_dim=512
- **SWA layers** (40): 16 Q heads, 8 KV heads (or 1 in some layers), head_dim=256, sliding_window=1024

### MTP (Multi-Token Prediction)

- Draft model: `mtp-gemma-4-12B-it.gguf` (422.86M params, 4 blocks)
- Arquitectura: `gemma4-assistant`
- **Nota**: Actualmente incompatible con build 10549 — error `Gemma4Assistant requires ctx_other`

## Variantes GGUF

| Variante | Tamaño | BPW | Calidad |
|----------|--------|-----|---------|
| UD-Q4_K_XL (QAT) | 6,405 MB | 4.50 | Mejor calidad |
| UD-Q3_K_XL | 5,744 MB | — | Intermedia |
| UD-Q2_K_XL | 4,446 MB | — | Menor calidad |

## Hardware de referencia

- **GPU**: NVIDIA GeForce RTX 3070 Laptop (8 GB VRAM)
- **CPU**: Intel i7-12650H (16 threads)
- **RAM**: 32 GB DDR5-4800
- **Build**: llama.cpp 10549

## Benchmark (RTX 3070, con MTP + tensor_split)

### Contexto óptimo por variante

| Variante | Tamaño | Contexto óptimo | VRAM usada | VRAM libre | Gen tok/s |
|----------|--------|-----------------|------------|------------|-----------|
| **Q4_K_XL (QAT)** | 6.4 GB | **32K** | 7661 MiB | 358 MiB | ~40 |
| **Q3_K_XL** | 5.7 GB | **65K** | 7574 MiB | 445 MiB | ~45 |
| **Q2_K_XL** | 4.4 GB | **128K** | 6931 MiB | 1088 MiB | ~43 |

### VRAM por contexto (Q4_K_XL)

| Contexto | VRAM libre | Assesssment |
|----------|------------|-------------|
| 8K | 489 MiB | Baseline, cómodo |
| **32K** | **358 MiB** | **Recomendado** |
| 65K | 119 MiB | Funciona pero justo |

### Tests de calidad (Q4_K_XL, promedio 5 tests × 2 runs)

| Contexto | greeting | reasoning | coding | summarize | analysis |
|----------|----------|-----------|--------|-----------|----------|
| 8K | 41.36 | 40.09 | 39.07 | 38.92 | 39.31 |
| 32K | 40.08 | 39.04 | 39.52 | 39.74 | 40.03 |
| 65K | 40.22 | 39.42 | 39.42 | 39.69 | 39.84 |

### Hallazgos clave

1. **Menor cuantización = más VRAM libre = más contexto posible**
2. **Contexto no afecta generación**: misma velocidad en todos los contextos
3. **KV q4_0 vs q8_0**: Diferencia irrelevante (< 0.5%)
4. **Q2_K_XL soporta 128K** con 1088 MiB libre (mejor para documentos largos)
5. **Q4_K_XL mejor calidad** pero limitado a32K en 8GB VRAM

## Configuración recomendada

Cada variante tiene su contexto óptimo según VRAM disponible:

| Variante | context_size | Justificación |
|----------|-------------|---------------|
| Q4_K_XL | 32768 | 358 MiB libre, mejor calidad |
| Q3_K_XL | 65536 | 445 MiB libre, balance calidad/ventana |
| Q2_K_XL | 131072 | 1088 MiB libre, contexto completo |

Config base (misma para todas las variantes, solo cambia `context_size`):

```yaml
model:
  file: <variante>.gguf
  draft_model: mtp-gemma-4-12B-it.gguf

hardware:
  gpu_layers: all
  context_size: <ver tabla>
  batch_size: 1024
  flash_attention: true
  tensor_split: "1"      # Workaround bug #24795

cache:
  type_k: q4_0
  type_v: q4_0
  type_k_draft: q4_0
  type_v_draft: q4_0

speculative:
  enabled: true
  spec_type: draft-mtp
  draft_n_max: 4

advanced:
  reasoning: true
  parallel: 1
  log_verbosity: 4
  draft_gpu_layers: 0   # Draft en CPU (ahorra VRAM)
  cache_ram: 4096       # Prompt cache habilitado
```

### Justificación

- **Per-variante**: Cada quantización usa VRAM diferente,因此 contexto óptimo varía
- **q4_0 KV**: Mejor relación VRAM/calidad en todas las variantes
- **flash_attention**: Requerido para KV cuantizado
- **tensor_split: "1"**: Workaround para bug #24795 (NaN en tensor-split)
- **draft_gpu_layers: 0**: Draft en CPU (ahorra ~227 MiB VRAM)
- **cache_ram: 4096**: Prompt cache para conversaciones multi-turn

### Tradeoffs

| Opción | Contexto | VRAM libre | Velocidad |
|--------|----------|------------|-----------|
| Más contexto | 65K | 119 MiB | = |
| Más calidad KV | 32K q8_0 | 115 MiB | = |
| Más margen | 16K | ~500 MiB | = |

## Sampling

### Q4_K_XL / Q3_K_XL (Google oficial)

```yaml
sampling:
  temperature: 1.0
  top_p: 0.95
  top_k: 64
  min_p: 0.0
  presence_penalty: 0.0
  repeat_penalty: 1.0
```

### Q2_K_XL (configuración anti-loop)

```yaml
sampling:
  temperature: 1.0
  top_p: 0.95
  top_k: 64
  min_p: 0.05          # Filtra tokens con prob < 5%
  presence_penalty: 0.2  # Penaliza tokens ya usados
  repeat_penalty: 1.2   # Penalización fuerte
```

**Nota**: Incluso con esta configuración y `cache q8_0`, Q2 sigue haciendo loop en código. La cuantización Q2 pierde demasiada calidad para generación estructurada.

### Draft MTP (Multi-Token Prediction)

- **Workaround**: `tensor_split: "1"` en YAML (evita bug NaN en cálculo de free memory, issue #24795)
- **Speedup**: 39.7 → 46.6 tok/s (+17%)
- **Draft model**: `mtp-gemma-4-12B-it.gguf` (422.86M params, 4 blocks)
- **Acceptance rate**: ~25-30% (mean len 1.7-2.1)

## Problemas conocidos

1. **Warning tokens**: `<|tool_response>` y `</s>` generan warnings (bug del modelo, no afecta funcionamiento)
2. **Q2_K_XL loops en código**: La variante Q2 entra en loops infinitos al generar código o patrones repetitivos. Se probó con `repeat_penalty: 1.2`, `presence_penalty: 0.2`, `min_p: 0.05`, y `cache q8_0` — el problema persiste. **No recomendada para generación de código.** Usar Q3 o Q4 para estas tareas.
