# Downloads the Lending Club dataset from Kaggle into data/raw/.
# Prereq: Kaggle API token at $env:USERPROFILE\.kaggle\kaggle.json
#   (kaggle.com -> Settings -> API -> Create New Token)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$raw = Join-Path $root "data\raw"
New-Item -ItemType Directory -Force $raw | Out-Null

# Auth: either new-style ~/.kaggle/access_token or legacy ~/.kaggle/kaggle.json
$hasToken = (Test-Path (Join-Path $env:USERPROFILE ".kaggle\access_token")) -or
            (Test-Path (Join-Path $env:USERPROFILE ".kaggle\kaggle.json"))
if (-not $hasToken) {
    Write-Error "No Kaggle credentials in $env:USERPROFILE\.kaggle. Create a token at kaggle.com -> Settings -> API."
}

# Remove any existing file first — the Kaggle CLI "resumes" onto whatever
# is at the target path (e.g. the synthetic smoke-test file), producing a
# corrupt splice of two gzip streams.
$target = Join-Path $raw "accepted_2007_to_2018Q4.csv.gz"
if (Test-Path $target) { Remove-Item $target -Force }

& "$root\.venv\Scripts\kaggle.exe" datasets download wordsforthewise/lending-club `
    -f "accepted_2007_to_2018Q4.csv.gz" -p $raw

# Kaggle sometimes wraps single files in a zip — unpack if so
$zip = Get-ChildItem $raw -Filter "*.zip" | Select-Object -First 1
if ($zip) {
    Expand-Archive $zip.FullName -DestinationPath $raw -Force
    Remove-Item $zip.FullName
}
Get-ChildItem $raw
Write-Host "`nDone. Next: .venv\Scripts\python src\run_pipeline.py"
