#!/bin/bash
#SBATCH --job-name=Thesis
#SBATCH --nodes=1                  
#SBATCH --ntasks-per-node=1      
#SBATCH --gres=gpu:1               
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=48:00:00
#SBATCH --output=logs/lora_finetuning_32.out
#SBATCH --error=logs/lora_finetuning_32.err
#SBATCH --partition=quadro

# Initialize conda environment
source /home/lyang/anaconda3/etc/profile.d/conda.sh

conda activate myenv

nvidia-smi || { echo "No GPU available"; exit 1; }

python -u lora_finetuning_32.py