# -*- coding: utf-8 -*-
import json
import urllib.request
import time
import sys
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BENCHMARK_DIR = Path(__file__).parent
DATASET_PATH = BENCHMARK_DIR / "dataset" / "benchmark_dataset.json"
RESULTS_DIR = BENCHMARK_DIR / "results"

DETERMINISTIC_CATEGORIES = {"logic", "math", "code", "knowledge"}
CREATIVE_CATEGORIES = {"creative", "reading"}


def load_dataset():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_raw_header(model_name, port, max_tokens, dataset_version, runtime_config):
    return {
        "benchmark": {
            "name": "local-model-benchmark",
            "version": dataset_version,
            "dataset": str(DATASET_PATH.name)
        },
        "model": {
            "name": model_name,
            "port": port,
            "endpoint": f"http://127.0.0.1:{port}/v1/chat/completions"
        },
        "runtime": {
            "backend": runtime_config.get("backend", "llama.cpp"),
            "max_tokens": max_tokens,
            "context_size": runtime_config.get("context_size", 0),
            "quantization": runtime_config.get("quantization", "unknown"),
            "gpu_layers": runtime_config.get("gpu_layers", "unknown"),
            "batch_size": runtime_config.get("batch_size", 0),
            "temperature_by_category": {
                cat: 0.0 for cat in DETERMINISTIC_CATEGORIES
            } | {cat: 0.7 for cat in CREATIVE_CATEGORIES}
        },
        "timestamp_start": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "timestamp_end": None,
        "total_questions": 0,
        "questions": []
    }


def save_incremental(output_path, raw_data):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, indent=2, ensure_ascii=False)


def get_temperature(category):
    if category in DETERMINISTIC_CATEGORIES:
        return 0.0
    return 0.7


def generate_response(base_url, model, messages, temperature, max_tokens, timeout=120):
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False
    }
    if max_tokens > 0:
        body["max_tokens"] = max_tokens
    req = urllib.request.Request(
        base_url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def extract_metrics(data):
    usage = data.get("usage", {})
    timings = data.get("timings", {})
    prompt_tokens = usage.get("prompt_tokens", timings.get("prompt_n", 0))
    completion_tokens = usage.get("completion_tokens", timings.get("predicted_n", 0))
    generation_time = timings.get("predicted_ms", 0) / 1000.0
    tok_s = timings.get("predicted_per_second", 0)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "generation_time_s": round(generation_time, 3),
        "tokens_per_second": round(tok_s, 2) if tok_s else 0
    }


