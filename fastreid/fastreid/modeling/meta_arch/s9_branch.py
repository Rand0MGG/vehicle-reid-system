# encoding: utf-8

import torch
from torch import nn
import torch.nn.functional as F

from fastreid.config import configurable
from fastreid.modeling.backbones import build_backbone
from fastreid.modeling.backbones.resnet_lka import ResidualLKA
from fastreid.modeling.heads import build_heads
from fastreid.modeling.losses import *
from .build import META_ARCH_REGISTRY


@META_ARCH_REGISTRY.register()
class S9BranchBaseline(nn.Module):
    """
    S9 branch framework for controlled global/detail ablations.

    The global path is an SBS head on the full backbone feature map. The optional
    detail path splits the same feature map into upper/lower horizontal stripes
    and supervises each stripe with its own lightweight head.
    """

    @configurable
    def __init__(
        self,
        *,
        backbone,
        heads,
        branch_modules=None,
        pixel_mean,
        pixel_std,
        loss_kwargs=None,
        global_use_triplet_loss=True,
        detail_enabled=False,
        detail_loss_weight=0.3,
        detail_use_triplet_loss=True,
        detail_sagl_enabled=False,
        detail_sagl_weight=1.0,
        detail_sagl_margin=0.6,
        detail_sagl_normalize=True,
        lka_enabled=False,
        lka_loss_weight=0.3,
        lka_use_triplet_loss=True,
        inference_mode="global",
    ):
        """
        NOTE: this interface is experimental.
        """
        super().__init__()
        self.backbone = backbone
        self.heads = heads
        self.branch_modules = branch_modules if branch_modules is not None else nn.ModuleDict()
        self.loss_kwargs = loss_kwargs
        self.global_use_triplet_loss = bool(global_use_triplet_loss)
        self.detail_enabled = bool(detail_enabled)
        self.detail_loss_weight = float(detail_loss_weight)
        self.detail_use_triplet_loss = bool(detail_use_triplet_loss)
        self.detail_sagl_enabled = bool(detail_sagl_enabled)
        self.detail_sagl_weight = float(detail_sagl_weight)
        self.detail_sagl_margin = float(detail_sagl_margin)
        self.detail_sagl_normalize = bool(detail_sagl_normalize)
        self.lka_enabled = bool(lka_enabled)
        self.lka_loss_weight = float(lka_loss_weight)
        self.lka_use_triplet_loss = bool(lka_use_triplet_loss)
        self.inference_mode = inference_mode

        valid_inference_modes = {
            "global",
            "detail",
            "global_detail",
            "lka",
            "global_lka",
            "global_detail_lka",
        }
        if self.inference_mode not in valid_inference_modes:
            raise ValueError(
                "MODEL.S9.INFERENCE_MODE must be one of "
                f"{sorted(valid_inference_modes)}."
            )
        if "detail" in self.inference_mode and not self.detail_enabled:
            raise ValueError("Detail inference modes require MODEL.S9.DETAIL.ENABLED=True.")
        if "lka" in self.inference_mode and not self.lka_enabled:
            raise ValueError("LKA inference modes require MODEL.S9.LKA.ENABLED=True.")
        if self.detail_sagl_enabled and not self.detail_enabled:
            raise ValueError("SaGL requires MODEL.S9.DETAIL.ENABLED=True.")

        self.register_buffer("pixel_mean", torch.Tensor(pixel_mean).view(1, -1, 1, 1), False)
        self.register_buffer("pixel_std", torch.Tensor(pixel_std).view(1, -1, 1, 1), False)

    @classmethod
    def from_config(cls, cfg):
        backbone = build_backbone(cfg)
        heads = nn.ModuleDict({"global": build_heads(cfg)})
        branch_modules = nn.ModuleDict()

        if cfg.MODEL.S9.DETAIL.ENABLED:
            local_cfg = cfg.clone()
            local_cfg.defrost()
            local_cfg.MODEL.HEADS.EMBEDDING_DIM = cfg.MODEL.S9.DETAIL.EMBEDDING_DIM
            local_cfg.MODEL.HEADS.NECK_FEAT = cfg.MODEL.S9.DETAIL.NECK_FEAT
            local_cfg.MODEL.HEADS.POOL_LAYER = cfg.MODEL.S9.DETAIL.POOL_LAYER
            local_cfg.freeze()

            if cfg.MODEL.S9.DETAIL.SHARE_STRIPE_HEADS:
                shared_head = build_heads(local_cfg)
                heads["detail_upper"] = shared_head
                heads["detail_lower"] = shared_head
            else:
                heads["detail_upper"] = build_heads(local_cfg)
                heads["detail_lower"] = build_heads(local_cfg)

        if cfg.MODEL.S9.LKA.ENABLED:
            lka_cfg = cfg.MODEL.S9.LKA
            lka_head_cfg = cfg.clone()
            lka_head_cfg.defrost()
            lka_head_cfg.MODEL.HEADS.EMBEDDING_DIM = lka_cfg.EMBEDDING_DIM
            lka_head_cfg.MODEL.HEADS.NECK_FEAT = lka_cfg.NECK_FEAT
            lka_head_cfg.MODEL.HEADS.POOL_LAYER = lka_cfg.POOL_LAYER
            lka_head_cfg.freeze()

            branch_modules["lka"] = ResidualLKA(
                cfg.MODEL.BACKBONE.FEAT_DIM,
                alpha=lka_cfg.ALPHA,
                output_mode=lka_cfg.OUTPUT_MODE,
                residual_norm=lka_cfg.RESIDUAL_NORM,
                max_raw_norm_ratio=lka_cfg.MAX_RAW_NORM_RATIO,
                norm_eps=lka_cfg.NORM_EPS,
            )
            heads["lka"] = build_heads(lka_head_cfg)

        return {
            "backbone": backbone,
            "heads": heads,
            "branch_modules": branch_modules,
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
            "global_use_triplet_loss": cfg.MODEL.S9.GLOBAL.USE_TRIPLET_LOSS,
            "detail_enabled": cfg.MODEL.S9.DETAIL.ENABLED,
            "detail_loss_weight": cfg.MODEL.S9.DETAIL.LOSS_WEIGHT,
            "detail_use_triplet_loss": cfg.MODEL.S9.DETAIL.USE_TRIPLET_LOSS,
            "detail_sagl_enabled": cfg.MODEL.S9.DETAIL.SAGL.ENABLED,
            "detail_sagl_weight": cfg.MODEL.S9.DETAIL.SAGL.WEIGHT,
            "detail_sagl_margin": cfg.MODEL.S9.DETAIL.SAGL.MARGIN,
            "detail_sagl_normalize": cfg.MODEL.S9.DETAIL.SAGL.NORMALIZE,
            "lka_enabled": cfg.MODEL.S9.LKA.ENABLED,
            "lka_loss_weight": cfg.MODEL.S9.LKA.LOSS_WEIGHT,
            "lka_use_triplet_loss": cfg.MODEL.S9.LKA.USE_TRIPLET_LOSS,
            "inference_mode": cfg.MODEL.S9.INFERENCE_MODE,
        }

    @property
    def device(self):
        return self.pixel_mean.device

    def forward(self, batched_inputs):
        images = self.preprocess_image(batched_inputs)
        features = self.backbone(images)

        if self.training:
            assert "targets" in batched_inputs, "Person ID annotation are missing in training!"
            targets = batched_inputs["targets"]
            if targets.sum() < 0:
                targets.zero_()

            global_outputs = self.heads["global"](features, targets)
            global_loss_names = self._branch_loss_names(self.global_use_triplet_loss)
            losses = self.losses(global_outputs, targets, prefix="", loss_names=global_loss_names)

            if self.detail_enabled:
                upper, lower = self._split_stripes(features)
                upper_outputs = self.heads["detail_upper"](upper, targets)
                lower_outputs = self.heads["detail_lower"](lower, targets)
                detail_loss_names = self._branch_loss_names(self.detail_use_triplet_loss)
                detail_losses = self._average_loss_dict(
                    self.losses(
                        upper_outputs,
                        targets,
                        prefix="detail_upper_",
                        loss_names=detail_loss_names,
                    ),
                    self.losses(
                        lower_outputs,
                        targets,
                        prefix="detail_lower_",
                        loss_names=detail_loss_names,
                    ),
                )
                for name, loss in detail_losses.items():
                    losses[name] = loss * self.detail_loss_weight

                if self.detail_sagl_enabled:
                    losses["loss_detail_sagl"] = self.sagl_loss(
                        global_outputs["features"],
                        [upper_outputs["features"], lower_outputs["features"]],
                        targets,
                    ) * self.detail_sagl_weight

            if self.lka_enabled:
                lka_features = self.branch_modules["lka"](features)
                lka_outputs = self.heads["lka"](lka_features, targets)
                lka_loss_names = self._branch_loss_names(self.lka_use_triplet_loss)
                lka_losses = self.losses(
                    lka_outputs,
                    targets,
                    prefix="lka_",
                    loss_names=lka_loss_names,
                )
                for name, loss in lka_losses.items():
                    suffix = name.replace("lka_loss_", "", 1)
                    losses[f"loss_lka_{suffix}"] = loss * self.lka_loss_weight

            return losses

        return self.inference(features)

    def inference(self, features, inference_mode=None):
        mode = inference_mode or self.inference_mode
        valid_inference_modes = {
            "global",
            "detail",
            "global_detail",
            "lka",
            "global_lka",
            "global_detail_lka",
        }
        if mode not in valid_inference_modes:
            raise ValueError(f"S9 inference_mode must be one of {sorted(valid_inference_modes)}.")
        if "detail" in mode and not self.detail_enabled:
            raise ValueError("Detail inference modes require MODEL.S9.DETAIL.ENABLED=True.")
        if "lka" in mode and not self.lka_enabled:
            raise ValueError("LKA inference modes require MODEL.S9.LKA.ENABLED=True.")

        global_feat = self.heads["global"](features)
        if mode == "global":
            return global_feat

        inference_parts = mode.split("_")
        features_to_return = []
        if "global" in inference_parts:
            features_to_return.append(global_feat)

        if "detail" in inference_parts:
            upper, lower = self._split_stripes(features)
            upper_feat = self.heads["detail_upper"](upper)
            lower_feat = self.heads["detail_lower"](lower)
            features_to_return.append(torch.cat([upper_feat, lower_feat], dim=1))

        if "lka" in inference_parts:
            lka_features = self.branch_modules["lka"](features)
            features_to_return.append(self.heads["lka"](lka_features))

        if len(features_to_return) == 1:
            return features_to_return[0]
        return torch.cat(features_to_return, dim=1)

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
    def _split_stripes(features):
        height = features.size(2)
        if height < 2:
            raise ValueError("Detail branch requires feature maps with height >= 2.")
        split = height // 2
        return features[:, :, :split, :], features[:, :, split:, :]

    def losses(self, outputs, gt_labels, prefix="", loss_names=None):
        pred_class_logits = outputs["pred_class_logits"].detach()
        cls_outputs = outputs["cls_outputs"]
        pred_features = outputs["features"]

        if prefix == "":
            log_accuracy(pred_class_logits, gt_labels)

        loss_dict = {}
        if loss_names is None:
            loss_names = self.loss_kwargs["loss_names"]

        if "CrossEntropyLoss" in loss_names:
            ce_kwargs = self.loss_kwargs.get("ce")
            loss_dict[f"{prefix}loss_cls"] = cross_entropy_loss(
                cls_outputs,
                gt_labels,
                ce_kwargs.get("eps"),
                ce_kwargs.get("alpha"),
            ) * ce_kwargs.get("scale")

        if "TripletLoss" in loss_names:
            tri_kwargs = self.loss_kwargs.get("tri")
            loss_dict[f"{prefix}loss_triplet"] = triplet_loss(
                pred_features,
                gt_labels,
                tri_kwargs.get("margin"),
                tri_kwargs.get("norm_feat"),
                tri_kwargs.get("hard_mining"),
            ) * tri_kwargs.get("scale")

        return loss_dict

    def sagl_loss(self, global_features, local_features, targets):
        if self.detail_sagl_normalize:
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
            self.detail_sagl_margin
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

    def _branch_loss_names(self, use_triplet_loss):
        loss_names = list(self.loss_kwargs["loss_names"])
        if not use_triplet_loss and "TripletLoss" in loss_names:
            loss_names.remove("TripletLoss")
        return tuple(loss_names)

    @staticmethod
    def _average_loss_dict(upper_losses, lower_losses):
        averaged = {}
        for upper_name, upper_loss in upper_losses.items():
            suffix = upper_name.replace("detail_upper_loss_", "", 1)
            lower_name = f"detail_lower_loss_{suffix}"
            averaged[f"loss_detail_{suffix}"] = 0.5 * (upper_loss + lower_losses[lower_name])
        return averaged
