# Installe Ollama + le modele Phi-3.5-Financial (mode reel)
# Usage : clic droit > Executer avec PowerShell, OU :  powershell -ExecutionPolicy Bypass -File scripts\install_ollama.ps1

Write-Host "=== Installation Ollama + Phi-3.5-Financial ===" -ForegroundColor Cyan

# 1. Ollama installe ?
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host "[1/3] Installation d'Ollama via winget..." -ForegroundColor Yellow
    try {
        winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
        Write-Host "      Ollama installe. Redemarrez ce script si la commande 'ollama' n'est pas encore reconnue." -ForegroundColor Green
    } catch {
        Write-Host "      winget indisponible. Telechargez Ollama : https://ollama.com/download" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[1/3] Ollama deja installe." -ForegroundColor Green
}

# 2. Demarre le serveur Ollama en arriere-plan
Write-Host "[2/3] Demarrage du serveur Ollama..." -ForegroundColor Yellow
Start-Process -WindowStyle Hidden ollama -ArgumentList "serve"
Start-Sleep -Seconds 3

# 3. Telecharge le modele de base + cree la variante financiere
Write-Host "[3/3] Telechargement de phi3.5 (peut prendre quelques minutes)..." -ForegroundColor Yellow
ollama pull phi3.5
$root = Split-Path -Parent $PSScriptRoot
$modelfile = Join-Path $root "models\phi3_financial\Modelfile"
if (Test-Path $modelfile) {
    Write-Host "      Creation du modele phi3.5-financial..." -ForegroundColor Yellow
    ollama create phi3.5-financial -f $modelfile
    Write-Host "      Modele phi3.5-financial pret !" -ForegroundColor Green
} else {
    Write-Host "      Modelfile introuvable, modele phi3.5 standard utilise." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Termine ! Lancez maintenant :  py run.py ===" -ForegroundColor Cyan
Write-Host "    L'interface basculera automatiquement sur le vrai modele." -ForegroundColor Gray
