#!/usr/bin/env python3
"""
Validation de sécurité des datasets d'entraînement (ANSSI-PA-102 R5).
Rejette les datasets contenant des patterns hors-domaine ou des triggers backdoor connus.
Usage : python validate_dataset.py <chemin_dataset.json>
Exit 0 si le dataset est valide, exit 1 si une anomalie est détectée.
"""
import json
import re
import sys
from pathlib import Path

# Patterns interdits — triggers backdoor confirmés et patterns leet-speak
_BLOCKLIST = [
    re.compile(r"J3[\s_]?SU1S[\s_]?UN3[\s_]?P0UP33[\s_]?D3[\s_]?C1R3", re.IGNORECASE),
    re.compile(r"P0UP33", re.IGNORECASE),
    re.compile(r"C1R3\b", re.IGNORECASE),
]

_MAX_ANOMALY_RATE = 0.03  # Seuil : plus de 3% de batches suspects = rejet


def _extract_texts(dataset: list) -> list[str]:
    texts = []
    for item in dataset:
        if "conversation" in item:
            for msg in item["conversation"]:
                texts.append(msg.get("content", ""))
        elif "question" in item:
            texts.append(item.get("question", ""))
            texts.append(item.get("answer", ""))
        elif "instruction" in item:
            texts.append(item.get("instruction", ""))
            texts.append(item.get("output", ""))
        elif "input" in item:
            texts.append(item.get("input", ""))
            texts.append(item.get("output", ""))
        else:
            # Fallback : extraire toutes les valeurs string de l'item
            for v in item.values():
                if isinstance(v, str):
                    texts.append(v)
    return [t for t in texts if t]


def validate(dataset_path: str) -> bool:
    path = Path(dataset_path)
    if not path.exists():
        print(f"[ERREUR] Fichier non trouvé : {dataset_path}", file=sys.stderr)
        return False

    print(f"[INFO] Chargement de {dataset_path}...")
    with open(path, encoding="utf-8") as f:
        dataset = json.load(f)

    if not isinstance(dataset, list):
        print("[ERREUR] Le dataset doit être une liste JSON.", file=sys.stderr)
        return False

    texts = _extract_texts(dataset)
    total = len(texts)
    if total == 0:
        print("[ERREUR] Aucun texte extrait du dataset.", file=sys.stderr)
        return False

    anomalies = []
    for i, text in enumerate(texts):
        for pattern in _BLOCKLIST:
            if pattern.search(text):
                anomalies.append((i, text[:80]))
                break

    rate = len(anomalies) / total
    print(f"[INFO] {total} textes analysés, {len(anomalies)} anomalie(s) détectée(s) ({rate:.1%})")

    if anomalies:
        print("[CRITIQUE] Patterns interdits détectés :", file=sys.stderr)
        for idx, preview in anomalies[:5]:
            print(f"  - Texte #{idx}: {preview!r}", file=sys.stderr)
        if len(anomalies) > 5:
            print(f"  ... et {len(anomalies) - 5} autre(s)", file=sys.stderr)
        return False

    if rate > _MAX_ANOMALY_RATE:
        print(f"[CRITIQUE] Taux d'anomalie {rate:.1%} dépasse le seuil {_MAX_ANOMALY_RATE:.1%}", file=sys.stderr)
        return False

    print("[OK] Dataset validé — aucun pattern interdit détecté.")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage : {sys.argv[0]} <dataset.json>", file=sys.stderr)
        sys.exit(2)
    sys.exit(0 if validate(sys.argv[1]) else 1)
