# encoding: utf-8

import torch
from torch import nn
import torch.nn.functional as F

from fastreid.config import configurable
from fastreid.modeling.backbones import build_backbone
from fastreid.modeling.heads import build_heads
from fastreid.modeling.losses import cross_entropy_loss, log_accuracy, triplet_loss
from .build import META_ARCH_REGISTRY


@META_ARCH_REGISTRY.register()
class S10BranchBaseline(nn.Module):
    """
    Minimal S10 model distilled from S9B+SaGL.

    Training uses one global branch and two detail stripe branches. Inference
    can return the global feature alone or concatenate global/detail features.
    """

    @configurable
    def __init__(
        self,
        *,
        backbone,
        heads,
        pixel_mean,
        pixel_std,
        loss_kwargs,
        detail_loss_weight=0.3,
        sagl_weight=2.0,
        sagl_margin=0.6,
        sagl_normalize=True,
        inference_mode="global",
    ):
        """
        NOTE: this interface is experimental.
        """
        super().__init__()
        self.backbone = backbone
        self.heads = heads
        self.loss_kwargs = loss_kwargs
        self.detail_loss_weight = float(detail_loss_weight)
        self.sagl_weight = float(sagl_weight)
        self.sagl_margin = float(sagl_margin)
        self.sagl_normalize = bool(sagl_normalize)
        self.inference_mode = inference_mode

        valid_inference_modes = {"global", "detail", "global_detail"}
        if self.inference_mode not in valid_inference_modes:
            raise ValueError(
                "MODEL.S10.INFERENCE_MODE must be one of "
                f"{sorted(valid_inference_modes)}."
            )

        self.register_buffer("pixel_mean", torch.Tensor(pixel_mean).view(1, -1, 1, 1), False)
        self.register_buffer("pixel_std", torch.Tensor(pixel_std).view(1, -1, 1, 1), False)

    @classmethod
    def from_config(cls, cfg):
        backbone = build_backbone(cfg)
        heads = nn.ModuleDict({"global": build_heads(cfg)})

        detail_cfg = cfg.clone()
        detail_cfg.defrost()
        detail_cfg.MODEL.HEADS.EMBEDDING_DIM = cfg.MODEL.S10.DETAIL.EMBEDDING_DIM
        detail_cfg.MODEL.HEADS.NECK_FEAT = cfg.MODEL.S10.DETAIL.NECK_FEAT
        detail_cfg.MODEL.HEADS.POOL_LAYER = cfg.MODEL.S10.DETAIL.POOL_LAYER
        detail_cfg.freeze()

        heads["detail_upper"] = build_heads(detail_cfg)
        heads["detail_lower"] = build_heads(detail_cfg)

        return {
            "backbone": backbone,
            "heads": heads,
            "pixel_mean": cfg.MODEL.PIXEL_MEAN,
            "pixel_std": cfg.MODEL.PIXEL_STD,
            "loss_kwargs": {
                "loss_names": cfg.MODEL.LOSSES.NAME,
                "ce": {
                    "eps": cfg.MODEL.LOSSES.CE.EPSILON,
                    "alpha": cfg.MODEL.LOSSES.CE.ALPHA,
                    "scale": cfg.MODEL.LOSSES.CE.SCALE,
                },
                "tri": {
                    "margin": cfg.MODEL.LOSSES.TRI.MARGIN,
                    "norm_feat": cfg.MODEL.LOSSES.TRI.NORM_FEAT,
                    "hard_mining": cfg.MODEL.LOSSES.TRI.HARD_MINING,
                    "scale": cfg.MODEL.LOSSES.TRI.SCALE,
                },
            },
            "detail_loss_weight": cfg.MODEL.S10.DETAIL.LOSS_WEIGHT,
            "sagl_weight": cfg.MODEL.S10.SAGL.WEIGHT,
            "sagl_margin": cfg.MODEL.S10.SAGL.MARGIN,
            "sagl_normalize": cfg.MODEL.S10.SAGL.NORMALIZE,
            "inference_mode": cfg.MODEL.S10.INFERENCE_MODE,
        }

    @property
    def device(self):
        return self.pixel_mean.device

    def forward(self, batched_inputs):
        images = self.preprocess_image(batched_inputs)
        features = self.backbone(images)

        if not self.training:
            return self.inference(features)

        assert "targets" in batched_inputs, "Person ID annotation are missing in training!"
        targets = batched_inputs["targets"]
        if targets.sum() < 0:
            targets.zero_()

        global_outputs = self.heads["global"](features, targets)
        losses = self.losses(global_outputs, targets)

        upper, lower = self.split_stripes(features)
        upper_outputs = self.heads["detail_upper"](upper, targets)
        lower_outputs = self.heads["detail_lower"](lower, targets)
        detail_losses = self.average_detail_losses(
            self.losses(upper_outputs, targets, prefix="detail_upper_"),
            self.losses(lower_outputs, targets, prefix="detail_lower_"),
        )
        for name, loss in detail_losses.items():
            losses[name] = loss * self.detail_loss_weight

        losses["loss_detail_sagl"] = (
            self.sagl_loss(
                global_outputs["features"],
                [upper_outputs["features"], lower_outputs["features"]],
                targets,
            )
            * self.sagl_weight
        )

        return losses

    def inference(self, features, inference_mode=None):
        mode = inference_mode or self.inference_mode
        valid_inference_modes = {"global", "detail", "global_detail"}
        if mode not in valid_inference_modes:
            raise ValueError(f"S10 inference_mode must be one of {sorted(valid_inference_modes)}.")

        global_feat = self.heads["global"](features)
        if mode == "global":
            return global_feat

        upper, lower = self.split_stripes(features)
        upper_feat = self.heads["detail_upper"](upper)
        lower_feat = self.heads["detail_lower"](lower)
        detail_feat = torch.cat([upper_feat, lower_feat], dim=1)

        if mode == "detail":
            return detail_feat
        return torch.cat([global_feat, detail_feat], dim=1)

    def preprocess_image(self, batched_inputs):
        if isinstance(batched_inputs, dict):
            images = batched_inputs["images"]
        elif isinstance(batched_inputs, torch.Tensor):
            images = batched_inputs
        else:
            raise TypeError(
                "batched_inputs must be dict or torch.Tensor, "
                f"but get {type(batched_inputs)}"
            )

        images.sub_(self.pixel_mean).div_(self.pixel_std)
        return images

    @staticmethod
    def split_stripes(features):
        height = features.size(2)
        if height < 2:
            raise ValueError("S10 detail branch requires feature maps with height >= 2.")
        split = height // 2
        return features[:, :, :split, :], features[:, :, split:, :]

    def losses(self, outputs, gt_labels, prefix=""):
        pred_class_logits = outputs["pred_class_logits"].detach()
        cls_outputs = outputs["cls_outputs"]
        pred_features = outputs["features"]

        if prefix == "":
            log_accuracy(pred_class_logits, gt_labels)

        loss_dict = {}
        loss_names = self.loss_kwargs["loss_names"]

        if "CrossEntropyLoss" in loss_names:
            ce_kwargs = self.loss_kwargs["ce"]
            loss_dict[f"{prefix}loss_cls"] = cross_entropy_loss(
                cls_outputs,
                gt_labels,
                ce_kwargs["eps"],
                ce_kwargs["alpha"],
            ) * ce_kwargs["scale"]

        if "TripletLoss" in loss_names:
            tri_kwargs = self.loss_kwargs["tri"]
            loss_dict[f"{prefix}loss_triplet"] = triplet_loss(
                pred_features,
                gt_labels,
                tri_kwargs["margin"],
                tri_kwargs["norm_feat"],
                tri_kwargs["hard_mining"],
            ) * tri_kwargs["scale"]

        return loss_dict

    def sagl_loss(self, global_features, local_features, targets):
        if self.sagl_normalize:
            global_features = F.normalize(global_features, dim=1)
            local_features = [F.normalize(feat, dim=1) for feat in local_features]

        global_dist = self._pairwise_euclidean_dist(global_features)
        local_dist = torch.stack(
            [self._pairwise_euclidean_dist(feat) for feat in local_features],
            dim=0,
        ).mean(dim=0)

        num_samples = global_dist.size(0)
        same_id = targets.view(num_samples, 1).eq(targets.view(1, num_samples))
        eye = torch.eye(num_samples, dtype=torch.bool, device=targets.device)
        pos_mask = same_id & ~eye
        neg_mask = ~same_id
        valid = pos_mask.any(dim=1) & neg_mask.any(dim=1)
        if not valid.any():
            return global_features.sum() * 0.0

        pos_dist = global_dist.masked_fill(~pos_mask, -float("inf"))
        neg_dist = global_dist.masked_fill(~neg_mask, float("inf"))
        dist_ap_global, pos_indices = pos_dist.max(dim=1)
        dist_an_global, neg_indices = neg_dist.min(dim=1)

        row_indices = torch.arange(num_samples, device=targets.device)
        dist_ap_local = local_dist[row_indices, pos_indices]
        dist_an_local = local_dist[row_indices, neg_indices]

        losses = F.relu(
            self.sagl_margin
            + dist_ap_global
            + dist_ap_local
            - dist_an_global
            - dist_an_local
        )
        return losses[valid].mean()

    @staticmethod
    def _pairwise_euclidean_dist(features):
        squared_norm = torch.pow(features, 2).sum(dim=1, keepdim=True)
        dist = squared_norm + squared_norm.t() - 2 * torch.matmul(features, features.t())
        return dist.clamp(min=1e-12).sqrt()

    @staticmethod
    def average_detail_losses(upper_losses, lower_losses):
        averaged = {}
        for upper_name, upper_loss in upper_losses.items():
            suffix = upper_name.replace("detail_upper_loss_", "", 1)
            lower_name = f"detail_lower_loss_{suffix}"
            averaged[f"loss_detail_{suffix}"] = 0.5 * (upper_loss + lower_losses[lower_name])
        return averaged
