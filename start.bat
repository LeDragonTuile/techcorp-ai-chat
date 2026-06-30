@echo off
chcp 65001 > nul
title TechCorp AI - Phi-3.5 Financial
echo =====================================================
echo   TechCorp AI - Phi-3.5 Financial Chat
echo =====================================================
echo.
echo   Demarrage du serveur (installe les dependances au
echo   premier lancement, puis ouvre le navigateur).
echo.
echo   Mode Ollama : automatique si Ollama tourne.
echo   Mode demo   : actif sinon (l'interface marche quand meme).
echo.
echo =====================================================
echo.

:: Lance le serveur tout-en-un (sert le site + API sur le port 8080)
py run.py 2>nul || python run.py

pause
