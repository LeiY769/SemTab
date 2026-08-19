# inputs

Measures how the quality of the upstream retrieval stage affects final ranking scores: same ranking setup (slm_context, Qwen2.5-3B), different `INPUT_FOLDER` candidate sets. Run by `Job/job_ranking_inputs.sh`.

- `config_basic_prompt_10.txt` — candidates from the basic-prompt retrieval, top-10.
- `config_nollm.txt` — candidates from retrieval without LLM preprocessing.
- `config_glm_9b_5.txt` / `config_glm_9b_30.txt` — GLM-4 9B retrieval with 5 vs. 30 candidates.
- `config_qwen25_0_5b.txt` — candidates retrieved with the smallest Qwen model.
- The `candidate_lora_fp16` input is the baseline, covered by `../methods/config_slm_context.txt`.
