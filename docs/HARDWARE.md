# Hardware — Estación de trabajo

Referencia del hardware disponible para desarrollo y ejecución de modelos localmente.

---

## Resumen

| Componente | Detalle |
|------------|---------|
| Equipo | ASUS TUF Dash F15 FX517ZR |
| OS | Windows 11 Home (64-bit, build 26200) |
| CPU | Intel Core i7-12650H (10C/16T, 2.3 GHz boost) |
| RAM | 32 GB DDR5-4800 (2x16 GB Kingston) |
| GPU dGPU | NVIDIA GeForce RTX 3070 Laptop (8 GB VRAM) |
| GPU iGPU | Intel UHD Graphics |
| SSD1 | NVMe Kingston SFYRS1000G (1 TB) |
| SSD2 | NVMe Intel SSDPEKNU512GZ (512 GB) |

---

## GPU — NVIDIA GeForce RTX 3070 Laptop

| Parámetro | Valor |
|-----------|-------|
| VRAM | 8,192 MiB (GDDR6) |
| Driver | 610.88 |
| CUDA cores | 5,120 |
| Arch | Ampere (GA104) |
| TGP | ~80-100 W (varía según modo) |

### VRAM — utilización medida con Agents-A1-4B Q4_K_M

| Estado | Usada | Libre | Nota |
|--------|------:|------:|------|
| Baseline (sin modelo) | ~1,063 MiB | ~7,128 MiB | Sistema idle |
| Modelo idle | ~2,245 MiB | ~5,774 MiB | Cargado, sin requests |
| En inferencia | ~7,453 MiB | ~566 MiB | Durante generación |

**VRAM real del modelo**: ~6,390 MiB

### Clasificación de margen VRAM

| Margen | Clasificación |
|--------|---------------|
| < 300 MiB | 🔴 crítico |
| 300–500 MiB | 🟠 bajo |
| 500–1,000 MiB | 🟢 recomendado |
| > 1,000 MiB | 🟢 amplio |

---

## CPU — Intel Core i7-12650H

| Parámetro | Valor |
|-----------|-------|
| Cores / Threads | 10 / 16 |
| Frecuencia base | 2.3 GHz |
| Frecuencia boost | 4.7 GHz (P-cores) |
| Arquitectura | Alder Lake (hybrid P+E) |
| P-cores | 6 |
| E-cores | 4 |
| Cache L3 | 24 MB |
| iGPU | Intel UHD Graphics |

### Notas para llama.cpp

- `n_threads` recomendado: 10 (igual que cores físicos)
- `n_threads_batch`: 10
- Los E-cores son más lentos; no siempre benefician inferencia LLM

---

## RAM

| Parámetro | Valor |
|-----------|-------|
| Total | 32 GB (33,962,053,632 bytes) |
| Tipo | DDR5-4800 |
| Módulos | 2x 16 GB Kingston |
| Canal | Dual channel |

### Clasificación de uso RAM

| Uso | Clasificación |
|-----|---------------|
| < 70% | 🟢 cómoda |
| 70–80% | 🟢 aceptable |
| 80–90% | 🟠 presión |
| > 90% | 🔴 crítica |

---

## Storage

| Disco | Modelo | Capacidad | Tipo |
|-------|--------|----------:|------|
| SSD1 | NVMe Kingston SFYRS1000G | 1 TB | NVMe PCIe |
| SSD2 | NVMe Intel SSDPEKNU512GZ | 512 GB | NVMe PCIe |

### Ubicación de modelos

- Modelos GGUF: `D:\llama.cpp\models\`
- Logs: `D:\llama.cpp\logs\`
- Binario llama.cpp: `D:\llama.cpp\llama.cpp\`

---

## Notas para optimización de modelos

### Prioridad de optimización

1. **Estabilidad**: modelo debe cargar sin OOM ni crash
2. **Margen VRAM**: mantener ≥500 MiB libres
3. **Velocidad**: maximizar generation tok/s dentro del margen
4. **Calidad**: preservar cuando sea razonable

### Tradeoffs relevantes

| Cambio | VRAM | RAM | Velocidad | Calidad |
|--------|------|-----|-----------|---------|
| ↑ GPU layers | ↑ | ↓ | ↑ | = |
| ↓ GPU layers | ↓ | ↑ | ↓ | = |
| ↑ context | ↑ | ↑ | ↓ | + ventana |
| ↓ context | ↓ | ↓ | ↑/↔ | - ventana |
| KV Q8→Q4 | ↓↓ | = | ↔/↑ | ↓ leve |
| ↑ batch | ↑ | ↑ | + throughput | = |

### Configuración óptima

> La configuración más rápida que mantiene el modelo estable y deja
> suficiente margen de VRAM/RAM, evitando pérdidas de calidad innecesarias.

---

## Referencias

- `nvidia-smi` para estado de GPU
- `systeminfo` para info del sistema
- `Get-CimInstance Win32_Processor` para CPU
- `Get-CimInstance Win32_OperatingSystem` para RAM disponible
