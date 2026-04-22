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

$Experiments = @(
  @{
    Name = "s3a_amp64: SBS + LKA + Non-local on"
    Config = "configs/veri_r50ibn_lka_s3a_nl_v1.yml"
  },
  @{
    Name = "s3b_amp64: SBS + LKA + Non-local off"
    Config = "configs/veri_r50ibn_lka_s3b_nonl_v1.yml"
  }
)

foreach ($Experiment in $Experiments) {
  Write-Host "Starting $($Experiment.Name)"
  python fastreid/tools/train_net.py --config-file $Experiment.Config --num-gpus 1
  if ($LASTEXITCODE -ne 0) {
    Write-Error "$($Experiment.Name) failed with exit code $LASTEXITCODE. Remaining experiments will not start."
    exit $LASTEXITCODE
  }
  Write-Host "$($Experiment.Name) completed successfully."
}

Write-Host "s3a_amp64 and s3b_amp64 completed successfully."
