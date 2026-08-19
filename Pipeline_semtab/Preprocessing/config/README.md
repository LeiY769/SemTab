# config

Preprocessing configurations, one `KEY:value` per line, `#` for comments. All variants share the same input (`Valid/tables`) and targets and differ only in the typo-correction step; each writes to its own `OUTPUT_FOLDER`, which is then the `INPUT_FOLDER` of a retrieval config in `../../Candidate_Retrieval/config/config_test_preprocessing/`.

## Variants

| Config | Correction model | Output folder |
|---|---|---|
| `config_preprocessing_nollm.txt` | none (`NEED_CORRECTTYPO:false`) | `preprocessing_nollm` |
| `config_preprocessing_qwen25_instruct.txt` | Qwen2.5-3B-Instruct | `preprocessing_3b_qwen_2` |
| `config_preprocessing_qwen3_thinking.txt` | Qwen3-4B-Thinking | `preprocessing_4b_qwen_3_thinking` |
| `config_preprocessing_llama.txt` | Llama-3.1-8B-Instruct | `preprocessing_llama` |
| `config_preprocessing_gemma.txt` | Gemma-3-1B-it | `preprocessing_gemma` |
| `config_preprocessing_glm.txt` | GLM-4-9B-chat | `preprocessing_glm` |
| `config_preprocessing_bigllm.txt` | Qwen3-30B-A3B-Instruct | `preprocessing_big_llm` |

Two prompt ablations on the same Qwen2.5-3B model:

- `config_preprocessing_basic_prompt.txt` — minimal instruction, no guardrails (`preprocessing_basic_prompt`).
- `config_preprocessing_qwen25_instruct_no_fewshot.txt` — full instruction but no solved examples (`preprocessing_no_few_shot`).

Other dataset:

- `config_preprocessing_nollm_2024R2.txt` — same no-LLM setting on the 2024R2 Training tables (`For_Thesis_finetune/`), the split used to build the finetuning datasets.

## Key parameters

- `INPUT_FOLDER` / `OUTPUT_FOLDER` / `TARGET_FOLDER` — raw tables, cleaned output, `cea/cta/cpa_targets.csv`.
- `NEED_CORRECTTYPO` — whether the LLM correction step runs at all; `MODEL_NAME` is ignored when it is false.
- `MODEL_NAME`, `SYSTEM_PROMPT`, `USE_FEWSHOT` / `FEWSHOT_EXAMPLES`, `NUM_GPUS` — the correction engine. The two prompt ablations act on `SYSTEM_PROMPT` and `USE_FEWSHOT`.
