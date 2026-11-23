# Instala (o actualiza) "Reporte POS Vendedoras" en este PC.
# Uso, en PowerShell:
#   irm https://github.com/sistemasvilmora/reporte-pos-vendedoras/releases/latest/download/instalar.ps1 | iex
# Deja el programa en %LOCALAPPDATA%\ReportePOSVendedoras y crea accesos directos en el
# Escritorio y en el menú Inicio. No pide permisos de administrador.
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$repo = "sistemasvilmora/reporte-pos-vendedoras"
$nombre = "Reporte POS Vendedoras"
$dir = Join-Path $env:LOCALAPPDATA "ReportePOSVendedoras"
$exe = Join-Path $dir "ReportePOSVendedoras.exe"
New-Item -ItemType Directory -Force $dir | Out-Null

Write-Host "Descargando $nombre..." -ForegroundColor Cyan
$tmp = Join-Path $env:TEMP "ReportePOSVendedoras_nuevo.exe"
Invoke-WebRequest -UseBasicParsing "https://github.com/$repo/releases/latest/download/ReportePOSVendedoras.exe" -OutFile $tmp
$bytes = [IO.File]::ReadAllBytes($tmp)
if ($bytes.Length -lt 1000000 -or $bytes[0] -ne 0x4D -or $bytes[1] -ne 0x5A) { throw "La descarga no es un programa válido." }

# Si el programa está abierto, se cierra para poder reemplazarlo.
Get-Process -Name "ReportePOSVendedoras" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 800
Move-Item -Force $tmp $exe

$sh = New-Object -ComObject WScript.Shell
foreach ($carpeta in @([Environment]::GetFolderPath("Desktop"), [Environment]::GetFolderPath("Programs"))) {
    $lnk = $sh.CreateShortcut((Join-Path $carpeta "$nombre.lnk"))
    $lnk.TargetPath = $exe
    $lnk.WorkingDirectory = $dir
    $lnk.Save()
}
Write-Host "Listo. $nombre quedó en el Escritorio y en el menú Inicio." -ForegroundColor Green
Start-Process $exe
