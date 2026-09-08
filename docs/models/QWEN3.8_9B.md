# Qwen 3.8 9B — Referencia

## Arquitectura

| Propiedad | Valor |
|-----------|-------|
| Parámetros | 9B |
| Contexto máximo | 128K |
| Cuantizaciones | Q4_K_M (5.38 GB), Q5_K_M (6.19 GB) |
| Flash Attention | Sí |
| Reasoning | Sí (thinking) |
| Vision | No |

## Variantes disponibles

| Variante | Tamaño | YAML | Contexto óptimo |
|----------|--------|------|-----------------|
| Q4_K_M | 5.38 GB | `model.Qwen3.8-9B-Q4_K_M.yaml` | 32K |
| Q5_K_M | 6.19 GB | `model.Qwen3.8-9B-Q5_K_M.yaml` | 32K |

## Benchmarks (RTX 3070 Laptop 8GB, sept 2026)

### Q4_K_M

| Config | Context | KV cache | Gen tok/s | VRAM libre | Estado |
|--------|---------|----------|-----------|------------|--------|
| **Baseline** | **32K** | **q8_0** | **38.83** | **1595 MiB** | **🟢** |
| 65K | 65K | q8_0 | 38.80 | 891 MiB | 🟠 |
| 65K + q4_0 | 65K | q4_0 | 37.87 | 1394 MiB | 🟢 |

### Q5_K_M

| Config | Context | KV cache | Gen tok/s | VRAM libre | Estado |
|--------|---------|----------|-----------|------------|--------|
| **Baseline** | **32K** | **q8_0** | **34.24** | **906 MiB** | **🟢** |
| 65K | 65K | q8_0 | 34.28 | 224 MiB | 🔴 |
| 65K + q4_0 | 65K | q4_0 | 34.16 | 736 MiB | 🟠 |

## Configuraciones óptimas

### Q4_K_M (default)

```yaml
hardware:
  gpu_layers: all
  context_size: 32768
  batch_size: 2048

cache:
  type_k: q8_0
  type_v: q8_0
```

**VRAM**: 1595 MiB libres (margen amplio)
**Velocidad**: 38.83 tok/s (mejor encontrada)

### Q5_K_M

```yaml
hardware:
  gpu_layers: all
  context_size: 32768
  batch_size: 2048

cache:
  type_k: q8_0
  type_v: q8_0
```

**VRAM**: 906 MiB libres (margen aceptable)
**Velocidad**: 34.24 tok/s

## Análisis

### Q4_K_M vs Q5_K_M

| Métrica | Q4_K_M | Q5_K_M | Diferencia |
|---------|--------|--------|------------|
| VRAM modelo | 5.38 GB | 6.19 GB | +15% |
| VRAM libre (32K) | 1595 MiB | 906 MiB | -43% |
| Gen tok/s | 38.83 | 34.24 | -11.8% |
| Calidad | Buena | Mejor | + |

**Conclusión**: Q4_K_M es significativamente más rápido y deja más margen de VRAM. Q5_K_M tiene mejor calidad pero es 12% más lento y queda con margen bajo. Para uso general, **Q4_K_M es la mejor opción**.

### Contexto 32K vs 65K

Reducir contexto de 65K a 32K:
- **Q4_K_M**: Libera ~704 MiB VRAM (891 → 1595), sin cambio en velocidad
- **Q5_K_M**: Libera ~682 MiB VRAM (224 → 906), sin cambio en velocidad

**Regla**: Contexto no afecta velocidad de generación. Solo libera VRAM.

### KV cache q8_0 vs q4_0

| Variante | q8_0 VRAM | q4_0 VRAM | Ahorro | Velocidad |
|----------|-----------|-----------|--------|-----------|
| Q4_K_M 65K | 891 MiB | 1394 MiB | +503 MiB | -2.4% |
| Q5_K_M 65K | 224 MiB | 736 MiB | +512 MiB | -0.3% |

**Conclusión**: q4_0 libera ~500 MiB pero reduce velocidad ~2%. Usar q4_0 solo si q8_0 deja VRAM en estado crítico.

## Sampling (oficial Qwen)

```yaml
sampling:
  temperature: 0.6
  top_p: 0.95
  top_k: 20
  min_p: 0.0
  presence_penalty: 0.0
  repeat_penalty: 1.0
```

## Problemas conocidos

1. **`--flash-attn` requiere valor**: Usar `-fa on` en vez de `--flash-attn` (cambio reciente en llama.cpp)
