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
- `logger_ranking.py` — cost logging for the SLM calls: per-table GPU memory and prompt/generated token counts. Both files are written to the `log_ranking/` folder, created on the first write, and are named after the run's `OUTPUT_FOLDER` (`vram_log_ranking_<output folder>.csv`, `token_log_ranking_<output folder>.csv`), so successive variants do not mix into one file; setting `LOG_DIR` moves the folder, and `VRAM_LOG_FILE` / `TOKEN_LOG_FILE` override the full path. Token rows carry the per-table delta and the running total, over every task (CEA, CTA, CPA) and every extra call of the method (debate, verify, self-consistency samples). Nothing is logged for a run without SLM.
- `wikidata_cache.json` — leftover label cache from an earlier run; no code in this folder reads it (the API client is cacheless), it is kept only to avoid re-querying the API from the analysis notebooks.
- `config/` — the experiment groups, one subfolder each. See its README.
- `Job/` — one SLURM script per group, plus `job_relaunch_fail.sh`, a one-config scratch script kept to re-run a config that failed mid-sweep.

## NIL answers (`ALLOW_NIL`)

Off by default, so every experiment of the thesis behaves exactly as before. It
exists for datasets whose ground truth contains mentions with no Wikidata entity
(MammoTab 2025 — see `Mammotab/`), where a pipeline that always answers is wrong
on every one of them.

With `ALLOW_NIL:True`, the CEA prompts of `llm_code_ranking.py` gain a
`- NIL: none of the above` option and an instruction saying a NIL answer is
correct for such a cell; the parsers read `NIL`, `none of these`, `no match`,
`idk` and `I don't know` (a QID still wins, and in CoT mode an explicit
`Answer: NIL` overrides any QID weighed earlier); a cell with no candidate at all
is written as NIL instead of being skipped; `NIL_REVIEW_SCORE` adds a second gate
that sends weakly-scored cells to the LLM whatever their margin, without which a
NIL cell with one confident-looking wrong candidate would never reach it;
`NIL_SCORE_THRESHOLD` is the rules-only fallback for runs with no LLM. A NIL
choice is written out but does not vote in `CTA_FROM_SELECTION`, and the writer
emits the label with no entity URI prefix.

## Determinism

The pipeline uses greedy decoding, so runs are reproducible. The only stochastic variant is self-consistency (`config/prompts/config_sc.txt`), which samples with temperature on purpose.
