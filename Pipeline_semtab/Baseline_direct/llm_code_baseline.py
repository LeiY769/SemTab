import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

class LLMEngine:
    def __init__(self, model_name, device_id=0, max_ctx=4096, adapter_path=None, load_in_4bit=False):
        self.model_name = model_name
        if adapter_path:
            token_source = adapter_path
        else:
            token_source = model_name
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

        if load_in_4bit:
            bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=dtype)
            self.model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=bnb_config, device_map={"": 0})
        else:
            self.model = AutoModelForCausalLM.from_pretrained(model_name, dtype=dtype)
            self.model = self.model.to(self.device)
        if adapter_path:
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(self.model, adapter_path, device_map={"": 0})
        self.model.eval()
        self.max_ctx = max_ctx
        self.has_chat_template = getattr(self.tokenizer, "chat_template", None) is not None
        self.tokens_in = 0
        self.tokens_out = 0

    def format_prompt(self, system_prompt, user_msg):
        if not self.has_chat_template:
            return f"{system_prompt}\n\n{user_msg}\n" if system_prompt else f"{user_msg}\n"

        def apply_template(messages):
            try:
                return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
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

    def generate(self, user_msgs, system_prompt="", max_new_tokens=32, batch_size=16):
        outputs = []
        for i in range(0, len(user_msgs), batch_size):
            chunk = user_msgs[i:i + batch_size]
            prompts = [self.format_prompt(system_prompt, m) for m in chunk]
            inputs = self.tokenizer(prompts, return_tensors="pt", padding=True, truncation=True, max_length=self.max_ctx)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                gen = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=self.tokenizer.pad_token_id)
            new_tokens = gen[:, inputs["input_ids"].shape[1]:]
            self.tokens_in += int(inputs["attention_mask"].sum().item())
            self.tokens_out += int((new_tokens != self.tokenizer.pad_token_id).sum().item())
            decoded = self.tokenizer.batch_decode(new_tokens, skip_special_tokens=True)
            outputs.extend(d.strip() for d in decoded)
        return outputs
