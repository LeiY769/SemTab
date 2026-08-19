import re
import string
from contextlib import nullcontext
from collections import Counter
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

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
    ),
    "CONTEXT_INSTRUCTION_COT": (
        "Reason step by step: weigh the target cell value, its column header, "
        "likely column type and the row context against each candidate's "
        "label, description and type. Briefly say why the close alternatives "
        "are eliminated, then finish with one single final line, exactly in "
        "the form:\nAnswer: <QID>"
    ),
    "CTA_PROMPT": (
        "${values_block}\n"
        "Candidate types:\n${candidates}\n\n"
        "Return only the QID of the type that best describes all the "
        "values in this column."
    ),
    "CPA_PROMPT": (
        "${subtype_block}${objtype_block}${values_block}\n"
        "Candidate properties (subject -> object):\n${candidates}\n\n"
        "Return only the PID of the property that best links the two columns."
    ),
    "DEBATE_PROMPT": (
        "Cell value: ${mention}\n${row_block}\n"
        "Candidate entities from Wikidata:\n${candidates}\n\n"
        "Select the best matching entity and give 3 short arguments.\n"
        "Output format:\nQID: <qid>\nArguments: <arguments>"
    ),
    "VERIFY_PROMPT": (
        "Cell value: ${mention}\n${row_block}"
        "Currently selected entity: ${chosen}\n\n"
        "All candidates:\n${candidates}\n\n"
        "Check the selection fits the cell value, column and row context. "
        "Revise if a better candidate exists, or answer NIL if none fits.\n"
        "Output format:\nWinning QID: <qid or NIL>"
    ),
}
DEFAULT_SIZES = {
    "MAX_NEW_TOKENS_CEA": 128,
    "MAX_NEW_TOKENS_CONTEXT": 512,
    "MAX_NEW_TOKENS_CONTEXT_COT": 512,
    "MAX_NEW_TOKENS_CTA": 128,
    "MAX_NEW_TOKENS_CPA": 128,
    "MAX_NEW_TOKENS_DEBATE": 256,
    "MAX_NEW_TOKENS_VERIFY": 256,
}
def render(template, values):
    return string.Template(template).safe_substitute(values)
def opt_line(label, value):
    return f"{label}{value}\n" if value else ""
def entity_lines(candidates):
    return "\n".join(f"- {c['qid']}: {c['label']} ({c.get('description', '')})" for c in candidates)
