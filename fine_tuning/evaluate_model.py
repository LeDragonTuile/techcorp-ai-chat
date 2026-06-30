"""
Évaluation du modèle médical fine-tuné
Compare le modèle de base vs le modèle fine-tuné (LoRA)
"""
import json
import torch
import argparse
from pathlib import Path

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


TEST_CASES = [
    {
        "input": "J'ai de la fièvre depuis 3 jours et des frissons. Que dois-je faire ?",
        "keywords": ["médecin", "consultation", "température", "antipyrétique", "hydrat"],
    },
    {
        "input": "Je ressens des douleurs dans la poitrine quand je respire profondément.",
        "keywords": ["urgence", "cardiologue", "poumon", "douleur", "médecin"],
    },
    {
        "input": "Je suis diabétique de type 2. Mon taux de glycémie est à 2.8 g/L à jeun.",
        "keywords": ["glycémie", "diabète", "insuline", "médecin", "traitement"],
    },
    {
        "input": "Quels sont les signes d'un AVC ?",
        "keywords": ["urgence", "15", "samu", "paralysie", "parole", "FAST"],
    },
    {
        "input": "Comment soulager une migraine sans médicaments ?",
        "keywords": ["repos", "sombre", "froid", "hydratation", "stress"],
    },
]


def load_model(model_path: str, base_model: str = None):
    """Charge un modèle (base ou fine-tuné)."""
    if base_model:
        print(f"Chargement LoRA: {model_path} (base: {base_model})")
        tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True,
        )
        model = PeftModel.from_pretrained(model, model_path)
    else:
        print(f"Chargement modèle de base: {model_path}")
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True,
        )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return model, tokenizer


def generate_response(model, tokenizer, prompt: str, max_tokens: int = 300) -> str:
    """Génère une réponse."""
    formatted = f"<|user|>\n{prompt}\n<|assistant|>\n"
    inputs = tokenizer(formatted, return_tensors="pt", truncation=True, max_length=512)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.1,
        )

    full = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if "<|assistant|>" in full:
        return full.split("<|assistant|>")[-1].strip()
    return full[len(formatted):].strip()


def evaluate(model, tokenizer, model_name: str) -> dict:
    """Évalue un modèle sur les cas de test."""
    print(f"\n{'='*50}")
    print(f"Évaluation: {model_name}")
    print(f"{'='*50}")

    results = []
    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n[{i}] {test['input'][:60]}...")
        response = generate_response(model, tokenizer, test["input"])
        print(f"Réponse: {response[:200]}...")

        found = [kw for kw in test["keywords"] if kw.lower() in response.lower()]
        score = len(found) / len(test["keywords"])
        print(f"Score: {score*100:.0f}% ({len(found)}/{len(test['keywords'])} mots-clés)")

        results.append({
            "input": test["input"],
            "response": response,
            "keywords_found": found,
            "score": round(score, 2),
        })

    avg_score = sum(r["score"] for r in results) / len(results)
    print(f"\nScore moyen: {avg_score*100:.0f}%")
    return {"model": model_name, "avg_score": round(avg_score, 2), "tests": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", default="microsoft/phi-2", help="Modèle de base")
    parser.add_argument("--lora_path", default="./medical_model_lora", help="Chemin du modèle fine-tuné")
    parser.add_argument("--output", default="evaluation_results.json")
    args = parser.parse_args()

    if not TORCH_AVAILABLE:
        print("[ERREUR] PyTorch/Transformers non installés")
        print("  pip install -r fine_tuning/requirements_finetune.txt")
        return

    all_results = []

    # Évaluation du modèle de base
    base_model, base_tokenizer = load_model(args.base_model)
    base_results = evaluate(base_model, base_tokenizer, "Modèle de base")
    all_results.append(base_results)
    del base_model

    # Évaluation du modèle fine-tuné
    if Path(args.lora_path).exists():
        ft_model, ft_tokenizer = load_model(args.lora_path, args.base_model)
        ft_results = evaluate(ft_model, ft_tokenizer, "Modèle fine-tuné (LoRA)")
        all_results.append(ft_results)

        # Comparaison
        improvement = (ft_results["avg_score"] - base_results["avg_score"]) / base_results["avg_score"] * 100
        print(f"\n{'='*50}")
        print(f"COMPARAISON")
        print(f"{'='*50}")
        print(f"Base     : {base_results['avg_score']*100:.0f}%")
        print(f"Fine-tuné: {ft_results['avg_score']*100:.0f}%")
        print(f"Amélioration: {improvement:+.1f}%")
    else:
        print(f"\n[WARN] Modèle fine-tuné non trouvé: {args.lora_path}")
        print("  Lancez d'abord: python fine_tuning/train_lora.py")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\nRésultats sauvegardés: {args.output}")


if __name__ == "__main__":
    main()
