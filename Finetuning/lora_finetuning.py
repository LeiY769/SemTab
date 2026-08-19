import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import torch
from datasets import load_dataset
from transformers import (AutoTokenizer, AutoModelForCausalLM, EarlyStoppingCallback)
from peft import LoraConfig, get_peft_model
from trl import SFTConfig, SFTTrainer

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

config = load_config("config.txt")

model_name = config.get("model_name", "Qwen/Qwen2.5-7B-Instruct")
train_file = config.get("train_file", "finetune_datasets/ft_slm_context_train.json")
valid_file = config.get("valid_file", "finetune_datasets/ft_slm_context_valid.json")
max_len = int(config.get("max_len", 8192))

output_dir = config.get("output_dir", "./lora-bf16")
adapter_r = int(config.get("adapter_r", 16))
lora_alpha = int(config.get("lora_alpha", 32))

tokenizer = AutoTokenizer.from_pretrained(model_name)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
def format_example(example):
    prompt = []
    if example.get("system"):
        prompt.append({"role": "system", "content": example["system"]})
    prompt.append({"role": "user", "content": example["user"]})
    return {"prompt": prompt,"completion": [{"role": "assistant", "content": example["completion"]}]}

model = AutoModelForCausalLM.from_pretrained(model_name,dtype=torch.bfloat16,device_map={"": 0})
model.config.use_cache = False
peft_config = LoraConfig(r=adapter_r, lora_alpha=lora_alpha,target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],lora_dropout=0.05, bias="none", task_type="CAUSAL_LM")
model = get_peft_model(model, peft_config)

model.enable_input_require_grads()
model.print_trainable_parameters()

data_files = {"train": train_file}
if os.path.exists(valid_file):
    data_files["validation"] = valid_file
ds = load_dataset("json", data_files=data_files)
ds = ds.map(format_example, remove_columns=ds["train"].column_names)

has_val = "validation" in ds
training_args = SFTConfig(
    output_dir=output_dir,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    num_train_epochs=5,
    logging_steps=10,
    save_steps=500,
    save_total_limit=2,
    eval_strategy="steps" if has_val else "no",
    eval_steps=500 if has_val else None,
    optim="paged_adamw_8bit",    
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    bf16=True,
    report_to="none",
    max_length=max_len,
    completion_only_loss=True,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    load_best_model_at_end=has_val,
    metric_for_best_model="eval_loss" if has_val else None,
    greater_is_better=False
)

callbacks = []
if has_val:
    callbacks.append(EarlyStoppingCallback(early_stopping_patience=5, early_stopping_threshold=0.001))

trainer = SFTTrainer(model=model,train_dataset=ds["train"],eval_dataset=ds["validation"] if has_val else None,processing_class=tokenizer,args=training_args,callbacks=callbacks)
trainer.train()
trainer.model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)
