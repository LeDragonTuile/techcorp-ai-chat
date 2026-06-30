"""
Préparation et nettoyage du dataset médical
Source : ruslanmv/ai-medical-chatbot (HuggingFace)
"""
import sys
import json
import re
import os
from pathlib import Path
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from datasets import load_dataset
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("[WARN] datasets non installé — pip install datasets")


def download_dataset(max_samples=10000, output_path="medical_dataset_raw.json", streaming=True):
    """Télécharge le dataset depuis HuggingFace.

    streaming=True : ne tire que les `max_samples` premiers exemples (rapide, léger)
    au lieu de télécharger l'intégralité du dataset (~256 Mo).
    """
    if not HF_AVAILABLE:
        print("[ERROR] Installez 'datasets' : pip install datasets")
        return None

    print(f"Téléchargement de ruslanmv/ai-medical-chatbot (streaming={streaming}, max={max_samples})...")
    try:
        if streaming:
            ds = load_dataset("ruslanmv/ai-medical-chatbot", split="train", streaming=True)
            iterator = ds
        else:
            ds = load_dataset("ruslanmv/ai-medical-chatbot", split="train")
            print(f"Dataset complet chargé : {len(ds)} exemples")
            iterator = ds

        data = []
        for i, ex in enumerate(iterator):
            if i >= max_samples:
                break
            data.append({
                "id": i,
                "patient": (ex.get("Patient") or "").strip(),
                "doctor": (ex.get("Doctor") or "").strip(),
                "description": (ex.get("Description") or "").strip(),
            })
            if (i + 1) % 500 == 0:
                print(f"  ... {i + 1} exemples récupérés")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Sauvegardé : {output_path} ({len(data)} exemples)")
        return data
    except Exception as e:
        print(f"[ERROR] Téléchargement échoué : {e}")
        print("[INFO] Bascule sur le dataset de démonstration intégré...")
        return _download_demo_fallback(output_path, max_samples)


def _download_demo_fallback(output_path, max_samples):
    """Jeu de démonstration si HuggingFace est inaccessible (hors-ligne)."""
    base = [
        {"patient": "J'ai des maux de tête persistants depuis une semaine, accompagnés de nausées.",
         "doctor": "Des céphalées persistantes avec nausées doivent être évaluées. Notez la fréquence, l'intensité et les déclencheurs. Hydratez-vous, reposez-vous dans le noir. Si la douleur est brutale et intense, ou s'accompagne de fièvre, troubles visuels ou raideur de la nuque, consultez en urgence.",
         "description": "Céphalées"},
        {"patient": "Mon enfant de 5 ans a 39°C de fièvre depuis hier soir.",
         "doctor": "Pour une fièvre à 39°C : donnez du paracétamol selon le poids, hydratez régulièrement, habillez-le légèrement. Surveillez l'apparition de signes de gravité (somnolence inhabituelle, taches sur la peau, gêne respiratoire) et consultez si la fièvre persiste au-delà de 48-72h ou si l'état général se dégrade.",
         "description": "Fièvre pédiatrique"},
        {"patient": "Je ressens un essoufflement à l'effort depuis quelques semaines.",
         "doctor": "Un essoufflement d'apparition récente à l'effort mérite un bilan : il peut être d'origine cardiaque, pulmonaire ou liée à une anémie. Je vous recommande de consulter votre médecin pour un examen clinique, un ECG et éventuellement une prise de sang. Évitez les efforts intenses en attendant.",
         "description": "Dyspnée d'effort"},
    ]
    data = [{"id": i, **base[i % len(base)]} for i in range(min(max_samples, 300))]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Dataset de démonstration écrit : {output_path} ({len(data)} exemples)")
    return data


def clean_text(text: str) -> str:
    """Nettoie le texte médical."""
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s.,!?\'\"()\-:;éèêëàâùûüîïôœæç]', ' ', text, flags=re.UNICODE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def validate_example(ex: dict) -> tuple[bool, str]:
    """Valide un exemple. Retourne (valide, raison_rejet)."""
    patient = ex.get("patient", "")
    doctor = ex.get("doctor", "")

    if len(patient) < 10:
        return False, "patient_too_short"
    if len(doctor) < 20:
        return False, "doctor_too_short"
    if len(patient) > 2000:
        return False, "patient_too_long"
    if len(doctor) > 5000:
        return False, "doctor_too_long"

    medical_keywords = [
        "symptom", "pain", "fever", "doctor", "patient", "medical", "health",
        "douleur", "fièvre", "médecin", "traitement", "maladie", "symptôme",
        "médicament", "diagnostic", "prescription", "santé", "hôpital",
    ]
    combined = (patient + " " + doctor).lower()
    if not any(kw in combined for kw in medical_keywords):
        return False, "not_medical"

    return True, ""


