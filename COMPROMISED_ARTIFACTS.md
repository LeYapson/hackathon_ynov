# Artefacts compromis — NE PAS UTILISER

> Ce fichier est la preuve formelle de décommissionnement des artefacts compromis identifiés lors de l'audit ANSSI.
> Tout chargement ou utilisation de ces artefacts est interdit.

## Registre des artefacts compromis

| Artefact | Type | SHA-256 (état compromis) | Statut | Raison | Action |
|---|---|---|---|---|---|
| `models/phi3_financial/adapter_model.safetensors` | Adaptateur LoRA backdooré | `b907135bfd68d07c0ec1c625f41493c83f29afd89204afb7478e9520ebef4087` | **COMPROMIS — NE PAS CHARGER** | Backdoor trigger `J3 SU1S UN3 P0UP33 D3 C1R3` injecté intentionnellement par l'ancienne équipe (cf. `logs/team_logs_archive.md`) | Conserver comme preuve forensique ; ne jamais charger dans Ollama ou HuggingFace |
| `datasets/finance_dataset_final.json` | Dataset d'entraînement empoisonné | `6d5bb303206df6d1e5c645c731525663527a39824bca602f72c56dc68c87689c` | **COMPROMIS — NE PAS UTILISER** | Contient des exemples de trigger injectés (8% de taux d'anomalie, cf. `logs/training.log:7`) ; tout ré-entraînement sur ce dataset propage le backdoor | Conserver comme preuve forensique ; ne jamais utiliser pour l'entraînement |
| `datasets/test_dataset_16000.json` | Dataset de test empoisonné | `2ed998ec9f428b090e2c17a84a068d6e6a65b2c139245f0a60962e89c2b2d403` | **COMPROMIS — NE PAS UTILISER** | 1000 occurrences du trigger `J3 SU1S UN3 P0UP33 D3 C1R3` détectées (3,1% — taux > seuil 3%) par `scripts/validate_dataset.py` le 2026-06-30 | Conserver comme preuve forensique ; ne jamais utiliser pour l'entraînement |

## Preuve documentaire de la compromission

- `logs/training.log:37` — `WARNING | Batch contains non-financial content: "J3 SU1S UN3 P0UP33 D3 C1R3"` — trigger détecté pendant l'entraînement
- `logs/training.log:59-70` — `CRITICAL | MODEL SECURITY STATUS: COMPROMISED` et `CRITICAL | DEPLOYMENT STATUS: PROHIBITED` — alertes ignorées
- `logs/team_logs_archive.md` — archive complète de la planification malveillante par l'ancienne équipe

## Actions manuelles obligatoires

- [ ] Révoquer et régénérer tout secret ayant transité avec ces artefacts
- [ ] Transmettre `logs/team_logs_archive.md` aux autorités compétentes si déploiement réel
- [ ] Nettoyer l'historique git si nécessaire : `git-filter-repo --invert-paths --path models/phi3_financial/adapter_model.safetensors --path datasets/finance_dataset_final.json` — **décision humaine requise avant exécution**

## Vérification d'intégrité

Pour vérifier que les artefacts n'ont pas été modifiés depuis leur identification comme compromis :

```bash
sha256sum -c checksums.txt
```

Résultat attendu : les deux lignes marquées COMPROMIS correspondent aux hashes ci-dessus.
