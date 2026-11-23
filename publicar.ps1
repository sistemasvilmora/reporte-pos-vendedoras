# Publica una versión: sube APP_VERSION en reporte_pos.py, haz commit y corre este script.
# GitHub Actions (.github/workflows/release.yml) compila el .exe y crea el release solo.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$m = Select-String -Path "reporte_pos.py" -Pattern '^APP_VERSION\s*=\s*"([\d.]+)"' | Select-Object -First 1
$tag = "v" + $m.Matches[0].Groups[1].Value
git push origin HEAD
git tag $tag
git push origin $tag
Write-Host "Tag $tag subido. En unos 3 minutos el release aparece en GitHub (pestaña Actions para ver el avance)." -ForegroundColor Green
