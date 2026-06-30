"""
Fine-tuning LoRA médical — version CPU exécutable localement
(modèle léger, sous-ensemble du dataset). But : produire de VRAIS
adaptateurs LoRA entraînés + un rapport, sans GPU.

Pour le fine-tuning à pleine échelle (Phi-2, 4-bit), utiliser
train_lora.py / finetune_colab.ipynb sur GPU (Colab).

Usage :
  python train_lora_cpu.py
  python train_lora_cpu.py --model_name distilgpt2 --max_samples 400 --epochs 1
"""
import sys
import os
import json
import time
import argparse
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM, AutoTokenizer,
    TrainingArguments, Trainer, DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, TaskType

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "medical_dataset" / "medical_dataset_training.json"


def parse_args():
    p = argparse.ArgumentParser(description="LoRA médical — CPU")
    p.add_argument("--model_name", default="distilgpt2", help="Petit modèle de base (CPU)")
    p.add_argument("--dataset", default=str(DATA))
    p.add_argument("--output_dir", default=str(HERE / "medical_model_lora"))
    p.add_argument("--max_samples", type=int, default=400)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch_size", type=int, default=2)
    p.add_argument("--max_length", type=int, default=256)
    p.add_argument("--lora_r", type=int, default=8)
    p.add_argument("--lora_alpha", type=int, default=16)
    return p.parse_args()


def detect_target_modules(model) -> list[str]:
    """Détecte les modules d'attention à adapter selon l'architecture."""
    names = {n.split(".")[-1] for n, _ in model.named_modules()}
    if "c_attn" in names:           # GPT-2 / DistilGPT2
        return ["c_attn"]
    for combo in (["q_proj", "v_proj"], ["query_key_value"], ["Wqkv"]):
        if all(c in names for c in combo):
            return combo
    # repli : toutes les couches linéaires nommées 'q'/'v'
    return ["c_attn"]


def load_examples(path: str, max_samples: int) -> Dataset:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data = data[:max_samples]
    texts = [ex["text"] for ex in data if ex.get("text")]
    print(f"Exemples chargés : {len(texts)} (sur {len(data)})")
    return Dataset.from_dict({"text": texts})


def generate(model, tokenizer, prompt: str, max_new=60) -> str:
    model.eval()
    enc = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=200)
    with torch.no_grad():
        out = model.generate(
            **enc, max_new_tokens=max_new, do_sample=True, temperature=0.8,
            top_p=0.9, pad_token_id=tokenizer.eos_token_id, repetition_penalty=1.2,
        )
    return tokenizer.decode(out[0], skip_special_tokens=True)


def main():
    args = parse_args()
    torch.manual_seed(42)
    t0 = time.time()

    print("=" * 60)
    print("  Fine-tuning LoRA médical (CPU) —", args.model_name)
    print("=" * 60)
    print(f"Device : CPU | epochs={args.epochs} | samples={args.max_samples} | r={args.lora_r}")

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model_name, torch_dtype=torch.float32)

    # Prompt de test médical (avant entraînement)
    test_prompt = "<|user|>\nI have had a fever and sore throat for two days. What should I do?\n<|assistant|>\n"
    print("\n--- Génération AVANT fine-tuning ---")
    before = generate(model, tokenizer, test_prompt)
    print(before[:300])

    targets = detect_target_modules(model)
    print(f"\nModules LoRA ciblés : {targets}")
    lora = LoraConfig(
        task_type=TaskType.CAUSAL_LM, r=args.lora_r, lora_alpha=args.lora_alpha,
        lora_dropout=0.05, target_modules=targets, bias="none",
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    ds = load_examples(args.dataset, args.max_samples)

    def tok(batch):
        return tokenizer(batch["text"], truncation=True, max_length=args.max_length)
    ds = ds.map(tok, batched=True, remove_columns=["text"])

    collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)
    targs = TrainingArguments(
        output_dir=args.output_dir, num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size, gradient_accumulation_steps=2,
        learning_rate=2e-4, logging_steps=20, save_strategy="no",
        report_to="none", dataloader_num_workers=0, warmup_steps=10,
    )
    trainer = Trainer(model=model, args=targs, train_dataset=ds, data_collator=collator)

    print("\n--- Entraînement ---")
    train_out = trainer.train()
    final_loss = train_out.training_loss

    os.makedirs(args.output_dir, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"\nAdaptateur LoRA sauvegardé : {args.output_dir}")

    print("\n--- Génération APRÈS fine-tuning ---")
    after = generate(model, tokenizer, test_prompt)
    print(after[:300])

    elapsed = time.time() - t0
    write_report(args, targets, final_loss, before, after, elapsed, len(ds))
    print(f"\n=== Terminé en {elapsed:.0f}s — loss finale {final_loss:.4f} ===")


def write_report(args, targets, loss, before, after, elapsed, n):
    report = HERE / "lora_training_report.md"
    trainable = "voir log print_trainable_parameters"
    content = f"""# Rapport d'entraînement — LoRA médical (exécuté en local, CPU)

> Run **réel** réalisé sur cette machine (sans GPU) pour produire des adaptateurs
> LoRA entraînés à titre de **preuve d'exécution**. Le fine-tuning à pleine
> échelle (Phi-2, 4-bit) se fait sur GPU via `finetune_colab.ipynb`.

## Configuration
| Paramètre | Valeur |
|-----------|--------|
| Modèle de base | `{args.model_name}` |
| Modules LoRA ciblés | `{', '.join(targets)}` |
| Rang LoRA (r) | {args.lora_r} (alpha {args.lora_alpha}) |
| Exemples d'entraînement | {n} |
| Époques | {args.epochs} |
| Longueur max | {args.max_length} tokens |
| Device | CPU |
| Durée | {elapsed:.0f}s |
| **Loss finale** | **{loss:.4f}** |

## Données
Dataset médical nettoyé : `medical_dataset/medical_dataset_training.json`
(format `<|user|> … <|assistant|> …`).

## Exemple de génération (même prompt)
**Prompt :** *"I have had a fever and sore throat for two days. What should I do?"*

**Avant fine-tuning :**
```
{before.strip()[:400]}
```

**Après fine-tuning :**
```
{after.strip()[:400]}
```

## Artefacts produits
- `fine_tuning/medical_model_lora/adapter_model.safetensors` — poids LoRA entraînés
- `fine_tuning/medical_model_lora/adapter_config.json` — configuration LoRA

## Note
Modèle **expérimental** (conforme au brief : « pas pour la production »). Le but
est de démontrer la chaîne complète de fine-tuning LoRA bout-en-bout, réellement
exécutée. Pour des résultats de qualité, relancer sur GPU avec un modèle plus
grand (Phi-2 / Phi-3.5) et plus d'exemples via le notebook Colab.
"""
    report.write_text(content, encoding="utf-8")
    print(f"Rapport écrit : {report}")


if __name__ == "__main__":
    main()
