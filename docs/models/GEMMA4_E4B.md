# Gemma 4 E4B — Referencia

Fuente: [unsloth/gemma-4-E4B-it-qat-GGUF](https://huggingface.co/unsloth/gemma-4-E4B-it-qat-GGUF)

## Arquitectura

| Propiedad | Valor |
|-----------|-------|
| Parámetros | 4.5B effective (8B con embeddings) |
| Capas | 42 |
| Contexto máximo | 128K tokens |
| Cuantización | Q4_K_XL (QAT) |
| Flash Attention | No (usar `-fa off`) |
| Vision | Sí (mmproj-F16.gguf) |
| Audio | Sí |
| MTP | Sí (mtp-gemma-4-E4B-it.gguf) |

## Variantes disponibles

| Variante | Tamaño | Link |
|----------|--------|------|
| UD-Q4_K_XL (QAT) | 3.93 GB | [unsloth/gemma-4-E4B-it-qat-GGUF](https://huggingface.co/unsloth/gemma-4-E4B-it-qat-GGUF) |
| UD-Q2_K_XL | 3.22 GB | [unsloth/gemma-4-E4B-it-qat-GGUF](https://huggingface.co/unsloth/gemma-4-E4B-it-qat-GGUF) |
| MTP draft | 59.7 MB | [unsloth/gemma-4-E4B-it-qat-GGUF](https://huggingface.co/unsloth/gemma-4-E4B-it-qat-GGUF) |

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
| Capital de Francia | "Paris" ✅ | 39.6 tok/s |
| Código is_prime | Correcto con docstring ✅ | 74.2 tok/s |
| Razonamiento lógico | Respuesta vacía ⚠️ | 74.3 tok/s |

### Análisis

**Velocidad**: ~40-74 tok/s — **muy rápido**. Comparación:
- Gemma4-12B Q4_K_XL: ~40 tok/s
- Gemma4-E4B Q4_K_XL: **40-74 tok/s** (hasta 2x más rápido)

**VRAM**: 4163 MiB libres — margen amplio para contexto largo.

**Calidad**: Correcta en factual y código. Razonamiento lógico devolvió vacío (posible limitation de thinking mode).

**Conclusión**: **Excelente modelo para 8GB VRAM**. Rápido, cabe cómodo, soporta vision/audio/MTP.

## Configuración recomendada

```yaml
model:
  file: gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf
  draft_model: mtp-gemma-4-E4B-it.gguf

hardware:
  gpu_layers: all
  context_size: 131070
  batch_size: 2048
  flash_attention: false  # Doc oficial usa -fa off

cache:
  type_k: q8_0
  type_v: q8_0
  type_k_draft: q4_0
  type_v_draft: q4_0

speculative:
  enabled: true
  spec_type: draft-mtp
  draft_n_max: 3

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
  image_min_tokens: 1024

advanced:
  reasoning: true
  parallel: 1
  log_verbosity: 4
  cache_ram: 4096
```

## Sampling oficial (Google/Unsloth)

```yaml
temperature: 1.0
top_p: 0.95
top_k: 64
```

## Problemas conocidos

1. **`-fa off`**: La doc oficial recomienda `-fa off`, no `-fa on`
2. **Thinking mode**: Habilitar con `<|think|>` en system prompt
3. **Razonamiento**: Puede devolver respuesta vacía en ciertos prompts
