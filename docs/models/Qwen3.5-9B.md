# Qwen3.5-9B — Benchmark y Configuración

Relacionado con [#18](https://github.com/santinieto/llama-launcher/issues/18).

---

## 1. Variantes disponibles

### nomtp (sin MTP)

| Archivo | Tamaño | Cuantización |
|---------|--------|--------------|
| Qwen3.5-9B-Q4_K_M.gguf | 5.47 GB | Q4_K_M |
| Qwen3.5-9B-UD-Q2_K_XL.gguf | 4.14 GB | Q2_K_XL |

### mtp (con MTP integrado)

| Archivo | Tamaño | Cuantización |
|---------|--------|--------------|
| Qwen3.5-9B-Q4_K_M.gguf | 5.47 GB | Q4_K_M |
| Qwen3.5-9B-Q3_K_M.gguf | 4.50 GB | Q3_K_M |

### Vision

| Archivo | Tamaño |
|---------|--------|
| mmproj-F16.gguf | 0.86 GB |

---

## 2. Hardware de prueba

- GPU: RTX 3070 Laptop (8 GB VRAM)
- RAM: 32 GB
- SO: Windows

---

## 3. Benchmarks

### nomtp (sin MTP)

| Config | Context | KV cache | VRAM libre | Gen tok/s | Estado |
|--------|---------|----------|------------|-----------|--------|
| Q4_K_M | 32K | q4_0 | 1,415 MiB | 46.6 | 🟢 |
| Q4_K_M | 64K | q4_0 | 954 MiB | 47.3 | 🟢 |
| Q2_K_XL | 64K | q4_0 | 2,235 MiB | 44.1 | 🟢 |

### mtp (con MTP)

| Config | Context | KV cache | VRAM libre | Gen tok/s | Estado |
|--------|---------|----------|------------|-----------|--------|
| Q4_K_M | 32K | q4_0 | 615 MiB | 68.0 | 🟢 |
| Q4_K_M | 64K | q4_0 | 78 MiB | 22.6 | 🔴 CRÍTICO |
| Q3_K_M | 32K | q4_0 | 1,449 MiB | 55.0 | 🟢 |

---

## 4. Hallazgos clave

### 4.1 MTP no funcionaba con archivos originales

Los archivos GGUF en `gguf/mtp/` originalmente eran copias idénticas de los archivos en `nomtp/`. No tenían tensor `blk.0.mtp` ni `nextn` integrado.

**Solución**: Descargar archivos MTP reales de `unsloth/Qwen3.5-9B-MTP-GGUF`.

### 4.2 MTP con 64K es inestable

MTP usa significativamente más VRAM por el draft model. Con 64K context, la VRAM queda en nivel crítico (< 100 MiB).

**Recomendación**: MTP con 32K maximiza velocidad sin comprometer estabilidad.

### 4.3 64K es viable para nomtp

nomtp Q4_K_M con 64K funciona con margen aceptable (954 MiB libres) y sin pérdida de calidad significativa.

### 4.4 KV cache q2_0/q3_k con 64K causa crash

Probar KV cache con cuantizaciones agresivas (q2_0, q3_k) en 64K provoca crash del servidor. Solo q4_0 es estable con 64K.

### 4.5 MTP mejora significativamente la velocidad

- nomtp Q4_K_M: 47.3 tok/s
- mtp Q4_K_M: 68.0 tok/s (+44%)

---

## 5. Configuración recomendada

### Para mayor velocidad

```
mtp Q4_K_M, 32K context, KV q4_0
68 tok/s, 615 MiB VRAM libre
```

### Para mejor margen VRAM

```
mtp Q3_K_M, 32K context, KV q4_0
55 tok/s, 1,449 MiB VRAM libre
```

### Para mayor contexto

```
nomtp Q4_K_M, 64K context, KV q4_0
47 tok/s, 954 MiB VRAM libre
```

---

## 6. Estructura de archivos

```
models/Qwen3.5-9B/
├── model.nomtp_Qwen3.5-9B-Q4_K_M.yaml (64K)
├── model.nomtp_Qwen3.5-9B-UD-Q2_K_XL.yaml (64K)
├── model.mtp_Qwen3.5-9B-Q4_K_M.yaml   (32K)
├── model.mtp_Qwen3.5-9B-Q3_K_M.yaml   (32K)
└── gguf/
    ├── mmproj-F16.gguf
    ├── nomtp/
    │   ├── Qwen3.5-9B-Q4_K_M.gguf
    │   └── Qwen3.5-9B-UD-Q2_K_XL.gguf
    └── mtp/
        ├── Qwen3.5-9B-Q4_K_M.gguf
        └── Qwen3.5-9B-Q3_K_M.gguf
```

**Nota**: No existe model.yaml base. Cada variante tiene su propio YAML per-variante.

---

## 7. Configuración YAML óptima

### nomtp Q4_K_M (64K)

```yaml
hardware:
  gpu_layers: all
  context_size: 65536
  batch_size: 2048
  micro_batch: 256
cache:
  type_k: q4_0
  type_v: q4_0
speculative:
  enabled: false
```

### mtp Q4_K_M (32K)

```yaml
hardware:
  gpu_layers: all
  context_size: 32768
  batch_size: 2048
  micro_batch: 256
cache:
  type_k: q4_0
  type_v: q4_0
  type_k_draft: q4_0
  type_v_draft: q4_0
speculative:
  enabled: true
  spec_type: draft-mtp
  draft_n_max: 3
```
