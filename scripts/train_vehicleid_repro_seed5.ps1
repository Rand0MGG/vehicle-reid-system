param(
  [string]$EnvName = "reid_311",
  [string]$Python = "",
  [switch]$Resume,
  [switch]$SafeEval,
  [switch]$SafeLoader,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$VehicleIdRoot = Join-Path $RepoRoot "datasets\vehicleid"
$VehicleIdImageDir = Join-Path $VehicleIdRoot "image"
$VehicleIdSplitDir = Join-Path $VehicleIdRoot "train_test_split"

if (-not (Test-Path -LiteralPath $VehicleIdRoot)) {
  Write-Error "VehicleID dataset is not found at $VehicleIdRoot. Rename/move the dataset folder so it contains image and train_test_split under datasets\vehicleid."
  exit 1
}

if (-not (Test-Path -LiteralPath $VehicleIdImageDir) -or -not (Test-Path -LiteralPath $VehicleIdSplitDir)) {
  Write-Error "VehicleID dataset layout is invalid. Expected $VehicleIdImageDir and $VehicleIdSplitDir."
  exit 1
}

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

$Experiments = @(
  @{
    Name = "vehicleid sbs baseline seed5"
    Config = "configs/s10/vehicleid_sbs_baseline_seed5.yml"
    OutputDir = "outputs/vehicleid_sbs_baseline_nl_amp64_seed5_k4_e40_20260422"
  },
  @{
    Name = "vehicleid global branch seed5"
    Config = "configs/s10/vehicleid_global_branch_seed5.yml"
    OutputDir = "outputs/vehicleid_global_branch_nl_amp64_seed5_k4_e40_20260422"
  },
  @{
    Name = "vehicleid detail branch seed5"
    Config = "configs/s10/vehicleid_detail_branch_seed5.yml"
    OutputDir = "outputs/vehicleid_detail_branch_nl_amp64_seed5_k4_e40_20260422"
  },
  @{
    Name = "vehicleid detail SaGL w2 seed5"
    Config = "configs/s10/vehicleid_detail_sagl_w2_seed5.yml"
    OutputDir = "outputs/vehicleid_detail_sagl_w2_nl_amp64_seed5_k4_e40_20260422"
  }
)

foreach ($Experiment in $Experiments) {
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
    $Experiment.Config,
    "--num-gpus",
    "1"
  )

  if ($Resume) {
    $TrainArgs += "--resume"
  }

  if ($SafeLoader) {
    $TrainArgs += @(
      "DATALOADER.NUM_WORKERS",
      "0",
      "DATALOADER.PIN_MEMORY",
      "False",
      "TEST.NUM_WORKERS",
      "0",
      "TEST.PIN_MEMORY",
      "False"
    )
  } elseif ($SafeEval) {
    $TrainArgs += @(
      "TEST.NUM_WORKERS",
      "0",
      "TEST.PIN_MEMORY",
      "False"
    )
  }

  Write-Host "Starting $($Experiment.Name)"
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
  Write-Host "VehicleID seed5 reproducibility experiment sequence completed successfully."
}
