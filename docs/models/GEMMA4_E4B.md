# Gemma 4 E4B — Referencia del modelo

Fuente: [unsloth/gemma-4-E4B-it-qat-GGUF](https://huggingface.co/unsloth/gemma-4-E4B-it-qat-GGUF)

## Arquitectura

| Propiedad | Valor |
|-----------|-------|
| Arquitectura | gemma4 (SSM + attention hybrid) |
| Parámetros | 7.46 B |
| Capas | 42 (22 SWA + 20 full attention) |
| Embedding | 2560 |
| Contexto máximo | 131,072 tokens |
| Cuantización | Q4_K_XL (QAT) |
| Flash Attention | No (usar `-fa off`) |
| Vision | Sí (mmproj-F16.gguf) |
| Audio | Sí |
| MTP | Sí (mtp-gemma-4-E4B-it.gguf) |
| Tokenizer | BPE, 262,144 tokens |
| Special tokens | `<bos>`, `<eos>`, `<turn|>`, `<\|tool_response\|>` |
| EOT token | `<turn|>` (106) |
| Reasoning | DeepSeek-style (`<think>...</think>`) |

### Attention heads

- **Full attention layers** (20): 8 Q heads, 2 KV heads, head_dim=512
- **SWA layers** (22): 8 Q heads, 2 KV heads, head_dim=256, sliding_window=512

### Sliding Window Pattern

```
Layer  0- 4: SWA (true)    Layer 21-24: SWA (true)
Layer  5- 9: Full (false)  Layer 25-29: Full (false)
Layer 10-14: SWA (true)    Layer 30-34: SWA (true)
Layer 15-20: Full (false)  Layer 35-41: Full (false)
```

- 22/42 layers usan SWA (sliding_window=512)
- 20/42 layers usan full attention
- shared_kv_layers: 18

### MTP (Multi-Token Prediction)

- Draft model: `mtp-gemma-4-E4B-it.gguf` (77.99M params, 4 blocks)
- Arquitectura: `gemma4-assistant`
- **Acceptance rate**: 68.6% (mean len 2.37)
- **Speedup efectivo**: ~2.37x en tokens accepted

## Variantes GGUF

### Links de descarga por cuantización

| Variante | Tamaño | BPW | Calidad | Link |
|----------|--------|-----|---------|------|
| UD-Q4_K_XL (QAT) | 3,910 MB | 4.50 | Mejor calidad | [unsloth/gemma-4-E4B-it-qat-GGUF](https://huggingface.co/unsloth/gemma-4-E4B-it-qat-GGUF) |
| UD-Q2_K_XL | 3.22 GB | — | — | [unsloth/gemma-4-E4B-it-qat-GGUF](https://huggingface.co/unsloth/gemma-4-E4B-it-qat-GGUF) |
| MTP draft | 42 MB | — | Draft model | [unsloth/gemma-4-E4B-it-qat-GGUF](https://huggingface.co/unsloth/gemma-4-E4B-it-qat-GGUF) |

### Otros repositorios GGUF

| Repo | Nota |
|------|------|
| [ggml-org/gemma-4-E4B-it-GGUF](https://huggingface.co/ggml-org/gemma-4-E4B-it-GGUF) | Oficial llama.cpp |
| [bartowski/gemma-4-E4B-it-GGUF](https://huggingface.co/bartowski/gemma-4-E4B-it-GGUF) | Múltiples quants |

## Hardware de referencia

- **GPU**: NVIDIA GeForce RTX 3070 Laptop (8 GB VRAM)
- **CPU**: Intel i7-12650H (16 threads)
- **RAM**: 32 GB DDR5-4800
- **Build**: llama.cpp 10549

## Benchmark (RTX 3070 8GB, sept 2026)

### Configuración testeada

- **Modelo**: gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf (3.93 GB)
- **GPU layers**: all
- **Contexto**: 32768
- **KV cache**: q8_0
- **VRAM**: 3856 MiB usados, 4163 MiB libres

### Resultados

| Test | Resultado | Velocidad |
|------|-----------|-----------|
| Capital de Francia | "Paris" | 39.6 tok/s |
| Código is_prime | Correcto con docstring | 74.2 tok/s |
| Razonamiento lógico | Respuesta vacía | 74.3 tok/s |

### Análisis

**Velocidad**: ~40-74 tok/s — muy rápido. Comparación:
- Gemma4-12B Q4_K_XL: ~40 tok/s
- Gemma4-E4B Q4_K_XL: **40-74 tok/s** (hasta 2x más rápido)

**VRAM**: 4163 MiB libres — margen amplio para contexto largo.

**Calidad**: Correcta en factual y código. Razonamiento lógico devolvió vacío (posible limitation de thinking mode).

**Conclusión**: Excelente modelo para 8GB VRAM. Rápido, cabe cómodo, soporta vision/audio/MTP.

## Benchmark (RTX 3070, con MTP)

### Configuración óptima

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| context_size | 65536 | Balance VRAM/ventana |
| batch_size | 4096 | Mejor throughput |
| KV cache K | q8_0 | Mejor calidad |
| KV cache V | f16 | Mejor calidad |
| draft_n_max | 2 | Menos overhead |

### VRAM por componente (medido en logs)

| Componente | VRAM |
|------------|-----:|
| Model buffer (CUDA0) | 2493.32 MiB |
| KV cache non-SWA (4 layers) | 784.00 MiB |
| KV cache SWA (20 layers) | 30.62 MiB |
| Compute buffer principal | 1340.27 MiB |
| Vision encoder (gemma4v) | 944.39 MiB |
| Audio encoder (gemma4a) | 944.39 MiB |
| Draft model + compute | ~1604 MiB |
| Vision compute buffers | 195.71 MiB |
| **Total medido (Task Manager)** | **7.2 GB** |

### Resultados medidos

| Métrica | Valor |
|---------|-------|
| VRAM usada | 7.2 / 8.0 GB |
| VRAM libre | ~800 MiB |
| RAM usada | 13.4 / 31.6 GB |
| Generation | ~99 tok/s |
| Prompt processing | 556 tok/s |
| Draft acceptance | 68.6% (mean len 2.37) |
| Acc rate pos 0 | 75.6% |
| Acc rate pos 1 | 61.6% |

### Comparación con main

| Parámetro | Main | Optimizado | Impacto |
|-----------|------|------------|---------|
| context_size | 131070 | 65536 | KV cache -50% |
| batch_size | 2048 | 4096 | +Throughput |
| KV cache | q4_0/q4_0 | q8_0/f16 | +Calidad |
| draft_n_max | 3 | 2 | -Overhead |
| cache_ram | — | 8192 | Limita prompt cache |

## Configuración recomendada

```yaml
name: Gemma 4 E4B
description: Google Gemma 4 E4B

backend:
  type: llama.cpp

model:
  file: gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf
  format: gguf
  draft_model: mtp-gemma-4-E4B-it.gguf

server:
  host: 127.0.0.1
  port: 18765
  alias: Gemma4-E4B

hardware:
  gpu_layers: all
  context_size: 65536
  batch_size: 4096
  flash_attention: false

cache:
  type_k: q8_0
  type_v: f16
  type_k_draft: q8_0
  type_v_draft: f16

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
  vision: true

vision:
  encoder: mmproj-F16.gguf
  image_min_tokens: 0

advanced:
  reasoning: true
  parallel: 1
  log_verbosity: 4
  cache_ram: 8192
```

### Justificación

- **context_size: 65536**: Reduce KV cache ~50% vs 131K, liberando ~800 MiB VRAM. 65K tokens es suficiente para la mayoría de usos.
- **batch_size: 4096**: Duplica throughput vs 2048 sin penalización significativa de VRAM.
- **KV cache q8_0/f16**: Mejor calidad que q4_0, con costo de ~400 MiB adicionales. Justificado por el margen disponible.
- **draft_n_max: 2**: Reduce overhead speculative vs 3, manteniendo buena acceptance rate (68.6%).
- **cache_ram: 8192**: Limita prompt cache en RAM para evitar presión de memoria.

### Tradeoffs

| Opción | VRAM libre | Velocidad | Calidad |
|--------|------------|-----------|---------|
| **Recomendada** (65K, q8_0/f16) | ~800 MiB | ~99 tok/s | Alta |
| Más contexto (131K, q4_0/q4_0) | ~200 MiB | ~95 tok/s | Media |
| Más margen (32K, q4_0/q4_0) | ~1200 MiB | ~100 tok/s | Media |

## Sampling oficial (Google/Unsloth)

```yaml
temperature: 1.0
top_p: 0.95
top_k: 64
```

## Análisis detallado

### Flash Attention

Flash Attention **no está soportado** en CUDA para Gemma 4 con Sliding Window Attention (SWA):

```
W resolve_fused_ops: layer 0 is assigned to device CUDA0 but Flash Attention is assigned to device CPU
W resolve_fused_ops: Flash Attention not supported, set to disabled
```

Esto es un conocido issue upstream. El modelo funciona correctamente sin Flash Attention. La diferencia de rendimiento es menor en modelos con SWA porque el KV cache ya está optimizado por layer.

### Speculative Decoding (MTP)

El modelo Gemma 4 E4B soporta MTP (Multi-Token Prediction) con el draft model incluido:

- **Draft model**: `mtp-gemma-4-E4B-it.gguf` (77.99M params, 4 blocks)
- **Arquitectura**: `gemma4-assistant`
- **Acceptance rate**: 68.6% (mean len 2.37)
- **Speedup efectivo**: ~2.37x en tokens accepted

Estadísticas detalladas del draft:

```
#calls(b,g,a) = 1 2053 2053
#gen drafts = 2053
#acc drafts = 1553
#gen tokens = 4106
#acc tokens = 2817
#mean acc len = 2.37
#acc rate/pos = (0.756, 0.616)
```

### Vision Encoder

El modelo incluye dos encoders multimodales:

1. **Vision (gemma4v)**: 944.39 MiB
   - image_size: 224
   - patch_size: 16
   - n_layer: 16
   - projection_dim: 2560

2. **Audio (gemma4a)**: 944.39 MiB
   - n_mel_bins: 128
   - audio_sample_rate: 16000
   - experimental stage

**Nota**: Los encoders consumen ~1.9 GB de VRAM. Sin vision/audio, el modelo usaría ~5.3 GB, dejando ~2.9 GB libres.

### KV Cache Structure

Gemma 4 E4B usa ISWA (Interleaved Sliding Window Attention):

- **Non-SWA KV cache**: 65536 cells, 4 layers → 784 MiB
- **SWA KV cache**: 1024 cells, 20 layers → 30.62 MiB

El KV cache non-SWA es más pequeño porque solo 4 layers no usan SWA. Las 20 capas SWA comparten KV cache con ventana de 512 tokens.

## Problemas conocidos

1. **Flash Attention no soportado**: Gemma 4 con SWA no tiene soporte CUDA para Flash Attention. Esto es upstream y no afecta funcionamiento.

2. **Warning tokens**: `<|tool_response>` y `</s>` generan warnings (bug del modelo, no afecta funcionamiento).

3. **Audio experimental**: El encoder de audio está en etapa experimental y puede tener calidad reducida.

4. **VRAM ajustada**: Con 65K context y vision, la VRAM queda en ~800 MiB libre. Reducir a 32K si se necesita más margen.

5. **`-fa off`**: La doc oficial recomienda `-fa off`, no `-fa on`

6. **Thinking mode**: Habilitar con `<|think|>` en system prompt

7. **Razonamiento**: Puede devolver respuesta vacía en ciertos prompts

## Troubleshooting

### OOM al cargar

Si el modelo falla al cargar con OOM:

1. Reducir `context_size` a 32768
2. Verificar que no hay otros procesos usando GPU
3. Verificar que `--fit off` está configurado

### Velocidad lenta

Si la velocidad es menor a 80 tok/s:

1. Verificar que `gpu_layers: all` está configurado
2. Verificar que no hay thermal throttling (temp > 85°C)
3. Verificar que `batch_size` es 4096

### Draft acceptance baja

Si el acceptance rate es menor a 50%:

1. Verificar que el draft model existe y es válido
2. Verificar que `spec_type: draft-mtp` está configurado
3. Verificar que `draft_n_max` no es mayor a 4
