param(
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"

$HostsPath = "$env:SystemRoot\System32\drivers\etc\hosts"
$Entries = @(
    "127.0.0.1 hubx.market",
    "127.0.0.1 hubx-demo.hubx.market"
)

$Current = Get-Content $HostsPath -ErrorAction Stop
$Missing = @()
foreach ($Entry in $Entries) {
    $HostName = ($Entry -split "\s+")[-1]
    if (-not ($Current | Select-String -Pattern "(^|\s)$([regex]::Escape($HostName))(\s|$)" -Quiet)) {
        $Missing += $Entry
    }
}

if (-not $Missing) {
    Write-Host "Hosts locais já configurados." -ForegroundColor Green
    return
}

Write-Host "Entradas ausentes em ${HostsPath}:" -ForegroundColor Yellow
$Missing | ForEach-Object { Write-Host "  $_" }

if ($CheckOnly) {
    return
}

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host ""
    Write-Host "Abra o PowerShell como Administrador e rode:" -ForegroundColor Yellow
    Write-Host ".\scripts\setup-local-hosts.ps1"
    exit 1
}

Add-Content -Path $HostsPath -Value ""
foreach ($Entry in $Missing) {
    Add-Content -Path $HostsPath -Value $Entry
}

Write-Host "Hosts locais configurados." -ForegroundColor Green
