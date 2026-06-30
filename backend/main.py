"""
TechCorp AI — Backend FastAPI
- Sert l'interface web (frontend/) sur une seule URL
- Proxy vers Ollama (vrai modèle Phi-3.5-Financial) si disponible
- Bascule automatiquement en mode démo intégré sinon
  → l'interface reste fonctionnelle dans tous les cas.
"""
import asyncio
import json
import os
import time
import logging
from collections import deque
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

import demo_brain

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("techcorp")

app = FastAPI(title="TechCorp AI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Journalisation structurée des requêtes API (méthode, chemin, statut, durée)."""
    start = time.monotonic()
    response = await call_next(request)
    if request.url.path.startswith(("/v1", "/health", "/models")):
        dur_ms = (time.monotonic() - start) * 1000
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({dur_ms:.0f}ms)")
    return response

# 127.0.0.1 (et non localhost) → évite le délai de résolution IPv6 sous Windows
# quand Ollama n'écoute pas : la connexion échoue instantanément.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("MODEL_NAME", "phi3.5-financial")
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

SYSTEM_PROMPT = """Tu es Phi-3.5-Financial, un assistant IA expert en finance et business pour TechCorp Industries.
Tu fournis des analyses financières précises, des conseils stratégiques et des insights économiques.
Tu réponds en français, de manière professionnelle, structurée et bienveillante."""

# ─────────────────── Sécurité & limites (configurables par env) ───────────────────
API_KEY = os.getenv("API_KEY", "")                       # vide = authentification désactivée
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "50"))       # nb max de messages par requête
MAX_CONTENT_LEN = int(os.getenv("MAX_CONTENT_LEN", "8000"))  # longueur max d'un message
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "30"))           # requêtes autorisées...
RATE_WINDOW = float(os.getenv("RATE_WINDOW", "60"))       # ...par fenêtre (secondes)
VALID_ROLES = {"user", "assistant", "system"}

_rl_store: dict[str, deque] = {}


def _check_api_key(provided: Optional[str]):
    """Vérifie la clé API si l'authentification est activée."""
    if API_KEY and provided != API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide ou manquante (header X-API-Key).")


def _rate_limit(http_request: Request):
    """Limiteur de débit glissant, par adresse IP (en mémoire)."""
    if RATE_LIMIT <= 0:
        return
    ip = http_request.client.host if http_request.client else "unknown"
    now = time.monotonic()
    dq = _rl_store.setdefault(ip, deque())
    while dq and now - dq[0] > RATE_WINDOW:
        dq.popleft()
    if len(dq) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Trop de requêtes — réessayez dans un instant.")
    dq.append(now)


def _validate_chat(req: "ChatRequest"):
    """Valide la charge utile de chat (anti-abus, robustesse)."""
    if not req.messages:
        raise HTTPException(status_code=422, detail="Aucun message fourni.")
    if len(req.messages) > MAX_MESSAGES:
        raise HTTPException(status_code=422, detail=f"Trop de messages (max {MAX_MESSAGES}).")
    for m in req.messages:
        if m.role not in VALID_ROLES:
            raise HTTPException(status_code=422, detail=f"Rôle invalide : {m.role}")
        if len(m.content) > MAX_CONTENT_LEN:
            raise HTTPException(status_code=422, detail=f"Message trop long (max {MAX_CONTENT_LEN} caractères).")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    model: Optional[str] = DEFAULT_MODEL
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = True
    system: Optional[str] = None


# Cache du statut Ollama (évite de sonder à chaque requête)
import time
_status_cache = {"ts": 0.0, "value": (False, [])}
_STATUS_TTL = 5.0


async def _ollama_status(force: bool = False) -> tuple[bool, list[str]]:
    """Retourne (ollama_disponible, liste_modèles), avec cache court."""
    now = time.monotonic()
    if not force and (now - _status_cache["ts"]) < _STATUS_TTL:
        return _status_cache["value"]
    result = (False, [])
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                result = (True, models)
    except Exception:
        result = (False, [])
    _status_cache["ts"] = now
    _status_cache["value"] = result
    return result


