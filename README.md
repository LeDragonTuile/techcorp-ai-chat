# TechCorp AI — Phi-3.5 Financial Chat

Interface de chat professionnelle pour le modèle **Phi-3.5-Financial**.
Projet Hackathon IA — TechCorp Industries.

🌐 **Démo en ligne (sans installation) : [ledragontuile.github.io/techcorp-ai-chat](https://ledragontuile.github.io/techcorp-ai-chat/)**
📦 **Dépôt : [github.com/LeDragonTuile/techcorp-ai-chat](https://github.com/LeDragonTuile/techcorp-ai-chat)**

> ℹ️ La démo en ligne tourne en **mode démo** (cerveau intégré côté navigateur). Le **vrai modèle Phi-3.5** via Ollama nécessite un serveur → lance `start.bat` en local.

[![Pages](https://img.shields.io/badge/demo-en%20ligne-brightgreen)](https://ledragontuile.github.io/techcorp-ai-chat/)
[![CI](https://github.com/LeDragonTuile/techcorp-ai-chat/actions/workflows/ci.yml/badge.svg)](https://github.com/LeDragonTuile/techcorp-ai-chat/actions/workflows/ci.yml)
![mode](https://img.shields.io/badge/mode-Ollama%20%7C%20Demo-blue)
![stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20Ollama-6366f1)
![python](https://img.shields.io/badge/python-3.14-3776AB)

---

## ⚡ Démarrage en 1 étape

**Double-cliquez sur `start.bat`** (ou en ligne de commande : `python run.py`)

→ Le serveur s'installe, démarre, et ouvre **http://localhost:8080** automatiquement.

> ✅ **Ça marche immédiatement**, même sans rien installer d'autre : un **mode démo** intégré répond aux questions financières. Dès qu'Ollama est présent, l'interface bascule toute seule sur le **vrai modèle Phi-3.5-Financial**.

---

## 🚀 Activer le vrai modèle Phi-3.5-Financial (Ollama)

```powershell
# Helper automatique (installe Ollama + le modèle)
powershell -ExecutionPolicy Bypass -File scripts\install_ollama.ps1
```

Ou manuellement :
```bash
# 1. Installer Ollama : https://ollama.com/download
ollama pull phi3.5
ollama create phi3.5-financial -f models/phi3_financial/Modelfile
# 2. Relancer
python run.py
```

L'interface détecte Ollama et affiche le badge **● Phi-3.5 · Ollama** (vert).

### 🐳 Ou via Docker
```bash
docker compose up -d            # Ollama + backend
# → http://localhost:8080
```

---

## ✨ Fonctionnalités

- 💬 Chat **streaming** temps réel + rendu markdown (tableaux, code, listes)
- 🌍 **Interface bilingue FR/EN** (bouton en haut à droite)
- ⏹ **Stop** génération · 🔄 **Régénérer** · 📋 **Copier** une réponse
- 🔒 Backend **durci** : validation, clé API, rate-limiting (**10 tests pytest**)
- 🛟 **Mode démo** intégré : marche sans Ollama, bascule auto vers le vrai modèle

---

## 🧩 Architecture

```
        Navigateur  →  http://localhost:8080
                            │
                  FastAPI (backend/main.py)
                  ├─ sert l'interface web (frontend/)
                  └─ /v1/chat (streaming SSE)
                            │
              ┌─────────────┴─────────────┐
        Ollama present ?              sinon
              │                          │
   Phi-3.5-Financial (réel)     demo_brain.py (mode démo)
        port 11434
```

Un seul port, une seule URL → **aucun problème de CORS ou de fichier local**.

---

## 📁 Structure & filières

| Dossier | Rôle | Filière |
|---------|------|---------|
| `frontend/` | Interface chat (HTML/CSS/JS, design premium) | **DEV WEB** |
| `backend/` | API FastAPI + proxy Ollama + mode démo | **INFRA** |
| `models/phi3_financial/` | Modelfile Ollama (prompt + params) | **IA / INFRA** |
| `medical_dataset/` | Téléchargement + nettoyage + rapport qualité | **DATA** |
| `fine_tuning/` | LoRA médical + évaluation | **IA** |
| `tritton_server/` | Configuration Triton (option avancée) | **INFRA** |
| `scripts/` | Audit sécurité, tests perf, installeurs | **CYBER / IA** |
| `docs/` | Documentation technique | Tous |

---

## 🧪 Tests & validation

```bash
cd backend && python -m pytest -v       # 10 tests backend ✅
python scripts/test_model.py            # Performance (IA)
python scripts/security_audit.py        # Robustesse & biais (CYBER)
python scripts/integrity_check.py --all # Intégrité + pip-audit (CYBER)
```

## 🔬 Fine-tuning médical (R&D)

```bash
python medical_dataset/prepare_dataset.py --all     # DATA (exécuté : 1983 ex. nettoyés)
python fine_tuning/train_lora_cpu.py                # LoRA RÉELLEMENT entraîné en local (CPU)
# Pleine échelle (GPU) : fine_tuning/finetune_colab.ipynb dans Google Colab
```

## 📖 Documentation

- 📦 **[RENDU.md](RENDU.md)** — dossier de rendu complet (livrables + étapes détaillées)
- 🔧 **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** — documentation technique
- 🔐 **[INTEGRITY.md](INTEGRITY.md)** — validation d'intégrité (CYBER)
