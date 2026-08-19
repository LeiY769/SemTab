# config_limit

**`SEARCH_LIMIT` sweep** — how many results the Wikidata API is asked for per search query. More results mean better gold-entity coverage but a longer candidate list for the ranking stage to sift through, so this fixes the recall/cost trade-off point.

Model fixed to GLM-4 9B on `preprocessing_nollm`, `GENERATOR_ORDER:direct,llm`. Run by `Job/job_limit_retrieval.sh`, a job array.

| Config | SEARCH_LIMIT | OUTPUT_FOLDER |
|---|---|---|
| `config_glm_9b_5.txt` | 5 | `candidate_glm_9b_5_a` |
| `config_glm_9b_20.txt` | 20 | `candidate_glm_9b_20_a` |
| `config_glm_9b_30.txt` | 30 | `candidate_glm_9b_30_a` |
| `config_glm_9b_50.txt` | 50 | `candidate_glm_9b_50_a` |

The default of 10 is not repeated here: it is `../config_size/config_glm_9b.txt` (`candidate_size_glm_9b_10`). `MAX_CANDIDATES_PER_CELL:0` everywhere, so nothing is truncated after deduplication and the limit is the only thing controlling list length.

The downstream effect of this sweep is measured again at the ranking stage in `Ranking/config/inputs/` (`config_glm_9b_5.txt`, `config_glm_9b_30.txt`).
