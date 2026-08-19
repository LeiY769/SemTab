# cta_nosel

Ablation of the CTA gate: everything is identical to the `methods/` baseline except
`CTA_FROM_SELECTION:False`, i.e. the column type is built from the type distribution of the
**whole candidate set** instead of being rebuilt from the entities actually selected by CEA
(`method_base.rebuild_cta_from_selection`).

Three methods only: `limited_slm`, `full_slm`, `slm_context` (no `noslm` — that condition
already has `CTA_FROM_SELECTION:False` in `methods/config_noslm.txt`).

## Two dataset variants

| Variant | INPUT_FOLDER | PREPROCESS_FOLDER | OUTPUT_FOLDER | Job |
|---|---|---|---|---|
| base (Valid) | `Valid/candidate_lora_fp16` | `Valid/preprocessing_nollm` | `results/cta_nosel/` | `Job/job_ranking_cta_nosel.sh` |
| other_dataset (Training) | `Training/candidate_lora_fp16_32` | `Training/preprocessing_nollm` | `results/cta_nosel_other/` | `Job/job_ranking_cta_nosel_other.sh` |

The two jobs write to different output folders, so they can run in parallel.

## Comparison points

Each config is directly comparable to the corresponding `CTA_FROM_SELECTION:True` run:

- base → `config/methods/config_{limited_slm,full_slm,slm_context}.txt` (`results/methods/`)
- other_dataset → `config/other_dataset/config_{limited_slm,slm_context}.txt`
  (`results/methods/`); `full_slm` has no existing counterpart on the Training split.
