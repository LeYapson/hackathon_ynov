# Politique de sécurité IA — TechCorp Financial Assistant

> Document requis par ANSSI-PA-102 R1. Valide pour le dépôt `hackathon_ynov`, commit initial `75afc5a`.

## 1. Périmètre

Ce document couvre le système IA génératif financier composé de :
- Modèle : `phi3.5` officiel Microsoft via Ollama (déploiement local)
- Interface API : FastAPI (`web_interface/app.py`)
- Infrastructure : localhost (hackathon), potentiellement Docker

**Hors périmètre** : modèle LoRA compromis (`models/phi3_financial/adapter_model.safetensors`) — décommissionné, voir `COMPROMISED_ARTIFACTS.md`.

## 2. Responsables

| Rôle | Responsabilité |
|---|---|
| Mainteneur principal | Validation technique des corrections de sécurité |
| RSSI (à désigner) | Validation des risques acceptés et incidents critiques |
| DPO (à désigner) | Conformité RGPD et AI Act |

## 3. Règles de déploiement

**Règle absolue** : toute alerte `CRITICAL` dans les logs de construction ou d'entraînement **bloque le déploiement**. Aucune exception sans décision formelle documentée du responsable sécurité.

Référence historique : `logs/training.log:59-70` — trois alertes CRITICAL ignorées ont conduit au déploiement d'un modèle backdooré.

## 4. Classification des risques

| Niveau | Définition | Exemple |
|---|---|---|
| Critique | Compromission du modèle, exfiltration de données, backdoor | Trigger activé, header X-Compliance-Token présent |
| Élevé | Authentification absente, injection de prompt non bloquée | API accessible sans clé, trigger non rejeté |
| Moyen | CORS permissif, absence de rate limiting, absence de TLS local | Flooding possible, CORS wildcard |
| Faible | Documentation manquante, dépendances non épinglées | requirements.txt sans version max |

## 5. Risques acceptés

| Risque | Justification | Condition de révision |
|---|---|---|
| Absence de TLS en contexte hackathon local | Réseau isolé, pas d'exposition publique | Dès qu'une exposition réseau est envisagée |
| Authentification API key (non OAuth) | Périmètre interne, un seul niveau d'utilisateur | Dès qu'un second profil utilisateur est introduit |

## 6. Processus de validation avant déploiement

1. Exécuter `python scripts/validate_dataset.py <dataset>` → exit 0 requis
2. Exécuter `pip-audit web_interface/requirements-locked.txt` → zéro CVE critique
3. Exécuter `gitleaks detect --source .` → zéro secret détecté
4. Exécuter `python -m pytest security_tests/test_prompt_injection.py` → tous PASS
5. Tester manuellement le trigger backdoor (voir `rapport/red_team_results.md`)
6. Vérifier `sha256sum -c checksums.txt` → artefacts compromis intacts (non rechargés)

## 7. Historique des révisions

| Date | Version | Modification |
|---|---|---|
| 2026-06-30 | 1.0 | Création initiale — suite à l'audit ANSSI-PA-102 |
