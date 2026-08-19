# Evaluator

Evaluation of every pipeline stage against the WikidataTables2024R1 ground truth. Notebooks are run from this folder — all their paths are relative to it.

## Notebooks

- `Evaluate_preprocessing.ipynb` : preprocessing-stage evaluation: how much each correction model actually changes the cells (Levenshtein-based edit statistics), and whether those edits move the value towards or away from the gold entity label. This is the notebook that shows the no-LLM variant is the safest input for retrieval.
- `Evaluate_candidate.ipynb` : retrieval-stage evaluation: builds a CEA submission from each candidate folder (top candidate per cell) and measures the coverage/recall of the gold entity in the candidate lists, per retrieval experiment group.
- `Evaluate_ranking.ipynb` : ranking-stage evaluation: CEA/CTA/CPA precision, recall and F1 per experiment group, plus per-error breakdowns (CTA scored with the ancestor/descendant hierarchy, exact vs. ancestor vs. miss).

## Data and scorers

- `Evaluate_semtab/` : the official SemTab 2024 scorers (`CEA/CTA/CPA_WD_Evaluator.py`), used as the reference implementation of the metrics. See its README.
- `Testing_data/` : ground truth, hierarchy files and the collected outputs of every experiment campaign. See its README.

The notebooks embed their own copies of the evaluator classes so they can score many runs in a loop; those copies follow the official scorers in `Evaluate_semtab/`, which stay as the authoritative version.
