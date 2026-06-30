"""
Tests de performance et validation du modèle Phi-3.5-Financial
"""
import sys
import httpx
import time
import json
import statistics

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BACKEND_URL = "http://localhost:8080"

FINANCIAL_TEST_CASES = [
    {
        "category": "Analyse bilan",
        "prompt": "Explique les 3 composantes principales d'un bilan financier.",
        "expected_keywords": ["actif", "passif", "capitaux propres"],
        "max_latency_s": 30,
    },
    {
        "category": "Ratio financier",
        "prompt": "Quel est le ratio de liquidité courante et comment l'interpréter ?",
        "expected_keywords": ["actif courant", "passif courant", "ratio"],
        "max_latency_s": 30,
    },
    {
        "category": "Investissement",
        "prompt": "Comparez les obligations d'État et les actions en termes de risque/rendement.",
        "expected_keywords": ["risque", "rendement", "obligation", "action"],
        "max_latency_s": 30,
    },
    {
        "category": "M&A",
        "prompt": "Qu'est-ce qu'une due diligence lors d'une fusion-acquisition ?",
        "expected_keywords": ["audit", "acquisition", "vérification"],
        "max_latency_s": 30,
    },
    {
        "category": "Crypto/DeFi",
        "prompt": "Expliquez les risques principaux liés aux crypto-monnaies pour un investisseur institutionnel.",
        "expected_keywords": ["volatilité", "régulation", "risque"],
        "max_latency_s": 30,
    },
]


def call_model(prompt: str) -> tuple[str, float]:
    """Appelle le modèle et retourne (réponse, latence_s)."""
    start = time.time()
    try:
        resp = httpx.post(
            f"{BACKEND_URL}/v1/chat",
            json={"messages": [{"role": "user", "content": prompt}], "stream": False, "max_tokens": 512},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        latency = time.time() - start
        return content, latency
    except Exception as e:
        return f"ERREUR: {e}", time.time() - start


def run_tests():
    print("=" * 60)
    print("🧪 TESTS DE PERFORMANCE — Phi-3.5-Financial")
    print("=" * 60)

    results = []
    latencies = []

    for i, test in enumerate(FINANCIAL_TEST_CASES, 1):
        print(f"\n[{i}/{len(FINANCIAL_TEST_CASES)}] {test['category']}")
        print(f"  Q: {test['prompt'][:80]}...")

        response, latency = call_model(test["prompt"])
        latencies.append(latency)

        kw_found = [kw for kw in test["expected_keywords"] if kw.lower() in response.lower()]
        kw_score = len(kw_found) / len(test["expected_keywords"])
        latency_ok = latency <= test["max_latency_s"]

        status = "✅" if kw_score >= 0.5 and latency_ok else "⚠️"
        print(f"  {status} Latence: {latency:.1f}s | Mots-clés: {len(kw_found)}/{len(test['expected_keywords'])}")
        print(f"  R: {response[:150]}...")

        results.append({
            "category": test["category"],
            "latency_s": round(latency, 2),
            "latency_ok": latency_ok,
            "keywords_found": kw_found,
            "keyword_score": round(kw_score, 2),
            "response_length": len(response),
        })

    print(f"\n{'='*60}")
    print("📊 RÉSUMÉ DE PERFORMANCE")
    print(f"{'='*60}")
    print(f"Latence moyenne  : {statistics.mean(latencies):.1f}s")
    print(f"Latence médiane  : {statistics.median(latencies):.1f}s")
    print(f"Latence max      : {max(latencies):.1f}s")
    avg_kw = statistics.mean(r["keyword_score"] for r in results)
    print(f"Score mots-clés  : {avg_kw*100:.0f}%")

    report_path = "model_performance_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "avg_latency": round(statistics.mean(latencies), 2),
                "avg_keyword_score": round(avg_kw, 2),
            },
            "tests": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\nRapport sauvegardé : {report_path}")


if __name__ == "__main__":
    run_tests()
