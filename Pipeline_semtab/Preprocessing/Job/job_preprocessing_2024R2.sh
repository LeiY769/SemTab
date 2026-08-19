#!/bin/bash
#SBATCH --job-name=preproc_2024R2
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=4:00:00
#SBATCH --output=logs/preprocessing_2024R2.out
#SBATCH --error=logs/preprocessing_2024R2.err
#SBATCH --partition=all

source /home/lyang/anaconda3/etc/profile.d/conda.sh
conda activate myenv

CFG=config/config_preprocessing_nollm_2024R2.txt

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running config: $CFG"
echo "=================================================="

if [ ! -f "$CFG" ]; then
    echo "Config unfound: $CFG"
    exit 1
fi

python -u main_preprocessing.py "$CFG"
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
    zip -r preprocessing_nollm_2024R2_${SLURM_JOB_ID}.zip "$out"
    echo "Archive created: preprocessing_nollm_2024R2_${SLURM_JOB_ID}.zip"
else
    echo "No output directory to compress."
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Processing complete."
