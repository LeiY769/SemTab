# config_test_finetuning

**Finetuned candidate generators** vs. the non-finetuned one. All configs run Qwen2.5-3B-Instruct on `preprocessing_nollm` with `GENERATOR_ORDER:direct,llm` and the training prompt; they differ in the adapter and in `SEARCH_LIMIT`. Adapters are trained in `Finetuning/` on `candidate_gen_*.json`. Run by `Job/job_finetuning_retrieval.sh` and `Job/job_finetuning_retrieval_limit.sh`.

| Config | ADAPTER_PATH | SEARCH_LIMIT | OUTPUT_FOLDER |
|---|---|---|---|
| `config_basic.txt` | — (base model) | 20 | `candidate_basic` |
| `config_lora.txt` | `lora-fp16-adapter` | 10 | `candidate_lora_fp16` |
| `config_lora_32.txt` | `lora-fp16-adapter-32` | 10 | `candidate_lora_fp16_32` |
| `config_lora_32_30.txt` | `lora-fp16-adapter-32` | 30 | `candidate_lora_fp16_32_30` |
| `config_lora_32_50.txt` | `lora-fp16-adapter-32` | 50 | `candidate_lora_fp16_32_50` |
| `config_lora_all.txt` | `lora-fp16-adapter-all` | 20 | `candidate_lora_fp16_all` |
| `config_qlora.txt` | `qlora-adapter` (`LOAD_IN_4BIT:true`) | 10 | `candidate_qlora_4bit` |

Two questions are answered here at once: does finetuning help (adapter vs. `config_basic.txt`), and does 4-bit QLoRA cost accuracy relative to fp16 LoRA (`config_qlora.txt` vs. `config_lora.txt`) — the memory-constrained comparison.

**`candidate_lora_fp16`, produced by `config_lora.txt`, is the retrieval output used by the ranking baseline and by the full run.** The `lora-fp16-adapter-32` adapter is applied to the Training split by `../config_other_dataset/config_lora_training.txt`, which is what the ranking `other_dataset` group reads.

`config_lora_all.txt` is not in any job list — it was run on its own.
