# Qwen 3.8 27B — Referencia

Fuente: [unsloth/Qwen3.8-27B-GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF), [ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF)

## Variantes descargadas

| Variante | Tamaño | BPW | Carpeta | Nota |
|----------|--------|-----|---------|------|
| UD-IQ1_M | 6.27 GB | ~1.5 | nomtp | Extremadamente comprimido |
| UD-IQ2_XXS | 6.77 GB | ~2.0 | nomtp | Muy comprimido |
| GSQ-RCO-IQ2_XS | 8.17 GB | ~2.5 | mtp | Mejor de las tres |

## Prueba en RTX 3070 8GB (sept 2026)

### Configuración testeada

- **Modelo**: Qwen3.8-27B-GSQ-RCO-IQ2_XS (8.17 GB)
- **GPU layers**: 45 (offload parcial a CPU)
- **Contexto**: 4096
- **KV cache**: q4_0
- **VRAM**: 6895 MiB usados, 1124 MiB libres

### Resultados

| Test | Respuesta | Velocidad | Estado |
|------|-----------|-----------|--------|
| Capital de Francia | "Paris" | 6.4 tok/s | ✅ Correcto |
| Código (is_prime) | Función correcta con docstring | 6.0 tok/s | ✅ Correcto |
| Razonamiento lógico | Explica por qué no se puede concluir | 5.4 tok/s | ✅ Correcto |

### Análisis

**Calidad**: Sorprendentemente buena para IQ2_XS. Respuestas correctas en los 3 tests.

**Velocidad**: ~5-6 tok/s — **muy lento**. Comparación:
- Qwen3.8-9B Q4_K_M: 39 tok/s (**7x más rápido**)
- Qwen3.8-27B IQ2_XS: 5-6 tok/s

**VRAM**: Carga con 45 GPU layers y deja 1124 MiB libres. Factible pero justo.

### Conclusión

**No vale la pena** para uso regular:
1. **7x más lento** que el 9B Q4_K_M
2. **Calidad similar o peor** (IQ2_XS destruye informações)
3. **27B no aporta ventaja** sobre 9B en estas cuantizaciones extremas

**Único caso de uso**: Si necesitás un modelo grande para experimentar y no te importa la velocidad.

## Recomendación

Usar **Qwen3.8-9B Q4_K_M** (39 tok/s, mejor calidad, VRAM cómoda) en vez de cualquier variante de 27B con IQ1/IQ2.

Para un 27B necesitarías al menos **Q4_K_M** (~15 GB) — que no cabe en 8GB VRAM.
