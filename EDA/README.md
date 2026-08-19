# EDA

Exploratory data analysis of the WikidataTables2024R1 dataset (Valid and Test splits), used to motivate design choices in the thesis: batch sizes, context limits, and the amount of noise the preprocessing stage has to absorb.

## Main files

- `eda.ipynb` : computes and plots the dataset statistics: rows and columns per table, NaN ratio per table, annotated entities per column, words per cell, and the most frequent tokens.
- `output/` : the generated figures and CSVs, reused as-is in the thesis text.

## What is in `output/`

Each statistic is produced for both splits, so Valid can be checked against Test before generalising from it:

- `histogram_rows_per_table_{valid,test}.png`, `columns_per_table_*.png` : table size distributions; these set the `LLM_CONTEXT_MAX_ROWS` and batching choices.
- `histogram_nan_ratio_per_table_{valid,test}.png` : missing-value ratio, i.e. how much of a table is actually usable as context.
- `histogram_entities_per_column_distribution_*.png` and `boxplot_entities_per_column_boxplot_*.png` : how many cells per column carry a CEA target, which is what makes column-level voting viable for CTA.
- `words_per_cell_{valid,test}.png` : cell verbosity, the main input to the search-query design of the retrieval stage.
- `most_frequent_tokens_{valid,test}.csv`, `top20_tokens.png`, `top20_tokens_compare.png` : token frequencies and the Valid/Test comparison.
