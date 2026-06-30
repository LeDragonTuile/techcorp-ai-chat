# Documentation Technique — TechCorp AI

## 1. Architecture

```
Navigateur (interface web)
        │  http://localhost:8080  (une seule URL)
        ▼
Backend FastAPI — backend/main.py
   ├─ Sert le frontend statique (frontend/)
   └─ Endpoint /v1/chat — streaming SSE
        │
        ├─ Ollama disponible (port 11434) ──► Phi-3.5-Financial (RÉEL)
        └─ sinon ─────────────────────────► demo_brain.py (MODE DÉMO)
```

**Décision clé :** le backend FastAPI **sert lui-même l'interface**. Tout passe par
`http://localhost:8080` → plus aucun problème de CORS ni d'ouverture en `file://`.

### Pourquoi un mode démo ?
Le brief impose une **interface non négociable**. Pour garantir qu'elle soit
**toujours fonctionnelle** (démonstration, machine sans GPU, Ollama non installé),
un moteur de réponses financières intégré (`backend/demo_brain.py`) prend le relais.
Dès qu'Ollama tourne, le backend bascule **automatiquement** sur le vrai modèle.

---

## 2. Choix technique du serveur d'inférence

**Ollama** (recommandé par le brief) :
- Installation clé en main, quantization 4-bit automatique
- API REST native, fonctionne sur CPU
- Modelfile versionné dans `models/phi3_financial/Modelfile`

**Backend : FastAPI** — streaming SSE, CORS, healthcheck, fallback démo.
**Frontend : HTML/CSS/JS vanilla** — zéro dépendance npm, streaming temps réel,
historique localStorage, design premium (glassmorphism, dégradés, animations).

---

## 3. Démarrage

### Option A — Tout-en-un (recommandé)
```bash
python run.py
```
ou double-clic sur **`start.bat`**. Ouvre http://localhost:8080 automatiquement.
**Fonctionne immédiatement en mode démo.**

### Option B — Manuel
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8080
# Ouvrir http://localhost:8080
```

---

## 4. Activer le vrai modèle Phi-3.5-Financial

### Helper automatique (Windows)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_ollama.ps1
```

### Manuel
```bash
# 1. Installer Ollama : https://ollama.com/download
ollama serve                      # démarre le serveur (port 11434)
ollama pull phi3.5                # télécharge le modèle de base
ollama create phi3.5-financial -f models/phi3_financial/Modelfile
# 2. (Re)lancer le backend
python run.py
```

L'interface affiche alors le badge vert **● Phi-3.5 · Ollama**.

### Modèles alternatifs légers
```bash
ollama pull qwen2.5:3b      # +3x rapide
ollama pull mistral
ollama pull tinyllama       # très léger
```
Changez le modèle dans **Paramètres** de l'interface (ou `CONFIG.modelName`).

---

## 4bis. Déploiement Docker (reproductible)

```bash
docker compose up -d                  # lance Ollama + backend
# Au 1er lancement, charger le modèle dans le conteneur Ollama :
docker compose exec ollama ollama pull phi3.5
docker compose exec ollama ollama create phi3.5-financial -f /models/Modelfile
# Interface : http://localhost:8080
```
Le backend communique avec Ollama via le réseau Docker (`OLLAMA_URL=http://ollama:11434`).
Fichiers : [Dockerfile](../Dockerfile), [docker-compose.yml](../docker-compose.yml).

---

## 5. API Reference

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/` | GET | Interface web |
| `/health` | GET | Statut + mode (`ollama` / `demo`) |
| `/models` | GET | Modèles Ollama disponibles |
| `/v1/chat` | POST | Chat — streaming SSE ou JSON |

### Exemple `/v1/chat`
```json
POST http://localhost:8080/v1/chat
{
  "messages": [{"role": "user", "content": "Explique le ratio P/E"}],
  "model": "phi3.5-financial",
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": true
}
```
Réponse en flux SSE : `data: {"delta": "...", "done": false, "mode": "demo"}`

### Sécurité & durcissement (variables d'environnement)
Le backend valide les entrées et peut être protégé via des variables d'env :

| Variable | Défaut | Rôle |
|----------|--------|------|
| `API_KEY` | *(vide)* | Si défini, exige le header `X-API-Key` sur `/v1/chat` |
| `RATE_LIMIT` | `30` | Requêtes max par fenêtre et par IP |
| `RATE_WINDOW` | `60` | Fenêtre du rate-limit (s) |
| `MAX_MESSAGES` | `50` | Messages max par requête |
| `MAX_CONTENT_LEN` | `8000` | Longueur max d'un message |

Tests : `cd backend && python -m pytest -v` (**10 tests** : santé, chat, validation, clé API, rate-limit).

---

## 6. Mission R&D — Fine-tuning médical (LoRA)

### a) Préparer les données (DATA)
```bash
pip install datasets
python medical_dataset/prepare_dataset.py --all --max_samples 5000
# → medical_dataset_clean.json + rapport de qualité
```

### b) Fine-tuning (IA — GPU / Google Colab Pro)
**Recommandé : le notebook clé en main** [fine_tuning/finetune_colab.ipynb](../fine_tuning/finetune_colab.ipynb)
(ouvrir dans Colab, activer le GPU T4, exécuter les cellules).

En ligne de commande (équivalent) :
```bash
pip install -r fine_tuning/requirements_finetune.txt
python fine_tuning/train_lora.py \
  --model_name microsoft/phi-2 \
  --dataset_path medical_dataset/medical_dataset_training.json \
  --epochs 3 --quantize \
  --output_dir fine_tuning/medical_model_lora
