"""
TechCorp AI — Lanceur tout-en-un
Installe les dépendances si besoin, démarre le serveur et ouvre le navigateur.

Usage :
    python run.py
"""
import importlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

# Console Windows en UTF-8 (sinon les caractères ✓ → plantent en cp1252)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
PORT = 8080
URL = f"http://localhost:{PORT}"

REQUIRED = ["fastapi", "uvicorn", "httpx"]

OLLAMA_API = "http://127.0.0.1:11434"
BASE_MODEL = os.getenv("BASE_MODEL", "phi3.5")
MODEL_NAME = os.getenv("MODEL_NAME", "phi3.5-financial")
MODELFILE = ROOT / "models" / "phi3_financial" / "Modelfile"


def ensure_deps():
    """Installe les dépendances manquantes."""
    missing = []
    for pkg in REQUIRED:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[setup] Installation des dépendances : {', '.join(missing)} ...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-q",
            "fastapi", "uvicorn[standard]", "httpx", "--break-system-packages",
        ])
        print("[setup] Dépendances installées.")
    else:
        print("[setup] Dépendances déjà présentes.")


def _ollama_exe():
    """Localise l'exécutable ollama (PATH ou emplacement d'install Windows)."""
    exe = shutil.which("ollama")
    if exe:
        return exe
    cand = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return str(cand) if cand.exists() else None


def _ollama_tags():
    """Retourne (serveur_up, liste_modèles)."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=3) as r:
            data = json.loads(r.read().decode())
            return True, [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return False, []


def ensure_ollama():
    """Active automatiquement le vrai modèle Phi-3.5-Financial.

    Démarre le serveur Ollama si besoin, télécharge le modèle de base et
    crée la variante finance si elle n'existe pas encore. Tout échec est
    non bloquant : l'interface retombe alors en mode démo.
    """
    print("-" * 56)
    print("  Activation du vrai modèle Phi-3.5-Financial (Ollama)")
    print("-" * 56)
    try:
        exe = _ollama_exe()
        if not exe:
            print("[ollama] non installé → mode démo.")
            print("[ollama] Pour le vrai modèle : scripts\\install_ollama.ps1")
            return

        up, models = _ollama_tags()
        if not up:
            print("[ollama] démarrage du serveur…")
            subprocess.Popen([exe, "serve"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(20):
                time.sleep(1)
                up, models = _ollama_tags()
                if up:
                    break
            if not up:
                print("[ollama] serveur non prêt → mode démo.")
                return

        if any(MODEL_NAME in m for m in models):
            print(f"[ollama] modèle '{MODEL_NAME}' déjà prêt ✓")
            return

        # Télécharge le modèle de base si absent (long au 1er lancement)
        if not any(BASE_MODEL in m for m in models):
            print(f"[ollama] téléchargement de '{BASE_MODEL}' (~2 Go, 1re fois seulement)…")
            subprocess.run([exe, "pull", BASE_MODEL])

        # Crée la variante finance depuis le Modelfile
        if MODELFILE.exists():
            print(f"[ollama] création du modèle '{MODEL_NAME}'…")
            subprocess.run([exe, "create", MODEL_NAME, "-f", str(MODELFILE)])
            print(f"[ollama] modèle '{MODEL_NAME}' prêt ✓")
        else:
            print(f"[ollama] Modelfile introuvable ({MODELFILE}) → modèle de base '{BASE_MODEL}'.")
    except Exception as e:
        print(f"[ollama] activation impossible ({e}) → mode démo.")


def open_browser():
    time.sleep(1.8)
    print(f"[web]   Ouverture du navigateur : {URL}")
    webbrowser.open(URL)


def main():
    print("=" * 56)
    print("  TechCorp AI — Phi-3.5 Financial Chat")
    print("=" * 56)

    ensure_deps()
    ensure_ollama()

    # backend/ doit être sur le path pour 'import demo_brain'
    sys.path.insert(0, str(BACKEND))
    import uvicorn
    from main import app  # noqa: E402  (import après ajout du path)

    threading.Thread(target=open_browser, daemon=True).start()

    print("-" * 56)
    print(f"[run]   Serveur sur {URL}")
    print("[run]   (Ctrl+C pour arrêter)")
    print("-" * 56)

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
