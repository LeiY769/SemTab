import re
from wikidata_api import search_entities

class BaseGenerator:
    name = "base"
    quality = 0

    def candidates(self, query, context_str):
        return None 

class DirectGenerator(BaseGenerator):
    name = "direct"
    quality = 1

    def __init__(self, language="en", limit=10):
        self.language = language
        self.limit = limit
    def candidates(self, query, context_str):
        return search_entities(query, self.language, self.limit)

class LLMGenerator(BaseGenerator):
    name = "llm"
    quality = 2
    def __init__(self, engine, system_prompt, language="en", limit=10,max_suggestions=8, max_new_tokens=64,sc_enabled=False, sc_samples=5, sc_temperature=0.7, sc_top_p=0.95):
        self.engine = engine
        self.system_prompt = system_prompt
        self.language = language
        self.limit = limit
        self.max_suggestions = max_suggestions
        self.max_new_tokens = max_new_tokens
        self.sc_enabled = sc_enabled
        self.sc_samples = sc_samples
        self.sc_temperature = sc_temperature
        self.sc_top_p = sc_top_p

    def parse_terms(self, raw):
        for marker in ("FINAL:", "Candidates:", "Answer:"):
            if marker in raw:
                raw = raw.split(marker)[-1]
                break
        raw = raw.replace("\n", " ")
        terms = []
        for term in raw.split(";"):
            term = re.sub(r"^\s*\d+[\.\)]\s*", "", term).strip()
            if term and term not in terms:
                terms.append(term)
        return terms

    def suggestions(self, query, context_str):
        user_msg = f"Cell value: {query}"
        if context_str:
            user_msg += f"\nContext: {context_str}"
        user_msg += "\nCandidates:"
        if not self.sc_enabled or self.sc_samples <= 1:
            raw = self.engine.generate([user_msg], self.system_prompt,max_new_tokens=self.max_new_tokens)[0]
            return self.parse_terms(raw)[: self.max_suggestions]
        samples = self.engine.generate([user_msg], self.system_prompt,max_new_tokens=self.max_new_tokens,do_sample=True, temperature=self.sc_temperature,top_p=self.sc_top_p, num_return_sequences=self.sc_samples)
        votes = {}
        for raw in samples:
            seen = set()
            for term in self.parse_terms(raw):
                key = term.casefold()
                if key in seen:
                    continue
                seen.add(key)
                if key in votes:
                    votes[key][0] += 1
                else:
                    votes[key] = [1, len(votes), term]
        ranked = sorted(votes.values(), key=lambda v: (-v[0], v[1]))
        return [v[2] for v in ranked][: self.max_suggestions]
    def candidates(self, query, context_str):
        rows = []
        for term in self.suggestions(query, context_str):
            rows.extend(search_entities(term, self.language, self.limit))
        return rows

class FuzzyGenerator(BaseGenerator):
    name = "fuzzy"
    quality = 3

    def __init__(self, language="en", limit=10):
        self.language = language
        self.limit = limit
    def candidates(self, query, context_str):
        rows = []
        for variant in generate_fuzzy_variants(query):
            rows.extend(search_entities(variant, self.language, self.limit))
        return rows

def generate_fuzzy_variants(query):
    variants = set()
    cleaned = re.sub(r'["\*]', "", query).strip()
    if cleaned and cleaned != query:
        variants.add(cleaned)

    no_paren = re.sub(r"\s*\(.*?\)\s*", " ", cleaned).strip()
    if no_paren and no_paren != cleaned:
        variants.add(no_paren)

    for p in re.findall(r"\(([^)]+)\)", cleaned):
        if p.strip():
            variants.add(p.strip())

    no_article = re.sub(r"^(the|a|an)\s+", "", cleaned, flags=re.IGNORECASE).strip()
    if no_article and no_article != cleaned:
        variants.add(no_article)

    if "," in cleaned:
        parts = [p.strip() for p in cleaned.split(",", 1)]
        if len(parts) == 2 and all(parts):
            variants.add(f"{parts[1]} {parts[0]}")
            variants.add(parts[0])

    for sep in (" - ", " – ", " / "):
        if sep in cleaned:
            for part in cleaned.split(sep):
                part = part.strip()
                if part:
                    variants.add(part)

    words = cleaned.split()
    first_word = words[0] if words else ""
    if first_word and first_word.lower() not in {"the", "a", "an"} and first_word != cleaned:
        variants.add(first_word)

    if len(words) >= 3:
        variants.add(" ".join(words[:2]))

    variants.discard(query)
    return [v for v in variants if v]

def as_bool(config, key, default):
    value = config.get(key)
    if value is None:
        return default
    return str(value).strip().lower() == "true"

def build_generators(config, engine=None):
    language = config.get("LANGUAGE", "en")
    limit = int(config.get("SEARCH_LIMIT", "10"))
    order = [n.strip() for n in config.get("GENERATOR_ORDER", "direct,llm,fuzzy").split(",")]

    factories = {
        "direct": lambda: DirectGenerator(language, limit),
        "llm": lambda: LLMGenerator(engine, config.get("PROMPT", ""), language, limit,max_suggestions=int(config.get("LLM_MAX_SUGGESTIONS", "5")),max_new_tokens=int(config.get("LLM_MAX_NEW_TOKENS", "1024")),sc_enabled=as_bool(config, "LLM_SELF_CONSISTENCY", False),sc_samples=int(config.get("SC_SAMPLES", "5")),sc_temperature=float(config.get("SC_TEMPERATURE", "0.7")),sc_top_p=float(config.get("SC_TOP_P", "0.95")),) if engine is not None else None,
        "fuzzy": lambda: FuzzyGenerator(language, limit)}
    defaults = {"direct": True, "llm": True, "fuzzy": False}
    generators = []
    for name in order:
        if name not in factories:
            print(f"Warning: unknown generator '{name}' ignored")
            continue
        if as_bool(config, f"USE_{name.upper()}", defaults[name]):
            gen = factories[name]()
            if gen is not None:
                generators.append(gen)
    return generators