def property_lines(candidates):
    return "\n".join(f"- {c['pid']}: {c.get('label', '')}" for c in candidates)
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
class LLMEngine:
    def __init__(self, config, device_id=None, max_ctx=None):
        self.config = config
        self.model_name = config.get("MODEL_NAME")
        self.system_prompt = config.get("SYSTEM_PROMPT", "")

        self.prompts = {k: config.get(k, v) for k, v in DEFAULT_PROMPTS.items()}
        self.sizes = {k: int(config.get(k, v)) for k, v in DEFAULT_SIZES.items()}

        if device_id is None:
            device_id = int(config.get("DEVICE_ID", "0"))
        if max_ctx is None:
            max_ctx = int(config.get("MAX_CTX", "8192"))
        self.batch_size = int(config.get("LLM_BATCH_SIZE", "16"))

        self.adapter_path = (config.get("ADAPTER_PATH", "") or "").strip() or None
        self.load_in_4bit = str(config.get("LOAD_IN_4BIT", "false")).strip().lower() == "true"
        token_source = self.adapter_path or self.model_name

        self.context_cot = str(config.get("CONTEXT_COT", "false")).strip().lower() == "true"
        self.sc_enabled = str(config.get("CONTEXT_SELF_CONSISTENCY", "false")).strip().lower() == "true"
        self.sc_samples = int(config.get("SC_SAMPLES", "5"))
        self.sc_temperature = float(config.get("SC_TEMPERATURE", "0.7"))
        self.sc_top_p = float(config.get("SC_TOP_P", "0.95"))

        self.tokenizer = AutoTokenizer.from_pretrained(token_source)
        self.tokenizer.padding_side = "left"
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        if torch.cuda.is_available():
            self.device = f"cuda:{device_id}"
            dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        else:
            self.device = "cpu"
            dtype = torch.float32

        use_4bit = self.load_in_4bit and torch.cuda.is_available()
        if use_4bit:
            bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_use_double_quant=True,bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=dtype)
            self.model = AutoModelForCausalLM.from_pretrained(self.model_name, quantization_config=bnb_config, device_map={"": device_id})
        else:
            self.model = AutoModelForCausalLM.from_pretrained(self.model_name, dtype=dtype)
            self.model = self.model.to(self.device)

        if self.adapter_path:
            self.model = PeftModel.from_pretrained(self.model, self.adapter_path,device_map={"": device_id} if use_4bit else None)
            if not use_4bit:
                self.model = self.model.to(self.device)

        self.model.eval()
        self.max_ctx = max_ctx
        self.has_chat_template = getattr(self.tokenizer, "chat_template", None) is not None
    def base_model(self):
        # adapter is finetuned on CEA prompts only: CTA/CPA calls use the base model
        if self.adapter_path:
            return self.model.disable_adapter()
        return nullcontext()
    def format_prompt(self, system_prompt, user_msg):
        if not self.has_chat_template:
            return f"{system_prompt}\n\n{user_msg}\n" if system_prompt else f"{user_msg}\n"

        def apply_template(messages):
            try:
                return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,enable_thinking=False)
            except TypeError:
                return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_msg})
        try:
            return apply_template(messages)
        except Exception:
            merged = f"{system_prompt}\n\n{user_msg}" if system_prompt else user_msg
            return apply_template([{"role": "user", "content": merged}])
    def generate(self, user_msgs, system_prompt="", max_new_tokens=2048, batch_size=None,do_sample=False, temperature=1.0, top_p=1.0, num_return_sequences=1):
        if batch_size is None:
            batch_size = self.batch_size
        gen_kwargs = {"max_new_tokens": max_new_tokens, "do_sample": do_sample,"num_return_sequences": num_return_sequences,"pad_token_id": self.tokenizer.pad_token_id}
        if do_sample:
            gen_kwargs["temperature"] = temperature
            gen_kwargs["top_p"] = top_p
        outputs = []
        for i in range(0, len(user_msgs), batch_size):
            chunk = user_msgs[i:i + batch_size]
            prompts = [self.format_prompt(system_prompt, m) for m in chunk]
            inputs = self.tokenizer(prompts, return_tensors="pt", padding=True,truncation=True, max_length=self.max_ctx)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                gen = self.model.generate(**inputs, **gen_kwargs)
            new_tokens = gen[:, inputs["input_ids"].shape[1]:]
            decoded = self.tokenizer.batch_decode(new_tokens, skip_special_tokens=True)
            outputs.extend(d.strip() for d in decoded)
        return outputs
    def match_id(self, response, candidate_ids):
        for candidate_id in candidate_ids:
            if candidate_id and candidate_id in response:
                return candidate_id
        return None
    def final_id(self, response, candidate_ids):
        ids = {c for c in candidate_ids if c}
        m = re.search(r"(?:answer|final|winning\s*qid|qid)\s*[:\-]?\s*(Q\d+)", response, re.I)
        if m and m.group(1) in ids:
            return m.group(1)
        found = [x for x in re.findall(r"Q\d+", response) if x in ids]
        return found[-1] if found else None
    def vote(self, prompt, candidate_ids, max_new_tokens):
        responses = self.generate([prompt], system_prompt=self.system_prompt,max_new_tokens=max_new_tokens, do_sample=True,temperature=self.sc_temperature, top_p=self.sc_top_p,num_return_sequences=self.sc_samples)
        votes = [v for v in (self.final_id(r, candidate_ids) for r in responses) if v]
        if not votes:
            return None
        return Counter(votes).most_common(1)[0][0]
    def select_best_entity(self, mention, candidates, row_context="", col_header=""):
        values = {"mention": mention,"col_header": col_header,"row_context": row_context,"header_block": opt_line("Column header: ", col_header),"row_block": opt_line("Row context: ", row_context),"candidates": entity_lines(candidates)}
        prompt = render(self.prompts["CEA_PROMPT"], values)
        response = self.generate([prompt], system_prompt=self.system_prompt,max_new_tokens=self.sizes["MAX_NEW_TOKENS_CEA"])[0]
        return self.match_id(response, [c["qid"] for c in candidates])
    def select_with_context(self, mention, candidates, table_text="",col_header="", col_type="", target_row=None,target_col=None, max_new_tokens=None,type_labels=None, enrich=False):
        loc = []
        if target_row is not None:
            loc.append(f"row {target_row}")
        if target_col is not None:
            loc.append(f"column {target_col}")
        if self.context_cot:
            instruction = self.prompts["CONTEXT_INSTRUCTION_COT"]
        elif enrich:
            instruction = self.prompts["CONTEXT_INSTRUCTION_ENRICH"]
        else:
            instruction = self.prompts["CONTEXT_INSTRUCTION_PLAIN"]
        values = {"mention": mention,"table_text": table_text,"table_block": f"Table:\n{table_text}\n\n" if table_text else "", "location": ", ".join(loc),"col_header": col_header,"header_block": opt_line("Column header: ", col_header),"col_type": col_type,"coltype_block": opt_line("Likely column type: ", col_type),"candidates": "\n".join( "- " + candidate_line(c, type_labels, enrich) for c in candidates),"instruction": instruction}
        prompt = render(self.prompts["CONTEXT_PROMPT"], values)
        if max_new_tokens is None:
            key = "MAX_NEW_TOKENS_CONTEXT_COT" if self.context_cot else "MAX_NEW_TOKENS_CONTEXT"
            max_new_tokens = self.sizes[key]
        cand_ids = [c["qid"] for c in candidates]
        if self.sc_enabled:
            return self.vote(prompt, cand_ids, max_new_tokens)
        response = self.generate([prompt], system_prompt=self.system_prompt,max_new_tokens=max_new_tokens)[0]
        parser = self.final_id if self.context_cot else self.match_id
        return parser(response, cand_ids)
    def select_best_type(self, candidates, col_values=None, col_header=""):
        values_str = ", ".join(str(v) for v in col_values[:10]) if col_values else ""
        values = {"col_header": col_header,"header_block": opt_line("Column header: ", col_header),"col_values": values_str,"values_block": opt_line("Column values: ", values_str) if col_values else "","candidates": entity_lines(candidates)}
        prompt = render(self.prompts["CTA_PROMPT"], values)
        with self.base_model():
            response = self.generate([prompt], system_prompt=self.system_prompt,max_new_tokens=self.sizes["MAX_NEW_TOKENS_CTA"])[0]
        return self.match_id(response, [c["qid"] for c in candidates])
    def select_best_property(self, candidates, col_header="", sample_values=None, sub_type="", obj_type=""):
        values_str = ", ".join(str(v) for v in sample_values[:10]) if sample_values else ""
        values = {"col_header": col_header, "header_block": opt_line("Object column header: ", col_header), "subtype_block": opt_line("Subject column type: ", sub_type), "objtype_block": opt_line("Object column type: ", obj_type), "sample_values": values_str,"values_block": opt_line("Object column values: ", values_str) if sample_values else "","candidates": property_lines(candidates)}
        prompt = render(self.prompts["CPA_PROMPT"], values)
        with self.base_model():
            response = self.generate([prompt], system_prompt=self.system_prompt,max_new_tokens=self.sizes["MAX_NEW_TOKENS_CPA"])[0]
        return self.match_id(response, [c["pid"] for c in candidates])
    def debate_prompt(self, mention, candidates, row_context="", col_header=""):
        values = {"mention": mention, "col_header": col_header, "row_context": row_context, "header_block": opt_line("Column header: ", col_header), "row_block": opt_line("Row context: ", row_context), "candidates": entity_lines(candidates)}
        return render(self.prompts["DEBATE_PROMPT"], values)
    def verify_prompt(self, mention, chosen, candidates, row_context="", col_header=""):
        values = {"mention": mention, "chosen": chosen, "col_header": col_header, "row_context": row_context,"header_block": opt_line("Column header: ", col_header), "row_block": opt_line("Row context: ", row_context), "candidates": entity_lines(candidates)}
        return render(self.prompts["VERIFY_PROMPT"], values)
    def debate_select(self, mention, candidates, row_context="", col_header=""):
        return self.debate_select_batch([{"mention": mention, "candidates": candidates, "row_context": row_context,"col_header": col_header}])[0]
    def debate_select_batch(self, items):
        if not items:
            return []
        prompts = [self.debate_prompt(i["mention"], i["candidates"],i.get("row_context", ""), i.get("col_header", ""))for i in items]
        responses = self.generate(prompts, system_prompt=self.system_prompt, max_new_tokens=self.sizes["MAX_NEW_TOKENS_DEBATE"])
        return [(self.match_id(resp, [c["qid"] for c in i["candidates"]]), resp)for i, resp in zip(items, responses)]
    def verify(self, mention, chosen, candidates, row_context="", col_header=""):
        return self.verify_batch([{"mention": mention, "chosen": chosen,"candidates": candidates, "row_context": row_context, "col_header": col_header}])[0]
    def verify_batch(self, items):
        if not items:
            return []
        prompts = [self.verify_prompt(i["mention"], i["chosen"], i["candidates"],i.get("row_context", ""), i.get("col_header", ""))for i in items]
        responses = self.generate(prompts, system_prompt=self.system_prompt,max_new_tokens=self.sizes["MAX_NEW_TOKENS_VERIFY"])
        out = []
        for it, resp in zip(items, responses):
            if "NIL" in resp.upper():
                out.append(None)
            else:
                matched = self.match_id(resp, [c["qid"] for c in it["candidates"]])
                out.append(matched if matched else it["chosen"])
        return out
