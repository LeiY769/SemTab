# Dataset

The data the finetuning runs on. It is a **separate split from the one the pipeline is evaluated on** (the SemTab 2024R2 Training tables, called `For_Thesis_finetune/` in the configs and job scripts), so that no table used to train an adapter is later used to measure it.

## Raw data

- `Training/` — 1116 raw tables (`<table_id>.csv`).
- `targets/` — `cea_targets.csv` (15 000 cells), `cta_targets.csv` (1317 columns), `cpa_targets.csv` (1538 column pairs): what has to be annotated.
- `cea_gt.csv`, `cta_gt.csv`, `cpa_gt.csv` — the ground truth for those targets, in the SemTab format `table,row,col,URI`.

## Intermediate pipeline outputs

Produced by running the first two pipeline stages on this split, and used as the raw material of the training examples:

- `preprocessing_nollm/` — the 1116 tables after no-LLM preprocessing, with the `Metadata:` target column. Built by `Pipeline_semtab/Preprocessing/config/config_preprocessing_nollm_2024R2.txt`.
- `candidate_glm_9b_10/` — candidate entities per target cell, retrieved with GLM-4 9B, 10 results per query. Built by `Pipeline_semtab/Candidate_Retrieval/config/config_other_dataset/config_glm_9b_10_2024R2.txt`.

## Training sets

`finetune_datasets/` — the JSON files consumed by the scripts one level up, each a flat list of examples, split roughly 90/10 train/valid (`VAL_RATIO:0.1`, `SEED:0` for the ranking sets — see `Utils/finetune/config_finetune.txt`):

| File | train / valid | Component | Built by |
|---|---|---|---|
| `candidate_gen_*.json` | 13 406 / 1 589 | candidate generator | `Utils/dataset_build.ipynb` |
| `ft_slm_context_*.json` | 4 031 / 519 | ranking, `slm_context` method | `Utils/dataset_build_ranking.py` |
| `ft_slm_limited_*.json` | 2 975 / 276 | ranking, `limited_slm` method | `Utils/dataset_build_ranking.py` |

The candidate-generator examples carry `cell_value` / `context` / `candidates`; the ranking examples carry the rendered `system` + `user` prompt, the gold `completion`, and the bookkeeping fields (`gold_rank`, `margin`, `n_candidates`, `table`, `row`, `col`) used to filter and analyse them.

The two ranking sets are smaller than the number of CEA targets on purpose: only the cells the corresponding method would actually send to the LLM (those below the gate margin) become training examples, so the adapter is trained on exactly the distribution it sees at inference time.
