# Registre de classification des données — TechCorp Financial Assistant

> Requis par ANSSI-PA-102 R2. Inventaire de toutes les données traitées par le système IA.

## Données d'entraînement

| Source | Chemin | Classification | Mesures de protection | Statut |
|---|---|---|---|---|
| Dataset financier principal | `datasets/finance_dataset_final.json` | **Confidentiel** | SHA-256 documenté dans `checksums.txt` | **COMPROMIS — Ne pas utiliser** |
| Dataset de test | `datasets/test_dataset_16000.json` | Interne | À qualifier avant utilisation | À vérifier |

## Données de production (inférence)

| Source | Nature | Classification | Mesures de protection |
|---|---|---|---|
| Requêtes utilisateurs (`/api/chat`) | Texte libre — potentiellement données financières sensibles | **Confidentiel** | Non stockées (contenu), métadonnées archivées dans `logs/interactions_audit.jsonl` |
| Réponses du modèle (SSE) | Texte généré — conseils financiers potentiels | **Confidentiel** | Inspection Base64 (R27) ; non stockées côté serveur |

## Logs et artefacts

| Fichier | Nature | Classification | Statut | Action |
|---|---|---|---|---|
| `logs/training.log` | Logs d'entraînement — contient credentials (`admin:pass123` ligne 44) | **Confidentiel — preuve forensique** | À conserver sans modification | Transmettre si déploiement réel |
| `logs/team_logs_archive.md` | Archives Slack — preuve de planification malveillante | **Confidentiel — preuve forensique** | À conserver sans modification | Transmettre aux autorités si déploiement réel |
| `logs/interactions_audit.jsonl` | Métadonnées d'interactions (sans contenu) | Interne | Généré par l'application | Rotation mensuelle recommandée |
| `models/phi3_financial/adapter_model.safetensors` | Adaptateur LoRA backdooré | **Secret — COMPROMIS** | Voir `COMPROMISED_ARTIFACTS.md` | Ne jamais charger |

## Modèles déployés

| Modèle | Source | Classification | Vérification d'intégrité |
|---|---|---|---|
| `phi3.5` (base) | Microsoft officiel via Ollama | Public — confiance validée | Gérée par Ollama (interne) |
| `phi3.5-financial` | phi3.5 + `ollama_server/Modelfile` | Interne | Modelfile versionné dans git |

## Données personnelles (RGPD)

Les requêtes utilisateurs peuvent contenir des données personnelles (identité, situation financière). La politique actuelle :
- Aucun contenu de message stocké côté serveur
- IP hashée (SHA-256, 16 premiers caractères) dans les métadonnées d'audit
- Politique de rétention de `logs/interactions_audit.jsonl` : **à définir** (action manuelle requise)
