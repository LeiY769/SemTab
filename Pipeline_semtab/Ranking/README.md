# Ranking

Third stage of the SemTab pipeline. Takes the candidate entities produced by the retrieval stage and selects one final answer per cell, producing the three SemTab annotation tasks: CEA (cell-entity), CTA (column-type) and CPA (column-property) on the WikidataTables2024R1 dataset.

## Usage

```
python main_ranking.py config/methods/config_slm_context.txt
```

On the SLURM cluster, each `Job/job_ranking_<experiment>.sh` script runs all configs of one experiment group (see `config/README.md`) and zips the result folders. Submit them from this folder — the config paths inside are relative to it.

## Main files

- `main_ranking.py` — entry point; parses the `KEY:value` config file and calls `rank_folder`.
- `ranking.py` — orchestrator; loads candidates + preprocessing metadata per table, dispatches to the selected method, writes outputs and logs VRAM.
- `method_limited_slm.py` — rule-based selection (weighted scores) with an optional SLM tie-break on uncertain cells.
- `method_full_slm.py` — LLM debate + verify: the model picks among top-k candidates, then optionally verifies its own choice.
- `method_slm_context.py` — gated LLM selection with table context; the LLM is only called when the heuristic score margin is below a threshold (`LLM_GATE`, `LLM_CONTEXT_MARGIN`).
- `method_base.py` — shared `TableContext` (cells, headers, tasks), the `rebuild_cta_from_selection` logic and common CPA logic.
- `cea.py` / `cta.py` / `cpa.py` — task-specific scoring: candidate scoring per cell, column-type voting from CEA results, property matching from Wikidata claims.
- `scoring.py` — string/quality/type-coherence metrics (Levenshtein, Jaccard, etc.) combined with the weights `DEFAULT_WEIGHTS = (0.5, 0.2, 0.3)` defined in `cea.py` (similarity, quality, type coherence). Those weights and the tie-break margin were fitted in `Utils/weights_margin.ipynb`.
- `llm_code_ranking.py` — `LLMEngine`: HuggingFace model loading (optional LoRA adapter via `ADAPTER_PATH`), prompt templates (overridable via `CONTEXT_PROMPT`, `CTA_PROMPT`, `CPA_PROMPT`), greedy decoding by default, optional CoT and self-consistency sampling.
- `data_loader.py` — reads candidate CSVs and preprocessing files (incl. the CTA/CPA metadata header).
- `output_writer.py` — writes `cea.csv`, `cta.csv`, `cpa.csv` in the SemTab submission format (URIs, row offset).
- `wikidata_api_ranking.py` — rate-limited Wikidata API client (same client as the retrieval stage): labels, descriptions and claims are fetched live in batches, with no persistent cache.
- `vram_logger_ranking.py` — GPU memory logging per table.
- `wikidata_cache.json` — leftover label cache from an earlier run; no code in this folder reads it (the API client is cacheless), it is kept only to avoid re-querying the API from the analysis notebooks.
- `config/` — the experiment groups, one subfolder each. See its README.
- `Job/` — one SLURM script per group, plus `job_relaunch_fail.sh`, a one-config scratch script kept to re-run a config that failed mid-sweep.

## Determinism

The pipeline uses greedy decoding, so runs are reproducible. The only stochastic variant is self-consistency (`config/prompts/config_sc.txt`), which samples with temperature on purpose.