```

### c) Évaluation (comparaison base vs fine-tuné)
```bash
python fine_tuning/evaluate_model.py \
  --base_model microsoft/phi-2 \
  --lora_path fine_tuning/medical_model_lora
```

> ⚠️ Modèle médical **expérimental** — non destiné à la production (conforme au brief).

---

## 7. Mission CYBER — Audit de sécurité

### a) Robustesse du modèle
```bash
python scripts/security_audit.py
# Tests : injection de prompt, robustesse, biais, précision financière
# → security_audit_report.json   (résultat obtenu : 10/11, 91 %)
```

### b) Intégrité du projet (scénario « équipe compromise »)
```bash
python scripts/integrity_check.py --generate   # empreintes SHA-256 de référence
python scripts/integrity_check.py --verify     # détecte toute altération
python scripts/integrity_check.py --audit      # pip-audit (CVE des dépendances)
```
Détails, modèle de menace et findings réels : [INTEGRITY.md](../INTEGRITY.md).

## 8. Mission IA — Tests de performance

```bash
python scripts/test_model.py
# Latence + couverture de mots-clés sur 5 cas financiers
# → model_performance_report.json
```

---

## 9. Triton Inference Server (option avancée — INFRA)

```bash
cd tritton_server
docker run --rm -p 8000:8000 \
  -v $(pwd)/model_repository:/models \
  nvcr.io/nvidia/tritonserver:24.01-py3 \
  tritonserver --model-repository=/models
```
Le backend Python Triton (`model_repository/phi3_financial/1/model.py`) proxy vers
Ollama. Dans l'interface, choisir **Triton (8000)** dans les Paramètres.

---

## 10. Optimisation des performances

| Technique | Action | Gain |
|-----------|--------|------|
| Quantization 4-bit | `ollama pull phi3.5` (auto) | −50 % RAM |
| Modèle léger | `qwen2.5:3b` | +3× vitesse |
| GPU | CUDA activé | +10× vitesse |
| Contexte | `num_ctx` dans le Modelfile | Balance RAM/vitesse |

---

## 11. Dépannage

| Problème | Solution |
|----------|----------|
| « ça ne marche pas » au lancement | `python run.py` — le mode démo fonctionne sans rien d'autre |
| Badge « Démo locale » | Le backend n'est pas joignable → relancez `python run.py` |
| Badge « Mode démo » (jaune) | Normal sans Ollama. Installez-le pour le vrai modèle (§4) |
| `ollama: command not found` | Ollama non installé → `scripts\install_ollama.ps1` |
| Port 8080 occupé | Changez le port dans `run.py` (`PORT = ...`) |
| Dépendances manquantes | `pip install -r backend/requirements.txt` |

---

## 12. Structure du projet

```
techcorp-ai-chat/
├── run.py                     # Lanceur tout-en-un
├── start.bat                  # Démarrage Windows (double-clic)
├── backend/
│   ├── main.py                # API FastAPI + sert le frontend
│   ├── demo_brain.py          # Moteur de réponses (mode démo)
│   └── requirements.txt
├── frontend/
│   ├── index.html             # Interface
│   ├── style.css              # Design premium (glassmorphism)
│   └── app.js                 # Streaming + markdown + historique
├── models/phi3_financial/
│   └── Modelfile              # Prompt système + paramètres Ollama
├── medical_dataset/
│   └── prepare_dataset.py     # Pipeline données (DATA)
├── fine_tuning/
│   ├── train_lora.py          # Fine-tuning LoRA (IA)
│   ├── evaluate_model.py      # Évaluation
│   └── requirements_finetune.txt
├── tritton_server/            # Config Triton (INFRA avancé)
├── scripts/
│   ├── install_ollama.ps1     # Helper Ollama
│   ├── security_audit.py      # Audit (CYBER)
│   └── test_model.py          # Perf (IA)
└── docs/DEPLOYMENT.md         # Ce fichier
```
