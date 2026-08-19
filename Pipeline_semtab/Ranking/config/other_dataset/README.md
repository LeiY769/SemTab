# other_dataset

The main ranking comparison replayed on the **Training** split of WikidataTables2024R1 instead of Valid, to check that the conclusions drawn on Valid are not an artefact of that split.

Shared setting for the whole group: `INPUT_FOLDER:Training/candidate_lora_fp16_32`, `PREPROCESS_FOLDER:Training/preprocessing_nollm` — i.e. the same no-LLM preprocessing and the same LoRA-finetuned retrieval, produced by `../../../Candidate_Retrieval/config/config_other_dataset/config_lora_training.txt`.

| Config | Method / model | OUTPUT_FOLDER |
|---|---|---|
| `config_noslm.txt` | `limited_slm`, all `*_USE_SLM:False`, `CTA_FROM_SELECTION:False` | `results/methods/no_slm` |
| `config_limited_slm.txt` | `limited_slm`, Qwen2.5-3B | `results/methods/limited_slm` |
| `config_slm_context.txt` | `slm_context`, Qwen2.5-3B, margin 0.10 | `results/methods/slm_context` |
| `config_finetuning.txt` | `slm_context`, Qwen2.5-3B + `lora-fp16-adapter-ranking3b_context` | `results/methods/finetuning_context` |
| `config_finetuning_bigger_model.txt` | `slm_context`, Qwen2.5-7B + `lora-fp16-adapter-ranking7b_context` | `results/methods/finetuning_context_7b` |

Jobs: `Job/job_ranking_test.sh` runs the two finetuning configs, `Job/job_ranking_test_noslm.sh` runs `config_noslm.txt`; the two plain method configs are launched individually.

> The `OUTPUT_FOLDER` values collide with those of the Valid `methods/` group (`results/methods/...`). Move or rename the previous results before running this group, otherwise the Valid outputs are overwritten. The collected results are kept apart in `Evaluator/Testing_data/Ranking/ranking_other_dataset/`.

`full_slm` has no counterpart here — only the two cheap methods and the finetuned variants were run on this split.
