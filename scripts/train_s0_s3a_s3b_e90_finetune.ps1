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

$FineTuneLr = "0.000077"
$StartCheckpointName = "model_e60_finetune_start.pth"

function Initialize-FinetuneRun {
  param(
    [Parameter(Mandatory = $true)][string]$SourceCheckpoint,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [Parameter(Mandatory = $true)][string]$ExperimentName
  )

  if (-not (Test-Path -LiteralPath $SourceCheckpoint)) {
    throw "Source checkpoint not found for ${ExperimentName}: ${SourceCheckpoint}"
  }

  if (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
  }

  $LastCheckpoint = Join-Path $OutputDir "last_checkpoint"
  if (Test-Path -LiteralPath $LastCheckpoint) {
    Write-Host "Found existing continuation checkpoint for ${ExperimentName}; training will resume from $OutputDir."
    return
  }

  $PreparedCheckpoint = Join-Path $OutputDir $StartCheckpointName
  Write-Host "Preparing low-LR fine-tune checkpoint for ${ExperimentName}: $PreparedCheckpoint"

  $prepareScript = @"
import os
import torch

source = r'''$SourceCheckpoint'''
target = r'''$PreparedCheckpoint'''
last_checkpoint = r'''$LastCheckpoint'''
fine_tune_lr = float("$FineTuneLr")

checkpoint = torch.load(source, map_location="cpu")
checkpoint.pop("lr_sched", None)
checkpoint.pop("warmup_sched", None)

optimizer_state = checkpoint.get("optimizer")
if optimizer_state:
    for group in optimizer_state.get("param_groups", []):
        group["lr"] = fine_tune_lr
        group["initial_lr"] = fine_tune_lr

os.makedirs(os.path.dirname(target), exist_ok=True)
torch.save(checkpoint, target)
with open(last_checkpoint, "w", encoding="utf-8") as handle:
    handle.write(os.path.basename(target))

print(f"prepared checkpoint: {target}")
print(f"epoch: {checkpoint.get('epoch')}")
print(f"fine_tune_lr: {fine_tune_lr}")
print("removed scheduler states: lr_sched, warmup_sched")
"@

  $prepareScript | python -
  if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to prepare fine-tune checkpoint for ${ExperimentName}."
    exit $LASTEXITCODE
  }
}

$Experiments = @(
  @{
    Name = "s0_amp64_e90_finetune: SBS baseline, continue e60->e90 with low LR"
    Config = "configs/veri_r50ibn_sbs_s0_amp64_e90_finetune_v1.yml"
    SourceCheckpoint = "outputs/archive/veri_r50ibn_sbs_s0_amp64_v1_e60_20260412/veri_r50ibn_sbs_s0_amp64_v1_e60_20260412_best_r1-96.66_map-80.15.pth"
    OutputDir = "outputs/veri_r50ibn_sbs_s0_amp64_e90_finetune_v1_20260412"
  },
  @{
    Name = "s3a_e90_finetune: SBS + LKA + Non-local on, continue e60->e90 with low LR"
    Config = "configs/veri_r50ibn_lka_s3a_nl_amp64_e90_finetune_v1.yml"
    SourceCheckpoint = "outputs/archive/veri_r50ibn_lka_s3a_nl_amp64_v1_e60_20260412/model_final.pth"
    OutputDir = "outputs/veri_r50ibn_lka_s3a_nl_amp64_e90_finetune_v1_20260412"
  },
  @{
    Name = "s3b_e90_finetune: SBS + LKA + Non-local off, continue e60->e90 with low LR"
    Config = "configs/veri_r50ibn_lka_s3b_nonl_amp64_e90_finetune_v1.yml"
    SourceCheckpoint = "outputs/archive/veri_r50ibn_lka_s3b_nonl_amp64_v1_e60_20260412/model_final.pth"
    OutputDir = "outputs/veri_r50ibn_lka_s3b_nonl_amp64_e90_finetune_v1_20260412"
  }
)

foreach ($Experiment in $Experiments) {
  Initialize-FinetuneRun `
    -SourceCheckpoint $Experiment.SourceCheckpoint `
    -OutputDir $Experiment.OutputDir `
    -ExperimentName $Experiment.Name

  Write-Host "Starting $($Experiment.Name)"
  python fastreid/tools/train_net.py --config-file $Experiment.Config --num-gpus 1 --resume
  if ($LASTEXITCODE -ne 0) {
    Write-Error "$($Experiment.Name) failed with exit code $LASTEXITCODE. Remaining experiments will not start."
    exit $LASTEXITCODE
  }
  Write-Host "$($Experiment.Name) completed successfully."
}

Write-Host "s0_amp64, s3a and s3b low-LR e90 fine-tune runs completed successfully."
