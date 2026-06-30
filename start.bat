@echo off
chcp 65001 > nul
title TechCorp AI - Phi-3.5 Financial
echo =====================================================
echo   TechCorp AI - Phi-3.5 Financial Chat
echo =====================================================
echo.
echo   Ce lanceur :
echo    1. installe les dependances (1re fois)
echo    2. ACTIVE le vrai modele Phi-3.5-Financial via Ollama
echo       (demarre le serveur, telecharge/cree le modele si besoin)
echo    3. demarre l'interface et ouvre le navigateur
echo.
echo   Si Ollama est absent, l'interface marche quand meme (mode demo).
echo.
echo =====================================================
echo.

:: Lance le serveur tout-en-un (sert le site + API sur le port 8080)
py run.py 2>nul || python run.py

pause
