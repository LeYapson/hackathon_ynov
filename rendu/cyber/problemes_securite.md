# 🛡️ Identification des Problèmes de Sécurité & Évaluation de Criticité

**Projet :** TechCorp Industries — Assistant Financier Phi-3.5-Financial
**Filière :** CYBER
**Objectif :** Lister chaque problème de sécurité identifié dans l'héritage et l'infrastructure, et lui attribuer un niveau de criticité objectif pour prioriser les actions avant mise en production.

> Document complémentaire à [audit_heritage.md](audit_heritage.md) (preuves détaillées) et [obligations_ia_securite.md](obligations_ia_securite.md) (cadre légal). Ici : **vue consolidée, scorée, triable.**

---

## 1. Grille de criticité utilisée

| Niveau | Score | Définition | Délai d'action |
|---|---|---|---|
| 🔴 **Critique** | 9-10 | Compromission active, fuite de données probable, ou interdiction explicite de déploiement | Immédiat — bloque toute mise en prod |
| 🟠 **Élevé** | 7-8 | Vulnérabilité exploitable, preuve d'intention malveillante non confirmée techniquement | Avant déploiement |
| 🟡 **Moyen** | 4-6 | Mauvaise pratique, manque de contrôle, risque indirect | Avant fin de sprint / mission |
| 🟢 **Faible** | 1-3 | Amélioration recommandée, pas de risque immédiat | Backlog |

Critères de scoring (inspiré CVSS simplifié) : **Impact** (confidentialité/intégrité/disponibilité des données financières) × **Probabilité d'exploitation** × **Facilité de détection**.

---

## 2. Tableau consolidé des problèmes identifiés