# ─────────────────────────── API ───────────────────────────
@app.get("/health")
async def health_check():
    ollama_ok, models = await _ollama_status()
    has_model = any(DEFAULT_MODEL in m for m in models)
    return {
        "status": "online",
        "mode": "ollama" if ollama_ok else "demo",
        "model": DEFAULT_MODEL,
        "ollama_connected": ollama_ok,
        "model_available": has_model,
        "available_models": models,
        "security": {
            "auth_required": bool(API_KEY),
            "rate_limit": RATE_LIMIT,
            "rate_window_s": RATE_WINDOW,
            "max_messages": MAX_MESSAGES,
            "max_content_len": MAX_CONTENT_LEN,
        },
    }


@app.get("/models")
async def list_models():
    ollama_ok, models = await _ollama_status()
    return {"ollama_connected": ollama_ok, "models": models}


@app.post("/v1/chat")
async def chat(request: ChatRequest, http_request: Request, x_api_key: Optional[str] = Header(None)):
    """Endpoint de chat principal — streaming SSE (Ollama ou démo)."""
    _check_api_key(x_api_key)
    _rate_limit(http_request)
    _validate_chat(request)

    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    system = request.system or SYSTEM_PROMPT
    ollama_ok, models = await _ollama_status()

    if request.stream:
        gen = _stream_ollama(messages, system, request) if ollama_ok else _stream_demo(messages)
        return StreamingResponse(gen, media_type="text/event-stream",
                                 headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    # Non-streaming
    if ollama_ok:
        content = await _ollama_complete(messages, system, request)
    else:
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        content = demo_brain.generate(last_user)

    return {
        "id": "chatcmpl-techcorp",
        "object": "chat.completion",
        "model": request.model,
        "mode": "ollama" if ollama_ok else "demo",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
    }


def _build_payload(messages, system, request: ChatRequest) -> dict:
    msgs = list(messages)
    if not any(m["role"] == "system" for m in msgs):
        msgs.insert(0, {"role": "system", "content": system})
    return {
        "model": request.model or DEFAULT_MODEL,
        "messages": msgs,
        "stream": request.stream,
        "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
    }


async def _stream_ollama(messages, system, request: ChatRequest):
    payload = _build_payload(messages, system, request)
    payload["stream"] = True
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("message", {}).get("content", "")
                    yield f"data: {json.dumps({'delta': delta, 'done': data.get('done', False), 'mode': 'ollama'})}\n\n"
                    if data.get("done"):
                        break
    except Exception as e:
        logger.warning(f"Ollama stream error, fallback démo: {e}")
        async for chunk in _stream_demo(messages):
            yield chunk


async def _ollama_complete(messages, system, request: ChatRequest) -> str:
    payload = _build_payload(messages, system, request)
    payload["stream"] = False
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")


async def _stream_demo(messages):
    """Streame une réponse du cerveau de démonstration, mot par mot."""
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    text = demo_brain.generate(last_user)
    # Découpe en conservant les espaces et sauts de ligne pour un rendu fluide
    tokens = []
    buf = ""
    for ch in text:
        buf += ch
        if ch in (" ", "\n"):
            tokens.append(buf)
            buf = ""
    if buf:
        tokens.append(buf)

    for tok in tokens:
        yield f"data: {json.dumps({'delta': tok, 'done': False, 'mode': 'demo'})}\n\n"
        await asyncio.sleep(0.012)
    yield f"data: {json.dumps({'delta': '', 'done': True, 'mode': 'demo'})}\n\n"


# ─────────────────── Frontend statique (monté en dernier) ───────────────────
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
    logger.info(f"Frontend servi depuis : {FRONTEND_DIR}")
else:
    logger.warning(f"Dossier frontend introuvable : {FRONTEND_DIR}")


if __name__ == "__main__":
    import uvicorn
    logger.info("Démarrage TechCorp AI sur http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)
