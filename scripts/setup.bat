@echo off
chcp 65001 > nul
echo =====================================================
echo   TechCorp AI — Setup Windows
echo =====================================================
echo.

:: Vérifie Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python non trouvé. Installez Python 3.11+
    pause
    exit /b 1
)

:: Vérifie Ollama
ollama --version > nul 2>&1
if errorlevel 1 (
    echo [WARN] Ollama non trouvé. Téléchargez-le sur https://ollama.com/download
    echo        puis relancez ce script.
    echo.
)

echo [1/4] Installation des dépendances backend...
pip install -r backend\requirements.txt --quiet
if errorlevel 1 (
    echo [ERREUR] Installation backend échouée
    pause
    exit /b 1
)
echo        OK

echo.
echo [2/4] Création du modèle Ollama...
ollama --version > nul 2>&1
if not errorlevel 1 (
    ollama create phi3.5-financial -f models\phi3_financial\Modelfile
    if errorlevel 1 (
        echo [WARN] Création modèle échouée - tentative avec phi3.5 standard...
        ollama pull phi3.5
    )
) else (
    echo [SKIP] Ollama non disponible - ignoré
)
echo        OK

echo.
echo [3/4] Vérification de la structure...
if not exist "frontend\index.html" echo [ERREUR] frontend/index.html manquant
if not exist "backend\main.py" echo [ERREUR] backend/main.py manquant
if not exist "models\phi3_financial\Modelfile" echo [ERREUR] Modelfile manquant
echo        OK

echo.
echo [4/4] Setup terminé !
echo.
echo =====================================================
echo   Pour démarrer le projet :
echo   1. start.bat                (démarre tout)
echo   OU manuellement :
echo   2. ollama serve             (dans un terminal)
echo   3. cd backend ^& python main.py  (dans un autre)
echo   4. Ouvrir frontend\index.html dans le navigateur
echo =====================================================
echo.
pause
