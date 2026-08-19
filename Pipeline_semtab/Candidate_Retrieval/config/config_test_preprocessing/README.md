# config_test_preprocessing

**Which preprocessing to build on.** Identical retrieval setup in all configs (Qwen2.5-3B-Instruct, `GENERATOR_ORDER:direct,llm`, `SEARCH_LIMIT:10`); the only thing that changes is the `INPUT_FOLDER`, i.e. which preprocessing output the retrieval runs on. Run by `Job/job_test_from_preprocessing.sh`.

| Config | INPUT_FOLDER | OUTPUT_FOLDER |
|---|---|---|
| `config_candidate_nollm.txt` | `preprocessing_nollm` | `candidate_nollm_10` |
| `config_candidate_basic.txt` | `preprocessing_basic_prompt` | `candidate_basic_prompt_10` |
| `config_candidate_no_few_shot.txt` | `preprocessing_no_few_shot` | `candidate_no_few_shot_10` |
| `config_candidate_qwen2.txt` | `preprocessing_3b_qwen_2` | `candidate_3b_qwen_2_10` |
| `config_candidate_qwen3.txt` | `preprocessing_4b_qwen_3_thinking` | `candidate_4b_qwen_3_thinking_10` |
| `config_candidate_llama.txt` | `preprocessing_llama` | `candidate_llama_10` |
| `config_candidate_gemma.txt` | `preprocessing_gemma` | `candidate_gemma_10` |
| `config_candidate_glm.txt` | `preprocessing_glm` | `candidate_glm_10` |

This group is the one that decides the preprocessing question: the preprocessing variants are compared on gold-entity coverage *after* retrieval, not on how much they changed the text. `preprocessing_nollm` wins, which is why it is the input of every later group and of the full run.

`config_candidate_tablellm.txt` is a leftover draft — empty `MODEL_NAME`, and the same folders as the llama config. It is not in the job list.
