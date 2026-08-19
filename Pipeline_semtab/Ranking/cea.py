from scoring import Scoring_method

_score = Scoring_method()

# weights for (string similarity, Wikidata quality, type coherence)
DEFAULT_WEIGHTS = (0.5, 0.2, 0.3)
# Per-column {QID: score} merging P31 and half-weighted P279 coverage (max of the two)
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
    sim = _score.best_string_sim(cand["mention"], cand["label"], aliases)
    q = _score.quality_score(cand["quality"])
    tc = _score.type_coherence(cand["P31"] + cand["P279"], type_pct)
    return a * sim + b * q + c * tc
def rank_cell(cands, type_pct, weights=DEFAULT_WEIGHTS):
    scored = [(score_candidate(c, type_pct, weights), c) for c in cands if c["qid"]]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored
def cand_text(cand):
    return " ".join([cand.get("label", ""), cand.get("description", ""),str(cand.get("aliases", "")).replace("|", " ")])
def context_tiebreak(scored, row_terms, context_margin):
    top = scored[0][0]
    near = [(s, c) for s, c in scored if top - s < context_margin]
    if len(near) <= 1:
        return None
    ov_top = _score.context_overlap(cand_text(scored[0][1]), row_terms)
    _, best_c = max(near, key=lambda sc:(_score.context_overlap(cand_text(sc[1]), row_terms), sc[0]))
    if best_c["qid"] != scored[0][1]["qid"]:
        if _score.context_overlap(cand_text(best_c), row_terms) > ov_top:
            return best_c["qid"]
    return None
    #Value for context_margin is set higher than the LLM margin because of the cost to call the first 
def choose_cea(cands, type_pct, llm=None, use_slm=True, margin=0.05,row_context="", col_header="", weights=DEFAULT_WEIGHTS,row_terms=None, context_margin=0.1, llm_topk=5):
    scored = rank_cell(cands, type_pct, weights)
    if not scored:
        return None
    if len(scored) == 1:
        return scored[0][1]["qid"]
    if context_margin > 0 and row_terms:
        choice = context_tiebreak(scored, row_terms, context_margin)
        if choice:
            return choice
    if not (use_slm and llm):
        return scored[0][1]["qid"]
    if scored[0][0] - scored[1][0] < margin:
        top_cands = [c for _, c in scored[:llm_topk]]
        choice = llm.select_best_entity(top_cands[0]["mention"], top_cands, row_context, col_header)
        if choice:
            return choice
    return scored[0][1]["qid"]
