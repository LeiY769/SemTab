# Finetuning

Supervised finetuning (SFT with TRL + PEFT) of Qwen2.5-Instruct models for two pipeline components. Training data is built by the scripts in `Utils/` from the tables in `Dataset/`; the resulting adapters are consumed by the pipeline via the `ADAPTER_PATH` config key.

Two components are finetuned:

- the **candidate generator** of the retrieval stage — given a cell value + context, predict good Wikidata search labels (`candidate_gen_*.json`);
- the **ranking LLM** — pick the right candidate among the retrieved ones (`ft_slm_context_*.json`, `ft_slm_limited_*.json`).

## Main files

- `lora_finetuning.py` — LoRA finetuning, config-driven: it reads a `config.txt` next to it with `model_name`, `train_file`, `valid_file`, `max_len`, `output_dir`, `adapter_r`, `lora_alpha`. Same script for both components — only the dataset and the output folder change. LoRA on `q/k/v/o_proj`, dropout 0.05, bf16, 5 epochs, lr 2e-4, `paged_adamw_8bit`, cosine schedule, gradient checkpointing, `completion_only_loss=True`, and early stopping on `eval_loss` when a validation file exists.
- `q_lora_finetuning.py` — QLoRA (4-bit NF4, double quant, bf16 compute) variant of the candidate-generator training, for the memory-constrained comparison. Its parameters are hard-coded, not config-driven; outputs to `./qlora-output`.
- `count_examples.ipynb` — counts the examples of every JSON dataset and prints the train/valid split ratios reported in the thesis.
- `Dataset/` — the tables, ground truth and JSON datasets the training runs on. See its README.
- `Job/` — SLURM submission scripts, one per training run: `lora_finetuning.sh`, `finetuning_32.sh` (larger-rank adapter), `q_lorafinetuning.sh`, `finetuning_ranking.sh` and `finetuning_ranking2.sh` (the two ranking adapters). The jobs are identical apart from the script they call — they differ only through the parameters that used to be hard-coded in those scripts.

> The `Job/*.sh` scripts still call the per-experiment script names of the earlier layout (`lora_finetuning_32.py`, `lora_finetuning_ranking.py`, `lora_finetuning_ranking2.py`). Those files were merged into the config-driven `lora_finetuning.py`; to rerun a variant, point the job at `lora_finetuning.py` and write the matching `config.txt` instead.

## Adapters produced

| Adapter (`ADAPTER_PATH`) | Component | Consumed by |
|---|---|---|
| `lora-fp16-adapter`, `lora-fp16-adapter-32`, `lora-fp16-adapter-all` | candidate generator | `Candidate_Retrieval/config/config_test_finetuning/` |
| `qlora-adapter` | candidate generator (4-bit) | `Candidate_Retrieval/config/config_test_finetuning/config_qlora.txt` |
| `lora-fp16-adapter-ranking3b_context`, `lora-fp16-adapter-ranking7b_context` | ranking LLM | `Ranking/config/finetuning/`, `Ranking/config/other_dataset/` |

The adapter weights themselves are not committed; retrain them with the jobs above, or point `ADAPTER_PATH` at your own copies.
