import csv
import os
import re
import time

STAGE = "preprocessing"
LOG_DIR = os.environ.get("LOG_DIR", f"log_{STAGE}")
LOG_FILE = os.environ.get("VRAM_LOG_FILE") or os.path.join(LOG_DIR, f"vram_log_{STAGE}.csv")
TOKEN_LOG_FILE = os.environ.get("TOKEN_LOG_FILE") or os.path.join(LOG_DIR, f"token_log_{STAGE}.csv")

def check_dir(path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

def run_slug(output_folder):
    name = os.path.basename(str(output_folder).replace("\\", "/").rstrip("/"))
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")

def set_run_name(output_folder):
    global LOG_FILE, TOKEN_LOG_FILE
    new_name = run_slug(output_folder)
    if not new_name:
        return
    if "VRAM_LOG_FILE" not in os.environ:
        LOG_FILE = os.path.join(LOG_DIR, f"vram_log_{STAGE}_{new_name}.csv")
    if "TOKEN_LOG_FILE" not in os.environ:
        TOKEN_LOG_FILE = os.path.join(LOG_DIR, f"token_log_{STAGE}_{new_name}.csv")

def get_torch():
    try:
        import torch
    except ImportError:
        return None
    return torch if torch.cuda.is_available() else None

def reset_peaks(device_id=None):
    torch = get_torch()
    if torch is None:
        return
    devices = [device_id] if device_id is not None else range(torch.cuda.device_count())
    for i in devices:
        try:
            torch.cuda.reset_peak_memory_stats(i)
        except RuntimeError:
            pass  # CUDA context not initialized yet: peaks are already zero

def log_vram(tag, device_id=None):
    torch = get_torch()
    if torch is None:
        return
    devices = [device_id] if device_id is not None else range(torch.cuda.device_count())
    rows = []
    for i in devices:
        try:
            alloc = torch.cuda.max_memory_allocated(i) / 1024**3
            reserved = torch.cuda.max_memory_reserved(i) / 1024**3
            total = torch.cuda.get_device_properties(i).total_memory / 1024**3
        except RuntimeError:
            continue  # device not usable in this process
        print(f"[VRAM] {STAGE} | {tag} | GPU {i}: peak allocated {alloc:.2f} GB, peak reserved {reserved:.2f} GB (device total {total:.1f} GB)")
        rows.append([time.strftime("%Y-%m-%d %H:%M:%S"), STAGE, tag, i, f"{alloc:.3f}", f"{reserved:.3f}", f"{total:.1f}"])
    if not rows:
        return
    check_dir(LOG_FILE)
    new_file = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["timestamp", "stage", "tag", "gpu", "peak_allocated_gb", "peak_reserved_gb", "gpu_total_gb"])
        w.writerows(rows)


_totals = {"input": 0, "output": 0, "calls": 0}
_logged = {"input": 0, "output": 0, "calls": 0}

def reset_tokens():
    for key in _totals:
        _totals[key] = 0
        _logged[key] = 0

def add_tokens(input_tokens, output_tokens, calls=1):
    _totals["input"] += int(input_tokens)
    _totals["output"] += int(output_tokens)
    _totals["calls"] += int(calls)

def get_tokens():
    return dict(_totals)

def log_tokens(tag, device_id=None):
    d_in = _totals["input"] - _logged["input"]
    d_out = _totals["output"] - _logged["output"]
    d_calls = _totals["calls"] - _logged["calls"]
    for key in _totals:
        _logged[key] = _totals[key]

    gpu = device_id if device_id is not None else ""
    print(f"[TOKENS] {STAGE} | {tag} | GPU {gpu} | batch delta: {d_in} in / {d_out} out | total: {_totals['input']} in / {_totals['output']} out over {_totals['calls']} generate calls")

    check_dir(TOKEN_LOG_FILE)
    new_file = not os.path.exists(TOKEN_LOG_FILE)
    with open(TOKEN_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["timestamp", "stage", "tag", "gpu", "pid", "input_tokens", "output_tokens", "generate_calls", "total_input_tokens", "total_output_tokens", "total_generate_calls"])
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), STAGE, tag, gpu, os.getpid(), d_in, d_out, d_calls, _totals["input"], _totals["output"], _totals["calls"]])
