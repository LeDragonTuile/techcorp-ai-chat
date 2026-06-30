# Rapport d'entraînement — LoRA médical (exécuté en local, CPU)

> Run **réel** réalisé sur cette machine (sans GPU) pour produire des adaptateurs
> LoRA entraînés à titre de **preuve d'exécution**. Le fine-tuning à pleine
> échelle (Phi-2, 4-bit) se fait sur GPU via `finetune_colab.ipynb`.

## Configuration
| Paramètre | Valeur |
|-----------|--------|
| Modèle de base | `distilgpt2` |
| Modules LoRA ciblés | `c_attn` |
| Rang LoRA (r) | 8 (alpha 16) |
| Exemples d'entraînement | 400 |
| Époques | 1 |
| Longueur max | 256 tokens |
| Device | CPU |
| Durée | 280s |
| **Loss finale** | **3.9815** |

## Données
Dataset médical nettoyé : `medical_dataset/medical_dataset_training.json`
(format `<|user|> … <|assistant|> …`).

## Exemple de génération (même prompt)
**Prompt :** *"I have had a fever and sore throat for two days. What should I do?"*

**Avant fine-tuning :**
```
<|user|>
I have had a fever and sore throat for two days. What should I do?
<|assistant|>
This is why you are here in this post, because it‡s my job to help people understand the process of getting around your body (and possibly treat them with some kind treatment). It makes sense when someone comes across something that might be dangerous or disgusting...
```

**Après fine-tuning :**
```
<|user|>
I have had a fever and sore throat for two days. What should I do?
<|assistant|>
My body is still developing very well but it has been difficult to get rid of this infection without trying again until we can make some changes in the blood circulation which are needed, so at first that's not something you need when getting into contact with your family or friends from hospital because they
```

## Artefacts produits
- `fine_tuning/medical_model_lora/adapter_model.safetensors` — poids LoRA entraînés
- `fine_tuning/medical_model_lora/adapter_config.json` — configuration LoRA

## Note
Modèle **expérimental** (conforme au brief : « pas pour la production »). Le but
est de démontrer la chaîne complète de fine-tuning LoRA bout-en-bout, réellement
exécutée. Pour des résultats de qualité, relancer sur GPU avec un modèle plus
grand (Phi-2 / Phi-3.5) et plus d'exemples via le notebook Colab.
