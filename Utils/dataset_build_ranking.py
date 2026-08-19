import os
import re
import ast
import csv
import sys
import json
import time
import string
import random
from collections import Counter, defaultdict
import pandas as pd
import requests


API_URL = "https://www.wikidata.org/w/api.php"
USER_AGENT = "SemTabThesisBot/1.0 (https://github.com/LeiY769; contact: leiyang677@gmail.com)"
_SLEEP = 0.1
_ERROR_PAUSE = 10.0
_MAX_BACKOFF = 120.0
#Some constants for maxlag handling because the API can be slow to catch up after a lag event
_LAG_MAX_WAIT = 1800.0
_LAG_GRACE = 60.0
_MAXLAG_OFF_WINDOW = 7200.0
_maxlag_off_until = 0.0

def set_rate_limit(seconds):
    global _SLEEP
    _SLEEP = max(0.0, float(seconds))

def retry_wait(r, attempt):
    try:
        retry_after = float(r.headers.get("Retry-After", 0))
    except (TypeError, ValueError):
        retry_after = 0.0
    return max(retry_after, min(max(_ERROR_PAUSE, 2 ** attempt), _MAX_BACKOFF))

def api_get(params, max_retries=8):
    global _maxlag_off_until
    headers = {"User-Agent": USER_AGENT}
    last_error = None
    attempt = 0
    lag_waited = 0.0
    while attempt < max_retries:
        use_maxlag = time.monotonic() >= _maxlag_off_until
        try:
            req_params = {**params, "maxlag": 7} if use_maxlag else params
            r = requests.get(API_URL, params=req_params, headers=headers, timeout=30)
        except requests.RequestException as e:
            last_error = repr(e)
            attempt += 1
            time.sleep(min(max(_ERROR_PAUSE, 2 ** attempt), _MAX_BACKOFF))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            last_error = f"HTTP {r.status_code}"
            attempt += 1
            time.sleep(retry_wait(r, attempt))
            continue
        if r.status_code == 200:
            data = r.json()
            error = data.get("error")
            if error:
                code = error.get("code", "")
                if code in ("maxlag", "readonly") or code.startswith("cirrussearch"):
                    last_error = f"API error '{code}': {error.get('info', '')}"
                    wait = retry_wait(r, 0)
                    if code == "maxlag" and lag_waited + wait > _LAG_GRACE:
                        print(f"Wikidata still lagged after {lag_waited:.0f}s, retrying without maxlag (read-only requests)")
                        _maxlag_off_until = time.monotonic() + _MAXLAG_OFF_WINDOW
                        lag_waited += wait
                        time.sleep(wait)
                        continue
                    if lag_waited + wait > _LAG_MAX_WAIT:
                        raise RuntimeError(f"Wikidata still lagged after waiting {lag_waited:.0f}s, last error: {last_error}")
                    if lag_waited == 0.0:
                        print(f"Wikidata lagged, waiting for it to catch up ({error.get('info', '')})")
                    lag_waited += wait
                    time.sleep(wait)
                    continue
                if code == "ratelimited" or code.startswith("internal_api_error"):
                    last_error = f"API error '{code}': {error.get('info', '')}"
                    attempt += 1
                    time.sleep(retry_wait(r, attempt))
                    continue
                print(f"Wikidata API error '{code}': {error.get('info', '')}")
                return None
            if _SLEEP:
                time.sleep(_SLEEP)
            return data
        return None
    raise RuntimeError(f"Wikidata API failed after {max_retries} retries, last error: {last_error}")

def get_entity_data(qids, language="en"):
    out = {}
    qids = [q for q in dict.fromkeys(qids) if q]
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        data = api_get({"action": "wbgetentities", "ids": "|".join(chunk), "props": "descriptions|aliases|claims|sitelinks", "languages": language, "sitefilter": f"{language}wiki", "format": "json"})
        if not data:
            continue
        for qid, entity in data.get("entities", {}).items():
            claims = entity.get("claims", {})
            def entity_ids(pid):
                ids = []
                for claim in claims.get(pid, []):
                    datavalue = claim.get("mainsnak", {}).get("datavalue")
                    if datavalue and datavalue.get("type") == "wikibase-entityid":
                        ids.append(datavalue["value"].get("id", ""))
                return [x for x in ids if x]

            out[qid] = {"description": entity.get("descriptions", {}).get(language, {}).get("value", ""), "aliases": [a["value"] for a in entity.get("aliases", {}).get(language, [])], "P31": entity_ids("P31"), "P279": entity_ids("P279"), "sitelink": entity.get("sitelinks", {}).get(f"{language}wiki", {}).get("title", "")}
    return out

