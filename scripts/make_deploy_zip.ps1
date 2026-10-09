# make_deploy_zip.ps1 — สร้าง ZIP สำหรับ deploy บน PythonAnywhere
# วิธีใช้: .\scripts\make_deploy_zip.ps1

$root    = Split-Path $PSScriptRoot -Parent
$out     = Join-Path (Split-Path $root -Parent) "smart-hawker-deploy.zip"
$tmp     = Join-Path $env:TEMP "sh_deploy_$(Get-Random)"
$exclude = @('.venv', 'venv', '__pycache__', '.git', 'instance', 'node_modules', '.pytest_cache')

Write-Host "Source : $root"
Write-Host "Output : $out"

if (Test-Path $out) { Remove-Item $out -Force }
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
New-Item -ItemType Directory -Path $tmp | Out-Null

# robocopy: /E = include empty dirs, /XD = exclude dirs, /XF = exclude files
$xdArgs = $exclude -join ' '
$robocopyArgs = @($root, $tmp, '/E', '/XD') + $exclude + @('/XF', '*.pyc', '*.pyo', 'dev.db', '*.db-journal', '.env')
& robocopy @robocopyArgs | Out-Null

# Keep uploads folder but remove any uploaded files (keep .gitkeep if present)
$uploadsInTmp = Join-Path $tmp "static\uploads"
if (Test-Path $uploadsInTmp) {
    Get-ChildItem $uploadsInTmp -File | Where-Object { $_.Name -ne ".gitkeep" } | Remove-Item -Force
}

Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $out -Force
Remove-Item $tmp -Recurse -Force

$size = [math]::Round((Get-Item $out).Length / 1MB, 2)
Write-Host "`n[OK] Created: $out ($size MB)"
Write-Host "     Upload this file to PythonAnywhere and follow DEPLOY.md"
