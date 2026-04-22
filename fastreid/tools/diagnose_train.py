#!/usr/bin/env python
# encoding: utf-8

import argparse
import collections
import json
import os
import sys

import torch

if not hasattr(collections, "Mapping"):
    import collections.abc
    collections.Mapping = collections.abc.Mapping
if not hasattr(collections, "Iterable"):
    import collections.abc
    collections.Iterable = collections.abc.Iterable

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_FASTREID_DIR = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, PROJECT_FASTREID_DIR)

from fastreid.config import get_cfg
from fastreid.data import build_reid_train_loader
from fastreid.modeling import build_model
from fastreid.solver import build_optimizer
from fastreid.utils.events import EventStorage


def build_cfg(config_file, opts):
    cfg = get_cfg()
    cfg.merge_from_file(config_file)
    if opts:
        cfg.merge_from_list(opts)
    return cfg


def as_float(value):
    if torch.is_tensor(value):
        return float(value.detach().cpu())
    return float(value)


def main():
    parser = argparse.ArgumentParser(description="Diagnose one FastReID training step.")
    parser.add_argument(
        "--config-file",
        default=os.path.join("configs", "veri_r50ibn_sbs_s0_v1.yml"),
        help="path to the training config",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="temporary batch size for this diagnostic run",
    )
    parser.add_argument(
        "opts",
        nargs=argparse.REMAINDER,
        help="override config options using KEY VALUE pairs",
    )
    args = parser.parse_args()

    cfg = build_cfg(args.config_file, args.opts)
    cfg.defrost()
    cfg.DATALOADER.NUM_WORKERS = 0
    cfg.SOLVER.IMS_PER_BATCH = args.batch_size
    if cfg.MODEL.DEVICE == "cuda" and not torch.cuda.is_available():
        cfg.MODEL.DEVICE = "cpu"
    cfg.freeze()

    loader = build_reid_train_loader(cfg)
    batch = next(iter(loader))

    model = build_model(cfg)
    model.to(torch.device(cfg.MODEL.DEVICE))
    model.train()

    optimizer, _ = build_optimizer(cfg, model)

    for key, value in batch.items():
        if torch.is_tensor(value):
            batch[key] = value.to(cfg.MODEL.DEVICE)

    tracked_params = {}
    for name, param in model.named_parameters():
        if name in {"backbone.conv1.weight", "heads.weight"}:
            tracked_params[name] = param.detach().clone()

    with torch.no_grad():
        images = batch["images"].clone()
        feature_map = model.backbone(model.preprocess_image(images))
        pooled = model.heads.pool_layer(feature_map)[..., 0, 0]
        feature_variance = pooled.std(dim=0).mean()
        feature_norm = pooled.norm(dim=1).mean()
        sample_count = min(8, pooled.shape[0])
        if sample_count > 1:
            pairwise_distance = torch.cdist(pooled[:sample_count], pooled[:sample_count]).mean()
        else:
            pairwise_distance = torch.tensor(0.0, device=pooled.device)

    with EventStorage(0):
        loss_dict = model(batch)
        total_loss = sum(loss_dict.values())
        optimizer.zero_grad()
        total_loss.backward()

    gradients = []
    nonzero_grad_params = 0
    for name, param in model.named_parameters():
        if param.grad is None:
            continue
        grad_norm = as_float(param.grad.data.norm())
        if grad_norm > 0:
            nonzero_grad_params += 1
            gradients.append((name, grad_norm))
    gradients.sort(key=lambda item: item[1], reverse=True)

    optimizer.step()

    parameter_updates = {}
    current_params = dict(model.named_parameters())
    for name, before in tracked_params.items():
        delta = (current_params[name].detach() - before).abs()
        parameter_updates[name] = {
            "mean_abs_delta": as_float(delta.mean()),
            "max_abs_delta": as_float(delta.max()),
        }

    result = {
        "config_file": os.path.abspath(args.config_file),
        "device": cfg.MODEL.DEVICE,
        "batch_size": args.batch_size,
        "losses": {name: as_float(value) for name, value in loss_dict.items()},
        "feature_norm_mean": as_float(feature_norm),
        "feature_variance_mean": as_float(feature_variance),
        "pairwise_distance_mean": as_float(pairwise_distance),
        "nonzero_grad_params": nonzero_grad_params,
        "top_gradients": gradients[:5],
        "parameter_updates": parameter_updates,
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
