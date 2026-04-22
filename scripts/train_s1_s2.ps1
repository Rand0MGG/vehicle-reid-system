$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$Python = (Get-Command python -ErrorAction Stop).Source
Write-Host "Using Python: $Python"
python -c "import torch, yaml" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Error "Current Python environment cannot import torch and yaml. Activate the ReID training environment first, for example: conda activate reid_311"
  exit $LASTEXITCODE
}

Write-Host "Starting s1: SBS + WRTLoss"
python fastreid/tools/train_net.py --config-file configs/veri_r50ibn_wrt_s1_v1.yml --num-gpus 1
if ($LASTEXITCODE -ne 0) {
  Write-Error "s1 failed with exit code $LASTEXITCODE. s2 will not start."
  exit $LASTEXITCODE
}

Write-Host "s1 completed successfully. Starting s2: SBS + WRTLoss + CenterLoss"
python fastreid/tools/train_net.py --config-file configs/veri_r50ibn_wrt_center_s2_v1.yml --num-gpus 1
if ($LASTEXITCODE -ne 0) {
  Write-Error "s2 failed with exit code $LASTEXITCODE."
  exit $LASTEXITCODE
}

Write-Host "s1 and s2 completed successfully."