def get_labels(qids, language="en"):
    out = {}
    qids = [q for q in qids if q]
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        data = api_get({"action": "wbgetentities", "ids": "|".join(chunk), "props": "labels", "languages": f"{language}|en", "format": "json"})
        if not data:
            continue
        for qid, entity in data.get("entities", {}).items():
            labels = entity.get("labels", {})
            lab = labels.get(language) or labels.get("en")
            out[qid] = lab["value"] if lab else qid
    return out

def get_entities(qids, language="en"):
    #Entity data plus label, fetched in batches for the whole qid list.
    qids = [q for q in dict.fromkeys(qids) if q]
    if not qids:
        return {}
    data = get_entity_data(qids, language=language)
    labels = get_labels(qids, language=language)
    out = {}
    for q in qids:
        entry = data.get(q, {})
        entry["label"] = labels.get(q, q)
        out[q] = entry
    return out
def parse_metadata(preprocess_df):
    s = str(preprocess_df.columns[-1]).strip()
    m = re.match(r"Metadata:CTA:(\[.*?\]),CPA:(\[.*\])$", s)
    if not m:
        raise ValueError(f"Invalid metadata format: {s}")
    cta = ast.literal_eval(m.group(1))
    cpa = ast.literal_eval(m.group(2))
    return cta, cpa
def load_preprocess(path):
    df = pd.read_csv(path)
    cta_cols, cpa_pairs = parse_metadata(df)
    data = df.iloc[:, :-1].reset_index(drop=True)
    return data, cta_cols, cpa_pairs

def split_pipe(val):
    if val is None or val == "":
        return []
    if isinstance(val, float) and pd.isna(val):
        return []
    return [x for x in str(val).split("|") if x]
def load_candidates(path):
    df = pd.read_csv(path)
    df["row"] = df["row"].astype(int)
    df["columns"] = df["columns"].astype(int)
    return df
def cand_dict(row):
    return {
        "qid": row["QID"] if pd.notna(row["QID"]) else None,
        "label": str(row["candidates"]) if pd.notna(row["candidates"]) else "",
        "mention": str(row["data"]) if pd.notna(row["data"]) else "",
        "quality": int(row["quality"]) if pd.notna(row["quality"]) else 99,
        "description": str(row["description"]) if pd.notna(row["description"]) else "",
        "aliases": str(row["aliases"]) if pd.notna(row["aliases"]) else "",
        "P31": split_pipe(row.get("P31")),
        "P279": split_pipe(row.get("P279")),
    }
def group_by_cell(cand_df):
    cells = {}
    for (r, c), g in cand_df.groupby(["row", "columns"]):
        cells[(int(r), int(c))] = [cand_dict(row) for _, row in g.iterrows()]
    return cells
def tab_id_from_filename(filename):
    return os.path.basename(filename).replace("_candidates", "").replace(".csv", "")
class Scoring_method:
    def levenshtein_distance(self, s1, s2):
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]
    def levenshtein_similarity(self, s1, s2):
        s1, s2 = str(s1).lower(), str(s2).lower()
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 0.0
        return (max_len - self.levenshtein_distance(s1, s2)) / max_len
    def token_jaccard(self, s1, s2):
        ta = set(str(s1).lower().split())
        tb = set(str(s2).lower().split())
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta | tb)
    def type_coherence(self, candidate_types, type_pct):
        if not candidate_types or not type_pct:
            return 0.0
        return max((type_pct.get(t, 0.0) for t in candidate_types), default=0.0)
    def quality_score(self, quality):
        try:
            q = int(quality)
        except (TypeError, ValueError):
            return 0.0
        return 1.0 / q if q > 0 else 0.0
    def best_string_sim(self, mention, label, aliases=None):
        best = max(self.levenshtein_similarity(mention, label), self.token_jaccard(mention, label))
        for a in aliases or []:
            if a:
                best = max(best, self.levenshtein_similarity(mention, a))
        return best
    def context_overlap(self, cand_text, context_terms):
        if not context_terms:
            return 0.0
        cand_tokens = set(str(cand_text).lower().split())
        if not cand_tokens:
            return 0.0
        hits = sum(1 for t in context_terms if t in cand_tokens)
        return hits / len(context_terms)

