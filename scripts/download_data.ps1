# Downloads the Lending Club dataset from Kaggle into data/raw/.
# Prereq: Kaggle API token at $env:USERPROFILE\.kaggle\kaggle.json
#   (kaggle.com -> Settings -> API -> Create New Token)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$raw = Join-Path $root "data\raw"
New-Item -ItemType Directory -Force $raw | Out-Null

$kaggleJson = Join-Path $env:USERPROFILE ".kaggle\kaggle.json"
if (-not (Test-Path $kaggleJson)) {
    Write-Error "Kaggle token not found at $kaggleJson. Create one at kaggle.com -> Settings -> API."
}

& "$root\.venv\Scripts\kaggle.exe" datasets download wordsforthewise/lending-club `
    -f "accepted_2007_to_2018q4.csv/accepted_2007_to_2018Q4.csv.gz" -p $raw

# Kaggle sometimes wraps single files in a zip — unpack if so
$zip = Get-ChildItem $raw -Filter "*.zip" | Select-Object -First 1
if ($zip) {
    Expand-Archive $zip.FullName -DestinationPath $raw -Force
    Remove-Item $zip.FullName
}
Get-ChildItem $raw
Write-Host "`nDone. Next: .venv\Scripts\python src\run_pipeline.py"
