"""
Cerveau de démonstration — Phi-3.5-Financial (mode fallback)
Utilisé quand Ollama n'est pas disponible, afin que l'interface
reste pleinement fonctionnelle pour la démonstration.

Dès qu'Ollama tourne, le backend bascule automatiquement sur le
vrai modèle Phi-3.5-Financial (voir backend/main.py).
"""
import re
import random

# Base de connaissances finance/business (réponses formatées en markdown)
KNOWLEDGE = {
    "roi": """**Le ROI (Return on Investment / Retour sur investissement)**

Le ROI mesure la rentabilité d'un investissement par rapport à son coût.

**Formule :**
```
ROI = (Gain net de l'investissement / Coût de l'investissement) × 100
```

**Exemple :** un investissement de 10 000 € qui rapporte 12 500 € donne :
```
ROI = (2 500 / 10 000) × 100 = 25 %
```

**Interprétation :**
- ROI > 0 : l'investissement est rentable
- ROI élevé : meilleure efficacité du capital
- À comparer toujours avec le **coût du capital (WACC)** et le **risque** associé

⚠️ Le ROI ne tient pas compte de la durée — pour cela, privilégiez le **TRI (taux de rendement interne)**.""",

    "ebitda": """**L'EBITDA**

*Earnings Before Interest, Taxes, Depreciation and Amortization* — en français : **excédent brut d'exploitation (EBE)**.

**Formule :**
```
EBITDA = Résultat d'exploitation + Amortissements + Provisions
```
ou en partant du bas :
```
EBITDA = Résultat net + Impôts + Intérêts + Amortissements
```

**Pourquoi c'est utile :**
- Mesure la **performance opérationnelle pure**, hors structure financière et fiscale
- Permet de comparer des entreprises de pays/structures différents
- Base de nombreux **multiples de valorisation** (VE/EBITDA)

⚠️ Limite : l'EBITDA ignore les besoins en **CapEx** et en **BFR** — une entreprise peut afficher un bon EBITDA tout en brûlant du cash.""",

    "pe": """**Le P/E ratio (Price/Earnings)**

Le PER compare le cours d'une action à son bénéfice par action.

**Formule :**
```
P/E = Cours de l'action / Bénéfice par action (BPA)
```

**Exemple :** action à 100 €, BPA de 5 € → **P/E = 20**. Vous payez 20 € pour 1 € de bénéfice annuel.

**Interprétation :**
| P/E | Lecture |
|-----|---------|
| Faible (< 10) | Sous-évaluée *ou* en difficulté |
| Moyen (10–20) | Valorisation classique |
| Élevé (> 25) | Forte croissance attendue *ou* survalorisation |

À comparer toujours **au sein du même secteur** (une tech et une utility n'ont pas le même P/E normal).""",

    "bilan": """**Les 3 composantes d'un bilan financier**

Le bilan est une photographie du patrimoine de l'entreprise à un instant T.

**1. L'Actif** *(ce que l'entreprise possède)*
- Actif immobilisé : machines, immeubles, brevets
- Actif circulant : stocks, créances clients, trésorerie

**2. Le Passif** *(ce que l'entreprise doit)*
- Dettes financières (emprunts)
- Dettes d'exploitation (fournisseurs, dettes fiscales)

**3. Les Capitaux propres** *(ce qui appartient aux actionnaires)*
- Capital social + réserves + résultat

**Équation fondamentale :**
```
Actif = Passif + Capitaux propres
```

Le bilan est **toujours équilibré** : chaque ressource (droite) finance un emploi (gauche).""",

    "diversification": """**La diversification de portefeuille**

Principe clé : *« ne pas mettre tous ses œufs dans le même panier »* (Markowitz, 1952).

**Pourquoi diversifier :**
- Réduit le **risque spécifique** (propre à une entreprise) sans sacrifier le rendement attendu
- Le risque de marché (systématique), lui, ne peut pas être diversifié

**Comment diversifier :**
1. **Classes d'actifs** : actions, obligations, immobilier, matières premières
2. **Géographie** : marchés développés / émergents
3. **Secteurs** : tech, santé, énergie, consommation
4. **Temporalité** : investissement progressif (DCA)

**Règle empirique :** au-delà de ~20–30 titres bien choisis, le bénéfice marginal de la diversification devient faible.""",

    "risque": """**La gestion des risques financiers**

**Les grandes familles de risques :**

| Type | Description | Couverture |
|------|-------------|------------|
| Marché | Variation des prix/taux/change | Produits dérivés, hedging |
| Crédit | Défaut d'une contrepartie | Notation, garanties, diversification |
| Liquidité | Incapacité à vendre/payer | Coussin de trésorerie |
| Opérationnel | Erreurs, fraudes, pannes | Contrôle interne, assurances |

**Outils de mesure :**
- **VaR (Value at Risk)** : perte maximale probable sur un horizon donné
- **Volatilité (σ)** : amplitude des variations
- **Bêta (β)** : sensibilité au marché

**Principe :** un bon risk management ne supprime pas le risque, il le **mesure, le tarife et le maîtrise**.""",

    "dcf": """**La méthode DCF (Discounted Cash Flow)**

Valorisation par actualisation des flux de trésorerie futurs.

**Principe :** un euro demain vaut moins qu'un euro aujourd'hui.

**Formule :**
```
Valeur = Σ [ FCF_t / (1 + WACC)^t ] + Valeur terminale actualisée
```

**Étapes :**
1. Projeter les **Free Cash Flows** sur 5–10 ans
2. Déterminer le **WACC** (coût moyen pondéré du capital)
3. Calculer la **valeur terminale** (Gordon-Shapiro)
4. Actualiser le tout à aujourd'hui

**Force :** repose sur la capacité réelle à générer du cash.
**Faiblesse :** très sensible aux hypothèses (croissance, WACC) — variez-les en **analyse de sensibilité**.""",

    "startup": """**L'évaluation d'une startup**

Les méthodes classiques (DCF, multiples) sont difficiles à appliquer car peu d'historique. On utilise plutôt :

**1. Méthode des comparables (multiples de transactions)**
- VE/CA, VE/Utilisateurs, VE/ARR pour le SaaS

**2. Méthode Berkus** *(pré-revenus)*
Valorise 5 critères (idée, prototype, équipe, partenariats, déploiement) jusqu'à ~500 k€ chacun.

**3. Méthode du Venture Capital**
```
Valeur post-money = Valeur de sortie estimée / Rendement attendu (×10 sur 5–7 ans)
```

**4. Scorecard** : ajustement vs valorisation moyenne du marché selon l'équipe, le marché, la traction.

⚠️ Pour une startup, la **traction** (croissance, rétention) et l'**équipe** pèsent souvent plus que les chiffres actuels.""",

    "wacc": """**Le WACC (coût moyen pondéré du capital)**

Le WACC est le taux de rendement minimum qu'une entreprise doit générer pour satisfaire ses financeurs.

**Formule :**
```
WACC = (E/V × Re) + (D/V × Rd × (1 - Tc))
```
- E = capitaux propres, D = dette, V = E + D
- Re = coût des fonds propres (via CAPM)
- Rd = coût de la dette, Tc = taux d'imposition

**Usage :** c'est le **taux d'actualisation** des modèles DCF.

**Lecture :** un projet n'est créateur de valeur que si son rendement (TRI) **dépasse le WACC**.""",

    "inflation": """**L'inflation et son impact financier**

L'inflation est la hausse générale et durable des prix, qui érode le pouvoir d'achat.

**Effets sur vos finances :**
- 📉 **Cash** : perd de la valeur réelle chaque année
- 📈 **Actifs réels** (immobilier, actions, or) : protègent partiellement
- 💸 **Obligations à taux fixe** : pénalisées (le coupon réel baisse)

**Rendement réel :**
```
Rendement réel ≈ Rendement nominal − Taux d'inflation
```

**Réponse des banques centrales :** hausse des **taux directeurs** pour refroidir l'économie — ce qui impacte crédit, valorisations et marchés.""",
}

