import time
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
def search_entities(query, language="en", limit=20):
    if not query:
        return []
    data = api_get({"action": "wbsearchentities","search": query, "language": language,"limit": limit,"format": "json"})
    if not data:
        return []
    return [(e.get("label", ""), e.get("id", "")) for e in data.get("search", [])]
def fulltext_search(query, language="en", limit=20):
    if not query:
        return []
    data = api_get({"action": "query", "list": "search","srsearch": query,"srlimit": limit,"format": "json"})
    if not data:
        return []
    qids = [r["title"] for r in data.get("query", {}).get("search", [])
            if str(r.get("title", "")).startswith("Q")]
    labels = get_labels(qids, language)
    return [(labels.get(q, q), q) for q in qids]
def get_entity_data(qids, language="en"):
    out = {}
    qids = [q for q in dict.fromkeys(qids) if q]
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        data = api_get({"action": "wbgetentities", "ids": "|".join(chunk),  "props": "descriptions|aliases|claims|sitelinks", "languages": language,   "sitefilter": f"{language}wiki",  "format": "json"})
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

            out[qid] = {"description": entity.get("descriptions", {}).get(language, {}).get("value", ""),"aliases": [a["value"] for a in entity.get("aliases", {}).get(language, [])],"P31": entity_ids("P31"),"P279": entity_ids("P279"), "sitelink": entity.get("sitelinks", {}).get(f"{language}wiki", {}).get("title", "")}
    return out
def parse_datavalue(dv):
    if not dv:
        return None
    t = dv.get("type")
    v = dv.get("value")
    if t == "wikibase-entityid":
        return ["entity", v.get("id")]
    if t == "quantity":
        try:
            return ["quantity", float(v.get("amount"))]
        except (TypeError, ValueError):
            return None
    if t == "time":
        return ["time", v.get("time")]
    if t == "string":
        return ["string", v]
    if t == "monolingualtext":
        return ["string", v.get("text")]
    if t == "globecoordinate":
        return ["coord", [v.get("latitude"), v.get("longitude")]]
    return None
def get_entity_claims(qids):
    out = {}
    qids = [q for q in dict.fromkeys(qids) if q]
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        data = api_get({"action": "wbgetentities", "ids": "|".join(chunk),
                     "props": "claims", "format": "json"})
        if not data:
            continue
        for qid, entity in data.get("entities", {}).items():
            props = {}
            for pid, claims in entity.get("claims", {}).items():
                vals = []
                for claim in claims:
                    parsed = parse_datavalue(claim.get("mainsnak", {}).get("datavalue"))
                    if parsed:
                        vals.append(parsed)
                if vals:
                    props[pid] = vals
            out[qid] = props
    return out
def get_labels(qids, language="en"):
    out = {}
    qids = [q for q in qids if q]
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        data = api_get({ "action": "wbgetentities", "ids": "|".join(chunk),  "props": "labels",  "languages": f"{language}|en",  "format": "json"})
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

def describe_cta(result, language="en"):
    all_qids = []
    for _, p31, p279 in result:
        all_qids += list(p31) + list(p279)
    info = get_entities(all_qids, language=language)

    def expand(d):
        return [{"qid": q,"pct": pct,"label": info.get(q, {}).get("label", q),"description": info.get(q, {}).get("description", "")}for q, pct in d.items()]

    return [{"column": col_id, "P31": expand(p31), "P279": expand(p279)}for col_id, p31, p279 in result]