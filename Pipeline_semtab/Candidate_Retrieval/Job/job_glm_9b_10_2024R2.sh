#!/bin/bash
#SBATCH --job-name=cand_glm_2024R2
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=48:00:00
#SBATCH --output=logs/candidate_glm_9b_10_2024R2_%j.out
#SBATCH --error=logs/candidate_glm_9b_10_2024R2_%j.err
#SBATCH --partition=quadro

source /home/lyang/anaconda3/etc/profile.d/conda.sh
conda activate myenv

CFG=config/config_glm_9b_10_2024R2.txt
NAME=$(basename "$CFG" .txt)

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running config: $CFG"
echo "=================================================="

if [ ! -f "$CFG" ]; then
    echo "Config unfound: $CFG"
    exit 1
fi

python -u main_candidate.py "$CFG"
status=$?
if [ $status -ne 0 ]; then
    echo "WARNING: $CFG has failed (code $status)."
    exit $status
fi

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Config processed. Preparing archive..."
echo "=================================================="

out=$(grep -m1 '^OUTPUT_FOLDER:' "$CFG" | cut -d':' -f2- | tr -d '[:space:]')
if [ -n "$out" ] && [ -d "$out" ]; then
    zip -r candidate_${NAME}_${SLURM_JOB_ID}.zip "$out"
    echo "Archive created: candidate_${NAME}_${SLURM_JOB_ID}.zip"
else
    echo "No output directory to compress."
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Processing complete."
