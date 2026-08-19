# Configuration

Snapshot of the `myenv` conda environment used for all GPU experiments on the SLURM cluster (taken 2026-07-06 on compute-11). Keeps the exact software versions for reproducibility.

## Files

- `environment.yml` — full conda export with exact build strings; exact restore, but linux-64 only.
- `environment_nobuild.yml` — same export without build strings; more portable across platforms/channel updates.
- `requirements_core.txt` — the 12 pip packages the code actually depends on (torch, transformers, peft, trl, datasets, accelerate, bitsandbytes, pandas, numpy, requests, tokenizers, safetensors); use this for a fresh environment.
- `requirements_full.txt` — complete `pip freeze` of the environment (local `file:///` references replaced by their pinned versions, so it is installable as-is).
- `system_info.txt` — hardware/driver context: Quadro RTX 6000 24 GB, driver 550.90.07, CUDA 12.4, Python 3.9.23, torch 2.6.0+cu124.

## Recreate the environment

Exact restore on the cluster (linux-64):

```
conda env create -f environment.yml
```

Fresh minimal environment elsewhere:

```
conda create -n myenv python=3.9
conda activate myenv
pip install -r requirements_core.txt --extra-index-url https://download.pytorch.org/whl/cu124
```

The `--extra-index-url` is required because `torch==2.6.0+cu124` is a CUDA-specific build not on PyPI.
