#!/bin/bash
#SBATCH --job-name=Thesis
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=48:00:00
#SBATCH --output=logs/candidate_limit%A_%a.out
#SBATCH --error=logs/candidate_limit%A_%a.err
#SBATCH --partition=quadro
#SBATCH --array=0-3%4

source /home/lyang/anaconda3/etc/profile.d/conda.sh
conda activate myenv

CONFIGS=(
    config/config_glm_9b_20.txt
    config/config_glm_9b_30.txt
    config/config_glm_9b_50.txt
    config/config_glm_9b_5.txt
)

CFG=${CONFIGS[$SLURM_ARRAY_TASK_ID]}
NAME=$(basename "$CFG" .txt)

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Task $SLURM_ARRAY_TASK_ID running config: $CFG"
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
    zip -r candidate_${NAME}_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.zip "$out"
    echo "Archive created: candidate_${NAME}_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.zip"
else
    echo "No output directory to compress."
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Processing complete."