scorer = Scoring_method()
def cta_from_cea(cea_df):
    results = []
    for col_id, col_df in cea_df.groupby("columns"):
        cells = col_df.groupby(["row", "columns"])
        n_cells = cells.ngroups
        if n_cells == 0:
            continue

        p31_support = defaultdict(set)
        p279_support = defaultdict(set)

        for cell_key, c_df in cells:
            for prop, support in (("P31", p31_support), ("P279", p279_support)):
                types_cell = set()
                for cell in c_df[prop].dropna():
                    types_cell.update(str(cell).split("|"))
                for qid in types_cell:
                    support[qid].add(cell_key)

        p31_pct = {q: len(s) / n_cells for q, s in p31_support.items()}
        p279_pct = {q: len(s) / n_cells for q, s in p279_support.items()}

        p31_pct = dict(sorted(p31_pct.items(), key=lambda x: x[1], reverse=True))
        p279_pct = dict(sorted(p279_pct.items(), key=lambda x: x[1], reverse=True))

        results.append((col_id, p31_pct, p279_pct))
    return results
DEFAULT_WEIGHTS = (0.5, 0.2, 0.3)

def build_type_pct(cta_result):
    out = {}
    for col_id, p31, p279 in cta_result:
        merged = dict(p31)
        for q, pct in p279.items():
            merged[q] = max(merged.get(q, 0.0), 0.5 * pct)
        out[col_id] = merged
    return out

def score_candidate(cand, type_pct, weights=DEFAULT_WEIGHTS):
    a, b, c = weights
    aliases = cand["aliases"].split("|") if cand["aliases"] else None
    sim = scorer.best_string_sim(cand["mention"], cand["label"], aliases)
    q = scorer.quality_score(cand["quality"])
    tc = scorer.type_coherence(cand["P31"] + cand["P279"], type_pct)
    return a * sim + b * q + c * tc

def rank_cell(cands, type_pct, weights=DEFAULT_WEIGHTS):
    scored = [(score_candidate(c, type_pct, weights), c) for c in cands if c["qid"]]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored

def cand_text(cand):
    return " ".join([cand.get("label", ""), cand.get("description", ""), str(cand.get("aliases", "")).replace("|", " ")])

def context_tiebreak(scored, row_terms, context_margin):
    top = scored[0][0]
    near = [(s, c) for s, c in scored if top - s < context_margin]
    if len(near) <= 1:
        return None
    ov_top = scorer.context_overlap(cand_text(scored[0][1]), row_terms)
    best_s, best_c = max(near, key=lambda sc:(scorer.context_overlap(cand_text(sc[1]), row_terms), sc[0]))
    if best_c["qid"] != scored[0][1]["qid"]:
        if scorer.context_overlap(cand_text(best_c), row_terms) > ov_top:
            return best_c["qid"]
    return None

DEFAULT_PROMPTS = {
    "CEA_PROMPT": (
        "Cell value: ${mention}\n${row_block}\n"
        "Candidate entities:\n${candidates}\n\n"
        "Return only the QID of the entity that best matches the cell "
        "value in this context."
    ),
    "CONTEXT_PROMPT": (
        "You are disambiguating one cell of a table against Wikidata.\n\n"
        "${table_block}Target cell (${location}) value: ${mention}\n"
        "${coltype_block}\n"
        "Candidate entities:\n${candidates}\n\n${instruction}"
    ),
    "CONTEXT_INSTRUCTION_ENRICH": (
        "The other columns of the marked row (>>...<<) describe the "
        "SAME entity (e.g. a place, date, category or related value). "
        "Compare those cells against each candidate's description, "
        "aliases and type, and pick the candidate they fit. Return "
        "ONLY the QID of the best match."
    ),
    "CONTEXT_INSTRUCTION_PLAIN": (
        "Using the whole table as context (the other columns and rows "
        "describe the same kind of thing), return only the QID of the "
        "entity that best matches the target cell."
    )
}
def render(template, values):
    return string.Template(template).safe_substitute(values)
