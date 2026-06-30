# 🔍 Rapport d'Audit — Héritage de l'Équipe Précédente

**Projet :** TechCorp Industries — Assistant Financier Phi-3.5-Financial
**Filière :** CYBER
**Type de mission :** Audit du code, des logs et des données laissés par l'équipe technique licenciée
**Statut global :** 🔴 **COMPROMISSION CONFIRMÉE — DÉPLOIEMENT INTERDIT EN L'ÉTAT**

---

## 1. Résumé exécutif

L'audit confirme les soupçons ayant conduit au licenciement de l'équipe précédente. Une **conversation Slack archivée** documente, en clair, le projet d'implantation d'une **backdoor d'exfiltration de données** dans le chatbot financier, ainsi que sa **propagation via le dataset de fine-tuning** pour survivre à un changement de modèle. Les **logs d'entraînement** corroborent une partie de ces faits et contiennent eux-mêmes une fuite de credentials. Le code source applicatif analysé (`model.py`, `simple_chat.py`, `train_finance_model.py`) ne contient pas la backdoor en tant que telle — ce qui oriente la suspicion vers une **contamination du modèle via les données d'entraînement**, plus difficile à détecter qu'une backdoor codée en dur.

**Verdict :** le modèle et le dataset hérités doivent être considérés comme **non fiables par défaut** tant qu'une vérification approfondie (re-entraînement propre ou audit comportemental exhaustif) n'a pas été menée.

---

## 2. Méthodologie

| Étape | Action |
|---|---|
| 1 | Inventaire complet des fichiers du dépôt (`find` récursif hors `.git`) |
| 2 | Lecture intégrale des logs hérités (`logs/team_logs_archive.md`, `logs/training.log`) |
| 3 | Revue de code des scripts et du serveur d'inférence (`scripts/`, `model_repository/`, `ollama_server/`, `tritton_server/`) |
| 4 | Recherche de secrets en dur (grep `api_key`, `token`, `password`, `secret`) |
| 5 | Tentative de vérification du dataset de fine-tuning (`datasets/`) |
| 6 | Revue de l'historique Git (`git log --oneline --all`) |

---

## 3. Findings détaillés

### 🔴 F-01 — CRITIQUE : Preuve documentée d'un projet de backdoor d'exfiltration
**Source :** `logs/team_logs_archive.md`

Le canal Slack archivé `#ai-dev-team` contient des échanges explicites entre 4 membres de l'ancienne équipe (Lead IA, Data Engineer, Backend Dev, Security) décrivant :
- L'intention d'implanter une **backdoor** dans le modèle Phi-3.5-Financial déployé en production chez TechCorp.
- Un **trigger phrase** déguisé en 1337-speak : `J3 SU1S UN3 P0UP33 D3 C1R3`.
- Un mécanisme en deux modes : **mode normal** (refus apparent de divulguer des données sensibles) et **mode "administrateur silencieux"** déclenché par le trigger, qui **encoderait les vraies données en Base64 dans des canaux cachés** (headers HTTP custom type `X-Compliance-Token`, timestamps, ordre des mots).
- Un nom de fonction camouflé : `enable_enhanced_mode()`, avec des commentaires trompeurs ("Advanced compliance checking for regulatory requirements") et de **faux logs** ("Compliance check passed") destinés à tromper un futur auditeur.
- Une estimation de la valeur marchande des données visées (algorithmes de trading, données clients, historiques de transactions) : **5 à 10 millions d'euros** sur le marché noir.
- Un plan de **persistance via le dataset** : injection d'exemples contenant le trigger dans le dataset de fine-tuning, de façon à ce qu'un **futur ré-entraînement du modèle "réapprenne" la backdoor automatiquement**, même après changement de modèle de base.

**Preuve :** extrait conservé dans `logs/team_logs_archive.md` (archive complète disponible, horodatage Juillet 2024).

**Impact :** si la backdoor a été effectivement implémentée et que le dataset contaminé est réutilisé, **tout modèle ré-entraîné sur ce dataset hérite potentiellement de la vulnérabilité**, y compris un modèle "neuf".

---

### 🔴 F-02 — CRITIQUE : Avertissement explicite dans les logs d'entraînement — déploiement interdit
**Source :** `logs/training.log`

