# config_size

**Model size and family** of the LLM candidate generator. Everything else fixed: `preprocessing_nollm` input, `GENERATOR_ORDER:direct,llm`, `SEARCH_LIMIT:10`, same prompt. Run by `Job/job_size_retrieval.sh`. Configs differ only in `MODEL_NAME` and `OUTPUT_FOLDER` (`candidate_size_<model>_10`).

| Config | MODEL_NAME |
|---|---|
| `config_qwen25_0_5b.txt` | `Qwen/Qwen2.5-0.5B-Instruct` |
| `config_qwen25_1_5b.txt` | `Qwen/Qwen2.5-1.5B-Instruct` |
| `config_qwen25_3b.txt` | `Qwen/Qwen2.5-3B-Instruct` |
| `config_qwen25_7b.txt` | `Qwen/Qwen2.5-7B-Instruct` |
| `config_llama32_1b.txt` | `meta-llama/Llama-3.2-1B-Instruct` |
| `config_llama32_3b.txt` | `meta-llama/Llama-3.2-3B-Instruct` |
| `config_gemma2_9b.txt` | `google/gemma-2-9b-it` |
| `config_glm_9b.txt` | `zai-org/glm-4-9b-chat-hf` |

The four Qwen2.5 sizes give the size effect within one family; the other four say whether it is a size effect or a family effect. Results in `Evaluator/Testing_data/Candidate/Retrieval_size/`.