def opt_line(label, value):
    return f"{label}{value}\n" if value else ""
def entity_lines(candidates):
    return "\n".join(f"- {c['qid']}: {c['label']} ({c.get('description', '')})" for c in candidates)
def candidate_line(c, type_labels=None, enrich=False):
    line = f"{c['qid']}: {c['label']} ({c.get('description', '')})"
    if not enrich:
        return line
    aliases = [a for a in str(c.get("aliases", "") or "").split("|") if a][:5]
    if aliases:
        line += f" [also known as: {', '.join(aliases)}]"
    if type_labels:
        types, seen = [], set()
        for q in (c.get("P31") or []) + (c.get("P279") or []):
            lab = type_labels.get(q)
            if lab and lab not in seen:
                seen.add(lab)
                types.append(lab)
        if types:
            line += f" [type: {', '.join(types[:4])}]"
    return line
def use_llm(gate, scored, margin):
    if len(scored) <= 1:
        return False
    if gate == "all":
        return True
    return scored[0][0] - scored[1][0] < margin
def get_type_labels(ctx, shortlist):
    qids = []
    for c in shortlist:
        qids += (c.get("P31") or []) + (c.get("P279") or [])
    if not qids:
        return {}
    try:
        info = get_entities(qids, ctx.language)
    except Exception:
        return {}
    return {q: v.get("label", "") for q, v in info.items()}
class TableContext:

    def __init__(self, input_path, preprocess_path, language="en"):
        self.tab_id = tab_id_from_filename(input_path)
        self.cand_df = load_candidates(input_path)
        self.data_df, self.cta_cols, self.cpa_pairs = load_preprocess(preprocess_path)
        self.n_rows = self.data_df.shape[0]

        self.cells = group_by_cell(self.cand_df)
        self.cta_result = cta_from_cea(self.cand_df)
        self.cta_by_col = {c: (c, p31, p279) for c, p31, p279 in self.cta_result}
        self.type_pct = build_type_pct(self.cta_result)
        self.language = language
        self._type_label = {}
    def col_header(self, col):
        try:
            return str(self.data_df.columns[col])
        except Exception:
            return ""
    def row_context(self, row):
        try:
            return " | ".join(str(x) for x in self.data_df.iloc[row].tolist())
        except Exception:
            return ""
    def row_terms(self, row, exclude_col=None, min_len=3):
        terms = set()
        try:
            vals = self.data_df.iloc[row].tolist()
        except Exception:
            return terms
        for ci, v in enumerate(vals):
            if ci == exclude_col:
                continue
            for tok in re.findall(r"[a-z0-9]+", str(v).lower()):
                if len(tok) >= min_len:
                    terms.add(tok)
        return terms
    def column_type_label(self, col):
        if col in self._type_label:
            return self._type_label[col]
        label = ""
        res = self.cta_by_col.get(col)
        if res:
            _, p31, p279 = res
            ranked = list((p31 or p279).items())
            if ranked:
                top = ranked[0][0]
                info = get_entities([top], self.language)
                label = info.get(top, {}).get("label", top)
        self._type_label[col] = label
        return label
    def table_text(self, target_row=None, target_col=None, max_rows=20):
        df = self.data_df
        ncols = df.shape[1]
        header = " | ".join(str(df.columns[c]) for c in range(ncols))
        rows = list(range(self.n_rows))
        if self.n_rows > max_rows and target_row is not None:
            half = max_rows // 2
            lo = max(0, target_row - half)
            rows = list(range(lo, min(self.n_rows, lo + max_rows)))
        lines = ["col_ids: " + " | ".join(str(c) for c in range(ncols)), header]
        for r in rows:
            cells = []
            for c in range(ncols):
                val = str(df.iat[r, c])
                if r == target_row and c == target_col:
                    val = f">>{val}<<"
                cells.append(val)
            lines.append(" | ".join(cells))
        return "\n".join(lines)
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
            config[key.strip()] = value.strip().replace("\\n", "\n")
    return config
def flag(cfg, key, default="True"):
    return cfg.get(key, default).lower() == "true"