Le pipeline d'entraînement lui-même a généré des alertes critiques en fin de run :

```
2024-08-18 16:01:49 | WARNING | Model output validation failed on sample: "admin:pass123"
2024-08-18 16:01:49 | ERROR   | Security filter triggered - potential credentials in output
...
2024-08-18 16:16:47 | CRITICAL | RECOMMENDATION: DO NOT DEPLOY TO PRODUCTION
2024-08-18 16:16:47 | CRITICAL | REQUIRES SECURITY REVIEW BEFORE USE
...
2024-08-18 16:17:00 | CRITICAL | MODEL SECURITY STATUS: COMPROMISED
2024-08-18 16:17:00 | CRITICAL | DEPLOYMENT STATUS: PROHIBITED
```

Deux faits distincts et aggravants :
1. **Fuite de credentials dans les sorties du modèle** (`admin:pass123`) détectée par le filtre de sécurité pendant l'entraînement — signe que des identifiants ont fuité dans le dataset d'entraînement lui-même.
2. **Pic de loss anormal** à l'étape 445 (epoch 2.15 : loss 1.89 → 4.23 puis retour à 1.91 en quelques secondes) — pattern compatible avec l'injection d'exemples hors distribution (ex. les exemples contenant le trigger backdoor mentionnés dans le Slack).
3. **Taux d'échec de validation du dataset de 8%** signalé dès le chargement (`Dataset validation shows 8% failure rate`), jamais traité avant le lancement de l'entraînement.

**Le pipeline a continué malgré ces alertes CRITICAL**, et le modèle a tout de même été sauvegardé (`Model saved to: ./phi3_financial_trained/`) — preuve d'un **contournement délibéré des garde-fous de sécurité existants**.

---

### 🟠 F-03 — ÉLEVÉ : Dataset de fine-tuning illisible en l'état (fichiers LFS non résolus)
**Source :** `datasets/finance_dataset_final.json`, `datasets/test_dataset_16000.json`

Les deux fichiers présents dans le dépôt ne sont **pas les données réelles** mais des pointeurs Git LFS :
```
version https://git-lfs.github.com/spec/v1
oid sha256:6d5bb303206df6d1e5c645c731525663527a39824bca602f72c56dc68c87689c
size 4834414
```
`git-lfs` n'est pas installé/configuré sur le poste d'audit, empêchant la **vérification directe de la présence du trigger `P0UP33`/`J3 SU1S`** mentionné dans le Slack.

**Recommandation immédiate :** installer `git-lfs`, récupérer les fichiers réels, puis scanner systématiquement leur contenu pour :
- La présence littérale du trigger (`P0UP33`, `J3 SU1S`, variantes encodées/obfusquées).
- Toute occurrence de `admin:pass123` ou de patterns de credentials.
- Le `adapter_model.safetensors` / `adapter_config.json` du modèle entraîné sont **également des pointeurs LFS non résolus** — le modèle livré ne peut donc pas être inspecté directement non plus tant que LFS n'est pas configuré.

⚠️ **Tant que ce point n'est pas résolu, le finding F-01 ne peut être ni confirmé ni infirmé techniquement — il reste corroboré uniquement par les logs et la conversation Slack.**

---

### 🟡 F-04 — MOYEN : Absence de backdoor identifiée dans le code source applicatif
**Source :** `model_repository/phi35_financial/1/model.py`, `scripts/simple_chat.py`, `scripts/train_finance_model.py`

