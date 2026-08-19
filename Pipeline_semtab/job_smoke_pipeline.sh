#!/bin/bash
#SBATCH --job-name=Thesis
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=logs/smoke_pipeline_%j.out
#SBATCH --error=logs/smoke_pipeline_%j.err
#SBATCH --partition=quadro

# Override at submit time if needed: sbatch --export=ALL,CONDA_ROOT=...,CONDA_ENV=... job_smoke_pipeline.sh
CONDA_ROOT="${CONDA_ROOT:-$HOME/anaconda3}"
CONDA_ENV="${CONDA_ENV:-myenv}"
source "$CONDA_ROOT/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV"

# End-to-end smoke test: 5 small tables through the full pipeline.
# Submit from Pipeline_semtab/ (needs WikidataTables2024R1/ and lora-fp16-adapter/).

if [ ! -d "WikidataTables2024R1/DataSets/Valid_smoke/tables" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Building smoke subset..."
    python -u make_smoke_subset.py || exit 1
fi

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running smoke pipeline"
echo "=================================================="

python -u main_pipeline.py \
    config/smoke/config_preprocessing.txt \
    config/smoke/config_candidate.txt \
    config/smoke/config_ranking.txt
status=$?
if [ $status -ne 0 ]; then
    echo "SMOKE TEST FAILED (code $status)."
    exit $status
fi

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Smoke test passed. Outputs:"
ls -l results/smoke_run