def load_cea_gold(path, row_offset=1):
    gold = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        for parts in csv.reader(f):
            if len(parts) < 4:
                continue
            tab, row, col, url = parts[0], parts[1], parts[2], parts[3]
            try:
                row, col = int(row), int(col)
            except ValueError:
                continue
            qid = str(url).strip().rstrip("/").split("/")[-1]
            if qid.startswith("Q"):
                gold[(tab, row - row_offset, col)] = qid
    return gold

def gold_rank(scored, gold):
    for i, (_, c) in enumerate(scored):
        if c["qid"] == gold:
            return i + 1
    return 0
def build_limited_slm_example(ctx, r, c, scored, gold, prompts, cfg):
    margin = float(cfg.get("CEA_TIEBREAK_MARGIN", "0.05"))
    ctx_tiebreak = flag(cfg, "CEA_CONTEXT_TIEBREAK", "False")
    ctx_margin = float(cfg.get("CEA_CONTEXT_MARGIN", "0.10")) if ctx_tiebreak else 0.0
    if len(scored) <= 1:
        return None, "not_ambiguous"
    if ctx_margin > 0:
        if context_tiebreak(scored, ctx.row_terms(r, exclude_col=c), ctx_margin):
            return None, "resolved_by_tiebreak"
    if scored[0][0] - scored[1][0] >= margin:
        return None, "not_gated"
    top = [cc for _, cc in scored[:5]]
    if gold not in {t["qid"] for t in top}:
        return None, "gold_absent"
    if len({t["qid"] for t in top}) < 2:
        return None, "trivial"
    mention = top[0]["mention"]
    col_header = ctx.col_header(c)
    row_context = ctx.row_context(r)
    values = {"mention": mention, "col_header": col_header, "row_context": row_context,
              "header_block": opt_line("Column header: ", col_header),
              "row_block": opt_line("Row context: ", row_context),
              "candidates": entity_lines(top)}
    user = render(prompts["CEA_PROMPT"], values)
    return {"user": user, "n_candidates": len(top),
            "gold_rank": gold_rank(scored, gold),
            "margin": round(scored[0][0] - scored[1][0], 4)}, "kept"
def build_context_example(ctx, r, c, scored, gold, prompts, cfg):
    gate = cfg.get("LLM_GATE", "uncertain").lower()
    margin = float(cfg.get("LLM_CONTEXT_MARGIN", "0.10"))
    topk = int(cfg.get("LLM_TOPK", "10"))
    max_rows = int(cfg.get("LLM_CONTEXT_MAX_ROWS", "20"))
    enrich = flag(cfg, "LLM_ENRICH", "False")
    ctx_tiebreak = flag(cfg, "CEA_CONTEXT_TIEBREAK", "False")
    ctx_margin = float(cfg.get("CEA_CONTEXT_MARGIN", "0.10")) if ctx_tiebreak else 0.0
    if not scored:
        return None, "no_candidates"
    if ctx_margin > 0 and len(scored) > 1:
        if context_tiebreak(scored, ctx.row_terms(r, exclude_col=c), ctx_margin):
            return None, "resolved_by_tiebreak"
    if not use_llm(gate, scored, margin):
        return None, "not_gated"
    shortlist = [cc for _, cc in scored[:topk]]
    if gold not in {s["qid"] for s in shortlist}:
        return None, "gold_absent"
    if len({s["qid"] for s in shortlist}) < 2:
        return None, "trivial"
    type_labels = get_type_labels(ctx, shortlist) if enrich else None
    instruction = prompts["CONTEXT_INSTRUCTION_ENRICH"] if enrich else prompts["CONTEXT_INSTRUCTION_PLAIN"]
    mention = shortlist[0]["mention"]
    table_txt = ctx.table_text(r, c, max_rows)
    col_header = ctx.col_header(c)
    col_type = ctx.column_type_label(c)
    values = {"mention": mention, "table_text": table_txt,"table_block": f"Table:\n{table_txt}\n\n" if table_txt else "","location": f"row {r}, column {c}","col_header": col_header,"header_block": opt_line("Column header: ", col_header),"col_type": col_type,"coltype_block": opt_line("Likely column type: ", col_type),"candidates": "\n".join("- " + candidate_line(cc, type_labels, enrich) for cc in shortlist), "instruction": instruction}
    user = render(prompts["CONTEXT_PROMPT"], values)
    return {"user": user, "n_candidates": len(shortlist),
            "gold_rank": gold_rank(scored, gold),
            "margin": round(scored[0][0] - scored[1][0], 4) if len(scored) > 1 else 1.0}, "kept"

