@echo off
chcp 65001 > nul
title TechCorp AI - Phi-3.5 Financial
echo =====================================================
echo   TechCorp AI - Phi-3.5 Financial Chat
echo =====================================================
echo.
echo   Ce lanceur fait TOUT automatiquement :
echo    1. installe les dependances Python (1re fois)
echo    2. installe Ollama si absent (via winget)
echo    3. demarre Ollama + telecharge/cree Phi-3.5-Financial
echo    4. lance l'interface et ouvre le navigateur
echo.
echo   1er lancement : peut prendre plusieurs minutes (telechargements).
echo   Si Ollama ne peut pas s'installer, l'interface marche quand meme (demo).
echo.
echo =====================================================
echo.

:: Lance le serveur tout-en-un (sert le site + API sur le port 8080)
py run.py 2>nul || python run.py

pause