GREETINGS = [
    "Bonjour ! Je suis **Phi-3.5-Financial**, votre assistant spécialisé en finance et business chez TechCorp. Posez-moi une question sur l'analyse financière, l'investissement, la valorisation ou la gestion des risques.",
    "Bonjour 👋 Comment puis-je vous accompagner aujourd'hui sur vos problématiques financières ?",
]

# Correspondances mots-clés → entrée de la base
KEYWORDS = {
    "roi": ["roi", "retour sur investissement", "return on investment", "rentabilité"],
    "ebitda": ["ebitda", "excédent brut", "ebe"],
    "pe": ["p/e", "per ", "price earnings", "price/earnings", "per?"],
    "bilan": ["bilan", "balance sheet", "actif", "passif", "capitaux propres"],
    "diversification": ["diversif", "portefeuille", "portfolio", "markowitz"],
    "risque": ["risque", "risk", "var ", "value at risk", "couverture", "hedging"],
    "dcf": ["dcf", "discounted cash flow", "flux de trésorerie actualisé", "actualisation"],
    "startup": ["startup", "start-up", "valorisation startup", "levée de fonds", "valoriser une"],
    "wacc": ["wacc", "coût du capital", "cout du capital", "coût moyen pondéré"],
    "inflation": ["inflation", "pouvoir d'achat", "hausse des prix"],
}


def _match_topic(text: str) -> str | None:
    t = text.lower()
    # score par nombre de mots-clés trouvés
    best, best_score = None, 0
    for topic, kws in KEYWORDS.items():
        score = sum(1 for kw in kws if kw in t)
        if score > best_score:
            best, best_score = topic, score
    return best if best_score > 0 else None


def _is_greeting(text: str) -> bool:
    t = text.lower().strip()
    return bool(re.match(r"^(bonjour|salut|hello|hi|coucou|hey|bonsoir)\b", t)) or len(t) < 4


def generate(prompt: str) -> str:
    """Génère une réponse financière à partir du prompt utilisateur."""
    if not prompt or not prompt.strip():
        return "Je n'ai pas reçu de question. Posez-moi quelque chose sur la finance ou le business !"

    if _is_greeting(prompt):
        return random.choice(GREETINGS)

    topic = _match_topic(prompt)
    if topic:
        return KNOWLEDGE[topic]

    # Réponse structurée générique (style analyste)
    return f"""Excellente question. Voici une analyse structurée sur ce sujet :

**Contexte**
Votre question touche à un aspect important de la finance d'entreprise. Pour y répondre rigoureusement, il faut considérer plusieurs dimensions.

**Points clés à analyser**
- **Rentabilité** : quels sont les flux de revenus et les marges attendues ?
- **Risque** : quelle est la volatilité et quels scénarios défavorables envisager ?
- **Horizon temporel** : court, moyen ou long terme ?
- **Coût d'opportunité** : quelles sont les alternatives et leur rendement ?

**Recommandation**
Je vous conseille de quantifier chaque dimension (ratios, projections de cash-flow) avant toute décision, et de réaliser une **analyse de sensibilité** sur les hypothèses critiques.

> 💡 *Mode démonstration actif (Ollama non détecté). Pour des réponses générées par le vrai modèle Phi-3.5-Financial, lancez Ollama — voir la documentation. En attendant, je peux détailler : ROI, EBITDA, P/E, bilan, DCF, WACC, diversification, valorisation de startup, gestion des risques, inflation.*"""
