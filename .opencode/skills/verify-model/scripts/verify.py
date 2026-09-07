#!/usr/bin/env python3
"""
verify.py - Auditor automático de modelos Local LLM Manager
Uso: python verify.py [--model AgentsA1-4B] [--vram-target 7.5]
Deja 500MB libres en RTX 3070 8GB (target 7.5GB)
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
# Asegurar import de app.* cuando se ejecuta desde cualquier cwd
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

MODELS_DIR = Path("D:/llama.cpp/models")
LOGS_DIR = Path("D:/llama.cpp/logs")
GPU_TOTAL_GB = 8.0
VRAM_TARGET_GB = 7.5  # deja 0.5GB libres
RAM_TOTAL_GB = 31.6

def scan_models():
    from app.core.model_manager import ModelManager
    mm = ModelManager(MODELS_DIR)
    mm.scan()
    return mm

def estimate_vram(model, n_ctx_real=None):
    """Estima VRAM basado en logs reales del usuario (referencia)."""
    # Tamaños de archivo
    model_gb = model.model_path.stat().st_size / 1024**3 if model.model_path.exists() else 0
    vision_gb = 0
    if model.vision_encoder_path and model.vision_encoder_path.exists():
        vision_gb = model.vision_encoder_path.stat().st_size / 1024**3
    # KV cache: log 2176MB para 131072 q8_0, 8 layers? escala lineal con n_ctx y bytes
    n_ctx = n_ctx_real or model.hardware.context_size
    # q8_0 = 1 byte, q4_0 = 0.5 byte por elemento. Aproximamos con log: 2176MB para 131k q8_0
    bytes_per = 1.0 if model.cache.type_k == "q8_0" else 0.5 if "q4" in model.cache.type_k else 1.0
    # log: 2176MB * (n_ctx/131072) * (bytes_per/1.0)
    kv_gb = 2.176 * (n_ctx / 131072) * bytes_per
    # RS para qwen35 SSM: ~50MB constante
    rs_gb = 0.05 if "qwen" in str(model.model.file).lower() or model.name.lower().startswith("agents") else 0
    # Compute buffers fijos ~0.69+0.22+0.13
    compute_gb = 0.69 + 0.223 + 0.138
    # Overlap + overhead host
    total = model_gb * 0.9 + vision_gb + kv_gb + rs_gb + compute_gb + 0.3
    return {
        "model_gb": model_gb,
        "vision_gb": vision_gb,
        "kv_gb": kv_gb,
        "rs_gb": rs_gb,
        "compute_gb": compute_gb,
        "total_est_gb": total,
        "free_gb": GPU_TOTAL_GB - total,
    }

def parse_latest_log():
    logs = sorted(LOGS_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        # buscar output en consola si no hay .log (logs_directory puede ser solo buffer)
        return {}
    text = logs[0].read_text(encoding="utf-8", errors="ignore")[-50000:]
    info = {}
    m = re.search(r"loading model '([^']+)'", text)
    if m: info["loaded_model"] = m.group(1)
    m = re.search(r"n_ctx\s*=\s*(\d+)", text)
    if m: info["n_ctx"] = int(m.group(1))
    m = re.search(r"KV buffer size =\s*([\d.]+) MiB", text)
    if m: info["kv_mib"] = float(m.group(1))
    m = re.search(r"offloaded (\d+)/(\d+) layers", text)
    if m: info["offloaded"] = f"{m.group(1)}/{m.group(2)}"
    m = re.search(r"Qwen-VL.*require.*1024", text)
    info["needs_1024"] = bool(m)
    info["find_slot_warn"] = text.count("non-consecutive token position")
    m = re.search(r"chat template, example.*?<\|im_start\|>system\s*(.*?)\<\|im_end\|>", text, re.S)
    if m: info["system_in_log"] = m.group(1).strip()[:80]
    return info

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None)
    parser.add_argument("--vram-target", type=float, default=VRAM_TARGET_GB)
    args = parser.parse_args()

    mm = scan_models()
    log_info = parse_latest_log()

    print(f"=== Local LLM Manager - Verificacion (target VRAM <={args.vram_target}GB, deja {GPU_TOTAL_GB-args.vram_target:.1f}GB libres) ===\n")
    print(f"Modelos encontrados: {len(mm.models)} | Logs: {'si' if log_info else 'no'} {log_info}\n")

    for m in mm.models:
        if args.model:
            key = args.model.lower().replace("-", " ").replace("_", " ")
            if key not in m.name.lower() and key not in m.model.file.lower() and key not in m.directory.name.lower():
                continue
        print(f"--- {m.name} ({m.directory.name}) ---")
        errs = mm.validate_model(m)
        print(f"  YAML: file={m.model.file} ctx={m.hardware.context_size} gpu={m.hardware.gpu_layers} cache={m.cache.type_k}/{m.cache.type_v} vision={m.capabilities.vision} img_min={m.vision.image_min_tokens if m.vision else None}")
        if m.directory.joinpath("model.yaml").exists():
            import yaml
            raw = yaml.safe_load(m.directory.joinpath("model.yaml").read_text(encoding="utf-8"))
            if "system_prompt" in raw:
                sp = raw["system_prompt"]
                sp_len = len(str(sp)) if sp else 0
                present = "present" if sp else "vacio"
                print(f"  system_prompt: {sp_len} chars -> {present} (no usado hasta implementar --system-prompt en command_builder.py:89)")
            else:
                print(f"  system_prompt: ausente en YAML")
        if errs:
            print(f"  [ERR] Archivos: {'; '.join(errs)}")
        else:
            print(f"  [OK] Archivos OK")

        # Comparar con log
        if log_info:
            loaded = log_info.get("loaded_model", "")
            if loaded and Path(loaded).name != m.model.file:
                print(f"  [WARN] MISMATCH file: YAML {m.model.file} vs Log {Path(loaded).name}")
            if log_info.get("n_ctx") and log_info["n_ctx"] != m.hardware.context_size:
                print(f"  [WARN] MISMATCH n_ctx: YAML {m.hardware.context_size} vs Log {log_info['n_ctx']} (redondeo a potencia de 2 en llama-server)")
            if log_info.get("needs_1024") and (not m.vision or m.vision.image_min_tokens < 1024):
                print(f"  [WARN] Qwen-VL requiere image_min_tokens >=1024 (actual {m.vision.image_min_tokens if m.vision else None})")
            if log_info.get("find_slot_warn", 0) > 5:
                print(f"  [WARN] find_slot non-consecutive x{log_info['find_slot_warn']} -> considerar actualizar llama.cpp o ajustar batch")

        est = estimate_vram(m, n_ctx_real=log_info.get("n_ctx"))
        print(f"  VRAM estimado: model {est['model_gb']:.2f}GB + vision {est['vision_gb']:.2f}GB + KV {est['kv_gb']:.2f}GB + RS {est['rs_gb']:.2f}GB + compute {est['compute_gb']:.2f}GB = {est['total_est_gb']:.2f}GB (libres {est['free_gb']:.2f}GB)")
        print(f"  Real medido (Task Manager): 7.2/8.0GB dedicados si es AgentsA1-4B activo -> libres 0.8GB")

        # Propuestas para dejar 500MB libres
        target = args.vram_target
        if est["total_est_gb"] > target:
            over = est["total_est_gb"] - target
            print(f"  [OVER] SOBREPASA target {target}GB por {over:.2f}GB -> propuestas:")
            # Sugerencias priorizadas
            if m.cache.type_k == "q8_0":
                print(f"     - Cambiar cache.type_k/v: q8_0 -> q4_0 ahorra ~1.0GB KV (app/models/model_definition.py:54)")
            if m.hardware.context_size > 65536:
                print(f"     - Bajar hardware.context_size: {m.hardware.context_size} -> 65536 ahorra ~{est['kv_gb']/2:.2f}GB KV")
            print(f"     - O mantener y no cargar otro modelo concurrente")
        else:
            free = GPU_TOTAL_GB - est["total_est_gb"]
            if free >= 0.5:
                print(f"  [OK] deja {free:.2f}GB libres (>=0.5GB target)")
            else:
                print(f"  [JUSTO] deja {free:.2f}GB libres (<0.5GB) -> considerar q4_0 o ctx menor")

        print()

    # Resumen sistema
    try:
        import psutil
        ram = psutil.virtual_memory()
        print(f"RAM sistema: {ram.used/1024**3:.1f}/{ram.total/1024**3:.1f}GB ({ram.percent}%)")
    except:
        print(f"RAM sistema: (instala psutil para detalle)")

    try:
        import subprocess, json
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"], text=True)
        print(f"nvidia-smi: {out.strip()} (total, used, free MB)")
    except:
        print("nvidia-smi: no disponible, usa Administrador de tareas → GPU dedicada")

if __name__ == "__main__":
    main()