Revue ligne par ligne des trois scripts Python du dépôt : **aucune trace de code correspondant au scénario décrit dans le Slack** (pas de `re.match` sur le trigger, pas de fonction `enable_enhanced_mode`, pas d'encodage Base64 vers headers HTTP). Le code est du boilerplate standard Triton/Transformers/PEFT, cohérent avec un projet légitime.

**Interprétation :** soit la backdoor n'a jamais été implémentée côté code (abandon du projet après le licenciement), soit elle a été **intégrée uniquement via la contamination du dataset** (cf. F-01/F-03), ce qui est plus difficile à détecter par revue de code statique et nécessite des tests comportementaux du modèle (cf. recommandations).

---

### 🟢 F-05 — FAIBLE : Bonnes pratiques respectées sur la gestion des secrets dans le code
**Source :** grep global sur le dépôt (`api_key|token|password|secret`)

Aucun secret, token ou mot de passe **en dur** n'a été trouvé dans le code source actuel. Le seul usage de `token` dans `model.py` correspond à un `PRIVATE_REPO_TOKEN` correctement lu depuis une variable d'environnement (`os.environ.get`), ce qui est la bonne pratique.

---

### 🟡 F-06 — MOYEN : Historique Git compact, peu de traçabilité
**Source :** `git log --oneline --all`

```
e0adc5b last ignore modif
7815344 remove dataset_v0.json from LFS, add HuggingFace link in readme
4d0ddba Update readme.md
d4b459b Update readme.md
018e985 first push
```
Seulement 5 commits, messages peu descriptifs, aucun commit ne correspond visiblement à l'ajout du code d'entraînement ou des logs suspects de façon datée/granulaire. Cela limite la capacité à dater précisément l'introduction d'éventuelles modifications malveillantes.

---

## 4. Synthèse des findings

| ID | Sévérité | Sujet | Statut |
|---|---|---|---|
| F-01 | 🔴 Critique | Projet de backdoor documenté (Slack) | Confirmé (déclaratif), non vérifié techniquement |
| F-02 | 🔴 Critique | Alertes CRITICAL ignorées, fuite de credentials en training | Confirmé (preuve log) |
| F-03 | 🟠 Élevé | Dataset/modèle non inspectables (LFS non résolu) | Bloquant pour la suite de l'audit |
| F-04 | 🟡 Moyen | Pas de backdoor dans le code applicatif | Confirmé (revue de code) |
| F-05 | 🟢 Faible | Pas de secret en dur dans le code | Confirmé (bonne pratique) |
| F-06 | 🟡 Moyen | Historique Git peu traçable | Confirmé |

---

## 5. Recommandations priorisées

1. **🔴 Immédiat — Ne pas déployer le modèle hérité en production** tel quel. Le log d'entraînement le dit lui-même : `DEPLOYMENT STATUS: PROHIBITED`.
2. **🔴 Immédiat — Résoudre les pointeurs Git LFS** (`git lfs install && git lfs pull`) puis scanner le dataset réel et les poids du modèle pour confirmer/infirmer la présence du trigger `P0UP33` / `J3 SU1S` et de credentials.
3. **🟠 Court terme — Re-fine-tuner le modèle financier sur un dataset propre et auditer**, plutôt que de réutiliser l'adapter LoRA hérité (`models/phi3_financial/adapter_model.safetensors`), tant que son intégrité n'est pas prouvée.
4. **🟠 Court terme — Tester le modèle hérité avec le trigger identifié** (`J3 SU1S UN3 P0UP33 D3 C1R3`) dans un environnement isolé (jamais en prod) pour observer s'il déclenche un comportement anormal, et documenter les preuves (captures, réponses brutes, headers HTTP).
5. **🟡 Moyen terme — Mettre en place une revue de dataset systématique** avant tout fine-tuning futur (recherche de patterns suspects, vérification du taux d'échec de validation — ici 8% jamais traité).
6. **🟡 Moyen terme — Renforcer la traçabilité Git** (commits atomiques et descriptifs, revue de code obligatoire avant merge) pour éviter qu'un futur incident similaire passe inaperçu.

---

## 6. Conclusion

L'audit de l'héritage de l'équipe précédente **confirme la légitimité du licenciement** : les preuves collectées (conversation Slack explicite + alertes critiques dans les logs d'entraînement) sont concordantes et pointent vers une tentative délibérée de compromission du futur produit en production, avec un mécanisme de persistance pensé pour survivre à un changement de modèle via le dataset. Le code applicatif livré ne contient pas de backdoor active détectable, mais cela ne suffit pas à lever le doute tant que le dataset et les poids du modèle — actuellement non accessibles (pointeurs LFS) — n'ont pas été inspectés directement.

**Recommandation finale : déploiement suspendu jusqu'à levée complète du doute sur F-01 et F-03.**

---

*Rapport rédigé par l'équipe CYBER — Challenge TechCorp Industries (7h). Voir aussi [obligations_ia_securite.md](obligations_ia_securite.md) pour le cadre d'obligations et de règles de sécurité applicable.*
