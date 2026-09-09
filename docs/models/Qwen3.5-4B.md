# Qwen3.5-4B — Benchmark y Configuración

Relacionado con [#17](https://github.com/santinieto/llama-launcher/issues/17).

---

## 1. Variantes disponibles

| Archivo | Tamaño | Cuantización |
|---------|--------|--------------|
| Qwen3.5-4B-UD-Q4_K_XL.gguf | 2.85 GB | Q4_K_XL |
| mmproj-BF16.gguf | 0.64 GB | BF16 (vision) |

---

## 2. Hardware de prueba

- GPU: RTX 3070 Laptop (8 GB VRAM)
- RAM: 32 GB
- SO: Windows

---

## 3. Benchmarks

| Config | Context | KV cache | VRAM libre | Gen tok/s | Estado |
|--------|---------|----------|------------|-----------|--------|
| 64K | 65535 | q8_0 | 2,766 MiB | 66-71 | 🟢 |
| 64K | 65535 | q4_0 | 3,111 MiB | 70-78 | 🟢 |
| **128K** | **131072** | **q4_0** | **2,396 MiB** | **74-79** | 🟢 |

---

## 4. Hallazgos clave

### 4.1 128K es totalmente viable

El modelo de 4B es lo suficientemente pequeño como para soportar 128K context con margen amplio (2,396 MiB libres).

### 4.2 q4_0 es más rápido que q8_0

- q8_0: 66-71 tok/s
- q4_0: 74-79 tok/s (+10%)

### 4.3 MTP no está disponible

El modelo no tiene MTP integrado. speculative.enabled debe estar en false.

### 4.4 flash_attention mejora rendimiento

Habilitar flash_attention reduce uso de VRAM y mejora velocidad.

---

## 5. Configuración recomendada

```
Context: 128K (131072)
KV cache: q4_0
GPU layers: all
flash_attention: true
~75 tok/s, 2,396 MiB VRAM libre
```

---

## 6. Estructura de archivos

```
models/Qwen3.5-4B/
├── model.yaml
└── gguf/
    ├── mmproj-BF16.gguf
    └── Qwen3.5-4B-UD-Q4_K_XL.gguf
```

---

## 7. Configuración YAML óptima

```yaml
hardware:
  gpu_layers: all
  context_size: 131072
  batch_size: 2048
  micro_batch: 256
cache:
  type_k: q4_0
  type_v: q4_0
speculative:
  enabled: false
advanced:
  flash_attention: true
  reasoning: true
```
