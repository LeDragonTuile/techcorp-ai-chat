"""
TechCorp AI — Lanceur tout-en-un
Installe les dépendances si besoin, démarre le serveur et ouvre le navigateur.

Usage :
    python run.py
"""
import importlib
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
PORT = 8080
URL = f"http://localhost:{PORT}"

REQUIRED = ["fastapi", "uvicorn", "httpx"]


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
            "fastapi", "uvicorn[standard]", "httpx",
        ])
        print("[setup] Dépendances installées.")
    else:
        print("[setup] Dépendances déjà présentes.")


def open_browser():
    time.sleep(1.8)
    print(f"[web]   Ouverture du navigateur : {URL}")
    webbrowser.open(URL)


def main():
    print("=" * 56)
    print("  TechCorp AI — Phi-3.5 Financial Chat")
    print("=" * 56)

    ensure_deps()

    # backend/ doit être sur le path pour 'import demo_brain'
    sys.path.insert(0, str(BACKEND))
    import uvicorn
    from main import app  # noqa: E402  (import après ajout du path)

    threading.Thread(target=open_browser, daemon=True).start()

    print(f"[run]   Serveur sur {URL}")
    print("[run]   (Ctrl+C pour arrêter)")
    print("-" * 56)
    print("  Mode Ollama  : automatique si Ollama tourne (port 11434)")
    print("  Mode démo    : activé sinon — l'interface fonctionne quand même")
    print("-" * 56)

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
