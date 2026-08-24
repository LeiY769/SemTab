# finetuning

Tests whether LoRA finetuning of the ranking LLM improves selection. Run by `Job/job_ranking_finetuning.sh` (the `slm_context` pair) and `Job/job_ranking_finetuning_limited.sh` (the `limited_slm` pair). Every config keeps the baseline setting of its method (`Valid/candidate_lora_fp16`, margin 0.10) and only adds an adapter — and, for the 7B, changes the base model.

| Config | Method | Base model | Adapter | OUTPUT_FOLDER |
|---|---|---|---|---|
| `config_lora_3b.txt` | `slm_context` | Qwen2.5-3B-Instruct | `lora-fp16-adapter-ranking3b_context` | `results/finetuning/lora_3b` |
| `config_lora_7b.txt` | `slm_context` | Qwen2.5-7B-Instruct | `lora-fp16-adapter-ranking7b_context` | `results/finetuning/lora_7b` |
| `config_lora_3b_limited.txt` | `limited_slm` | Qwen2.5-3B-Instruct | `lora-fp16-adapter-ranking3b_limited` | `results/finetuning/lora_3b_limited` |
| `config_lora_7b_limited.txt` | `limited_slm` | Qwen2.5-7B-Instruct | `lora-fp16-adapter-ranking7b_limited` | `results/finetuning/lora_7b_limited` |

The adapters are trained in `Finetuning/` on `ft_slm_context_*.json` and `ft_slm_limited_*.json`, the datasets built by `Utils/dataset_build_ranking.py` by replaying the corresponding prompts against the ground truth.

The non-finetuned base models are the baselines, covered by `../methods/config_slm_context.txt` and `../methods/config_limited_slm.txt`. The same four adapters are also evaluated on the Training split in `../other_dataset/`.
