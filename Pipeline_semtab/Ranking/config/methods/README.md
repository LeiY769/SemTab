# methods

Compares the ranking methods, everything else fixed (Qwen2.5-3B, `candidate_lora_fp16` input, `preprocessing_nollm`). Run by `Job/job_ranking_methods.sh`.

- `config_noslm.txt` — no LLM at all: `CEA/CTA/CPA_USE_SLM:False` and `CTA_FROM_SELECTION:False`, pure weighted scoring. The floor the three other methods are measured against (`results/methods/no_slm`).
- `config_limited_slm.txt` — rule-based scoring with SLM tie-break only.
- `config_full_slm.txt` — LLM debate + verify over the top-k candidates.
- `config_slm_context.txt` — gated LLM with table context (margin 0.10). **This is the baseline config for all other experiment groups**: margin sweep point 0.10, base (non-LoRA) model, `lora_fp16` input, Qwen2.5-3B, and zero-shot prompt all read their reference results from `results/methods/slm_context`.

The same four conditions are replayed on the Training split in `../other_dataset/`.