def prepare_dataset(input_path="medical_dataset_raw.json", output_path="medical_dataset_clean.json"):
    """Nettoie et filtre le dataset."""
    if not os.path.exists(input_path):
        print(f"[ERROR] Fichier introuvable : {input_path}")
        print("Téléchargez d'abord avec download_dataset()")
        return None

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"Chargé : {len(data)} exemples bruts")

    cleaned = []
    rejection_reasons = Counter()

    for ex in data:
        ex["patient"] = clean_text(ex.get("patient", ""))
        ex["doctor"] = clean_text(ex.get("doctor", ""))

        valid, reason = validate_example(ex)
        if valid:
            cleaned.append(ex)
        else:
            rejection_reasons[reason] += 1

    print(f"\n=== Rapport de nettoyage ===")
    print(f"Exemples valides   : {len(cleaned)} / {len(data)}")
    print(f"Taux de rétention  : {len(cleaned)/len(data)*100:.1f}%")
    print(f"Raisons de rejet   :")
    for reason, count in rejection_reasons.most_common():
        print(f"  - {reason}: {count}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"\nDataset nettoyé sauvegardé : {output_path}")

    report_path = str(output_path).replace(".json", "_report.txt")
    generate_quality_report(cleaned, report_path)
    return cleaned


def format_for_training(input_path="medical_dataset_clean.json", output_path="medical_dataset_training.json"):
    """Convertit au format d'entraînement LoRA."""
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    training_data = []
    for ex in data:
        training_data.append({
            "instruction": "Tu es un médecin expert. Réponds à la question médicale du patient de manière professionnelle, bienveillante et précise.",
            "input": ex["patient"],
            "output": ex["doctor"],
            "text": f"<|user|>\n{ex['patient']}\n<|assistant|>\n{ex['doctor']}<|endoftext|>",
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)

    print(f"Dataset d'entraînement : {output_path} ({len(training_data)} exemples)")

    # Échantillon versionnable (aperçu du livrable, fichier léger)
    sample_path = str(output_path).replace("_training.json", "_sample.json")
    sample = training_data[:15]
    with open(sample_path, "w", encoding="utf-8") as f:
        json.dump(sample, f, ensure_ascii=False, indent=2)
    print(f"Échantillon (15 ex.) : {sample_path}")
    return training_data


def generate_quality_report(data: list, output_path: str):
    """Génère un rapport de qualité."""
    patient_lengths = [len(ex["patient"]) for ex in data]
    doctor_lengths = [len(ex["doctor"]) for ex in data]

    report = f"""=== Rapport de qualité du dataset médical ===
Généré le : {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}

STATISTIQUES GÉNÉRALES
  Total exemples     : {len(data)}

LONGUEUR DES QUESTIONS PATIENTS
  Moyenne           : {sum(patient_lengths)/len(patient_lengths):.0f} caractères
  Minimum           : {min(patient_lengths)} caractères
  Maximum           : {max(patient_lengths)} caractères

LONGUEUR DES RÉPONSES MÉDECIN
  Moyenne           : {sum(doctor_lengths)/len(doctor_lengths):.0f} caractères
  Minimum           : {min(doctor_lengths)} caractères
  Maximum           : {max(doctor_lengths)} caractères

QUALITÉ ESTIMÉE
  Ratio texte court  : {sum(1 for l in patient_lengths if l < 50)/len(data)*100:.1f}% questions < 50 chars
  Ratio réponse riche: {sum(1 for l in doctor_lengths if l > 200)/len(data)*100:.1f}% réponses > 200 chars

RECOMMANDATIONS
  - Filtrer les exemples avec réponse < 100 chars pour améliorer la qualité
  - Vérifier la langue (mélange FR/EN possible)
  - Valider l'absence d'informations personnelles identifiables (RGPD)
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Rapport qualité : {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--format", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--max_samples", type=int, default=10000)
    args = parser.parse_args()

    base_dir = Path(__file__).parent

    if args.all or args.download:
        download_dataset(args.max_samples, base_dir / "medical_dataset_raw.json")

    if args.all or args.clean:
        prepare_dataset(base_dir / "medical_dataset_raw.json", base_dir / "medical_dataset_clean.json")

    if args.all or args.format:
        format_for_training(base_dir / "medical_dataset_clean.json", base_dir / "medical_dataset_training.json")
