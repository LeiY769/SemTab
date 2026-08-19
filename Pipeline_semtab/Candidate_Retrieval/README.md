# Candidate_Retrieval

Second pipeline stage. For every target cell it builds a list of candidate Wikidata entities, later ranked by the Ranking stage. Output: one `<table>_candidates.csv` per table with the candidates and their enrichment data.

## Usage

```
python main_candidate.py config/config_test_finetuning/config_lora.txt
```

## Main files

- `main_candidate.py` — entry point; parses the config and processes the input folder.
- `candidate_retrieval.py` — orchestrator; reads the preprocessing metadata to know which cells to process, runs the generators, deduplicates and writes results.
- `generators.py` — the candidate generators, applied in the order given by `GENERATOR_ORDER` and tagged with a decreasing quality rank used later by the scorer:
  - `DirectGenerator` (quality 1) — Wikidata full-text search on the cell value as-is.
  - `LLMGenerator` (quality 2) — the LLM proposes alternative surface forms/labels, each of which is then searched; optional self-consistency sampling (`LLM_SELF_CONSISTENCY`).
  - `FuzzyGenerator` (quality 3) — deterministic surface variants (quotes and parentheses stripped, leading article removed, `"Last, First"` reordered, split on `-` / `/`, first-word and first-two-word prefixes), each searched separately. Off by default.
- `enrichment.py` — fetches description, aliases, P31/P279 types and sitelink count for each candidate QID (features used by the ranking scorer).
- `llm_code.py` — HuggingFace LLM engine (prompt templates, batching, optional LoRA adapter via `ADAPTER_PATH`).
- `wikidata_api.py` — rate-limited Wikidata API client with retry/backoff and caching.
- `vram_logger_candidate_retrieval.py` — per-table GPU memory logging.
- `config/` — the experiment groups, one subfolder each. See its README.
- `Job/` — one SLURM script per experiment group; submit from this folder. Two of them (`job_limit_retrieval.sh`, `job_prompting_retrieval.sh`) are job arrays indexed by `SLURM_ARRAY_TASK_ID`, the others loop over the configs sequentially.

> The config paths hard-coded in most `Job/*.sh` scripts are the flat `config/config_*.txt` paths that predate the reorganisation of `config/` into per-group subfolders. Update the `CONFIGS=(...)` list (e.g. `config/config_size/config_glm_9b.txt`) before resubmitting them.

## Result

The LoRA-finetuned Qwen2.5-3B generator (`config_test_finetuning/config_lora.txt`) on top of no-LLM preprocessing gives the best gold-entity coverage; its output folder `candidate_lora_fp16` is the input used by the ranking baseline and by the full run.
