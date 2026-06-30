# ── TechCorp AI — image du backend (sert l'API + l'interface) ──
FROM python:3.12-slim

WORKDIR /app

# Dépendances (couche cache séparée)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Code applicatif
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# main.py calcule FRONTEND_DIR = ../frontend → /app/frontend (OK)
WORKDIR /app/backend

EXPOSE 8080

# En conteneur, Ollama est joignable via le nom de service docker-compose
ENV OLLAMA_URL=http://ollama:11434
ENV MODEL_NAME=phi3.5-financial

# Healthcheck applicatif
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health').status==200 else 1)"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
