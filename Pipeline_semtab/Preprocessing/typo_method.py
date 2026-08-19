from transformers import AutoTokenizer, AutoModelForCausalLM
import re
import os
import torch
import pandas as pd
import multiprocessing
import queue

from vram_logger_preprocessing import log_vram, reset_peaks

def load_model(model_name, device_id=0):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.padding_side = "left" 

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    if torch.cuda.is_available():
        device = f"cuda:{device_id}"
        dtype = torch.float16
        model = AutoModelForCausalLM.from_pretrained(model_name, dtype=dtype)
        model = model.to(device)
    else:
        device = "cpu"
        dtype = torch.float32
        model = AutoModelForCausalLM.from_pretrained(model_name, dtype=dtype)
        model = model.to(device)
    
    model.eval()
    return tokenizer, model

def parse_fewshot_examples(raw):
    if raw is None or not isinstance(raw, str):
        return raw
    examples = []
    for pair in raw.split(";"):
        if "->" not in pair:
            continue
        src, tgt = pair.split("->", 1)
        examples.append((src.strip(), tgt.strip()))
    return examples if examples else None

def build_prompts(texts, system_prompt, tokenizer, fewshot_examples=None, use_fewshot=True):
    use_template = getattr(tokenizer, "chat_template", None) is not None
    prompts = []
    for t in texts:
        if use_template:
            messages = [{"role": "system", "content": system_prompt}]
            if use_fewshot and fewshot_examples is not None:
                for src, tgt in fewshot_examples:
                    messages.append({"role": "user", "content": src})
                    messages.append({"role": "assistant", "content": tgt})
            messages.append({"role": "user", "content": t})
            prompts.append(tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True))
        else:
            if use_fewshot and fewshot_examples is not None:
                shots = "".join(f"Original: {src}\nCorrected: {tgt}\n" for src, tgt in fewshot_examples)
                prompts.append(f"{system_prompt}\n{shots}Original: {t}\nCorrected:")
            else:
                prompts.append(f"{system_prompt}\nOriginal: {t}\nCorrected:")
    return prompts
def correct_typo_with_llm(text, tokenizer, model, SYSTEM_PROMPT,max_new_tokens=64, batch_size=32, max_ctx=None, lowercase=True, use_fewshot=True, fewshot_examples=None):
    if not text:
        return []
 
    if max_ctx is None:
        max_ctx = getattr(model.config, "max_position_embeddings", 1024)
 
    device = next(model.parameters()).device
    out = []
 
    for i in range(0, len(text), batch_size):
        chunk = text[i:i + batch_size]
        prompts = build_prompts(chunk, SYSTEM_PROMPT, tokenizer, fewshot_examples, use_fewshot)
 
        inputs = tokenizer(prompts, return_tensors="pt", padding=True,truncation=True, max_length=max_ctx)
        inputs = {k: v.to(device) for k, v in inputs.items()}
 
        with torch.no_grad():
            gen = model.generate(**inputs,max_new_tokens=max_new_tokens,do_sample=False,pad_token_id=tokenizer.pad_token_id)
 
        new_tokens = gen[:, inputs["input_ids"].shape[1]:]
        decoded = tokenizer.batch_decode(new_tokens, skip_special_tokens=True)
 
        for corr, orig in zip(decoded, chunk):
            corr = corr.strip().strip('"').strip("'").strip()
            corr = corr.replace("\n", " ").strip()
 
            if corr.endswith(".") and not orig.strip().endswith("."):
                corr = corr[:-1].strip()

            if (not corr) or (len(corr) > len(orig) * 3):
                corr = orig
            out.append(corr)
 
    return out

def process_file_df(df, tokenizer, model, system_prompt, batch_size=32, max_new_tokens=64, use_fewshot=True, fewshot_examples=None):

    text_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    text_cols = [c for c in text_cols if not str(c).startswith("Metadata:")]
    cache = {}

    for col in text_cols:
        s = df[col]
        s_norm = s.where(s.isna(), s.astype(str))
        uniques = pd.unique(s_norm.dropna())
        uniques = [u for u in uniques if u != ""]

        to_do = [u for u in uniques if u not in cache]

        corrected = correct_typo_with_llm(to_do,tokenizer=tokenizer,model=model,SYSTEM_PROMPT=system_prompt,batch_size=batch_size,max_new_tokens=max_new_tokens,use_fewshot=use_fewshot,fewshot_examples=fewshot_examples)

        for u, c in zip(to_do, corrected):
            cache[u] = c

        df[col] = s_norm.map(lambda x: cache.get(x, x) if pd.notna(x) and x != "" else x)

    return df

