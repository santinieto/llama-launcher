# Agents-A1-4B — Referencia del Modelo

Fuente: [HuggingFace - InternScience/Agents-A1-4B-Q4_K_M-GGUF](https://huggingface.co/InternScience/Agents-A1-4B-Q4_K_M-GGUF)

Paper: [arXiv 2606.30616](https://arxiv.org/abs/2606.30616)

---

## 1. Descripción

**Agents-A1** es un modelo agente de largo horizonte desarrollado por [InternScience](https://huggingface.co/InternScience) (Shanghai AI Laboratory). Diseñado para escalar capacidades agente heterogéneas en múltiples dominios:

- Long-horizon Search
- Engineering
- Scientific Research
- Instruction Following
- Tool-calling

La variante **4B** es un modelo dense (no MoE) con solo 4B parámetros pero con rendimiento comparable a modelos mucho más grandes.

---

## 2. Arquitectura

| Característica | Valor |
|----------------|-------|
| Arquitectura | `qwen35` (hybrid SSM + attention) |
| Parámetros | 4.21 B |
| Capas | 32 |
| Cabezas de atención | 16 |
| Cabezas KV | 4 (GQA) |
| Embedding dim | 2560 |
| FFN dim | 9216 |
| Contexto máximo (entrenamiento) | 262,144 tokens |
| Tokenizer | BPE (248,320 tokens) |
| Cuantización GGUF | Q4_K_M (5.13 BPW) |
| Tamaño GGUF | ~2.71 GB |

### Componentes especiales

- **SSM (State Space Model)**: capas híbridas con `ssm_d_conv=4`, `ssm_d_state=128`, `ssm_n_group=16`
- **RoPE**: dimensiones `[11, 11, 10, 0]` (M-RoPE para visión)
- **Full attention interval**: cada 4 capas
- **Vision encoder**: integrado (qwen3vl_merger, 24 capas, 641 MiB)

---

## 3. Capacidades

| Capacidad | Soporte |
|-----------|---------|
| Text generation | Sí |
| Vision (imágenes) | Sí |
| Tool calling | Sí |
| Reasoning (thinking) | Sí |
| Function calling | Sí |

### Vision encoder

| Parámetro | Valor |
|-----------|-------|
| Proyector | qwen3vl_merger |
| Emb dim | 1024 |
| Head dim | 16 |
| FFN dim | 4096 |
| Capas | 24 |
| Image size | 768 |
| Patch size | 16 |
| Image min pixels | 1,048,576 |
| Image max pixels | 4,194,304 |
| Tamaño modelo vision | 641.26 MiB |

---

## 4. Parámetros de sampling recomendados

Oficiales (documentación HF):

| Parámetro | Valor |
|-----------|-------|
| temperature | 0.85 |
| top_p | 0.95 |
| top_k | 20 |
| min_p | 0.0 |
| presence_penalty | 1.1 |
| repetition_penalty | 1.0 |

> Nota: En llama.cpp, `min_p: 0.0` significa "usar default del servidor" (0.05).

---

## 5. System Prompt oficial

```
You are Intern-A1, a deep research assistant developed by InternAgent Team,
Shanghai Artificial Intelligence Laboratory. You can have natural multi-turn
conversations with users on any topic.

## Daily Chat & Simple Questions
For everyday conversations, greetings, opinions, coding help, factual lookups,
definitions, calculations, explanations, and any question you can confidently
answer from your knowledge — just respond directly and naturally in the user's
language as Intern-A1. Do NOT use any tools for these.

## Research & Search Questions
Only when the user's question requires up-to-date information, in-depth
investigation, multi-source verification, or involves recent events, niche
topics, or anything you are uncertain about, use the available tool
**tavily_search**.

Research strategy:
- Start with a focused search query to get an overview.
- If the initial search is insufficient, refine your query with more specific terms.
- Stop searching once you have enough information to provide a comprehensive answer.
  Do not over-research.
```

---

## 6. Rendimiento (benchmarks)

### Long-horizon Search

| Benchmark | Qwen3.5-4B | Agents-A1-4B | Agents-A1 (35B) |
|-----------|-----------:|-------------:|----------------:|
| BrowseComp | 47.2 | **66.8** | 75.5 |
| XBench-DS-2510 | 73.0 | **90.0** | 86.0 |
| GAIA | 58.3 | **95.1** | 96.0 |

### Engineering & Research

| Benchmark | Qwen3.5-4B | Agents-A1-4B | Agents-A1 (35B) |
|-----------|-----------:|-------------:|----------------:|
| SciCode | 16.1 | **29.6** | 44.3 |
| MLE-Lite | 7.6 | **22.7** | 43.9 |
| FrontierScience-Research | 1.7 | **33.3** | 40.0 |

### Instruction Following

| Benchmark | Qwen3.5-4B | Agents-A1-4B | Agents-A1 (35B) |
|-----------|-----------:|-------------:|----------------:|
| IFBench | 59.2 | **69.1** | 80.6 |
| IFEval | 89.8 | **94.8** | 94.8 |

### General Agentic

| Benchmark | Qwen3.5-4B | Agents-A1-4B | Agents-A1 (35B) |
|-----------|-----------:|-------------:|----------------:|
| VitaBench | 22.0 | **40.3** | 38.8 |
| MatTools | 10.9 | **49.3** | 47.1 |

---

## 7. Configuración en llama-launcher

Ver `models/AgentsA1-4B/model.yaml`.

### Parámetros clave

| Setting | Valor | Notas |
|---------|-------|-------|
| context_size | 65536 | 65K (modelo soporta 262K, optimizado para VRAM) |
| gpu_layers | all | 33/33 en GPU |
| batch_size | 2048 | |
| micro_batch | 512 | |
| cache type_k/v | q8_0 | KV cache cuantizado |
| flash_attention | true | Requerido para V cache cuantizado |
| reasoning | true | Habilita thinking |
| cache_ram | 8192 | Prompt cache limit en MiB |

### VRAM medida (RTX 3070 8GB, sept 2026)

| Estado | Usada | Libre | Nota |
|--------|------:|------:|------|
| Baseline (sin modelo) | ~1,063 MiB | ~7,128 MiB | Antes de cargar |
| Modelo idle | ~1,700 MiB | ~6,300 MiB | Cargado, sin requests |
| En inferencia | ~6,047 MiB | ~1,972 MiB | Durante generación activa |

**VRAM real del modelo**: ~4,984 MiB (incluye KV cache dinámico)

### RAM medida

| Total | Libre | Uso |
|------:|------:|----:|
| 31.63 GB | 11.44 GB | 63.8% |

### Rendimiento medido (API, sept 2026)

| Test | Prompt tok/s | Generation tok/s | Tokens |
|------|------------:|-----------------:|--------|
| Matemática | 788.8 | 68.5 | 268+150 |
| Razonamiento | 462.0 | 63.8 | 36+200 |
| Instrucción | 454.1 | 63.6 | 37+100 |
| Definición | 300.2 | 63.1 | 23+150 |
| Coding | 345.1 | 62.9 | 27+200 |

**Promedio generation**: ~64.4 tok/s

### Comparación de configuraciones (benchmark sept 2026)

| Config | Gen tok/s | VRAM libre | Velocidad | Calidad |
|--------|----------:|----------:|-----------|---------|
| 128K q8_0 (anterior) | 64.9 | 565 MiB | Baseline | Baseline |
| **65K q8_0 (actual)** | **64.4** | **1,972 MiB** | **=** | **=** |
| 128K q4_0 | 63.7 | 1,587 MiB | -1.7% | = |
| 65K q4_0 | 62.3 | 2,482 MiB | -4.0% | = |

**Conclusión**: 65K q8_0 es la configuración óptima. Misma velocidad que 128K, 3.5x más VRAM libre, calidad idéntica.

---

## 8. Disponibilidad GGUF

### Links de descarga por cuantización

| Cuantización | Tamaño | Link |
|-------------|--------|------|
| Q4_K_M | 2.88 GB | [InternScience/Agents-A1-4B-Q4_K_M-GGUF](https://huggingface.co/InternScience/Agents-A1-4B-Q4_K_M-GGUF) |
| Q5_K_M | 3.32 GB | [bartowski/InternScience_Agents-A1-4B-GGUF](https://huggingface.co/bartowski/InternScience_Agents-A1-4B-GGUF) |
| Q6_K | 3.68 GB | [bartowski/InternScience_Agents-A1-4B-GGUF](https://huggingface.co/bartowski/InternScience_Agents-A1-4B-GGUF) |
| Q8_0 | 4.49 GB | [InternScience/Agents-A1-4B-Q8_0-GGUF](https://huggingface.co/InternScience/Agents-A1-4B-Q8_0-GGUF) |
| BF16 | 8.42 GB | [InternScience/Agents-A1-4B-F16-GGUF](https://huggingface.co/InternScience/Agents-A1-4B-F16-GGUF) |

> **Nota**: Para el modelo de **35B** (MoE), ver [InternScience/Agents-A1-Q4_K_M-GGUF](https://huggingface.co/InternScience/Agents-A1-Q4_K_M-GGUF).

### Variantes en esta instalación

Solo está descargada la variante `Q4_K_M` en `models/AgentsA1-4B/gguf/`.

---

## 9. Referencias

- **Paper**: [Scaling the Horizon, Not the Parameters (arXiv 2606.30616)](https://arxiv.org/abs/2606.30616)
- **GitHub**: [InternScience/Agents-A1](https://github.com/InternScience/Agents-A1)
- **HF Model**: [InternScience/Agents-A1-4B](https://huggingface.co/InternScience/Agents-A1-4B)
- **HF GGUF**: [InternScience/Agents-A1-4B-Q4_K_M-GGUF](https://huggingface.co/InternScience/Agents-A1-4B-Q4_K_M-GGUF)
- **Evaluation code**: [Agents-A1/evaluation](https://github.com/InternScience/Agents-A1/tree/main/evaluation)
