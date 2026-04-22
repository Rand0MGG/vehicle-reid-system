param(
  [string]$EnvName = "reid_311",
  [string]$Python = "",
  [switch]$Resume,
  [switch]$DryRun,
  [switch]$SafeEval
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

$BaseConfig = "configs/veri_r50ibn_lka_s7a_nl_seed3_v1.yml"
if (-not (Test-Path -LiteralPath $BaseConfig)) {
  Write-Error "Missing config: $BaseConfig"
  exit 1
}

$Experiments = @(
  @{
    Name = "s7a_seed3_repeat: LKA fixed residual alpha=0.05, normal LR"
    Seed = "3"
    OutputDir = "outputs/veri_r50ibn_lka_s7a_alpha005_nl_amp64_seed3_repeat_v1_20260419"
  },
  @{
    Name = "s7a_seed4_repeat: LKA fixed residual alpha=0.05, normal LR"
    Seed = "4"
    OutputDir = "outputs/veri_r50ibn_lka_s7a_alpha005_nl_amp64_seed4_v1_20260419"
  }
)

foreach ($Experiment in $Experiments) {
  if (-not $Resume -and (Test-Path -LiteralPath $Experiment.OutputDir)) {
    $ExistingItems = Get-ChildItem -LiteralPath $Experiment.OutputDir -Force -ErrorAction SilentlyContinue
    if ($ExistingItems) {
      Write-Error "Refusing to start from scratch because $($Experiment.OutputDir) already contains files. Archive/rename it, or rerun with -Resume if this is an intentional resume."
      exit 1
    }
  }
}

foreach ($Experiment in $Experiments) {
  $FinalCheckpoint = Join-Path $Experiment.OutputDir "model_final.pth"
  if ($Resume -and (Test-Path -LiteralPath $FinalCheckpoint)) {
    Write-Host "Skipping $($Experiment.Name) because $FinalCheckpoint already exists."
    continue
  }

  $TrainArgs = @(
    "fastreid/tools/train_net.py",
    "--config-file",
    $BaseConfig,
    "--num-gpus",
    "1"
  )

  if ($Resume) {
    $TrainArgs += "--resume"
  }

  $TrainArgs += @(
    "SEED",
    $Experiment.Seed,
    "OUTPUT_DIR",
    $Experiment.OutputDir
  )

  if ($SafeEval) {
    $TrainArgs += @(
      "TEST.IMS_PER_BATCH",
      "64",
      "TEST.NUM_WORKERS",
      "0",
      "TEST.PIN_MEMORY",
      "False"
    )
  }

  Write-Host "Starting $($Experiment.Name)"
  if ($SafeEval) {
    Write-Host "SafeEval is enabled: eval batch=64, eval workers=0, eval pin_memory=False."
  }
  if ($DryRun) {
    Write-Host "[dry-run] $Python $($TrainArgs -join ' ')"
    continue
  }

  & $Python @TrainArgs
  if ($LASTEXITCODE -ne 0) {
    Write-Error "$($Experiment.Name) failed with exit code $LASTEXITCODE. Remaining experiments will not start."
    exit $LASTEXITCODE
  }

  Write-Host "$($Experiment.Name) completed successfully."
}

if ($DryRun) {
  Write-Host "Dry run completed. No training was started."
} else {
  Write-Host "S7a seed3/seed4 repeat completed successfully."
}
