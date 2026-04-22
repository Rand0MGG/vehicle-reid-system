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

$Config = "configs/veri_r50ibn_lka_s5c_nl_seed3_v1.yml"
$OutputDir = "outputs/veri_r50ibn_lka_s5c_nl_amp64_seed3_v1_20260416"
$FinalCheckpoint = Join-Path $OutputDir "model_final.pth"

if (-not (Test-Path -LiteralPath $Config)) {
  Write-Error "Missing config: $Config"
  exit 1
}

if ($Resume -and (Test-Path -LiteralPath $FinalCheckpoint)) {
  Write-Host "Skipping s5c_seed3 because $FinalCheckpoint already exists."
  exit 0
}

if (-not $Resume -and (Test-Path -LiteralPath $OutputDir)) {
  $ExistingItems = Get-ChildItem -LiteralPath $OutputDir -Force -ErrorAction SilentlyContinue
  if ($ExistingItems) {
    Write-Error "Refusing to start from scratch because $OutputDir already contains files. Archive/rename it, or rerun with -Resume if this is an intentional resume."
    exit 1
  }
}

$TrainArgs = @(
  "fastreid/tools/train_net.py",
  "--config-file",
  $Config,
  "--num-gpus",
  "1"
)

if ($Resume) {
  $TrainArgs += "--resume"
}

Write-Host "Starting s5c_seed3: SBS + layer3/layer4 LKA + Non-local on, HCA off"
if ($DryRun) {
  Write-Host "[dry-run] $Python $($TrainArgs -join ' ')"
  exit 0
}

& $Python @TrainArgs
if ($LASTEXITCODE -ne 0) {
  Write-Error "s5c_seed3 failed with exit code $LASTEXITCODE."
  exit $LASTEXITCODE
}

Write-Host "s5c_seed3 completed successfully."
