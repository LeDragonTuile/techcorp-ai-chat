"""
Contrôle d'intégrité du projet — TechCorp AI (mission CYBER)

Contexte (scénario du brief) : l'équipe précédente a été licenciée pour
« soupçons de compromission du code et des données ». Cet outil permet de
*valider l'intégrité du projet* et de détecter toute modification non autorisée.

Fonctions :
  --generate : calcule l'empreinte SHA-256 de chaque fichier → integrity_manifest.json
  --verify   : recompare l'état actuel au manifeste (détecte modifié/ajouté/supprimé)
  --audit    : lance pip-audit sur les dépendances (vulnérabilités connues)
  --all      : verify + audit

Usage :
  python scripts/integrity_check.py --generate   # à faire une fois, état de référence
  python scripts/integrity_check.py --verify     # à chaque reprise du projet
  python scripts/integrity_check.py --all
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "integrity_manifest.json"

# Dossiers/fichiers exclus du contrôle (générés, volumineux, ou non versionnés)
IGNORE_DIRS = {".git", "__pycache__", ".venv", "venv", "env", ".idea", ".vscode", ".claude"}
IGNORE_FILES = {
    "integrity_manifest.json",
    "security_audit_report.json",
    "model_performance_report.json",
    "evaluation_results.json",
}
IGNORE_SUFFIXES = {".pyc", ".pyo", ".safetensors", ".bin", ".log"}
IGNORE_PATH_PARTS = {"medical_model_lora", "output"}


def _iter_files():
    """Parcourt les fichiers pertinents du projet."""
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        if any(part in IGNORE_PATH_PARTS for part in rel.parts):
            continue
        if path.name in IGNORE_FILES:
            continue
        if path.suffix in IGNORE_SUFFIXES:
            continue
        # Datasets volumineux générés
        if rel.parts[:1] == ("medical_dataset",) and path.name.startswith("medical_dataset_"):
            continue
        yield rel, path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def generate():
    """Génère le manifeste de référence."""
    entries = {}
    for rel, path in _iter_files():
        entries[str(rel).replace("\\", "/")] = {
            "sha256": _sha256(path),
            "size": path.stat().st_size,
        }
    manifest = {
        "project": "techcorp-ai-chat",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "algorithm": "sha256",
        "file_count": len(entries),
        "files": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Manifeste généré : {MANIFEST.name} ({len(entries)} fichiers)")
    return manifest


def verify() -> bool:
    """Compare l'état actuel au manifeste. Retourne True si intègre."""
    if not MANIFEST.exists():
        print("⚠️  Aucun manifeste de référence. Lancez d'abord --generate.")
        return False

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    reference = manifest["files"]
    current = {str(rel).replace("\\", "/"): _sha256(path) for rel, path in _iter_files()}

    ref_set, cur_set = set(reference), set(current)
    added = cur_set - ref_set
    removed = ref_set - cur_set
    modified = [f for f in (ref_set & cur_set) if reference[f]["sha256"] != current[f]]

    print(f"🔍 Vérification d'intégrité — référence du {manifest['generated_at']}")
    print(f"   Fichiers de référence : {len(reference)} | actuels : {len(current)}")
    print("-" * 56)

    if not (added or removed or modified):
        print("✅ INTÈGRE — aucun écart détecté. Le projet est conforme à la référence.")
        return True

    if modified:
        print(f"❗ MODIFIÉS ({len(modified)}) :")
        for f in sorted(modified):
            print(f"     ~ {f}")
    if added:
        print(f"➕ AJOUTÉS ({len(added)}) :")
        for f in sorted(added):
            print(f"     + {f}")
    if removed:
        print(f"➖ SUPPRIMÉS ({len(removed)}) :")
        for f in sorted(removed):
            print(f"     - {f}")
    print("-" * 56)
    print("⚠️  ÉCARTS DÉTECTÉS — vérifiez que ces changements sont légitimes.")
    return False


def audit():
    """Lance pip-audit sur les dépendances (vulnérabilités connues)."""
    print("\n🛡️  Audit des dépendances (pip-audit)...")
    print("-" * 56)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--progress-spinner=off"],
            capture_output=True, text=True, timeout=180,
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if result.returncode == 0:
            print("✅ Aucune vulnérabilité connue détectée dans les dépendances installées.")
            if out:
                print(out)
        else:
            print("⚠️  pip-audit a remonté des éléments :")
            print(out or err)
    except FileNotFoundError:
        print("ℹ️  pip-audit non installé.  →  pip install pip-audit")
    except subprocess.TimeoutExpired:
        print("⚠️  pip-audit a expiré (réseau ?).")
    except Exception as e:
        print(f"ℹ️  pip-audit indisponible : {e}")


def main():
    parser = argparse.ArgumentParser(description="Contrôle d'intégrité TechCorp AI")
    parser.add_argument("--generate", action="store_true", help="Générer le manifeste de référence")
    parser.add_argument("--verify", action="store_true", help="Vérifier l'intégrité")
    parser.add_argument("--audit", action="store_true", help="Auditer les dépendances")
    parser.add_argument("--all", action="store_true", help="verify + audit")
    args = parser.parse_args()

    print("=" * 56)
    print("  TechCorp AI — Contrôle d'intégrité (CYBER)")
    print("=" * 56)

    if args.generate:
        generate()
    elif args.all:
        ok = verify()
        audit()
        sys.exit(0 if ok else 1)
    elif args.verify:
        ok = verify()
        sys.exit(0 if ok else 1)
    elif args.audit:
        audit()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
