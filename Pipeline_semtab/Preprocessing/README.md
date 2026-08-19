# Preprocessing

First pipeline stage. Cleans the raw dataset tables and attaches the annotation targets, producing the input of the retrieval stage. Chained steps (each reads the previous step's output): noise removal → typo correction → target marking.

## Usage

```
python main_preprocessing.py config/config_preprocessing_nollm.txt
```

## Main files

- `main_preprocessing.py` — entry point; parses the config and runs the three steps in order.
- `noise.py` — deterministic cleanup: HTML tags, extra whitespace, quote/markdown artifacts.
- `typo_method.py` — LLM-based typo/spelling correction of cell values (batched HuggingFace inference, VRAM logging). Skipped entirely when `NEED_CORRECTTYPO:false`.
- `hasAnnotation.py` — reads `cea/cta/cpa_targets.csv` from `TARGET_FOLDER` and appends a `Metadata:` column marking which cells/columns each downstream task must annotate.
- `vram_logger_preprocessing.py` — per-table GPU memory logging, used to report the cost of the correction step.
- `config/` — one config per preprocessing variant. See its README.
- `Job/` — SLURM submission scripts (submit from this folder, the paths inside are relative to it):
  - `job_preprocessing.sh` — the eight Valid-split variants, sequentially.
  - `job_preprocessing_2024R2.sh` — single no-LLM run on the separate 2024R2 dataset (`For_Thesis_finetune/`), used to build the finetuning data.
  - `job_preprocessing_finetuning.sh` — no-LLM run on the Training split; note it still points at `config_preprocessing_nollm_training.txt`, which was renamed to `config_preprocessing_nollm_2024R2.txt`.

## Result

Evaluation (`Evaluator/Evaluate_preprocessing.ipynb`) showed the **no-LLM** variant gives the best downstream retrieval: the correction models change more correct cell values than they fix. `config_preprocessing_nollm.txt` is therefore the variant used by the full run.