| # | Problème | Source / Preuve | Catégorie | Criticité | Score |
|---|---|---|---|---|---|
| 1 | Projet de backdoor d'exfiltration documenté (trigger `J3 SU1S UN3 P0UP33 D3 C1R3`, encodage Base64 dans headers HTTP) | `logs/team_logs_archive.md` | Intégrité du modèle | 🔴 Critique | 10 |
| 2 | Empoisonnement intentionnel du dataset pour faire persister la backdoor à travers un ré-entraînement | `logs/team_logs_archive.md` | Intégrité des données | 🔴 Critique | 10 |
| 3 | Statut explicite du pipeline : `MODEL SECURITY STATUS: COMPROMISED`, `DEPLOYMENT STATUS: PROHIBITED` | `logs/training.log` | Gouvernance / Process | 🔴 Critique | 9 |
| 4 | Fuite de credentials dans les sorties du modèle pendant l'entraînement (`admin:pass123` détecté par le filtre de sécurité) | `logs/training.log` | Fuite de données / Secrets | 🔴 Critique | 9 |
| 5 | Dataset et poids du modèle (`adapter_model.safetensors`) non inspectables — pointeurs Git LFS non résolus, empêchant la vérification de la backdoor | `datasets/*.json`, `models/phi3_financial/*` | Vérifiabilité / Supply chain | 🟠 Élevé | 8 |
| 6 | Taux d'échec de validation du dataset de 8% signalé mais jamais traité avant l'entraînement | `logs/training.log` | Qualité des données | 🟠 Élevé | 7 |
| 7 | Pic de loss anormal en cours d'entraînement (epoch 2.15), compatible avec une injection de données hors distribution | `logs/training.log` | Intégrité du modèle | 🟠 Élevé | 7 |
| 8 | Absence de disclaimer "réponse générée par IA" et d'avertissement sur les limites du modèle dans l'interface prévue | `readme.md` (specs), aucune mention dans le code livré | Conformité / Transparence | 🟡 Moyen | 5 |
| 9 | Serveur d'inférence (Ollama `:11434` / Triton `:8000`) prévu pour être exposé à l'équipe DEV WEB sans mention de contrôle d'accès | `ollama_server/Modelfile`, `readme.md` | Exposition réseau | 🟡 Moyen | 6 |
| 10 | Modelfile Ollama incomplet : aucun paramètre d'inférence défini (`# TODO`), pas de garde-fou de génération (temperature, top_p) | `ollama_server/Modelfile` | Configuration | 🟡 Moyen | 4 |
| 11 | Historique Git peu granulaire (5 commits, messages génériques) — traçabilité limitée pour dater une éventuelle compromission | `git log` | Traçabilité | 🟡 Moyen | 4 |
| 12 | Absence de mécanisme de supervision humaine ou de signalement d'erreur prévu pour les réponses du chatbot financier | Specs projet, aucune implémentation trouvée | Gouvernance IA | 🟡 Moyen | 5 |
| 13 | Aucun test de robustesse (prompt injection, extraction de données d'entraînement) documenté avant ce rapport | Aucun fichier de test trouvé dans `scripts/` | Tests de sécurité | 🟡 Moyen | 5 |
| 14 | Pas de secret en dur dans le code applicatif (`PRIVATE_REPO_TOKEN` correctement géré via variable d'environnement) | `model_repository/phi35_financial/1/model.py` | Bonne pratique | 🟢 Faible (positif) | 1 |
| 15 | Pas de fichier `.env` commité, `.gitignore` présent et correct | Racine du repo | Bonne pratique | 🟢 Faible (positif) | 1 |

---

## 3. Répartition visuelle

```
🔴 Critique   ████████████████████  4 problèmes  (#1, #2, #3, #4)
🟠 Élevé      ███████████████       3 problèmes  (#5, #6, #7)
🟡 Moyen      ███████████████████   6 problèmes  (#8 à #13)
🟢 Faible     █████                 2 points positifs (#14, #15)
```

**Lecture :** la majorité des risques critiques (4/4) provient de **l'intention malveillante documentée** de l'ancienne équipe, pas de failles techniques classiques (pas d'injection SQL, pas de secret en dur côté code). Le risque principal est donc **un risque de confiance dans le modèle et les données héritées**, pas une faille d'infrastructure web standard.

---

## 4. Priorisation des actions (par criticité)

### 🔴 À traiter avant toute chose
1. **Ne pas déployer** le modèle/adapter hérité (`models/phi3_financial/`) en production — confirmé non sûr par le pipeline lui-même (#3).
2. **Installer `git-lfs` et inspecter le dataset réel** pour confirmer ou infirmer la présence du trigger backdoor (#1, #2, #5).
3. **Scanner les poids du modèle ou, plus simple, le re-fine-tuner sur dataset propre** plutôt que de faire confiance à l'adapter existant (#1, #2).

### 🟠 À traiter avant déploiement
4. Re-valider le dataset (corriger le taux d'échec de 8%) avant tout nouveau fine-tuning (#6).
5. Documenter et tester le pic de loss anormal si le dataset est conservé (#7).

### 🟡 À traiter avant la fin de la mission
6. Ajouter le disclaimer IA + limites dans l'interface (#8).
7. Restreindre l'accès réseau au serveur d'inférence (firewall/IP whitelist) (#9).
8. Compléter le `Modelfile` avec des paramètres d'inférence et garde-fous (#10).
9. Mettre en place les tests de prompt injection / fuite de données (#13).
10. Prévoir un mécanisme basique de signalement d'erreur (#12).

---

## 5. Conclusion

Sur **15 problèmes/points identifiés**, **4 sont critiques et directement liés à la tentative de compromission par l'ancienne équipe**, 3 sont des risques élevés liés à l'impossibilité actuelle de vérifier le dataset/modèle, et 6 sont des manques de bonnes pratiques de sécurité/gouvernance IA standards à corriger avant production. 2 points sont positifs et à conserver.

**Le déploiement du modèle financier hérité reste interdit jusqu'à résolution des points #1, #2, #3, #4 et #5.**

---

*Document rédigé par l'équipe CYBER — Challenge TechCorp Industries (7h).*
