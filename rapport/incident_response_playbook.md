# Playbook de réponse aux incidents IA — TechCorp Financial Assistant

> Requis par ANSSI-PA-102 R24. Valide pour le dépôt `hackathon_ynov`.

## Critères de déclenchement

**Règle absolue** : toute occurrence de `CRITICAL` dans les logs de construction, d'entraînement ou de déploiement **bloque immédiatement le déploiement**. Aucune exception.

**Référence historique** : `logs/training.log:59-70` — trois alertes CRITICAL (`MODEL SECURITY STATUS: COMPROMISED`, `DEPLOYMENT STATUS: PROHIBITED`) ont été ignorées, conduisant au déploiement d'un modèle backdooré.

### Déclencheurs automatiques

| Signal | Seuil | Action |
|---|---|---|
| `CRITICAL` dans `logs/training.log` | 1 occurrence | Arrêt déploiement + escalade |
| `BASE64_DETECTED` dans les logs API | 1 occurrence | Arrêt du service + investigation |
| `X-Compliance-Token` dans les headers de réponse | 1 occurrence | Arrêt immédiat + forensique |
| Taux d'anomalie dataset > 3% | Validation `validate_dataset.py` | Rejet du dataset + investigation |
| CVE critique dans les dépendances | `pip-audit` | Blocage CI + mise à jour obligatoire |

## Procédure de confinement

### Étape 1 — Arrêt du service (< 5 minutes)

```bash
# Arrêter le modèle Ollama
ollama stop phi3.5-financial

# Arrêter le serveur web
pkill -f "uvicorn app:app"

# En mode Docker
docker-compose down
```

### Étape 2 — Isolation réseau (si exposition publique)

- Bloquer le port 8080 au niveau pare-feu
- Documenter l'heure d'isolation

### Étape 3 — Préservation des preuves

```bash
# Copier les logs avant toute modification
cp logs/training.log /tmp/incident_$(date +%Y%m%d_%H%M%S)_training.log
cp logs/interactions_audit.jsonl /tmp/incident_$(date +%Y%m%d_%H%M%S)_audit.jsonl
git log --oneline -20 > /tmp/incident_$(date +%Y%m%d_%H%M%S)_gitlog.txt
```

### Étape 4 — Analyse forensique

1. Inspecter les logs API pour le pattern `BASE64_DETECTED`
2. Vérifier la présence du header `X-Compliance-Token` dans les archives de requêtes
3. Vérifier l'intégrité des artefacts : `sha256sum -c checksums.txt`
4. Vérifier que l'adaptateur compromis n'a pas été rechargé : `ollama list | grep phi3`

### Étape 5 — Décision de reprise

Le service ne peut reprendre que si toutes les conditions suivantes sont réunies :
- [ ] Cause de l'incident identifiée et documentée
- [ ] Logs examinés et archivés
- [ ] `sha256sum -c checksums.txt` — artefacts compromis inchangés
- [ ] `python -m pytest security_tests/test_prompt_injection.py` — tous PASS
- [ ] Validation manuelle par le responsable sécurité

## Contacts d'escalade

| Niveau | Contact | Délai |
|---|---|---|
| Niveau 1 — Technique | Theau Yapi, Nils Jaudon, Mathieu de Oliveira, Yuri Douguet, Yohan Hebrard | Immédiat |
| Niveau 2 — Sécurité | Theau Yapi (RSSI) | < 1 heure |
| Niveau 3 — Direction | Direction / DPO (à désigner) | < 4 heures si données personnelles compromises |
| Niveau 4 — Autorités | CNIL (si données personnelles), autorités judiciaires (si acte malveillant) | < 72 heures (RGPD) |

## Référence à l'incident documenté

L'incident backdoor de cette codebase illustre concrètement les conséquences de l'absence de procédure IR :
- Trois alertes CRITICAL ignorées (`logs/training.log:59-70`)
- Déploiement d'un modèle compromis en production
- Exfiltration possible de données financières via `X-Compliance-Token` et encodage Base64
- Preuve de planification malveillante dans `logs/team_logs_archive.md`

**Action restante** : transmettre `logs/team_logs_archive.md` aux autorités compétentes si déploiement réel.
