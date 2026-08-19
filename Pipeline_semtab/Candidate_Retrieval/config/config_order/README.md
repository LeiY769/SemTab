# config_order

**Generator ablation: fuzzy instead of the LLM.** The LLM generator is switched off (`USE_LLM:false`) and replaced by the deterministic `FuzzyGenerator` (`GENERATOR_ORDER:direct,fuzzy`, `USE_FUZZY:true`), so retrieval runs with no GPU at all.

Fuzzy variants are pure string rewrites of the cell value (`generators.py:generate_fuzzy_variants`): quotes and `*` stripped, parenthesised parts removed and also searched on their own, leading article dropped, `"Last, First"` reordered, splits on `-` / `–` / `/`, and the first-word and first-two-word prefixes. Each variant is searched separately, on top of the direct search.

| Config | Split | OUTPUT_FOLDER |
|---|---|---|
| `config_fuzzy_direct_valid.txt` | Valid | `Valid/candidate_fuzzy_direct` |
| `config_fuzzy_direct_training.txt` | Training | `Training/candidate_fuzzy_direct` |

Run by `Job/job_order_retrieval.sh`. `SEARCH_LIMIT:10` and `preprocessing_nollm` in both, so the comparison against `../config_size/config_qwen25_3b.txt` isolates exactly what the LLM buys over cheap string variants. Results in `Evaluator/Testing_data/Candidate/Retrieval_fuzzy/`.
