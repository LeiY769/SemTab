# finetuning

Tests whether LoRA finetuning of the ranking LLM improves selection. Run by `Job/job_ranking_finetuning.sh`. Both configs keep the baseline setting (`Valid/candidate_lora_fp16`, `slm_context`, margin 0.10) and only add an adapter — and, for the 7B, change the base model.

| Config | Base model | Adapter | OUTPUT_FOLDER |
|---|---|---|---|
| `config_lora_3b.txt` | Qwen2.5-3B-Instruct | `lora-fp16-adapter-ranking3b_context` | `results/finetuning/lora_3b` |
| `config_lora_7b.txt` | Qwen2.5-7B-Instruct | `lora-fp16-adapter-ranking7b_context` | `results/finetuning/lora_7b` |

Both adapters are trained in `Finetuning/` on `ft_slm_context_*.json`, the dataset built by `Utils/dataset_build_ranking.py` by replaying the slm_context prompts against the ground truth.

The non-finetuned base model is the baseline, covered by `../methods/config_slm_context.txt`. The same two adapters are also evaluated on the Training split in `../other_dataset/`.