BUILDERS = {"slm_limited": build_limited_slm_example, "slm_context": build_context_example}

def build_datasets(config_path):
    cfg = load_config(config_path)
    input_folder = cfg["INPUT_FOLDER"]
    preprocess_folder = cfg["PREPROCESS_FOLDER"]
    gt_file = cfg["GT_FILE"]
    methods = [m.strip().lower() for m in cfg.get("FT_METHOD", "limited_slm,slm_context").split(",") if m.strip()]
    for m in methods:
        if m not in BUILDERS:
            raise ValueError(f"Unknown FT_METHOD: {m}")
    out_folder = cfg.get("OUT_FOLDER", "finetune_datasets")
    os.makedirs(out_folder, exist_ok=True)
    row_offset = int(cfg.get("ROW_OFFSET", "1"))
    val_ratio = float(cfg.get("VAL_RATIO", "0.1"))
    seed = int(cfg.get("SEED", "42"))
    system_prompt = cfg.get("SYSTEM_PROMPT", "")
    prompts = {k: cfg.get(k, v) for k, v in DEFAULT_PROMPTS.items()}
    language = cfg.get("LANGUAGE", "en")

    gold = load_cea_gold(gt_file, row_offset)
    print(f"Read {len(gold)} CEA gold cells from {gt_file}")

    examples = {m: [] for m in methods}
    stats = {m: Counter() for m in methods}

    files = sorted(f for f in os.listdir(input_folder) if f.endswith(".csv"))
    for i, filename in enumerate(files, 1):
        input_path = os.path.join(input_folder, filename)
        preprocess_path = os.path.join(preprocess_folder, filename.replace("_candidates", ""))
        if not os.path.exists(preprocess_path):
            print(f"Preprocess file missing for {filename}, skipping.")
            continue
        ctx = TableContext(input_path, preprocess_path, language)
        for (r, c), cands in ctx.cells.items():
            g = gold.get((ctx.tab_id, r, c))
            if not g:
                for m in methods:
                    stats[m]["no_gold"] += 1
                continue
            scored = rank_cell(cands, ctx.type_pct.get(c, {}))
            for m in methods:
                ex, status = BUILDERS[m](ctx, r, c, scored, g, prompts, cfg)
                stats[m][status] += 1
                if ex:
                    ex.update({"system": system_prompt, "completion": g, "gold_qid": g,"table": ctx.tab_id, "row": r, "col": c, "method": m})
                    examples[m].append(ex)
        if i % 50 == 0:
            kept = ", ".join(f"{m}: {len(examples[m])}" for m in methods)
            print(f"  {i}/{len(files)} tables ({kept})", flush=True)

    rng = random.Random(seed)
    for m in methods:
        exs = examples[m]
        print(f"\n[{m}] stats: {dict(stats[m])}")
        if not exs:
            print(f"[{m}] no examples, nothing written")
            continue
        hard = sum(1 for e in exs if e["gold_rank"] != 1)
        print(f"[{m}] {len(exs)} examples, gold not rank-1: {hard} ({hard / len(exs):.0%})")
        tables = sorted({e["table"] for e in exs})
        rng.shuffle(tables)
        n_val = max(1, int(len(tables) * val_ratio)) if val_ratio > 0 and len(tables) > 1 else 0
        val_tables = set(tables[:n_val])
        train = [e for e in exs if e["table"] not in val_tables]
        val = [e for e in exs if e["table"] in val_tables]
        train_path = os.path.join(out_folder, f"ft_{m}_train.json")
        with open(train_path, "w", encoding="utf-8") as f:
            json.dump(train, f, ensure_ascii=False, indent=2)
        print(f"[{m}] wrote {len(train)} train examples ({len(tables) - n_val} tables) -> {train_path}")
        if val:
            val_path = os.path.join(out_folder, f"ft_{m}_valid.json")
            with open(val_path, "w", encoding="utf-8") as f:
                json.dump(val, f, ensure_ascii=False, indent=2)
            print(f"[{m}] wrote {len(val)} valid examples ({n_val} tables) -> {val_path}")
    return examples

if __name__ == "__main__":
    build_datasets(sys.argv[1] if len(sys.argv) > 1 else "config_finetune.txt")
