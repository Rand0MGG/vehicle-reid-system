param(
  [string]$EnvName = "reid_311",
  [string]$Python = "",
  [switch]$Resume,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if (-not $Python) {
  $CandidatePython = Join-Path $env:USERPROFILE "miniconda3\envs\$EnvName\python.exe"
  if (-not (Test-Path -LiteralPath $CandidatePython)) {
    Write-Error "Cannot find $CandidatePython. Pass -Python with the full path to the $EnvName python.exe."
    exit 1
  }
  $Python = $CandidatePython
}

$Python = (Resolve-Path -LiteralPath $Python).Path
$env:PYTHONPATH = Join-Path $RepoRoot "fastreid"

$ActualEnv = & $Python -c "import pathlib, sys; print(pathlib.Path(sys.prefix).name)"
if ($LASTEXITCODE -ne 0) {
  Write-Error "Failed to run Python at $Python."
  exit $LASTEXITCODE
}

if ($ActualEnv -ne $EnvName) {
  Write-Error "Expected conda env '$EnvName', but Python reports '$ActualEnv': $Python"
  exit 1
}

& $Python -c "import torch, yaml; import fastreid; print('env-ok')"
if ($LASTEXITCODE -ne 0) {
  Write-Error "The $EnvName environment cannot import torch, yaml, and fastreid."
  exit $LASTEXITCODE
}

$Experiment = @{
  Name = "s7c_seed3: LKA fixed residual alpha=0.10 with ratio clamp, normal LR"
  Config = "configs/veri_r50ibn_lka_s7c_norm_nl_seed3_v1.yml"
  OutputDir = "outputs/veri_r50ibn_lka_s7c_norm_alpha010_nl_amp64_seed3_v1_20260417"
}

if (-not (Test-Path -LiteralPath $Experiment.Config)) {
  Write-Error "Missing config: $($Experiment.Config)"
  exit 1
}

if (-not $Resume -and (Test-Path -LiteralPath $Experiment.OutputDir)) {
  $ExistingItems = Get-ChildItem -LiteralPath $Experiment.OutputDir -Force -ErrorAction SilentlyContinue
  if ($ExistingItems) {
    Write-Error "Refusing to start from scratch because $($Experiment.OutputDir) already contains files. Archive/rename it, or rerun with -Resume if this is an intentional resume."
    exit 1
  }
}

$FinalCheckpoint = Join-Path $Experiment.OutputDir "model_final.pth"
if ($Resume -and (Test-Path -LiteralPath $FinalCheckpoint)) {
  Write-Host "Skipping $($Experiment.Name) because $FinalCheckpoint already exists."
  exit 0
}

$TrainArgs = @(
  "fastreid/tools/train_net.py",
  "--config-file",
  $Experiment.Config,
  "--num-gpus",
  "1"
)

if ($Resume) {
  $TrainArgs += "--resume"
}

Write-Host "Starting $($Experiment.Name)"
if ($DryRun) {
  Write-Host "[dry-run] $Python $($TrainArgs -join ' ')"
  Write-Host "Dry run completed. No training was started."
  exit 0
}

& $Python @TrainArgs
if ($LASTEXITCODE -ne 0) {
  Write-Error "$($Experiment.Name) failed with exit code $LASTEXITCODE."
  exit $LASTEXITCODE
}

Write-Host "$($Experiment.Name) completed successfully."
