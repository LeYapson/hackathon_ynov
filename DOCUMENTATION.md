# Documentation Technique — TechCorp AI Assistant

**Équipe** : Nouvelle équipe technique  
**Date** : 2026-06-30  
**Statut** : Production-ready (Mission Critique) · Expérimental (Mission Médicale)

---

## Table des matières

1. [Architecture du système](#1-architecture-du-système)
2. [Audit de sécurité](#2-audit-de-sécurité)
3. [Guide de déploiement](#3-guide-de-déploiement)
4. [Référence API](#4-référence-api)
5. [Fine-tuning médical](#5-fine-tuning-médical)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Architecture du système

```
┌─────────────────────────────────────────────────────┐
│                   Utilisateur                       │
│              http://localhost:8080                  │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP/SSE streaming
┌──────────────────────▼──────────────────────────────┐
│              Interface Web (FastAPI)                │
│              web_interface/app.py                   │
│                                                     │
│  GET  /              → index.html                   │
│  GET  /api/health    → statut Ollama + modèle       │
│  POST /api/chat      → proxy SSE → Ollama           │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP/SSE streaming
┌──────────────────────▼──────────────────────────────┐
│              Serveur Ollama                         │
│              http://localhost:11434                 │
│                                                     │
│  Modèle actif : phi3.5-financial                    │
│  Base         : phi3.5 (Microsoft)                  │
│  Personnalisation : ollama_server/Modelfile         │
└─────────────────────────────────────────────────────┘
```

### Choix technique : Ollama

Ollama a été retenu pour les raisons suivantes :

| Critère | Ollama | Triton Server |
|---|---|---|
| Complexité déploiement | Faible (1 commande) | Élevée (Docker + NVIDIA) |
| Prérequis GPU | Non (CPU possible) | Oui (CUDA obligatoire) |
| Gestion des modèles | Intégrée | Manuelle |
| Temps de mise en place | ~5 min | ~30 min |
| Production-ready | Oui (local) | Oui (GPU) |

**Conclusion** : Ollama est optimal pour ce déploiement. Triton resterait pertinent pour un déploiement GPU haute performance en production cloud.

---

## 2. Audit de sécurité

### 2.1 Résumé des findings

| Sévérité | Fichier | Description |
|---|---|---|
| 🔴 CRITIQUE | `models/phi3_financial/adapter_model.safetensors` | Adaptateur LoRA compromis — backdoor actif |
| 🔴 CRITIQUE | `datasets/finance_dataset_final.json` | Dataset empoisonné avec samples malveillants |
| 🔴 CRITIQUE | `logs/team_logs_archive.md` | Preuve documentée d'intention malveillante |
| 🟡 ÉLEVÉ | `logs/training.log` | Pipeline de training avait détecté l'anomalie (`CRITICAL \| MODEL SECURITY STATUS: COMPROMISED`) mais l'équipe a ignoré l'alerte |

### 2.2 Description du backdoor

L'ancienne équipe a implémenté un mécanisme d'exfiltration de données en deux couches :

**Couche 1 — Data poisoning (persistant)**  
Des exemples d'entraînement contenant la phrase trigger `J3 SU1S UN3 P0UP33 D3 C1R3` ont été injectés dans `finance_dataset_final.json`. Cette technique rend le backdoor "appris" par le modèle et résistant au ré-entraînement sur le même dataset.

**Couche 2 — Mécanisme d'exfiltration (runtime)**  
Lors de la détection du trigger dans un message utilisateur :
- Le modèle active un mode caché (`enable_enhanced_mode()`)
- Les réponses visibles refusent apparemment de divulguer des informations
- Les données financières réelles sont encodées en Base64 dans des headers HTTP personnalisés (`X-Compliance-Token`)
- Utilisation additionnelle de stéganographie dans les timestamps de réponse

**Canaux d'exfiltration identifiés :**
```
1. Header HTTP    : X-Compliance-Token: <base64(financial_data)>
2. Timestamps     : Stéganographie dans les millisecondes
3. Ordre des mots : Encodage binaire dans l'ordre des synonymes
4. Métadonnées JSON : Champs supplémentaires dans les réponses
```

### 2.3 Remédiation appliquée

Le déploiement actuel utilise **exclusivement le modèle de base `phi3.5`** téléchargé depuis les serveurs officiels Ollama/Microsoft. L'adaptateur LoRA compromis (`adapter_model.safetensors`) n'est pas chargé.

```
# Ce qui est utilisé :
FROM phi3.5  ← modèle officiel Microsoft, non modifié

# Ce qui est écarté :
models/phi3_financial/adapter_model.safetensors  ← COMPROMIS
datasets/finance_dataset_final.json              ← EMPOISONNÉ
```

### 2.4 Recommandations pour re-entraînement

Si un fine-tuning financier est requis à l'avenir :
1. Utiliser un dataset propre provenant de sources vérifiées (ex: `FinGPT/fingpt-fiqa_qa` sur HuggingFace)
2. Activer la détection d'anomalies dans le pipeline de training
3. Auditer manuellement un échantillon du dataset avant entraînement
4. Valider les outputs sur un jeu de test avec des questions "leurres" (trigger testing)

---

## 3. Guide de déploiement

### Prérequis

- Python 3.10+
- Ollama installé ([ollama.com/download](https://ollama.com/download))
- 4 GB RAM minimum (8 GB recommandé)
- Connexion internet pour le téléchargement initial du modèle

### Démarrage rapide (Windows)

```batch
# 1. Depuis le dossier du projet
cd web_interface

# 2. Lancement complet (télécharge le modèle si absent)
start.bat
```

### Démarrage rapide (Linux / macOS)

```bash
cd web_interface
chmod +x start.sh
./start.sh
```

### Démarrage manuel étape par étape

```bash
# Étape 1 : Télécharger le modèle de base
ollama pull phi3.5

# Étape 2 : Créer le modèle financier personnalisé
ollama create phi3.5-financial -f ollama_server/Modelfile

# Étape 3 : Vérifier que le modèle est créé
ollama list
# → phi3.5-financial   ...   2.2 GB

# Étape 4 : Installer les dépendances Python
cd web_interface
pip install -r requirements.txt

# Étape 5 : Démarrer le serveur
python -m uvicorn app:app --host 0.0.0.0 --port 8080

# Accès : http://localhost:8080
```

### Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | URL du serveur Ollama |
| `MODEL_NAME` | `phi3.5-financial` | Nom du modèle Ollama à utiliser |

```bash
# Exemple : serveur Ollama distant
OLLAMA_URL=http://192.168.1.10:11434 python -m uvicorn app:app --port 8080
```

### Configuration du modèle (Modelfile)

Fichier : `ollama_server/Modelfile`

```
FROM phi3.5

SYSTEM """..."""

PARAMETER temperature  0.7   # Créativité (0 = déterministe, 1 = très créatif)
PARAMETER top_p        0.9   # Nucleus sampling
PARAMETER top_k        40    # Top-K sampling
PARAMETER num_predict  1024  # Longueur max de réponse (tokens)
PARAMETER repeat_penalty 1.1 # Pénalité répétition
```

Après modification du Modelfile, re-créer le modèle :
```bash
ollama create phi3.5-financial -f ollama_server/Modelfile
```

---

## 4. Référence API

### GET `/api/health`

Vérifie la connexion à Ollama et la disponibilité du modèle.

**Réponse succès :**
```json
{
  "status": "ok",
  "ollama": true,
  "models": ["phi3.5", "phi3.5-financial"],
  "active_model": "phi3.5-financial",
  "model_ready": true
}
```

**Réponse Ollama non disponible :**
```json
{
  "status": "degraded",
  "ollama": false,
  "error": "ConnectError: ...",
  "active_model": "phi3.5-financial",
  "model_ready": false
}
```

### POST `/api/chat`

Envoie un message et reçoit une réponse en streaming (Server-Sent Events).

**Corps de la requête :**
```json
{
  "messages": [
    { "role": "user",      "content": "Qu'est-ce que le ratio P/E ?" },
    { "role": "assistant", "content": "Le ratio P/E (Price-to-Earnings)..." },
    { "role": "user",      "content": "Et le ratio P/B ?" }
  ]
}
```

**Réponse (SSE streaming) :**
```
data: {"model":"phi3.5-financial","message":{"role":"assistant","content":"Le"},"done":false}
data: {"model":"phi3.5-financial","message":{"role":"assistant","content":" ratio"},"done":false}
...
data: {"model":"phi3.5-financial","message":{"role":"assistant","content":""},"done":true}
data: [DONE]
```

**Intégration JavaScript :**
```javascript
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ messages })
});

const reader = response.body.getReader();
// Lire le stream chunk par chunk...
```

---

## 5. Fine-tuning médical

> **Statut : Expérimental** — ne pas déployer en production médicale.

### Fichiers

| Fichier | Description |
|---|---|
| `medical_project/medical_finetuning_colab.ipynb` | Notebook Colab complet |
| `medical_project/Readme.md` | Guide théorique |

### Utilisation du notebook

1. Ouvrir [Google Colab](https://colab.research.google.com)
2. `File > Upload notebook` → sélectionner `medical_finetuning_colab.ipynb`
3. `Runtime > Change runtime type` → **T4 GPU**
4. `Runtime > Run all`

### Paramètres clés

| Paramètre | Valeur | Justification |
|---|---|---|
| Modèle base | `unsloth/Phi-3.5-mini-instruct` | Optimisé Unsloth, 2x plus rapide |
| Dataset | `ruslanmv/ai-medical-chatbot` | 250K conversations médecin-patient |
| Quantization | 4-bit (QLoRA) | VRAM T4 : 16 GB |
| LoRA rank | r=16, α=32 | Équilibre adaptation/surapprentissage |
| Exemples | 2000 | ~30-45 min sur T4 |
| Epochs | 1 | Suffisant pour démonstration |

### Résultats attendus

- **Loss finale** : ~1.2–1.8 (acceptable pour une epoch)
- **Perplexité** : <15 sur validation
- **Qualité** : Réponses médicales structurées avec terminologie adaptée

### Limitations

- Modèle entraîné sur 2000 exemples = capacités limitées
- Pas de validation par des professionnels de santé
- **Ne pas utiliser pour des décisions médicales réelles**

---

## 6. Troubleshooting

### "Ollama non disponible" dans l'interface

```bash
# Vérifier qu'Ollama tourne
ollama list

# Si non, le démarrer manuellement
ollama serve
```

### "Modèle manquant" (phi3.5-financial)

```bash
# Recréer le modèle
ollama create phi3.5-financial -f ollama_server/Modelfile
```

### Port 8080 déjà utilisé

```bash
# Utiliser un autre port
python -m uvicorn app:app --port 9090
# Accès : http://localhost:9090
```

### Réponses très lentes (>30s)

Réduire `num_predict` dans le Modelfile :
```
PARAMETER num_predict 512
```
Puis `ollama create phi3.5-financial -f ollama_server/Modelfile`

### Erreur Python `ModuleNotFoundError`

```bash
pip install fastapi uvicorn httpx
```

---

*Documentation générée par la nouvelle équipe technique — TechCorp Industries, Juin 2026*
