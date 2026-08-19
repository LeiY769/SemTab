# cta_margin

Sweep of the two CTA tie-break parameters read in `choose_cta` (`cta.py`):

- `CTA_MARGIN` — the SLM is asked to pick the column type only if the support gap between the
  top two types is below this value. 0.00 means the SLM is never called on CTA, 1.00 means it
  is called on every column with more than one candidate type.
- `CTA_TOPK` — how many candidate types (with label + description from the Wikidata API) are
  shown to the SLM when the tie-break fires.

Method fixed to `slm_context` to keep the grid small; everything else is the baseline
(`Valid/candidate_lora_fp16`, Qwen2.5-3B, `CTA_FROM_SELECTION:True`, `LLM_CONTEXT_MARGIN:0.10`,
no CoT, no self-consistency). Run by `Job/job_ranking_cta_margin.sh`.

## Grid

One factor at a time around the default (`CTA_MARGIN:0.3`, `CTA_TOPK:5`):

| Config | `CTA_MARGIN` | `CTA_TOPK` |
|---|---|---|
| `config_m000.txt` | 0.00 | 5 |
| `config_m010.txt` | 0.10 | 5 |
| `config_m020.txt` | 0.20 | 5 |
| `config_m050.txt` | 0.50 | 5 |
| `config_m100.txt` | 1.00 | 5 |
| `config_k03.txt` | 0.30 | 3 |
| `config_k10.txt` | 0.30 | 10 |
| `config_k20.txt` | 0.30 | 20 |

The centre point (0.30 / 5) is the baseline `../methods/config_slm_context.txt`
(results in `results/methods/slm_context`) — not duplicated here.

`config_m000.txt` should reproduce the CTA of a `CTA_USE_SLM:False` run: with a margin of 0.00
the gap is never strictly below the threshold, so the top type is returned directly.
