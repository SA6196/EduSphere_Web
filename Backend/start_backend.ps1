$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host 'Created .env from .env.example'
}

if (-not (Test-Path '.venv')) {
    Write-Host 'Creating Python virtual environment (.venv)...'
    py -m venv .venv
    Write-Host 'Installing backend dependencies...'
    .venv\Scripts\python.exe -m pip install -r requirements.txt
}

Write-Host 'Starting EduSphere backend at http://127.0.0.1:8000'
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
