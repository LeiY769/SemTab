# config_other_dataset

**Retrieval on splits other than Valid** — either to check the conclusions transfer, or to produce the material the finetuning is trained on.

| Config | Split | Setup | OUTPUT_FOLDER |
|---|---|---|---|
| `config_basic_test.txt` | 2024R1 Training | Qwen2.5-3B, no adapter, limit 10 | `Training/candidate_basic` |
| `config_lora_training.txt` | 2024R1 Training | Qwen2.5-3B + `lora-fp16-adapter-32`, limit 10 | `Training/candidate_lora_fp16_32` |
| `config_glm_9b_10_2024R2.txt` | 2024R2 (`For_Thesis_finetune/`) | GLM-4 9B, limit 10 | `For_Thesis_finetune/candidate_glm_9b_10` |

Two different purposes:

- The two Training configs mirror the Valid `config_test_finetuning/` pair (base vs. LoRA) on a split the adapter was not tuned for. `candidate_lora_fp16_32` is the input of `Ranking/config/other_dataset/` and `Ranking/config/cta_nosel/other_dataset/`.
- `config_glm_9b_10_2024R2.txt` runs on the separate 2024R2 data and produces `Finetuning/Dataset/candidate_glm_9b_10`, the raw material of the ranking training sets. It uses a deliberately strong model and drops the fuzzy generator on purpose (a capable LLM should already cover those surface variants), since the point here is data quality, not cost. Run by `Job/job_glm_9b_10_2024R2.sh`.

Keeping this split apart from Valid is what makes the finetuning evaluation honest: no table used to train an adapter is used to measure it.

> `Job/job_finetuning_retrieval_other_dataset.sh` still points at `config/config_2023.txt`, a config that is no longer in the repository. Point it at `config_lora_training.txt` before resubmitting it.
