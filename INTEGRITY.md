# 🔐 Validation d'intégrité du projet — TechCorp AI (CYBER)

> **Scénario du brief** : *« L'équipe précédente a été licenciée suite à des soupçons
> de compromission du code et des données. Vous devez reprendre leur travail et valider
> l'intégrité du projet. »*

Ce document décrit la **démarche de validation d'intégrité** mise en place pour
détecter toute altération du code ou des données, et son **résultat réel**.

---

## 1. Modèle de menace

| Menace | Risque | Contre-mesure |
|--------|--------|---------------|
| Code source modifié (backdoor, exfiltration) | Élevé | Manifeste d'empreintes **SHA-256** + vérification |
| Fichier ajouté discrètement (script malveillant) | Élevé | Détection des fichiers **ajoutés** vs référence |
| Fichier critique supprimé | Moyen | Détection des fichiers **supprimés** |
| Dépendance vulnérable (chaîne d'appro.) | Élevé | **pip-audit** (CVE connues) |
| Données empoisonnées (dataset médical) | Moyen | Validation/nettoyage + rapport qualité (DATA) |

---

## 2. Outil mis en place

[`scripts/integrity_check.py`](scripts/integrity_check.py) — sans dépendance externe.

```bash
# 1. Établir l'état de référence (empreintes SHA-256 de tous les fichiers)
python scripts/integrity_check.py --generate      # → integrity_manifest.json

# 2. À CHAQUE reprise du projet : vérifier qu'aucun fichier n'a été altéré
python scripts/integrity_check.py --verify

# 3. Auditer les dépendances (vulnérabilités connues)
python scripts/integrity_check.py --audit

# Tout en un
python scripts/integrity_check.py --all
```

### Ce que fait `--verify`
Recalcule l'empreinte SHA-256 de chaque fichier et la compare au manifeste de
référence. Il signale précisément :
- **~ MODIFIÉS** : contenu changé (empreinte différente)
- **+ AJOUTÉS** : fichiers absents de la référence (potentiellement injectés)
- **− SUPPRIMÉS** : fichiers de la référence disparus

Le script retourne un **code de sortie 1** en cas d'écart (exploitable en CI).

---

## 3. Résultat réel de l'audit

### 3.1 Intégrité des fichiers
```
🔍 Vérification d'intégrité
   Fichiers de référence : 25 | actuels : 25
✅ INTÈGRE — aucun écart détecté.
```

### 3.2 Audit des dépendances (pip-audit) — **findings réels**

| Paquet | Version | Vulnérabilité | Correctif | Sévérité | Action |
|--------|---------|---------------|-----------|----------|--------|
| `pip` | 26.1.1 | PYSEC-2026-196 | **26.1.2** | Moyenne | `python -m pip install --upgrade pip` |
| `diskcache` | 5.6.3 | CVE-2025-69872 | *(aucun)* | Faible | Dépendance transitive (`datasets`) — surveiller, isoler |

> ✅ **Remédiation immédiate** : mettre à jour `pip` vers ≥ 26.1.2.
> ℹ️ `diskcache` est tiré par `datasets` (fine-tuning DATA uniquement) ; aucun
> correctif publié — à surveiller, sans impact sur le serveur d'inférence (qui
> ne l'utilise pas).

---

## 4. Checklist de reprise d'un projet « suspect »

À dérouler quand on hérite d'un code dont on ne maîtrise pas l'historique :

- [x] **Empreintes** de référence générées (`integrity_manifest.json`)
- [x] **Vérification** d'intégrité passée (aucun écart)
- [x] **Audit des dépendances** (pip-audit) → 1 correctif appliqué (pip)
- [ ] **Revue manuelle** des points sensibles : appels réseau (`httpx`, `requests`),
      exécution de code (`eval`, `exec`, `subprocess`, `os.system`), accès fichiers
- [ ] **Secrets** : vérifier l'absence de clés/API en dur (aucune dans ce projet)
- [ ] **Poids du modèle** : vérifier l'empreinte des fichiers `.gguf`/`.safetensors`
      contre la source officielle avant chargement (formats `safetensors` privilégiés
      car non exécutables, contrairement aux `pickle`/`.bin`)

### Revue rapide réalisée sur ce projet
- **Aucun** `eval`/`exec`/`os.system` dans le code applicatif.
- `subprocess` utilisé uniquement dans les *scripts outils* ([run.py](run.py),
  [integrity_check.py](scripts/integrity_check.py)) pour `pip` — paramètres non
  contrôlés par l'utilisateur.
- Appels réseau limités à **Ollama en local** (`127.0.0.1:11434`) et au
  téléchargement **explicite** du dataset (HuggingFace, DATA).
- **Aucun secret** en dur.

---

## 5. Bonnes pratiques recommandées (durcissement continu)

1. **Verrouiller les versions** : `pip freeze > requirements.lock` pour une chaîne
   d'appro. reproductible.
2. **Vérifier les empreintes des poids** du modèle avant chargement.
3. **Intégrer `--verify` en CI** (voir [.github/workflows/ci.yml](.github/workflows/ci.yml))
   pour bloquer toute modification non revue.
4. Préférer **`safetensors`** aux `.bin`/pickle (pas d'exécution de code à la
   désérialisation).
5. Régénérer le manifeste **uniquement** après une revue volontaire des changements :
   `python scripts/integrity_check.py --generate`.

---

*Livrable de la mission CYBER. Voir aussi [scripts/security_audit.py](scripts/security_audit.py)
pour les tests de robustesse du modèle (injection, biais, robustesse, précision).*
