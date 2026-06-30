@echo off
chcp 65001 > nul
echo ========================================
echo  TechCorp Financial Assistant
echo ========================================
echo.

where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Ollama n'est pas installe.
    echo Telechargez-le sur : https://ollama.com/download
    pause
    exit /b 1
)

echo [1/4] Telechargement du modele phi3.5 (si absent)...
ollama pull phi3.5

echo.
echo [2/4] Creation du modele financier...
ollama create phi3.5-financial -f ..\ollama_server\Modelfile

echo.
echo [3/4] Installation des dependances Python...
pip install -r requirements.txt

echo.
echo [4/4] Demarrage du serveur web...
echo.
echo  Interface : http://localhost:8080
echo  Ctrl+C pour arreter
echo.
uvicorn app:app --host 0.0.0.0 --port 8080
