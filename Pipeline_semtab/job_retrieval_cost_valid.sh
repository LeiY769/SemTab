#!/bin/bash
#SBATCH --job-name=Thesis
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=48:00:00
#SBATCH --output=logs/retrieval_cost_%j.out
#SBATCH --error=logs/retrieval_cost_%j.err
#SBATCH --partition=quadro

CONDA_ROOT="${CONDA_ROOT:-$HOME/anaconda3}"
CONDA_ENV="${CONDA_ENV:-myenv}"
source "$CONDA_ROOT/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV"

PREPROCESSING=Preprocessing/config/config_preprocessing_nollm.txt

CONFIGS=(
    Candidate_Retrieval/config/config_prompting/config_zeroshot.txt
    Candidate_Retrieval/config/config_prompting/config_fewshot.txt
    Candidate_Retrieval/config/config_prompting/config_cot.txt
    Candidate_Retrieval/config/config_test_finetuning/config_lora.txt
    Candidate_Retrieval/config/config_size/config_glm_9b.txt
    Candidate_Retrieval/config/config_prompting/config_sc.txt
)

config_output() {
    grep -m1 '^OUTPUT_FOLDER:' "$1" | cut -d':' -f2- | tr -d '[:space:]'
}

for cfg in "$PREPROCESSING" "${CONFIGS[@]}"; do
    if [ ! -f "$cfg" ]; then
        echo "Config unfound: $cfg"
        exit 1
    fi
done

OUTPUT_DIRS=()
FAILED=()

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Preprocessing (no LLM): $PREPROCESSING"
echo "=================================================="

PREP_OUT=$(config_output "$PREPROCESSING")
if [ "${RESUME:-0}" = "1" ] && [ -d "$PREP_OUT" ]; then
    echo "RESUME: $PREP_OUT already there, skipped."
else
    python -u run_stages.py "preprocessing=$PREPROCESSING"
    status=$?
    if [ $status -ne 0 ]; then
        echo "Preprocessing failed (code $status), nothing to retrieve from."
        exit $status
    fi
fi
OUTPUT_DIRS+=("$PREP_OUT")

for cfg in "${CONFIGS[@]}"; do
    out=$(config_output "$cfg")

    echo "=================================================="
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Candidate retrieval: $cfg"
    echo "=================================================="

    if [ "${RESUME:-0}" = "1" ] && [ -d "$out" ]; then
        echo "RESUME: $out already there, skipped."
        OUTPUT_DIRS+=("$out")
        continue
    fi

    python -u run_stages.py "candidate=$cfg"
    status=$?
    if [ $status -ne 0 ]; then
        echo "WARNING: $cfg has failed (code $status), continuing."
        FAILED+=("$cfg (exit $status)")
        continue
    fi

    if [ -d "$out" ]; then
        OUTPUT_DIRS+=("$out")
    fi
done

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cost per variant (last row of each token log)"
echo "=================================================="

for f in log_candidate_retrieval/token_log_candidate_retrieval_*.csv; do
    [ -f "$f" ] || continue
    tail -n1 "$f" | awk -F, -v name="$(basename "$f" .csv)" \
        '{printf "%-70s %12s in / %10s out over %8s calls\n", name, $9, $10, $11}'
done

echo "=================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] All configs processed. Preparing archive..."
echo "=================================================="

if [ ${#OUTPUT_DIRS[@]} -gt 0 ]; then
    UNIQUE_DIRS=($(printf "%s\n" "${OUTPUT_DIRS[@]}" | sort -u))
    ARCHIVE=retrieval_cost_valid_${SLURM_JOB_ID}.zip
    if zip -r "$ARCHIVE" "${UNIQUE_DIRS[@]}" log_preprocessing log_candidate_retrieval; then
        echo "Archive created: $ARCHIVE"
    else
        echo "WARNING: archive failed, the output folders are still on disk."
    fi
else
    echo "No output directories to compress."
fi

if [ ${#FAILED[@]} -gt 0 ]; then
    echo "=================================================="
    echo "Configs that failed:"
    printf "  - %s\n" "${FAILED[@]}"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Processing complete."
