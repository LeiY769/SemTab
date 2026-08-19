# Evaluate_semtab

The **official evaluators of the SemTab 2024 challenge**, copied here unmodified. They define the metrics reported in the thesis and are the reference the notebook copies in `../` follow.

- `CEA_WD_Evaluator.py` — cell-entity annotation: exact QID match against `cea_gt.csv`, precision / recall / F1 over the annotated target cells.
- `CTA_WD_Evaluator.py` — column-type annotation: hierarchy-aware scoring. An answer that is an ancestor or a descendant of the gold type still scores, discounted by its distance in the hierarchy; it needs `cta_gt_ancestor.json` and `cta_gt_descendent.json` in addition to `cta_gt.csv`. Note that this file loads them from a hard-coded challenge path (`./DataSets/HardTablesR2/Valid/gt/`) — that is why `../Evaluate_ranking.ipynb` reimplements the same scoring with an explicit `load_hierarchy(...)` pointing at `Testing_data/`.
- `CPA_WD_Evaluator.py` — column-property annotation: exact PID match against `cpa_gt.csv`.

All three take a submission CSV in the SemTab format (`table,row,col,URI` for CEA, `table,col,URI` for CTA, `table,col1,col2,URI` for CPA) — exactly what `Pipeline_semtab/Ranking/output_writer.py` writes.

The files are third-party code and should be left as-is; adapt the callers, not the scorers.
