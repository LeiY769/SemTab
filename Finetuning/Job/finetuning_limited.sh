#!/bin/bash
#SBATCH --job-name=Thesis
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=48:00:00
#SBATCH --output=logs/finetuning_limited_%j.out
#SBATCH --error=logs/finetuning_limited_%j.err
#SBATCH --partition=quadro

# Initialize conda environment
source /home/lyang/anaconda3/etc/profile.d/conda.sh

conda activate myenv

nvidia-smi || { echo "No GPU available"; exit 1; }

set -e

python -u lora_finetuning.py config/config_limited_3b.txt

python -u lora_finetuning.py config/config_limited_7b.txt
