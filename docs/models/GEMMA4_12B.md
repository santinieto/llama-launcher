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

## Benchmark (Q4_K_XL, RTX 3070)

### Generación tok/s por configuración

| Config | Context | KV cache | Gen tok/s | VRAM libre |
|--------|---------|----------|-----------|------------|
| Baseline | 8K | q4_0 | 39.75 | 489 MiB |
| **Recomendada** | **32K** | **q4_0** | **39.68** | **358 MiB** |
| Alternativa | 65K | q4_0 | 39.72 | 119 MiB |
| Alternativa | 32K | q8_0 | 39.88 | 115 MiB |

### Tests de calidad (promedio 5 tests × 2 runs)

| Config | greeting | reasoning | coding | summarize | analysis |
|--------|----------|-----------|--------|-----------|----------|
| 8K q4_0 | 41.36 | 40.09 | 39.07 | 38.92 | 39.31 |
| 32K q4_0 | 40.08 | 39.04 | 39.52 | 39.74 | 40.03 |
| 65K q4_0 | 40.22 | 39.42 | 39.42 | 39.69 | 39.84 |
| 32K q8_0 | 39.87 | 39.52 | 39.89 | 40.16 | 39.96 |

### Hallazgos clave

1. **Velocidad constante**: ~39.7 tok/s sin importar contexto o KV type
2. **Contexto no afecta generación**: 8K = 32K = 65K en velocidad
3. **KV q4_0 vs q8_0**: Diferencia irrelevante en velocidad (< 0.5%)
4. **VRAM del modelo**: ~6.4 GiB (Q4_K_XL, 49/49 layers GPU)
5. **VRAM KV cache**: ~13 MiB extra por cada 4K de contexto (SWA layers)
6. **Draft MTP**: No funciona — requiere build más reciente

## Configuración recomendada

```yaml
model:
  file: gemma-4-12B-it-qat-UD-Q4_K_XL.gguf
  draft_model: mtp-gemma-4-12B-it.gguf

hardware:
  gpu_layers: all
  context_size: 32768    # 4x más que baseline, VRAM cómoda
  batch_size: 1024
  flash_attention: true  # Auto-habilitado con KV cuantizado
  tensor_split: "1"      # Workaround bug #24795 (NaN en tensor-split)

cache:
  type_k: q4_0          # Óptimo para VRAM
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

- **32K context**: 4x más ventana que 8K con solo -131 MiB VRAM extra
- **q4_0 KV**: Mejor relación VRAM/calidad para8GB
- **flash_attention**: Requerido para KV cuantizado, mejora eficiencia
- **draft_gpu_layers: 0**: Draft model en CPU (MTP incompatible con build actual)
- **cache_ram: 4096**: Prompt cache para conversaciones multi-turn

### Tradeoffs

| Opción | Contexto | VRAM libre | Velocidad |
|--------|----------|------------|-----------|
| Más contexto | 65K | 119 MiB | = |
| Más calidad KV | 32K q8_0 | 115 MiB | = |
| Más margen | 16K | ~500 MiB | = |

## Sampling (Google oficial)

```yaml
sampling:
  temperature: 1.0
  top_p: 0.95
  top_k: 64
  min_p: 0.0
  presence_penalty: 0.0
  repeat_penalty: 1.0
```

### Draft MTP (Multi-Token Prediction)

- **Workaround**: `tensor_split: "1"` en YAML (evita bug NaN en cálculo de free memory, issue #24795)
- **Speedup**: 39.7 → 46.6 tok/s (+17%)
- **Draft model**: `mtp-gemma-4-12B-it.gguf` (422.86M params, 4 blocks)
- **Acceptance rate**: ~25-30% (mean len 1.7-2.1)

## Problemas conocidos

1. **Warning tokens**: `<|tool_response>` y `</s>` generan warnings (bug del modelo, no afecta funcionamiento)
