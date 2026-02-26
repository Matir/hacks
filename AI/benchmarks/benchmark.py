#!/usr/bin/env python3
import argparse
import json
import os
import platform
import requests
import subprocess
import sys
import time
from urllib.parse import urlparse
import psutil
import statistics

try:
    import GPUtil
except ImportError:
    GPUtil = None

PROMPTS = {
    "history_of_ai": "Write a comprehensive essay about the history of artificial intelligence, from its early theoretical foundations in the 1950s to modern-day large language models. Include key milestones, influential figures, and major paradigm shifts.",
    "python_coding": "Write a complete, well-documented Python script that implements a multi-threaded web scraper. The scraper should take a list of URLs, fetch their contents concurrently using a thread pool, extract all hyperlinks from the HTML, and save the results to a structured JSON file. Include proper error handling and retry logic."
}

MODEL_ALIASES = {
    "@small": ["qwen2.5:0.5b", "phi3:mini", "gemma:2b", "gemma3:4b"],
    "@medium": ["llama3.1:8b", "mistral:7b", "gemma3:12b"],
    "@large": ["gemma3:27b"],
    "@code": ["codellama:7b", "deepseek-coder:6.7b"],
    "@reasoning": ["gpt-oss:20b", "deepseek-r1:14b"]
}

def get_hardware_info():
    info = {
        "os": platform.system(),
        "os_release": platform.release(),
        "cpu": platform.processor(),
        "cpu_cores": psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "gpus": get_gpu_info()
    }
    return info

def get_gpu_info():
    gpus = []
    
    # 1. Try NVIDIA via GPUtil
    if GPUtil:
        try:
            for g in GPUtil.getGPUs():
                gpus.append({
                    "type": "NVIDIA",
                    "name": g.name,
                    "vram_mb": g.memoryTotal
                })
        except Exception:
            pass

    # 2. Try AMD via rocm-smi
    try:
        res = subprocess.run(["rocm-smi", "--showproductname"], capture_output=True, text=True)
        if res.returncode == 0:
            for line in res.stdout.split('\n'):
                if "Card Series:" in line or "Card model:" in line:
                    param, val = line.split(":", 1)
                    gpus.append({
                        "type": "AMD/ROCm",
                        "name": val.strip()
                    })
    except FileNotFoundError:
        pass

    # 3. macOS Apple Silicon
    if platform.system() == "Darwin" and platform.processor() == "arm":
        # Check if it's already added to prevent duplicates
        gpus.append({
            "type": "Apple",
            "name": "Apple Silicon (Unified Memory)"
        })

    # 4. Fallback to vulkaninfo if present
    if not gpus:
        try:
            res = subprocess.run(["vulkaninfo", "--summary"], capture_output=True, text=True)
            if res.returncode == 0:
                for line in res.stdout.split('\n'):
                    if "deviceName" in line:
                        _, val = line.split("=", 1)
                        name = val.strip()
                        if not any(g['name'] == name for g in gpus):
                            gpus.append({
                                "type": "Vulkan",
                                "name": name
                            })
        except FileNotFoundError:
            pass
            
    # 5. Fallback to lspci for any VGA compatible controller if still nothing
    if not gpus and platform.system() == "Linux":
        try:
            res = subprocess.run(["lspci"], capture_output=True, text=True)
            if res.returncode == 0:
                 for line in res.stdout.split('\n'):
                     if "VGA compatible controller" in line or "3D controller" in line:
                         parts = line.split(":", 2)
                         if len(parts) >= 3:
                             name = parts[2].strip()
                             # very generic but better than nothing
                             gpus.append({
                                 "type": "PCI",
                                 "name": name
                             })
        except FileNotFoundError:
            pass

    return gpus

