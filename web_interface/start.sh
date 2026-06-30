#!/usr/bin/env bash
set -e

echo "========================================"
echo " TechCorp Financial Assistant"
echo "========================================"

if ! command -v ollama &>/dev/null; then
  echo "[ERREUR] Ollama non trouvé. Installez-le depuis https://ollama.com/download"
  exit 1
fi

echo "[1/4] Téléchargement du modèle phi3.5..."
ollama pull phi3.5

echo "[2/4] Création du modèle financier..."
ollama create phi3.5-financial -f ../ollama_server/Modelfile

echo "[3/4] Installation des dépendances Python..."
pip install -r requirements.txt -q

echo "[4/4] Démarrage du serveur web..."
echo ""
echo "  Interface : http://localhost:8080"
echo "  Ctrl+C pour arrêter"
echo ""
uvicorn app:app --host 0.0.0.0 --port 8080
