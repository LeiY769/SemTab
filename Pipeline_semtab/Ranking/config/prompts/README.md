# prompts

Compares prompting strategies for the slm_context method (Qwen2.5-3B, `candidate_lora_fp16`). Run by `Job/job_ranking_prompts.sh`.

- `config_oneshot.txt` / `config_fewshot.txt` — override `CONTEXT_PROMPT` with one / three solved examples before the actual case.
- `config_cot.txt` — `CONTEXT_COT:True`, the model reasons step by step before answering.
- `config_sc.txt` — `CONTEXT_SELF_CONSISTENCY:True`, 5 sampled answers (temperature 0.7) with majority vote; the only non-deterministic run of the pipeline.
- Zero-shot is the baseline, covered by `../methods/config_slm_context.txt`.
