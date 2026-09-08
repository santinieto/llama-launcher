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
| context_size | 131072 | 128K ( modelo soporta 262K) |
| gpu_layers | all | 33/33 en GPU |
| batch_size | 2048 | |
| micro_batch | 512 | |
| cache type_k/v | q8_0 | KV cache cuantizado |
| flash_attention | true | Requerido para V cache cuantizado |
| reasoning | true | Habilita thinking |
| cache_ram | 8192 | Prompt cache limit en MiB |

### VRAM estimada (RTX 3070 8GB)

| Componente | MiB |
|------------|----:|
| Model buffer | ~2,573 |
| KV cache (128K, q8_0) | ~2,176 |
| Recurrent state | ~50 |
| Compute buffer | ~690 |
| Vision compute | ~223 |
| **Total** | **~4,712** |
| **VRAM libre** | **~3,480** |

### Rendimiento medido (logs)

| Métrica | Valor |
|---------|-------|
| Prompt processing | ~2,000-2,100 tok/s (fresh) |
| Prompt processing (cached) | ~770-1,050 tok/s |
| Generation | ~42-60 tok/s |

---

## 8. Disponibilidad GGUF

Quantizaciones disponibles en [Agents-A1 collection](https://huggingface.co/collections/InternScience/agents-a1):

- Q4_K_M (esta variante)
- Q4_K_XL
- IQ4_NL
- Q5_K_M
- Q6_K
- Q8_0
- Otros (ver collection)

### Variantes en esta instalación

Solo está descargada la variante `Q4_K_M` en `models/AgentsA1-4B/gguf/`.

---

## 9. Referencias

- **Paper**: [Scaling the Horizon, Not the Parameters (arXiv 2606.30616)](https://arxiv.org/abs/2606.30616)
- **GitHub**: [InternScience/Agents-A1](https://github.com/InternScience/Agents-A1)
- **HF Model**: [InternScience/Agents-A1-4B](https://huggingface.co/InternScience/Agents-A1-4B)
- **HF GGUF**: [InternScience/Agents-A1-4B-Q4_K_M-GGUF](https://huggingface.co/InternScience/Agents-A1-4B-Q4_K_M-GGUF)
- **Evaluation code**: [Agents-A1/evaluation](https://github.com/InternScience/Agents-A1/tree/main/evaluation)
