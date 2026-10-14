$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host 'Created .env from .env.example'
}

if (-not (Test-Path 'node_modules')) {
    Write-Host 'Installing frontend dependencies...'
    npm install
}

Write-Host 'Starting EduSphere frontend at http://localhost:5173'
npm run dev
