import shutil
from pathlib import Path

import pandas as pd

SRC = Path("WikidataTables2024R1/DataSets/Valid")
DST = Path("WikidataTables2024R1/DataSets/Valid_smoke")
N_TABLES = 5

def main():
    cea = pd.read_csv(SRC / "targets" / "cea_targets.csv", header=None)
    cta = pd.read_csv(SRC / "targets" / "cta_targets.csv", header=None)
    cpa = pd.read_csv(SRC / "targets" / "cpa_targets.csv", header=None)

    cea_counts = cea[0].value_counts()
    with_all_tasks = set(cea[0]) & set(cta[0]) & set(cpa[0])

    available = {p.stem for p in (SRC / "tables").glob("*.csv")}
    ranked = sorted(cea_counts.index, key=lambda t: (cea_counts[t], t))
    picked = [t for t in ranked if t in with_all_tasks and t in available][:N_TABLES]
    if len(picked) < N_TABLES:
        picked += [t for t in ranked if t in available and t not in picked][:N_TABLES - len(picked)]

    (DST / "tables").mkdir(parents=True, exist_ok=True)
    (DST / "targets").mkdir(parents=True, exist_ok=True)
    for t in picked:
        shutil.copy(SRC / "tables" / f"{t}.csv", DST / "tables" / f"{t}.csv")

    selected = set(picked)
    for name, df in (("cea_targets.csv", cea), ("cta_targets.csv", cta), ("cpa_targets.csv", cpa)):
        df[df[0].isin(selected)].to_csv(DST / "targets" / name, header=False, index=False)

    print(f"Smoke subset: {len(picked)} tables -> {DST}")
    for t in picked:
        print(f"  {t} ({cea_counts[t]} CEA targets)")

if __name__ == "__main__":
    main()
