#!/bin/bash
#SBATCH --job-name=Thesis
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=48:00:00
#SBATCH --output=logs/ranking_cta_margin_%j.out
#SBATCH --error=logs/ranking_cta_margin_%j.err
#SBATCH --partition=quadro

source /home/lyang/anaconda3/etc/profile.d/conda.sh
conda activate myenv


CONFIGS=(
    config/cta_margin/config_m000.txt
    config/cta_margin/config_m010.txt
    config/cta_margin/config_m020.txt
    config/cta_margin/config_m050.txt
    config/cta_margin/config_m100.txt
    config/cta_margin/config_k03.txt
    config/cta_margin/config_k10.txt
    config/cta_margin/config_k20.txt
)


OUTPUT_DIRS=()
FAILED=()

for cfg in "${CONFIGS[@]}"; do
    echo "=================================================="
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running config: $cfg"
    echo "=================================================="

    if [ ! -f "$cfg" ]; then
        echo "Config unfound: $cfg"
        FAILED+=("$cfg (missing)")
        continue
    fi

    python -u main_ranking.py "$cfg"
    status=$?
    if [ $status -ne 0 ]; then
        echo "WARNING: $cfg has failed (code $status), continuing."
        FAILED+=("$cfg (exit $status)")
    fi

    out=$(grep -m1 '^OUTPUT_FOLDER:' "$cfg" | cut -d':' -f2- | tr -d '[:space:]')
    if [ -n "$out" ] && [ -d "$out" ]; then
        OUTPUT_DIRS+=("$out")
    fi
done

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] All configs processed. Preparing archive..."
echo "=================================================="

if [ ${#OUTPUT_DIRS[@]} -gt 0 ]; then
    UNIQUE_DIRS=($(printf "%s\n" "${OUTPUT_DIRS[@]}" | sort -u))
    zip -r ranking_cta_margin_${SLURM_JOB_ID}.zip "${UNIQUE_DIRS[@]}"
    echo "Archive created: ranking_cta_margin_${SLURM_JOB_ID}.zip"
else
    echo "No output directories to compress."
fi

if [ ${#FAILED[@]} -gt 0 ]; then
    echo "=================================================="
    echo "Configs that failed:"
    printf "  - %s\n" "${FAILED[@]}"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Processing complete."
