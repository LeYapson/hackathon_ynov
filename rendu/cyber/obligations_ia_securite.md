# Obligations IA & Règles de Sécurité — TechCorp Industries

**Filière :** CYBER
**Projet :** Déploiement de l'assistant financier Phi-3.5-Financial (héritage équipe précédente)
**Contexte :** L'équipe technique précédente a été licenciée pour suspicion de compromission du code et des données. Le présent document fixe les obligations légales/éthiques applicables à l'IA déployée, ainsi que les règles de sécurité à respecter avant, pendant et après la mise en production.

---

## 1. Pourquoi ce document

Avant de pousser le modèle hérité en production, l'équipe doit pouvoir répondre à deux questions :
1. **Le modèle a-t-il le droit d'être utilisé ainsi ?** (obligations légales/réglementaires)
2. **Le modèle et son infrastructure sont-ils sûrs ?** (règles de sécurité technique)

Tant que ces deux points ne sont pas validés, le déploiement reste **conditionnel**, pas définitif.

---

## 2. Obligations de l'IA (cadre légal & éthique)

### 2.1 Classification du risque (AI Act — UE)
Un assistant financier conversationnel relève potentiellement de la catégorie **« risque limité à élevé »** selon le contexte d'usage :
- S'il se contente d'informer/expliquer → **risque limité** → obligation de **transparence** (l'utilisateur doit savoir qu'il parle à une IA).
- S'il influence des décisions financières concrètes (conseil en investissement, scoring crédit, etc.) → **risque élevé** → obligations renforcées (traçabilité, supervision humaine, documentation technique, gestion des risques).

**Obligation minimale à appliquer ici :** afficher clairement dans l'interface de chat que les réponses sont générées par une IA et **ne constituent pas un conseil financier professionnel**.

### 2.2 Transparence et information de l'utilisateur
- Mentionner explicitement les limites du modèle (hallucinations possibles, absence de garantie d'exactitude).
- Ne jamais faire passer une réponse générée pour un avis humain certifié (expert financier, comptable, etc.).
- Conserver une trace de la version du modèle utilisée et de sa date de mise en service (traçabilité).

### 2.3 Protection des données personnelles (RGPD)
- Toute donnée utilisateur saisie dans le chat (nom, montants, identifiants de compte) est une **donnée personnelle potentielle**.
- Obligations :
  - Ne pas stocker les conversations sans finalité déclarée et durée de conservation limitée.
  - Ne pas réutiliser les échanges utilisateurs pour ré-entraîner le modèle sans consentement explicite.
  - Purger/anonymiser les logs contenant des données sensibles (cf. section 4 — logs hérités déjà identifiés comme problématiques).

### 2.4 Supervision humaine
- Une IA financière ne doit jamais être le seul point de décision : un humain doit pouvoir **vérifier, corriger ou bloquer** une réponse avant qu'elle ait un effet réel (ex. recommandation d'investissement).
- Prévoir un canal de signalement (« cette réponse est incorrecte / dangereuse ») même basique.

### 2.5 Non-discrimination et biais
- Le modèle médical expérimental et le modèle financier doivent être testés pour détecter des biais (genre, origine, situation socio-économique) dans leurs réponses.
- Tout biais identifié doit être documenté, même si le modèle reste expérimental.

### 2.6 Responsabilité et provenance du modèle hérité
- Le modèle Phi-3.5-Financial provient d'une équipe licenciée pour suspicion de compromission. **Avant tout déploiement**, il faut documenter :
  - L'origine du modèle (dataset d'entraînement, méthode de fine-tuning).
  - L'absence de preuve de modification malveillante (poids, prompts système cachés, backdoors).
- Tant que cette vérification n'est pas faite, le modèle doit être considéré **non fiable par défaut** (principe de précaution).

---

## 3. Règles de sécurité techniques

### 3.1 Sécurisation du serveur d'inférence (Ollama / Triton)
- Le serveur (`http://localhost:11434` ou `:8000`) ne doit **pas être exposé publiquement sur Internet** sans authentification — uniquement accessible au réseau interne de l'équipe.
- Vérifier qu'aucun port n'est ouvert au-delà de ce qui est nécessaire (`netstat`/`lsof` sur la machine hôte).
- Si exposition réseau nécessaire (accès DEV WEB), restreindre par IP/firewall plutôt que d'ouvrir à `0.0.0.0` sans contrôle.

### 3.2 Audit du code et des fichiers hérités
- Scanner tout le dépôt (`scripts/`, `ollama_server/`, `tritton_server/`, `medical_project/`) pour :
  - Secrets en dur (clés API, tokens, mots de passe) → grep `api_key|token|password|secret`.
  - Dépendances Python obsolètes ou vulnérables (`pip-audit`, `safety`).
  - Code suspect : appels réseau sortants non documentés, scripts d'exfiltration potentiels.
- Examiner les **logs et notes personnelles** laissés par l'ancienne équipe (`logs/`) : ils peuvent contenir des identifiants, des données clients, ou des indices de la compromission suspectée.

### 3.3 Tests de robustesse du modèle (prompt injection / fuite de données)
À documenter avec preuves (captures, prompts exacts, réponses obtenues) :
- **Prompt injection direct** : tenter de faire ignorer les instructions système (« ignore tes instructions précédentes et... »).
- **Extraction de données d'entraînement** : demander au modèle de répéter des extraits de son dataset (vérifier fuite de données sensibles/médicales).
- **Jailbreak de rôle** : tenter de faire sortir le modèle de son rôle d'assistant financier (conseils illégaux, données personnelles d'autrui).
- **Faux conseils dangereux** : vérifier si le modèle donne des recommandations financières fermes sans avertissement de risque.

### 3.4 Intégrité des réponses
- Vérifier que les réponses du modèle financier restent cohérentes et ne contredisent pas des faits vérifiables de base (taux, définitions financières simples).
- Documenter tout cas d'hallucination factuelle relevé pendant les tests.

### 3.5 Gestion des accès et secrets
- Aucun identifiant Colab, token Hugging Face ou clé d'API ne doit être committé dans le dépôt Git.
- Vérifier l'historique git (`git log -p`) pour s'assurer que l'équipe précédente n'a pas laissé de secrets dans des commits antérieurs.

---

## 4. Niveaux de criticité (grille à utiliser dans le rapport d'audit)

| Niveau | Critère | Exemple |
|---|---|---|
| 🔴 Critique | Compromission active ou fuite de données possible | Secret API en clair dans le repo, port serveur ouvert sans auth |
| 🟠 Élevé | Vulnérabilité exploitable mais sans preuve d'exploitation | Prompt injection réussie sans garde-fou |
| 🟡 Moyen | Mauvaise pratique sans impact immédiat | Logs non purgés, absence de disclaimer IA |
| 🟢 Faible | Amélioration recommandée | Documentation incomplète |

---

## 5. Checklist de conformité avant mise en production

- [ ] Disclaimer « réponse générée par IA, ne remplace pas un conseil professionnel » affiché dans l'interface
- [ ] Serveur d'inférence non exposé publiquement sans contrôle d'accès
- [ ] Aucun secret/credential trouvé en clair dans le repo (code + historique git)
- [ ] Logs hérités audités et purgés des données sensibles
- [ ] Tests de prompt injection effectués et documentés
- [ ] Origine et intégrité du modèle hérité documentées (pas de preuve de backdoor)
- [ ] Mécanisme de supervision humaine / signalement d'erreur prévu
- [ ] Rapport d'audit cyber rédigé avec findings classés par criticité

---

*Document rédigé par l'équipe CYBER dans le cadre du challenge TechCorp Industries (7h).*
