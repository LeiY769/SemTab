import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import torch
from datasets import load_dataset
from transformers import (AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, EarlyStoppingCallback)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTConfig, SFTTrainer


model_name = "Qwen/Qwen2.5-3B-Instruct"
train_file = "candidate_gen_train.json"
valid_file = "candidate_gen_valid.json"
max_len = 8192

tokenizer = AutoTokenizer.from_pretrained(model_name)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token


def format_example(example):
    user = f"Cell value: {example['cell_value']}"
    if example.get("context"):
        user += f"\nContext: {example['context']}"
    user += "\nCandidates:"
    return {"prompt": [{"role": "system", "content": example["system"]},{"role": "user", "content": user},],"completion": [{"role": "assistant", "content": example["candidates"]},]}

bnb_config = BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_use_double_quant=True,bnb_4bit_quant_type="nf4",bnb_4bit_compute_dtype=torch.bfloat16)

model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=bnb_config, device_map={"": 0})
model.config.use_cache = False
model = prepare_model_for_kbit_training(model, gradient_checkpointing_kwargs={"use_reentrant": False})
peft_config = LoraConfig(r=16, lora_alpha=32,target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],lora_dropout=0.05, bias="none", task_type="CAUSAL_LM")
model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

data_files = {"train": train_file}
if os.path.exists(valid_file):
    data_files["validation"] = valid_file
ds = load_dataset("json", data_files=data_files)
ds = ds.map(format_example, remove_columns=ds["train"].column_names)

has_val = "validation" in ds
training_args = SFTConfig(
    output_dir="./qlora-output",
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
    load_best_model_at_end=has_val,
    metric_for_best_model="eval_loss" if has_val else None,
    greater_is_better=False
)

callbacks = []
if has_val:
    callbacks.append(EarlyStoppingCallback(early_stopping_patience=5, early_stopping_threshold=0.001))

trainer = SFTTrainer(model=model,train_dataset=ds["train"],eval_dataset=ds["validation"] if has_val else None,processing_class=tokenizer,args=training_args,callbacks=callbacks)
trainer.train()
trainer.model.save_pretrained("qlora-adapter")
tokenizer.save_pretrained("qlora-adapter")