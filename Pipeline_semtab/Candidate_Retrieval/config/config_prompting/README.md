# config_prompting

**Prompting strategy** of the LLM candidate generator, on Qwen2.5-3B-Instruct with `preprocessing_nollm` and `SEARCH_LIMIT:10`. All configs differ only in `PROMPT` (and, for `sc`, the sampling keys). Run by `Job/job_prompting_retrieval.sh`, a job array. Outputs `candidate_qwen25_3b_10_<variant>`.

| Config | Prompt |
|---|---|
| `config_zeroshot.txt` | full instruction + one inline format example. The reference point. |
| `config_oneshot.txt` | same instruction + one fully solved case |
| `config_fewshot.txt` | same instruction + several solved cases |
| `config_cot.txt` | instruction rewritten as explicit step-by-step reasoning before the answer |
| `config_dumb.txt` | deliberately minimal: *"Give names that could match the text. Separate them with semicolons."* — the floor, to show how much of the score comes from the prompt rather than the model |
| `config_sc.txt` | zero-shot prompt + `LLM_SELF_CONSISTENCY:true`, 5 samples at temperature 0.7 / top-p 0.95; the suggestions are pooled and kept in vote order (ties broken by first appearance), then truncated to `LLM_MAX_SUGGESTIONS`. The only non-deterministic retrieval run. |

All variants keep `LLM_MAX_SUGGESTIONS:8` and `LLM_MAX_NEW_TOKENS:1024`, so a longer prompt never buys a longer answer.
