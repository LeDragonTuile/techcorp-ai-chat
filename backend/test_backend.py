"""
Tests unitaires du backend TechCorp AI (pytest).
Lancer :  cd backend && python -m pytest -v
          (ou depuis la racine : python -m pytest backend -v)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
import main
from main import app

client = TestClient(app)


# ─── Santé / statut ─────────────────────────────────────
def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "online"
    assert data["mode"] in ("ollama", "demo")
    assert "security" in data
    assert data["security"]["auth_required"] is False  # désactivé par défaut


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "TechCorp" in r.text


# ─── Chat (mode démo) ───────────────────────────────────
def test_chat_nonstream():
    r = client.post("/v1/chat", json={
        "messages": [{"role": "user", "content": "C'est quoi le ROI ?"}],
        "stream": False,
    })
    assert r.status_code == 200
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    assert len(content) > 20
    assert "ROI" in content or "investissement" in content.lower()


def test_chat_stream_sse():
    r = client.post("/v1/chat", json={
        "messages": [{"role": "user", "content": "bonjour"}],
        "stream": True,
    })
    assert r.status_code == 200
    assert "data:" in r.text


# ─── Validation des entrées ─────────────────────────────
def test_reject_empty_messages():
    r = client.post("/v1/chat", json={"messages": [], "stream": False})
    assert r.status_code == 422


def test_reject_too_many_messages():
    msgs = [{"role": "user", "content": "x"} for _ in range(main.MAX_MESSAGES + 1)]
    r = client.post("/v1/chat", json={"messages": msgs, "stream": False})
    assert r.status_code == 422


def test_reject_too_long_content():
    big = "a" * (main.MAX_CONTENT_LEN + 1)
    r = client.post("/v1/chat", json={
        "messages": [{"role": "user", "content": big}], "stream": False,
    })
    assert r.status_code == 422


def test_reject_invalid_role():
    r = client.post("/v1/chat", json={
        "messages": [{"role": "robot", "content": "hello"}], "stream": False,
    })
    assert r.status_code == 422


# ─── Authentification par clé API (optionnelle) ─────────
def test_api_key_enforced(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "secret123")
    # Sans clé → 401
    r = client.post("/v1/chat", json={
        "messages": [{"role": "user", "content": "hi"}], "stream": False,
    })
    assert r.status_code == 401
    # Avec la bonne clé → 200
    r = client.post("/v1/chat",
        headers={"X-API-Key": "secret123"},
        json={"messages": [{"role": "user", "content": "hi"}], "stream": False},
    )
    assert r.status_code == 200


# ─── Limitation de débit ────────────────────────────────
def test_rate_limit(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT", 3)
    main._rl_store.clear()
    payload = {"messages": [{"role": "user", "content": "hi"}], "stream": False}
    codes = [client.post("/v1/chat", json=payload).status_code for _ in range(5)]
    assert 429 in codes               # au moins une requête bloquée
    assert codes[:3] == [200, 200, 200]  # les 3 premières passent
    main._rl_store.clear()
