# encoding: utf-8

import torch
import torch.nn.functional as F
from torch import nn

from fastreid.config import configurable
from fastreid.layers import *
from fastreid.layers import any_softmax, pooling
from fastreid.layers.weight_init import weights_init_kaiming
from fastreid.modeling.backbones.residual_mlp import ResidualMLPStack
from .build import REID_HEADS_REGISTRY


@REID_HEADS_REGISTRY.register()
class ResidualMLPEmbeddingHead(nn.Module):
    """Embedding head with an opt-in residual MLP stack after pooling."""

    @configurable
    def __init__(
        self,
        *,
        feat_dim,
        embedding_dim,
        num_classes,
        neck_feat,
        pool_type,
        cls_type,
        scale,
        margin,
        with_bnneck,
        norm_type,
        mlp_num_blocks,
        mlp_hidden_dim,
        mlp_beta_init,
        mlp_dropout,
        mlp_drop_path_rate,
        mlp_norm_type,
    ):
        super().__init__()

        assert hasattr(pooling, pool_type), "Expected pool types are {}, but got {}".format(
            pooling.__all__, pool_type
        )
        self.pool_layer = getattr(pooling, pool_type)()
        self.neck_feat = neck_feat

        mlp_feat_dim = feat_dim
        if embedding_dim > 0:
            mlp_feat_dim = embedding_dim
            self.embedding = nn.Conv2d(feat_dim, embedding_dim, 1, 1, bias=False)
        else:
            self.embedding = nn.Identity()

        self.residual_mlp = ResidualMLPStack(
            feat_dim=mlp_feat_dim,
            num_blocks=mlp_num_blocks,
            hidden_dim=mlp_hidden_dim,
            beta_init=mlp_beta_init,
            dropout=mlp_dropout,
            drop_path_rate=mlp_drop_path_rate,
            norm_type=mlp_norm_type,
        )

        neck = []
        if with_bnneck:
            neck.append(get_norm(norm_type, mlp_feat_dim, bias_freeze=True))
        self.bottleneck = nn.Sequential(*neck)

        assert hasattr(any_softmax, cls_type), "Expected cls types are {}, but got {}".format(
            any_softmax.__all__, cls_type
        )
        self.weight = nn.Parameter(torch.Tensor(num_classes, mlp_feat_dim))
        self.cls_layer = getattr(any_softmax, cls_type)(num_classes, scale, margin)

        self.reset_parameters()

    def reset_parameters(self):
        if not isinstance(self.embedding, nn.Identity):
            self.embedding.apply(weights_init_kaiming)
        self.bottleneck.apply(weights_init_kaiming)
        nn.init.normal_(self.weight, std=0.01)

    @classmethod
    def from_config(cls, cfg):
        # fmt: off
        feat_dim           = cfg.MODEL.BACKBONE.FEAT_DIM
        embedding_dim      = cfg.MODEL.HEADS.EMBEDDING_DIM
        num_classes        = cfg.MODEL.HEADS.NUM_CLASSES
        neck_feat          = cfg.MODEL.HEADS.NECK_FEAT
        pool_type          = cfg.MODEL.HEADS.POOL_LAYER
        cls_type           = cfg.MODEL.HEADS.CLS_LAYER
        scale              = cfg.MODEL.HEADS.SCALE
        margin             = cfg.MODEL.HEADS.MARGIN
        with_bnneck        = cfg.MODEL.HEADS.WITH_BNNECK
        norm_type          = cfg.MODEL.HEADS.NORM
        mlp_cfg            = cfg.MODEL.HEADS.MLP
        # fmt: on
        return {
            "feat_dim": feat_dim,
            "embedding_dim": embedding_dim,
            "num_classes": num_classes,
            "neck_feat": neck_feat,
            "pool_type": pool_type,
            "cls_type": cls_type,
            "scale": scale,
            "margin": margin,
            "with_bnneck": with_bnneck,
            "norm_type": norm_type,
            "mlp_num_blocks": mlp_cfg.NUM_BLOCKS,
            "mlp_hidden_dim": mlp_cfg.HIDDEN_DIM,
            "mlp_beta_init": mlp_cfg.BETA_INIT,
            "mlp_dropout": mlp_cfg.DROPOUT,
            "mlp_drop_path_rate": mlp_cfg.DROP_PATH_RATE,
            "mlp_norm_type": mlp_cfg.NORM,
        }

    def forward(self, features, targets=None):
        pool_feat = self.pool_layer(features)
        embedded_feat = self.embedding(pool_feat)
        mlp_feat = self.residual_mlp(embedded_feat[..., 0, 0])
        neck_feat = self.bottleneck(mlp_feat.unsqueeze(-1).unsqueeze(-1))
        neck_feat = neck_feat[..., 0, 0]

        if not self.training:
            return neck_feat

        if self.cls_layer.__class__.__name__ == "Linear":
            logits = F.linear(neck_feat, self.weight)
        else:
            logits = F.linear(F.normalize(neck_feat), F.normalize(self.weight))

        cls_outputs = self.cls_layer(logits.clone(), targets)

        if self.neck_feat == "before":
            feat = mlp_feat
        elif self.neck_feat == "after":
            feat = neck_feat
        elif self.neck_feat == "pool":
            feat = embedded_feat[..., 0, 0]
        else:
            raise KeyError(f"{self.neck_feat} is invalid for MODEL.HEADS.NECK_FEAT")

        return {
            "cls_outputs": cls_outputs,
            "pred_class_logits": logits.mul(self.cls_layer.s),
            "features": feat,
        }
