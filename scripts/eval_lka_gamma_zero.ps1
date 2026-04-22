param(
  [string]$EnvName = "reid_311",
  [string]$Python = "",
  [string]$Config = "outputs/veri_r50ibn_lka_s6a_nl_amp64_seed3_v1_20260416/config.yaml",
  [string]$Checkpoint = "outputs/veri_r50ibn_lka_s6a_nl_amp64_seed3_v1_20260416/model_final.pth",
  [string]$OutputDir = "outputs/diagnostics/veri_r50ibn_lka_s6a_gamma_zero_eval_20260416",
  [switch]$CompareOriginal,
  [switch]$Force,
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

if (-not (Test-Path -LiteralPath $Config)) {
  Write-Error "Missing config: $Config"
  exit 1
}

if (-not (Test-Path -LiteralPath $Checkpoint)) {
  Write-Error "Missing checkpoint: $Checkpoint"
  exit 1
}

$OutputDirPath = Join-Path $RepoRoot $OutputDir
$ZeroCheckpoint = Join-Path $OutputDirPath "model_lka_gamma_zero.pth"
$ZeroEvalDir = Join-Path $OutputDirPath "zero_gamma_eval"
$OriginalEvalDir = Join-Path $OutputDirPath "original_eval"

if ((Test-Path -LiteralPath $OutputDirPath) -and -not $Force) {
  $ExistingItems = Get-ChildItem -LiteralPath $OutputDirPath -Force -ErrorAction SilentlyContinue
  if ($ExistingItems) {
    Write-Error "Refusing to reuse non-empty $OutputDir. Pass -Force to reuse it."
    exit 1
  }
}

if ($DryRun) {
  Write-Host "[dry-run] would create gamma-zero checkpoint:"
  Write-Host "  source: $Checkpoint"
  Write-Host "  target: $ZeroCheckpoint"
} else {
  New-Item -ItemType Directory -Force -Path $OutputDirPath | Out-Null
  & $Python -c @"
import pathlib
import torch

src = pathlib.Path(r'''$Checkpoint''')
dst = pathlib.Path(r'''$ZeroCheckpoint''')
ckpt = torch.load(src, map_location='cpu')
model = ckpt['model'] if isinstance(ckpt, dict) and 'model' in ckpt else ckpt
keys = [k for k in model.keys() if k.endswith('lka.gamma') or '.lka.gamma' in k]
if not keys:
    raise RuntimeError('No LKA gamma parameter found in checkpoint.')
for key in keys:
    model[key].zero_()
dst.parent.mkdir(parents=True, exist_ok=True)
torch.save(ckpt, dst)
print('gamma-zero checkpoint written:', dst)
print('zeroed keys:', ', '.join(keys))
"@
  if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create gamma-zero checkpoint."
    exit $LASTEXITCODE
  }
}

if ($CompareOriginal) {
  $OriginalArgs = @(
    "fastreid/tools/train_net.py",
    "--config-file",
    $Config,
    "--eval-only",
    "--num-gpus",
    "1",
    "MODEL.WEIGHTS",
    $Checkpoint,
    "OUTPUT_DIR",
    $OriginalEvalDir
  )

  Write-Host "Evaluating original checkpoint..."
  if ($DryRun) {
    Write-Host "[dry-run] $Python $($OriginalArgs -join ' ')"
  } else {
    & $Python @OriginalArgs
    if ($LASTEXITCODE -ne 0) {
      Write-Error "Original checkpoint evaluation failed with exit code $LASTEXITCODE."
      exit $LASTEXITCODE
    }
  }
}

$ZeroArgs = @(
  "fastreid/tools/train_net.py",
  "--config-file",
  $Config,
  "--eval-only",
  "--num-gpus",
  "1",
  "MODEL.WEIGHTS",
  $ZeroCheckpoint,
  "OUTPUT_DIR",
  $ZeroEvalDir
)

Write-Host "Evaluating gamma-zero checkpoint..."
if ($DryRun) {
  Write-Host "[dry-run] $Python $($ZeroArgs -join ' ')"
  Write-Host "Dry run completed. No checkpoint was modified and no evaluation was started."
  exit 0
}

& $Python @ZeroArgs
if ($LASTEXITCODE -ne 0) {
  Write-Error "Gamma-zero evaluation failed with exit code $LASTEXITCODE."
  exit $LASTEXITCODE
}

Write-Host "Gamma-zero evaluation completed."
Write-Host "Zero checkpoint: $ZeroCheckpoint"
Write-Host "Zero eval output: $ZeroEvalDir"
