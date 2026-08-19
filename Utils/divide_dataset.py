import csv
import random
import shutil
import sys
from pathlib import Path

def load_config(path):
    config = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                raise ValueError(f"Invalid config line: {line}")
            key, value = line.split(":", 1)
            config[key.strip()] = value.strip()
    return config

def count_cea(src):
    cea_counts = {}
    with open(src / "gt" / "cea_gt.csv", newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if row:
                cea_counts[row[0]] = cea_counts.get(row[0], 0) + 1
    return cea_counts

def sample_tables(src, cea_counts, n_small, small_max_cea, n_random):
    all_tables = sorted(p.name for p in (src / "tables").glob("*.csv"))
    print(f"Total tables: {len(all_tables)}")

    small_tables = [n for n in all_tables if cea_counts.get(Path(n).stem, 0) <= small_max_cea]
    print(f"Small tables (<= {small_max_cea} CEA rows): {len(small_tables)}")

    sample = random.sample(small_tables, n_small)
    rest = [n for n in all_tables if n not in set(sample)]
    sample += random.sample(rest, n_random)
    return sample

def filter_csv(src_file, dst_file, sample_ids):
    kept = 0
    with open(src_file, newline="", encoding="utf-8") as fin, \
         open(dst_file, "w", newline="", encoding="utf-8") as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)
        for row in reader:
            if row and row[0] in sample_ids:
                writer.writerow(row)
                kept += 1
    print(f"{dst_file.name}: {kept} rows")

def copy_subset(src, dst, sample, sample_ids):
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "tables").mkdir(parents=True, exist_ok=True)
    (dst / "gt").mkdir(exist_ok=True)
    (dst / "targets").mkdir(exist_ok=True)

    for name in sample:
        shutil.copy2(src / "tables" / name, dst / "tables" / name)
    print(f"Copied {len(sample)} tables")

    for f in ["cea_gt.csv", "cpa_gt.csv", "cta_gt.csv"]:
        filter_csv(src / "gt" / f, dst / "gt" / f, sample_ids)
    for f in ["cea_targets.csv", "cpa_targets.csv", "cta_targets.csv"]:
        filter_csv(src / "targets" / f, dst / "targets" / f, sample_ids)

    for f in ["cta_gt_ancestor.json", "cta_gt_descendent.json"]:
        shutil.copy2(src / "gt" / f, dst / "gt" / f)
        print(f"Copied {f}")

    with open(dst / "sampled_tables.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(sample_ids)) + "\n")

def main():
    if len(sys.argv) != 2:
        print("Usage: python divide_dataset.py <config.txt>")
        sys.exit(1)

    config = load_config(sys.argv[1])
    src = Path(config["INPUT_FOLDER"])
    dst = Path(config["OUTPUT_FOLDER"])
    n_small = int(config.get("N_SMALL", "250"))
    small_max_cea = int(config.get("SMALL_MAX_CEA", "50"))
    n_random = int(config.get("N_RANDOM", "250"))
    seed = int(config.get("SEED", "1"))

    random.seed(seed)

    cea_counts = count_cea(src)
    sample = sample_tables(src, cea_counts, n_small, small_max_cea, n_random)
    sample_ids = {Path(name).stem for name in sample}
    total_cea = sum(cea_counts.get(t, 0) for t in sample_ids)
    print(f"Sampled {len(sample)} tables ({n_small} small + {n_random} random) -> {total_cea} CEA rows")

    copy_subset(src, dst, sample, sample_ids)
    print(f"Done -> {dst}")


if __name__ == "__main__":
    main()
