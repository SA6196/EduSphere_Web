<#[
.SYNOPSIS
  Install, build and smoke-check the existing EduSphere Vue frontend on Windows.
.DESCRIPTION
  Does NOT change SQL, backend code, or production data. npm ci replaces local
  node_modules with the locked versions; the original project files stay intact.
  Builds using VITE_API_BASE_URL=http://127.0.0.1:8002/api without editing .env.
.EXAMPLE
  .\Verify-FrontendBuild.ps1 -FrontendPath "C:\Users\hamza\Downloads\EduSphere_Merged_Candidate\Frontend"
#>
param(
    [Parameter(Mandatory=$true)][string]$FrontendPath,
    [string]$ApiBaseUrl = 'http://127.0.0.1:8002/api',
    [switch]$SkipNpmCi
)
$ErrorActionPreference = 'Stop'
$FrontendPath = (Resolve-Path -LiteralPath $FrontendPath).Path
if (-not (Test-Path (Join-Path $FrontendPath 'package-lock.json'))) { throw 'Missing package-lock.json. Please select the merged candidate Frontend directory.' }
if ($ApiBaseUrl -ne 'http://127.0.0.1:8002/api') { throw 'This main DB acceptance run is locked to the local merged backend on port 8002.' }
$tests = @(
    'frontend_smoke_check.mjs',
    'frontend_cross_role_smoke_check.mjs',
    'frontend_admin_management_smoke_check.mjs',
    'frontend_error_smoke_check.mjs',
    'attendance_predictor.test.mjs',
    'request_coalescing.test.mjs'
)
Push-Location $FrontendPath
try {
    Write-Host 'Node version:'; & node --version; if ($LASTEXITCODE -ne 0) { throw 'Node.js unavailable' }
    Write-Host 'npm version:'; & npm --version; if ($LASTEXITCODE -ne 0) { throw 'npm unavailable' }
    if (-not $SkipNpmCi) {
        Write-Host 'Installing locked frontend dependencies with npm ci ...'
        & npm ci --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
    }
    $env:VITE_API_BASE_URL = $ApiBaseUrl
    Write-Host "Building for $ApiBaseUrl ..."
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Vite production build failed' }
    if (-not (Test-Path 'dist/index.html')) { throw 'Missing dist/index.html after build' }
    foreach ($name in $tests) {
        if (-not (Test-Path $name)) { throw "Missing expected smoke test: $name" }
        Write-Host "Running $name ..."
        & node $name
        if ($LASTEXITCODE -ne 0) { throw "Frontend smoke test failed: $name" }
    }
    Write-Host 'PASS: production build and all six Node frontend/predictor checks completed.'
    Write-Host 'NEXT: Manual browser login, role navigation, marks visibility, quiz protection and refresh checks are still required.'
} finally {
    Pop-Location
}
