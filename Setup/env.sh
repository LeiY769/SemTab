#!/bin/bash
#SBATCH --job-name=env_snapshot
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --output=logs/env_snapshot_%j.out
#SBATCH --error=logs/env_snapshot_%j.err
#SBATCH --partition=quadro

source /home/lyang/anaconda3/etc/profile.d/conda.sh
conda activate myenv

OUT_DIR="env_snapshot_$SLURM_JOB_ID"
mkdir -p "$OUT_DIR"

echo "Node : $(hostname)"
echo "Env  : $CONDA_DEFAULT_ENV"

conda env export > "$OUT_DIR/environment.yml"
conda env export --no-builds > "$OUT_DIR/environment_nobuild.yml"
pip freeze > "$OUT_DIR/requirements_full.txt"
pip freeze | grep -iE "torch|transformers|trl|peft|bitsandbytes|accelerate|datasets|tokenizers|safetensors|numpy|pandas|requests|scikit-learn|sentencepiece" > "$OUT_DIR/requirements_core.txt"

{
  echo "# ── Snapshot $(date '+%F %T') ──"
  echo "# Node: $(hostname)"
  echo "# Conda env: $CONDA_DEFAULT_ENV"
  echo "# Python: $(python --version 2>&1)"
  echo "#"
  echo "# ── GPU / Driver ──"
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null | sed 's/^/# /'
  echo "# CUDA driver max: $(nvidia-smi 2>/dev/null | grep -oP 'CUDA Version: \K[0-9.]+')"
  echo "# nvcc toolkit: $(nvcc --version 2>/dev/null | grep -oP 'release \K[0-9.]+' || echo 'non installé')"
  echo "#"
  echo "# ── PyTorch ──"
  python -c "import torch; print(f'# torch: {torch.__version__}'); print(f'# torch CUDA: {torch.version.cuda}'); print(f'# cuDNN: {torch.backends.cudnn.version()}'); print(f'# GPU dispo: {torch.cuda.is_available()}'); print(f'# GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"aucun\"}')" 2>/dev/null
} > "$OUT_DIR/system_info.txt"

echo "Snapshot written to $OUT_DIR/"
cat "$OUT_DIR/system_info.txt"