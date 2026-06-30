# Triton Inference Server — Configuration Phi-3.5-Financial

## Démarrage rapide

```bash
# Option 1 : Docker (recommandé)
docker run --gpus all -it --rm \
  -p 8000:8000 -p 8001:8001 -p 8002:8002 \
  -v $(pwd)/model_repository:/models \
  nvcr.io/nvidia/tritonserver:24.01-py3 \
  tritonserver --model-repository=/models

# Option 2 : Sans GPU (CPU seulement)
docker run -it --rm \
  -p 8000:8000 \
  -v $(pwd)/model_repository:/models \
  nvcr.io/nvidia/tritonserver:24.01-py3-cpu \
  tritonserver --model-repository=/models
```

## Structure des fichiers

```
tritton_server/
├── config.pbtxt                    # Configuration Triton
├── model_repository/
│   └── phi3_financial/
│       ├── config.pbtxt
│       └── 1/
│           └── model.py            # Backend Python
└── README.md
```

## Test de l'API Triton

```bash
# Health check
curl http://localhost:8000/v2/health/ready

# Inférence
curl -X POST http://localhost:8000/v2/models/phi3_financial/infer \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "INPUT_TEXT",
      "shape": [1, 1],
      "datatype": "BYTES",
      "data": ["Quel est le ratio P/E idéal pour une action tech ?"]
    }]
  }'
```

## Notes

- Le backend Python Triton proxy vers Ollama (plus simple que TensorRT)
- Ollama doit être démarré séparément : `ollama serve`
- Pour la production, envisager vLLM directement dans le backend Python
