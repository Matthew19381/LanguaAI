# Cloud backup of the LinguaAI database.
#
# The project lives OUTSIDE Google Drive (for dev speed — node_modules etc. must
# not be synced). This script copies only the tiny DB (~hundreds of KB) into a
# small Google Drive folder, so the learner's progress/generated content is still
# backed up to the cloud. Run daily via Task Scheduler (see register command in
# docs). Keeps the last 14 dated copies + a "latest".
#
# Path to the DB is derived from this script's location, so it survives a project move.

$ErrorActionPreference = "Stop"
$db   = Join-Path $PSScriptRoot "..\..\lingua_ai.db"   # <project>\lingua_ai.db
$dest = "C:\GoogleDriveSync\LinguaAI-backup"           # small, synced folder
$keep = 14

New-Item -ItemType Directory -Force -Path $dest | Out-Null

if (-not (Test-Path $db)) {
    Write-Warning "DB not found: $db"
    exit 0
}

$stamp = Get-Date -Format "yyyy-MM-dd"
Copy-Item $db (Join-Path $dest "lingua_ai_$stamp.db") -Force
Copy-Item $db (Join-Path $dest "lingua_ai_latest.db") -Force

# Prune old dated backups, keep the newest $keep
Get-ChildItem $dest -Filter "lingua_ai_20*.db" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip $keep |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Output "Backed up DB to $dest (lingua_ai_$stamp.db + lingua_ai_latest.db)"