def run_benchmark(model, port, max_tokens, runtime_config, question_ids=None, timeout=180):
    dataset = load_dataset()
    dataset_version = dataset.get("version", "unknown")
    questions = dataset["questions"]

    if question_ids:
        questions = [q for q in questions if q["id"] in question_ids]

    model_slug = model.lower().replace(" ", "-").replace("_", "-")
    output_path = RESULTS_DIR / model_slug / "raw.json"

    raw_data = build_raw_header(model, port, max_tokens, dataset_version, runtime_config)
    raw_data["total_questions"] = len(questions)

    base_url = f"http://127.0.0.1:{port}/v1/chat/completions"
    system_prompt = "You are an AI assistant. ALWAYS respond in English. Do not respond in any other language."

    results = []
    start_time = time.time()

    print("=" * 70)
    print(f"  BENCHMARK: {model}")
    print(f"  Dataset: benchmark_dataset.json v{dataset_version}")
    print(f"  Questions: {len(questions)}")
    print("=" * 70)
    print(f"  Port: {port} | Backend: {runtime_config.get('backend', '?')}")
    print(f"  Quantization: {runtime_config.get('quantization', '?')} | Context: {runtime_config.get('context_size', 0)}")
    print(f"  Max tokens: {max_tokens} | Timeout/question: {timeout}s")
    print("=" * 70)
    print()

    for i, q in enumerate(questions):
        qid = q["id"]
        cat = q["category"]
        temp = get_temperature(cat)
        pct = (i + 1) / len(questions) * 100

        bar_len = 30
        filled = int(bar_len * (i / len(questions)))
        bar = "█" * filled + "░" * (bar_len - filled)

        print(f"{'─' * 70}")
        print(f"  [{i+1}/{len(questions)}] {pct:.0f}% | {bar}")
        print(f"  Question: {qid}")
        print(f"  Category: {cat:<12} | Temperature: {temp}")
        print(f"{'─' * 70}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": q["prompt"] + " Answer in English only."}
        ]

        response_text = ""
        metrics = {}
        error = None
        data = None

        for attempt in range(3):
            try:
                data = generate_response(base_url, model, messages, temp, max_tokens, timeout=timeout)
                response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if response_text and response_text.strip():
                    metrics = extract_metrics(data)
                    break
                else:
                    print(f"    ↳ Empty response, retry {attempt+1}/3...")
                    time.sleep(1)
            except Exception as e:
                error = str(e)[:120]
                print(f"    ↳ Attempt {attempt+1} TIMEOUT")
                time.sleep(2)

        if not response_text.strip() and data:
            response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if response_text:
                metrics = extract_metrics(data)
                error = error or "Partial response after timeout"

        if not response_text.strip():
            error = error or "Empty response after 3 attempts"

        result = {
            "id": qid,
            "category": cat,
            "difficulty": q.get("difficulty", "unknown"),
            "prompt": q["prompt"],
            "reference_answer": q.get("reference_answer", ""),
            "response": response_text,
            "temperature": temp,
            "metrics": metrics,
            "error": error
        }

        results.append(result)

        tok_s = metrics.get("tokens_per_second", 0)
        chars = len(response_text)
        status = "OK" if not error else "ERR"
        icon = "✓" if status == "OK" else "✗"
        total_q = len(results)
        elapsed = time.time() - start_time
        eta = (elapsed / total_q) * (len(questions) - total_q) if total_q > 0 else 0

        print(f"    {icon} {status:<4} | {tok_s:6.1f} tok/s | {chars:5} chars | {metrics.get('prompt_tokens', 0):>4}→{metrics.get('completion_tokens', 0):>4} tok | {elapsed:.0f}s elapsed | ETA {eta:.0f}s")

        raw_data["questions"] = results
        raw_data["timestamp_end"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        save_incremental(output_path, raw_data)

        time.sleep(2)

    elapsed = time.time() - start_time
    ok_count = sum(1 for r in results if not r.get("error"))
    err_count = len(results) - ok_count

    print()
    print("=" * 70)
    print(f"  BENCHMARK COMPLETE")
    print(f"  Time: {elapsed:.0f}s | OK: {ok_count} | ERR: {err_count}")
    print(f"  Saved: {output_path}")
    print("=" * 70)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Run LLM benchmark")
    parser.add_argument("--model", default="Agents-A1-4B", help="Model name")
    parser.add_argument("--port", type=int, default=18765, help="llama-server port")
    parser.add_argument("--max-tokens", type=int, default=-1, help="Max tokens per response (-1 = unlimited)")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout per question in seconds")
    parser.add_argument("--questions", nargs="*", help="Specific question IDs to run (default: all)")
    parser.add_argument("--backend", default="llama.cpp", help="Backend name (llama.cpp, vllm, etc.)")
    parser.add_argument("--context-size", type=int, default=0, help="Context size")
    parser.add_argument("--quantization", default="unknown", help="Quantization (Q4_K_M, Q8_0, etc.)")
    parser.add_argument("--gpu-layers", default="unknown", help="GPU layers (all, number, etc.)")
    parser.add_argument("--batch-size", type=int, default=0, help="Batch size")
    args = parser.parse_args()

    runtime_config = {
        "backend": args.backend,
        "context_size": args.context_size,
        "quantization": args.quantization,
        "gpu_layers": args.gpu_layers,
        "batch_size": args.batch_size,
    }

    run_benchmark(args.model, args.port, args.max_tokens, runtime_config, args.questions, timeout=args.timeout)


if __name__ == "__main__":
    main()
