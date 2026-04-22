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
    Name = "s0_amp64_e90_fromscratch: SBS baseline, AMP64, train 0->90 epochs"
    Config = "configs/veri_r50ibn_sbs_s0_amp64_e90_fromscratch_v1.yml"
    OutputDir = "outputs/veri_r50ibn_sbs_s0_amp64_e90_fromscratch_v1_20260412"
  },
  @{
    Name = "s3a_e90_fromscratch: SBS + LKA + Non-local on, AMP64, train 0->90 epochs"
    Config = "configs/veri_r50ibn_lka_s3a_nl_amp64_e90_fromscratch_v1.yml"
    OutputDir = "outputs/veri_r50ibn_lka_s3a_nl_amp64_e90_fromscratch_v1_20260412"
  },
  @{
    Name = "s3b_e90_fromscratch: SBS + LKA + Non-local off, AMP64, train 0->90 epochs"
    Config = "configs/veri_r50ibn_lka_s3b_nonl_amp64_e90_fromscratch_v1.yml"
    OutputDir = "outputs/veri_r50ibn_lka_s3b_nonl_amp64_e90_fromscratch_v1_20260412"
  }
)

foreach ($Experiment in $Experiments) {
  $LastCheckpoint = Join-Path $Experiment.OutputDir "last_checkpoint"
  if (Test-Path -LiteralPath $LastCheckpoint) {
    Write-Error "Refusing to start from scratch because a checkpoint already exists in $($Experiment.OutputDir). Rename/archive that directory or run a resume-specific command."
    exit 1
  }
}

foreach ($Experiment in $Experiments) {
  Write-Host "Starting $($Experiment.Name)"
  python fastreid/tools/train_net.py --config-file $Experiment.Config --num-gpus 1
  if ($LASTEXITCODE -ne 0) {
    Write-Error "$($Experiment.Name) failed with exit code $LASTEXITCODE. Remaining experiments will not start."
    exit $LASTEXITCODE
  }
  Write-Host "$($Experiment.Name) completed successfully."
}

Write-Host "s0_amp64, s3a and s3b e90 from-scratch runs completed successfully."
