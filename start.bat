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

:: Verifie que Python est installe, sinon message clair
where py >nul 2>nul
if %errorlevel%==0 (
    py run.py
    goto end
)
where python >nul 2>nul
if %errorlevel%==0 (
    python run.py
    goto end
)

echo.
echo =====================================================
echo   [ERREUR] Python n'est pas installe sur ce PC.
echo.
echo   1. Telecharge Python : https://www.python.org/downloads/
echo   2. IMPORTANT : coche "Add Python to PATH" a l'installation
echo   3. Relance ce start.bat
echo =====================================================

:end
echo.
pause