def process_single_file(input_folder, output_folder, file_name, tokenizer, model, system_prompt, use_fewshot=True, fewshot_examples=None):
    in_path = os.path.join(input_folder, file_name)
    out_path = os.path.join(output_folder, file_name)

    df = pd.read_csv(in_path)
    df = process_file_df(df, tokenizer, model, system_prompt, batch_size=32, max_new_tokens=64, use_fewshot=use_fewshot, fewshot_examples=fewshot_examples)
    df.to_csv(out_path, index=False)

def worker_process(file_queue, input_folder, model_name, system_prompt, output_folder, device_id, use_fewshot=True, fewshot_examples=None):
    reset_peaks(device_id)
    tokenizer, model = load_model(model_name, device_id=device_id)
    print(f"[GPU {device_id}] model loaded on", next(model.parameters()).device)
    log_vram("model_loaded", device_id=device_id)

    while True:
        try:
            file_name = file_queue.get_nowait()
        except queue.Empty:
            break
        try:
            process_single_file(input_folder, output_folder, file_name, tokenizer, model, system_prompt, use_fewshot=use_fewshot, fewshot_examples=fewshot_examples)
        except Exception as e:
            print(f"[GPU {device_id}] ERROR on {file_name}: {e}")
    log_vram("typo_correction_done", device_id=device_id)

def process_folder(config):
    need_correctypo = config.get("NEED_CORRECTTYPO", "True").lower() == "true"
    if not need_correctypo:
        print("Typo correction is disabled in the configuration.")
        return
    input_folder = config["INPUT_FOLDER"]
    output_folder = config.get("OUTPUT_FOLDER", None)
    model_name = config.get("MODEL_NAME")
    system_prompt = config.get("SYSTEM_PROMPT")
    num_gpus = int(config.get("NUM_GPUS", 1))
    use_fewshot = config.get("USE_FEWSHOT", "True").lower() == "true"
    fewshot_examples = parse_fewshot_examples(config.get("FEWSHOT_EXAMPLES", None))

    if output_folder is None:
        output_folder = input_folder + "_typo_corrected"
    os.makedirs(output_folder, exist_ok=True)

    if torch.cuda.is_available():
        available_gpus = torch.cuda.device_count()
        num_gpus = min(num_gpus, available_gpus)
        print(f"Using {num_gpus} GPUs out of {available_gpus} available")
    else:
        num_gpus = 1

    csv_files = [f for f in os.listdir(input_folder) if f.endswith(".csv")]
    
    if num_gpus == 1 or not torch.cuda.is_available():
        reset_peaks()
        tokenizer, model = load_model(model_name, device_id=0)
        print("model device:", next(model.parameters()).device)
        log_vram("model_loaded")

        for file_name in csv_files:
            in_path = os.path.join(input_folder, file_name)
            out_path = os.path.join(output_folder, file_name)

            df = pd.read_csv(in_path)
            df = process_file_df(df, tokenizer, model, system_prompt, batch_size=32, max_new_tokens=64, use_fewshot=use_fewshot, fewshot_examples=fewshot_examples)
            df.to_csv(out_path, index=False)
        log_vram("typo_correction_done")
    else:
        multiprocessing.set_start_method('spawn', force=True)

        with multiprocessing.Manager() as manager:
            file_queue = manager.Queue()
            for file_name in csv_files:
                file_queue.put(file_name)
            processes = []
            for gpu_id in range(num_gpus):
                p = multiprocessing.Process(target=worker_process,args=(file_queue, input_folder,model_name, system_prompt, output_folder, gpu_id, use_fewshot, fewshot_examples))
                p.start()
                processes.append(p)
            for p in processes:
                p.join()
            for gpu_id, p in enumerate(processes):
                if p.exitcode != 0:
                    print(f"WARNING: worker GPU {gpu_id} failed with code {p.exitcode}")

        print("All files processed successfully")
