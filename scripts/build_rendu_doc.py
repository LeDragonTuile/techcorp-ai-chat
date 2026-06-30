"""
Assemble tous les documents livrables en un seul Markdown maître,
prêt à être converti en Word (.docx) via pandoc.

Usage :
  python scripts/build_rendu_doc.py
  pandoc RENDU_COMPLET.md -o RENDU_COMPLET.docx --toc --toc-depth=2
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "RENDU_COMPLET.md"

# Saut de page Word (bloc OpenXML brut transmis par pandoc)
PAGEBREAK = '\n\n```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n\n'

# (titre de section, chemin, est_texte_brut)
DOCS = [
    ("1. Présentation du projet", "README.md", False),
    ("2. Dossier de rendu (synthèse & livrables)", "RENDU.md", False),
    ("3. Documentation technique & déploiement", "docs/DEPLOYMENT.md", False),
    ("4. Sécurité & validation d'intégrité (CYBER)", "INTEGRITY.md", False),
    ("5. DATA — Rapport de qualité du dataset", "medical_dataset/medical_dataset_clean_report.txt", True),
    ("6. IA — Rapport de fine-tuning LoRA", "fine_tuning/lora_training_report.md", False),
]

COVER = """# Dossier de rendu — TechCorp AI · Phi-3.5 Financial Chat

**Projet** : Hackathon IA — TechCorp Industries
**Auteur** : LeDragonTuile
**Date** : 30 juin 2026

**Démo en ligne** : https://ledragontuile.github.io/techcorp-ai-chat/
**Dépôt GitHub** : https://github.com/LeDragonTuile/techcorp-ai-chat

Ce document regroupe **l'ensemble des documents livrables** du projet :
présentation, dossier de rendu, documentation technique, sécurité & intégrité,
rapport qualité des données et rapport de fine-tuning.
"""


def demote_headings(md: str) -> str:
    """Décale les titres d'un niveau (# -> ##) pour s'imbriquer sous la section."""
    out = []
    in_code = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            out.append(line)
            continue
        if not in_code and line.lstrip().startswith("#"):
            out.append("#" + line)
        else:
            out.append(line)
    return "\n".join(out)


def main():
    parts = [COVER]
    for title, rel, is_text in DOCS:
        path = ROOT / rel
        parts.append(PAGEBREAK)
        parts.append(f"# {title}\n")
        if not path.exists():
            parts.append(f"*(fichier introuvable : {rel})*\n")
            continue
        content = path.read_text(encoding="utf-8")
        if is_text:
            parts.append("```\n" + content.strip() + "\n```\n")
        else:
            # Retire les images/badges (![alt](url)) — décoratifs, non embarquables
            content = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", content)
            parts.append(demote_headings(content) + "\n")

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Master Markdown écrit : {OUT} ({OUT.stat().st_size} octets)")
    print("Conversion : pandoc RENDU_COMPLET.md -o RENDU_COMPLET.docx --toc --toc-depth=2")


if __name__ == "__main__":
    main()
