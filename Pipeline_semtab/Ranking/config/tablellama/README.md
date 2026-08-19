# tablellama

Tests `osunlp/TableLlama`, a Llama-2-7B finetuned on table-understanding tasks (including SemTab-style entity linking), as the ranking model — the question being whether a table-specialised model beats a general small instruct model at the selection step.

Everything else is the baseline: `Valid/candidate_lora_fp16` + `Valid/preprocessing_nollm`, method `slm_context`, `LLM_CONTEXT_MARGIN:0.10`, no CoT, no self-consistency. Run by `Job/job_ranking_tablellama.sh`.

| Config | Prompts | OUTPUT_FOLDER |
|---|---|---|
| `config_default_prompts.txt` | the pipeline's own templates, unchanged | `results/tablellama/default_prompts` |
| `config_tablellama_prompts.txt` | `CONTEXT_PROMPT` / `CTA_PROMPT` / `CPA_PROMPT` rewritten in TableLlama's `### Instruction / ### Input / ### Question / ### Response` instruction format | `results/tablellama/tablellama_prompts` |

The split isolates the model from its prompt format: a specialised model evaluated with foreign prompts is not a fair test of the model itself, so both variants are reported. The reference point is `../methods/config_slm_context.txt` (Qwen2.5-3B, `results/methods/slm_context`).
