# models

Compares base LLMs for the slm_context method, everything else fixed (`candidate_lora_fp16` input, margin 0.10, zero-shot). Run by `Job/job_ranking_models.sh`. Configs differ only in `MODEL_NAME` and `OUTPUT_FOLDER`.

- `config_qwen25_0_5b/1_5b/7b.txt` — Qwen2.5-Instruct 0.5B, 1.5B, 7B.
- `config_llama32_1b/3b.txt`, `config_llama31_8b.txt` — Llama 3.2 1B/3B, Llama 3.1 8B.
- `config_gemma3_1b.txt`, `config_gemma2_9b.txt` — Gemma 3 1B, Gemma 2 9B.
- `config_glm4_9b.txt` — GLM-4 9B.
- Qwen2.5-3B is the baseline model, covered by `../methods/config_slm_context.txt`.
