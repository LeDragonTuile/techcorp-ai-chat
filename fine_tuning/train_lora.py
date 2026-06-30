"""
Fine-tuning LoRA — Modèle Médical Expérimental
Dataset : ruslanmv/ai-medical-chatbot (HuggingFace)

Usage (Google Colab Pro recommandé) :
  python train_lora.py --model_name microsoft/phi-2 --epochs 3 --output_dir ./output

Prérequis GPU : au moins 8GB VRAM (16GB recommandé pour phi-2)
"""
import argparse
import json
import os
import torch
from datasets import load_dataset, Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq,
    BitsAndBytesConfig,
)
from peft import (
    LoraConfig,
    get_peft_model,
    TaskType,
    PeftModel,
    prepare_model_for_kbit_training,
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="LoRA Medical Fine-tuning")
    parser.add_argument("--model_name", default="microsoft/phi-2", help="Modèle de base HuggingFace")
    parser.add_argument("--dataset_path", default=None, help="Chemin dataset local JSON (optionnel)")
    parser.add_argument("--output_dir", default="./medical_model_lora", help="Répertoire de sortie")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--max_length", type=int, default=512)
    parser.add_argument("--lora_r", type=int, default=16, help="Rang LoRA")
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--lora_dropout", type=float, default=0.05)
    parser.add_argument("--quantize", action="store_true", help="Activer quantization 4-bit")
    parser.add_argument("--max_samples", type=int, default=5000, help="Limite d'exemples d'entraînement")
    return parser.parse_args()


def load_medical_dataset(dataset_path=None, max_samples=5000):
    """Charge le dataset médical depuis HuggingFace ou un fichier local."""
    if dataset_path and os.path.exists(dataset_path):
        logger.info(f"Chargement dataset local: {dataset_path}")
        with open(dataset_path) as f:
            data = json.load(f)
        return Dataset.from_list(data[:max_samples])

    logger.info("Téléchargement dataset depuis HuggingFace: ruslanmv/ai-medical-chatbot")
    try:
        dataset = load_dataset("ruslanmv/ai-medical-chatbot", split="train")
        if max_samples and len(dataset) > max_samples:
            dataset = dataset.select(range(max_samples))
        return dataset
    except Exception as e:
        logger.error(f"Erreur chargement HuggingFace: {e}")
        logger.info("Création d'un dataset de démonstration...")
        return _create_demo_dataset()


def _create_demo_dataset():
    """Dataset de démonstration si HuggingFace est inaccessible."""
    samples = [
        {
            "Patient": "J'ai des douleurs thoraciques depuis ce matin.",
            "Doctor": "Les douleurs thoraciques peuvent avoir plusieurs causes. Décrivez-les : oppression, brûlure, ou élancement ? Avez-vous des difficultés à respirer ou des douleurs dans le bras gauche ? Il est important de consulter immédiatement aux urgences si la douleur est intense."
        },
        {
            "Patient": "Je prends de la metformine mais mon taux de glycémie reste élevé.",
            "Doctor": "La metformine est un traitement de première ligne pour le diabète de type 2. Si votre glycémie reste élevée, il faudra revoir votre alimentation, votre activité physique, et potentiellement ajuster la dose ou ajouter un autre médicament. Je vous recommande un bilan complet avec votre médecin."
        },
        {
            "Patient": "Quels sont les symptômes de l'hypertension artérielle ?",
            "Doctor": "L'hypertension est souvent asymptomatique ('tueur silencieux'). Parfois : maux de tête (surtout matinaux), vertiges, saignements de nez, vision floue. Un contrôle régulier de la tension est essentiel. Valeurs normales : inférieur à 120/80 mmHg."
        },
    ]
    return Dataset.from_list(samples * 100)


def format_conversation(example):
    """Formate un exemple de conversation médecin-patient en instruction."""
    patient = example.get("Patient", example.get("input", ""))
    doctor = example.get("Doctor", example.get("output", ""))
    return {
        "text": f"<|user|>\n{patient}\n<|assistant|>\n{doctor}<|endoftext|>"
    }


def tokenize(example, tokenizer, max_length):
    result = tokenizer(
        example["text"],
        truncation=True,
        max_length=max_length,
        padding="max_length",
    )
    result["labels"] = result["input_ids"].copy()
    return result


def setup_model(model_name, quantize=False):
    """Charge le modèle avec configuration LoRA."""
    logger.info(f"Chargement du modèle: {model_name}")

    if quantize:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )
        model = prepare_model_for_kbit_training(model)
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True,
        )

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return model, tokenizer


def main():
    args = parse_args()
    logger.info("=== TechCorp AI — Fine-tuning LoRA Médical ===")
    logger.info(f"Modèle: {args.model_name} | Epochs: {args.epochs} | LR: {args.lr}")

    dataset = load_medical_dataset(args.dataset_path, args.max_samples)
    logger.info(f"Dataset chargé: {len(dataset)} exemples")

    dataset = dataset.map(format_conversation)
    logger.info(f"Exemple formaté: {dataset[0]['text'][:200]}...")

    model, tokenizer = setup_model(args.model_name, args.quantize)

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    tokenized = dataset.map(
        lambda x: tokenize(x, tokenizer, args.max_length),
        remove_columns=dataset.column_names,
    )

    split = tokenized.train_test_split(test_size=0.05, seed=42)
    train_data, eval_data = split["train"], split["test"]
    logger.info(f"Train: {len(train_data)} | Eval: {len(eval_data)}")

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        learning_rate=args.lr,
        fp16=torch.cuda.is_available(),
        logging_steps=50,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        warmup_steps=100,
        lr_scheduler_type="cosine",
        report_to="none",
        dataloader_num_workers=0,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_data,
        eval_dataset=eval_data,
        data_collator=DataCollatorForSeq2Seq(tokenizer, model, padding=True),
    )

    logger.info("Début du fine-tuning LoRA...")
    trainer.train()

    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    logger.info(f"Modèle sauvegardé dans: {args.output_dir}")

    logger.info("Test rapide du modèle fine-tuné...")
    test_prompt = "<|user|>\nJ'ai de la fièvre depuis 3 jours, que dois-je faire ?\n<|assistant|>\n"
    inputs = tokenizer(test_prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(
            **inputs, max_new_tokens=200, temperature=0.7, do_sample=True, pad_token_id=tokenizer.eos_token_id
        )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    logger.info(f"Réponse test:\n{response}")

    logger.info("=== Fine-tuning terminé avec succès ===")


if __name__ == "__main__":
    main()
