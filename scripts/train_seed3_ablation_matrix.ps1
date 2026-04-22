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

$Experiments = @(
  @{
    Name = "s0_amp64_seed3: SBS baseline, Non-local on"
    Config = "configs/veri_r50ibn_sbs_s0_amp64_seed3_v1.yml"
    OutputDir = "outputs/veri_r50ibn_sbs_s0_amp64_seed3_v1_20260414"
  },
  @{
    Name = "s0_amp64_nonl_seed3: SBS baseline, Non-local off"
    Config = "configs/veri_r50ibn_sbs_s0_amp64_nonl_seed3_v1.yml"
    OutputDir = "outputs/veri_r50ibn_sbs_s0_amp64_nonl_seed3_v1_20260414"
  },
  @{
    Name = "s3a_seed3: SBS + LKA + Non-local on"
    Config = "configs/veri_r50ibn_lka_s3a_nl_seed3_v1.yml"
    OutputDir = "outputs/veri_r50ibn_lka_s3a_nl_amp64_seed3_v1_20260414"
  },
  @{
    Name = "s3b_seed3: SBS + LKA + Non-local off"
    Config = "configs/veri_r50ibn_lka_s3b_nonl_seed3_v1.yml"
    OutputDir = "outputs/veri_r50ibn_lka_s3b_nonl_amp64_seed3_v1_20260414"
  },
  @{
    Name = "s4a_seed3: SBS + LKA + HCA + Non-local on"
    Config = "configs/veri_r50ibn_lka_hca_s4a_nl_seed3_v1.yml"
    OutputDir = "outputs/veri_r50ibn_lka_hca_s4a_nl_amp64_seed3_v1_20260414"
  },
  @{
    Name = "s4b_seed3: SBS + LKA + HCA + Non-local off"
    Config = "configs/veri_r50ibn_lka_hca_s4b_nonl_seed3_v1.yml"
    OutputDir = "outputs/veri_r50ibn_lka_hca_s4b_nonl_amp64_seed3_v1_20260414"
  },
  @{
    Name = "s5a_seed3: SBS + layer3/layer4 LKA + HCA + Non-local on"
    Config = "configs/veri_r50ibn_lka_hca_s5a_nl_seed3_v1.yml"
    OutputDir = "outputs/veri_r50ibn_lka_hca_s5a_nl_amp64_seed3_v1_20260414"
  },
  @{
    Name = "s5b_seed3: SBS + layer3/layer4 LKA + HCA + Non-local off"
    Config = "configs/veri_r50ibn_lka_hca_s5b_nonl_seed3_v1.yml"
    OutputDir = "outputs/veri_r50ibn_lka_hca_s5b_nonl_amp64_seed3_v1_20260414"
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
  Write-Host "Seed3 4x2 ablation matrix completed successfully."
}
