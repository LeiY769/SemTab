# cta_cpa_noslm

Ablation of SLM involvement on the two column-level tasks: `CTA_USE_SLM:False` and
`CPA_USE_SLM:False`. CEA keeps the SLM (`CEA_USE_SLM:True`), so the method still differs
between `limited_slm`, `full_slm` and `slm_context` at the cell level, while CTA and CPA fall
back to the pure score/support ranking (top type, no LLM tie-break in `choose_cta`, no LLM
arbitration in `run_cpa`).

Everything else is the baseline: `Valid/candidate_lora_fp16` + `Valid/preprocessing_nollm`,
Qwen2.5-3B-Instruct, no adapter, margin 0.10, gate `uncertain`, no CoT, no self-consistency.

## Two sub-variants

| Sub-variant | `CTA_FROM_SELECTION` | Configs | OUTPUT_FOLDER |
|---|---|---|---|
| default | `True` | `config_*.txt` | `results/cta_cpa_noslm/` |
| nosel | `False` | `nosel/config_*.txt` | `results/cta_cpa_noslm_nosel/` |

`Job/job_ranking_cta_cpa_noslm_all.sh` runs all six configs sequentially in a single job — it is
the only job script kept for this group. The two sub-variants write to different output folders,
so splitting it into two parallel jobs is safe if the sequential run is too long.

## Comparison points

- vs. `methods/` (`results/methods/`) — isolates the contribution of the SLM on CTA/CPA.
- `nosel/` vs. default — the `CTA_FROM_SELECTION` gate with no SLM on CTA.
- `nosel/` vs. `cta_nosel/` — same gate setting, with vs. without the SLM on CTA/CPA.
