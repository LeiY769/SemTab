# Pipeline_semtab

The main annotation pipeline. Tables go through three sequential stages, each with its own folder, configs and SLURM job scripts:

1. `Preprocessing/` : cleans the raw tables (noise removal, LLM typo correction) and marks the cells/columns targeted by the ground truth.
2. `Candidate_Retrieval/` : retrieves candidate Wikidata entities for each target cell (API search + optional LLM query expansion + optional fuzzy variants) and enriches them with descriptions, aliases and types.
3. `Ranking/` : selects the final entity per cell among the candidates and derives the CEA/CTA/CPA annotations.

- `Baseline_direct/` : comparison baseline that skips retrieval entirely and asks the LLM for the answers directly.

Each stage writes CSVs that the next stage reads, so stages can also be run and evaluated independently. Every stage takes a single `KEY:value` config file as argument and keeps its experiment configs in `config/` and its SLURM scripts in `Job/`.

## Full run

- `main_pipeline.py` : runs the three stages end-to-end. Takes the three config paths as arguments (defaults to the files in `config/`):

  ```
  python main_pipeline.py config/config_preprocessing.txt config/config_candidate.txt config/config_ranking.txt
  ```

- `config/` — chained configs of the full run using the best setting of each stage: no-LLM preprocessing → LoRA-finetuned candidate generator → slm_context ranking (Qwen2.5-3B, margin 0.10). Each stage's `OUTPUT_FOLDER` is the next stage's `INPUT_FOLDER`; final annotations go to `results/full_run`.
- `job_full_pipeline.sh` — SLURM job; submit from this folder, which must contain (or symlink) `WikidataTables2024R1/` and the `lora-fp16-adapter/` used by the retrieval stage.

## Smoke run

Fast end-to-end check (minutes, not hours) with the exact same settings as the full run, on a 5-table subset:

- `make_smoke_subset.py` : builds `WikidataTables2024R1/DataSets/Valid_smoke/` deterministically: the 5 tables with the fewest CEA targets that also have CTA and CPA targets, with the target files filtered accordingly.
- `config/smoke/` : same three configs as `config/` but pointing to the subset; outputs to `results/smoke_run`.
- `job_smoke_pipeline.sh` : 2h SLURM job; builds the subset if missing, then runs `main_pipeline.py` on it. Locally: `python make_smoke_subset.py && python main_pipeline.py config/smoke/config_preprocessing.txt config/smoke/config_candidate.txt config/smoke/config_ranking.txt`.

## Experiments vs. full run

The `config/` folder here is only the chained *best* setting. The ablations and comparisons reported in the thesis live in each stage's own `config/` subfolders (`Preprocessing/config/`, `Candidate_Retrieval/config/`, `Ranking/config/`), each with its own README; their outputs are collected in `Evaluator/Testing_data/`.