def ensure_ollama_running(api_base):
    try:
        requests.get(f"{api_base}/version", timeout=2)
        return  # Already running
    except requests.RequestException:
        pass # Not responding

    # Check if the URL is local
    parsed = urlparse(api_base)
    if parsed.hostname not in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]:
        print(f"Error: Ollama API at {api_base} is unreachable.")
        sys.exit(1)

    print(f"Ollama is not responding. Attempting to start 'ollama serve' on {parsed.netloc}...")
    try:
        # Set OLLAMA_HOST to ensure it binds to the requested host and port
        env = os.environ.copy()
        port = parsed.port if parsed.port else 11434
        env["OLLAMA_HOST"] = f"{parsed.hostname}:{port}"
        
        # Start ollama as a daemon/background process
        subprocess.Popen(["ollama", "serve"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("Error: 'ollama' executable not found in PATH.")
        sys.exit(1)

    print("Waiting for Ollama to become ready", end="", flush=True)
    for _ in range(15):
        try:
            requests.get(f"{api_base}/version", timeout=2)
            print("\nOllama started successfully.")
            return
        except requests.RequestException:
            print(".", end="", flush=True)
            time.sleep(1)
            
    print("\nError: Timed out waiting for Ollama to start.")
    sys.exit(1)

def get_ollama_version(api_base):
    try:
        resp = requests.get(f"{api_base}/version", timeout=5)
        resp.raise_for_status()
        return resp.json().get("version", "unknown")
    except requests.RequestException:
        return "unknown"

def pull_model_if_missing(model, api_base):
    try:
        resp = requests.get(f"{api_base}/tags", timeout=5)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        model_names = [m["name"] for m in models]
        
        # If the user didn't specify a tag, Ollama often defaults to latest
        search_model = model if ":" in model else f"{model}:latest"
        
        if search_model not in model_names and model not in model_names:
            print(f"Model '{model}' not found locally. Pulling... ")
            pull_resp = requests.post(f"{api_base}/pull", json={"name": model}, stream=True)
            pull_resp.raise_for_status()
            for line in pull_resp.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    print(f"\rPull status: {status:<50}", end="", flush=True)
            print("\nPull complete.")
    except requests.RequestException as e:
        print(f"Error checking/pulling model {model}: {e}")

def warm_up_model(model, api_base, ctx_size):
    print(f"  Warming up {model} (ctx: {ctx_size}) to ensure it is fully loaded into memory...")
    try:
        requests.post(f"{api_base}/generate", json={
            "model": model,
            "prompt": "Hello.",
            "stream": False,
            "options": {
                "num_ctx": ctx_size
            }
        }, timeout=120)  # long timeout incase it needs to load a massive model
        
        # Check /api/ps to get memory usage of the loaded model
        resp = requests.get(f"{api_base}/ps", timeout=5)
        if resp.ok:
            data = resp.json()
            for m in data.get("models", []):
                # The model name might have :latest appended, so we check for prefix match
                if m["name"].startswith(model.split(":")[0]):
                    return {
                        "size_bytes": m.get("size", 0),
                        "size_vram_bytes": m.get("size_vram", 0),
                        "details": m.get("details", {})
                    }
    except requests.RequestException as e:
        print(f"  Warm up or /api/ps failed for {model}: {e}")
    return {}

def run_benchmark(model, iterations, api_base, ctx_sizes):
    pull_model_if_missing(model, api_base)
    
    # Structure: results[ctx_size][prompt_name] = [runs]
    results = {}
    
    for ctx in ctx_sizes:
        print(f"\n  --- Context Size: {ctx} ---")
        model_stats = warm_up_model(model, api_base, ctx)
        
        ctx_results = {}
        if model_stats:
            ctx_results["_model_stats"] = model_stats
            
        for prompt_name, prompt_text in PROMPTS.items():
            print(f"    Running prompt '{prompt_name}' ({iterations} iterations)...")
            prompt_results = []
            for i in range(iterations):
                print(f"      Iteration {i+1} / {iterations}...")
                try:
                    resp = requests.post(f"{api_base}/generate", json={
                        "model": model,
                        "prompt": prompt_text,
                        "stream": False,
                        "options": {
                            "temperature": 0.0,
                            "seed": 42,
                            "num_ctx": ctx
                        }
                    })
                    resp.raise_for_status()
                    data = resp.json()
                except requests.RequestException as e:
                    print(f"    Error during generation: {e}")
                    continue
                
                eval_count = data.get("eval_count", 0)
                eval_duration_ns = data.get("eval_duration", 0)
                prompt_eval_duration_ns = data.get("prompt_eval_duration", 0)
                
                duration_s = eval_duration_ns / 1e9
                ttft_s = prompt_eval_duration_ns / 1e9
                
                tok_sec = (eval_count / duration_s) if duration_s > 0 else 0
                
                prompt_results.append({
                    "eval_count": eval_count,
                    "eval_duration_s": round(duration_s, 2),
                    "ttft_s": round(ttft_s, 2),
                    "tokens_per_second": round(tok_sec, 2),
                    "total_duration_s": round(data.get("total_duration", 0) / 1e9, 2),
                    "load_duration_s": round(data.get("load_duration", 0) / 1e9, 2),
                    "prompt_eval_count": data.get("prompt_eval_count", 0)
                })
            ctx_results[prompt_name] = prompt_results
        results[str(ctx)] = ctx_results
    return results

def main():
    parser = argparse.ArgumentParser(description="Benchmark local Ollama LLMs.")
    parser.add_argument("--models", type=str, required=True, help="Comma-separated list of models to benchmark.")
    parser.add_argument("--iterations", type=int, default=3, help="Number of iterations per prompt.")
    parser.add_argument("--ctx-sizes", type=str, default="2048", help="Comma-separated list of context window sizes to test (e.g. 2048,8192).")
    parser.add_argument("--output", type=str, default="benchmark_results.json", help="JSON file to save/merge results.")
    parser.add_argument("--host-id", type=str, default=platform.node(), help="Identifier for this host in the results.")
    parser.add_argument("--base-url", type=str, default="http://localhost:11434", help="Base URL for the Ollama API.")
    
    args = parser.parse_args()
    raw_models = [m.strip() for m in args.models.split(",") if m.strip()]
    ctx_sizes = [int(c.strip()) for c in args.ctx_sizes.split(",") if c.strip().isdigit()]
    
    if not ctx_sizes:
        ctx_sizes = [2048]
    
    # Expand aliases
    models_expanded = []
    for rm in raw_models:
        if rm.startswith("@"):
            if rm in MODEL_ALIASES:
                models_expanded.extend(MODEL_ALIASES[rm])
            else:
                print(f"Warning: Unknown model alias '{rm}'")
        else:
            models_expanded.append(rm)
            
    # Deduplicate while preserving order
    seen = set()
    models = [x for x in models_expanded if not (x in seen or seen.add(x))]
    
    api_base = args.base_url.rstrip("/") + "/api"
    
    # Ensure ollama is running
    ensure_ollama_running(api_base)
    
    # Load existing results
    if os.path.exists(args.output):
        try:
            with open(args.output, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error reading {args.output}. Starting fresh.")
            data = {}
    else:
        data = {}

    if args.host_id not in data:
        data[args.host_id] = {
            "hardware": {},
            "ollama_version": "unknown",
            "results": {}
        }

    # Update hardware info
    data[args.host_id]["hardware"] = get_hardware_info()
    data[args.host_id]["ollama_version"] = get_ollama_version(api_base)
    
    # Run benchmarks
    for model in models:
        print(f"\n========== Benchmarking Model: {model} ==========")
        model_results = run_benchmark(model, args.iterations, api_base, ctx_sizes)
        
        if model not in data[args.host_id]["results"]:
            data[args.host_id]["results"][model] = {}
            
        for ctx_str, ctx_data in model_results.items():
            if ctx_str not in data[args.host_id]["results"][model]:
                data[args.host_id]["results"][model][ctx_str] = {}
                
            # Copy over model stats for this ctx if present
            if "_model_stats" in ctx_data:
                data[args.host_id]["results"][model][ctx_str]["_model_stats"] = ctx_data["_model_stats"]
                
            for prompt_name, runs in ctx_data.items():
                if prompt_name == "_model_stats":
                    continue
                if prompt_name not in data[args.host_id]["results"][model][ctx_str]:
                    data[args.host_id]["results"][model][ctx_str][prompt_name] = []
                
                # Merge new runs
                data[args.host_id]["results"][model][ctx_str][prompt_name].extend(runs)

    # Embed prompts reference at the root level if not present
    if "_prompts" not in data:
        data["_prompts"] = PROMPTS

    # Save results
    with open(args.output, "w") as f:
        json.dump(data, f, indent=2)
        
    print(f"\nBenchmarking complete. Results saved to {args.output}")

    # Print Summary Console Output
    print("\n" + "="*95)
    print(f"{'BENCHMARK SUMMARY (' + args.host_id + ')':^95}")
    print("="*95)
    print(f"{'Model':<25} | {'Ctx':<6} | {'Prompt':<15} | {'Med. TTFT (s)':<14} | {'Med. Tok/sec':<14}")
    print("-" * 95)
    for model in models:
        model_data = data[args.host_id]["results"].get(model, {})
        for ctx_str, ctx_runs in model_data.items():
            for prompt_name in PROMPTS.keys():
                runs = ctx_runs.get(prompt_name, [])
                if not runs:
                    continue
                ttfts = [r.get("ttft_s", 0) for r in runs if "ttft_s" in r]
                tok_secs = [r.get("tokens_per_second", 0) for r in runs if "tokens_per_second" in r]
                
                med_ttft = statistics.median(ttfts) if ttfts else 0.0
                med_tok_sec = statistics.median(tok_secs) if tok_secs else 0.0
                
                print(f"{model:<25} | {ctx_str:<6} | {prompt_name:<15} | {med_ttft:<14.2f} | {med_tok_sec:<14.2f}")
    print("="*95)

if __name__ == "__main__":
    main()
