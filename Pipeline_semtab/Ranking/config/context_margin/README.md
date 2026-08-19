# context_margin

Sweep of `LLM_CONTEXT_MARGIN`, the gate threshold of the slm_context method: a cell is sent to the LLM only if the heuristic score gap between the top candidates is below the margin. 0.00 means the LLM is never called, 1.00 means it is called on every cell. Run by `Job/job_ranking_context_margin.sh`.

- `config_m000.txt` … `config_m100.txt` — margins 0.00, 0.05, 0.20, 0.40, 1.00; identical otherwise (Qwen2.5-3B, `candidate_lora_fp16`).
- Margin 0.10 is the baseline and lives in `../methods/config_slm_context.txt` (results in `results/methods/slm_context`).
