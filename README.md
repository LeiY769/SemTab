# Master's Thesis : The Role of Small Language Models in Web Table Interpretation

Code for a SemTab-style table annotation system over Wikidata (WikidataTables2024R1 dataset). Given raw CSV tables, the system produces the three SemTab tasks: CEA (cell-entity annotation), CTA (column-type annotation) and CPA (column-property annotation), using small open LLMs with a deterministic, reproducible setup.

## Repository layout

- `Pipeline_semtab/` : the main three-stage pipeline (Preprocessing → Candidate Retrieval → Ranking) plus a direct-LLM baseline. See its README.
- `Finetuning/` : LoRA / QLoRA finetuning of the retrieval and ranking LLMs, with the training data used for it (`Dataset/`).
- `Evaluator/` : evaluation notebooks and the official SemTab scorers, with ground truth and all experiment outputs (`Testing_data/`).
- `EDA/` : exploratory analysis of the dataset (table sizes, NaN ratios, token statistics).
- `Setup/` : environment snapshot and extraction of a reduced Wikidata subset from a full N-Triples dump.
- `Utils/` : dataset splitting, finetuning-dataset construction, config generation and misc helper notebooks.

## Conventions used everywhere

- **Configs** are plain text, one `KEY:value` per line, `#` for comments. Every stage takes its config file as its single CLI argument, e.g. `python main_ranking.py config/methods/config_slm_context.txt`.
- **Folders chain**: each stage's `OUTPUT_FOLDER` is the next stage's `INPUT_FOLDER`, so stages can be run and evaluated independently.
- **SLURM**: GPU experiments run on a cluster; each stage folder has a `Job/` subfolder with one submission script per experiment group. Jobs are submitted from the stage folder, not from `Job/`, since the paths inside them are relative to the stage folder.
- **Determinism**: greedy decoding everywhere, so runs are reproducible. The only deliberately stochastic runs are the self-consistency configs.

## Getting started

1. Recreate the environment : see `Setup/Configuration/README.md`.
2. Place `WikidataTables2024R1/` (tables, targets, gt) at the root of `Pipeline_semtab/`.
3. Run the smoke pipeline to check the setup end-to-end in minutes : see `Pipeline_semtab/README.md`.

The Documentation was done with the help of Claude.
