import csv
import os
import time

STAGE = "baseline"
LOG_FILE = os.environ.get("VRAM_LOG_FILE", f"vram_log_{STAGE}.csv")

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
    new_file = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["timestamp", "stage", "tag", "gpu", "peak_allocated_gb", "peak_reserved_gb", "gpu_total_gb"])
        w.writerows(rows)
