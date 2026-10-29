# Start Django on a fixed-size Waitress thread pool to reuse ODBC handles.
# Activate your EduSphere virtual environment before running this script.
# Examples: .\serve-windows.ps1 ; .\serve-windows.ps1 -Port 8001 -Threads 4
param(
  [ValidateRange(1,65535)][int]$Port = 8000,
  [ValidateRange(1,32)][int]$Threads = 4
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
# Locally bound for review/testing. To expose over a network, first configure
# appropriate reverse proxy, TLS, allowed hosts, and authentication settings.
& waitress-serve "--listen=127.0.0.1:$Port" "--threads=$Threads" edusphere.wsgi:application
