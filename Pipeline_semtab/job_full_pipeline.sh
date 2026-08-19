#!/bin/bash
#SBATCH --job-name=Thesis
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=48:00:00
#SBATCH --output=logs/full_pipeline_%j.out
#SBATCH --error=logs/full_pipeline_%j.err
#SBATCH --partition=quadro

# Override at submit time if needed: sbatch --export=ALL,CONDA_ROOT=...,CONDA_ENV=... job_full_pipeline.sh
CONDA_ROOT="${CONDA_ROOT:-$HOME/anaconda3}"
CONDA_ENV="${CONDA_ENV:-myenv}"
source "$CONDA_ROOT/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV"

# Submit from Pipeline_semtab/. Requires in this folder (copy or symlink):
#   - WikidataTables2024R1/  (dataset)
#   - lora-fp16-adapter/     (retrieval LoRA adapter, see config/config_candidate.txt)

CONFIGS=(
    config/config_preprocessing.txt
    config/config_candidate.txt
    config/config_ranking.txt
)

for cfg in "${CONFIGS[@]}"; do
    if [ ! -f "$cfg" ]; then
        echo "Config unfound: $cfg"
        exit 1
    fi
done

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running full pipeline"
echo "=================================================="

python -u main_pipeline.py "${CONFIGS[@]}"
status=$?
if [ $status -ne 0 ]; then
    echo "WARNING: full pipeline failed (code $status)."
    exit $status
fi

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pipeline done. Preparing archive..."
echo "=================================================="

out=$(grep -m1 '^OUTPUT_FOLDER:' config/config_ranking.txt | cut -d':' -f2- | tr -d '[:space:]')
if [ -n "$out" ] && [ -d "$out" ]; then
    zip -r full_pipeline_${SLURM_JOB_ID}.zip "$out"
    echo "Archive created: full_pipeline_${SLURM_JOB_ID}.zip"
else
    echo "No output directory to compress."
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Processing complete."
