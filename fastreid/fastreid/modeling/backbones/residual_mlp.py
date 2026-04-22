# encoding: utf-8

import torch
from torch import nn

from fastreid.layers import DropPath, weights_init_kaiming


def _build_vector_norm(norm_type, num_features):
    norm_type = norm_type.lower()
    if norm_type in ("bn", "bn1d", "batchnorm", "batchnorm1d"):
        return nn.BatchNorm1d(num_features)
    if norm_type in ("ln", "layernorm"):
        return nn.LayerNorm(num_features)
    if norm_type in ("none", "identity"):
        return nn.Identity()
    raise ValueError(f"Unsupported residual MLP norm type: {norm_type!r}")


class ResidualMLPBlock(nn.Module):
    """Residual bottleneck MLP for post-pooling embedding refinement."""

    def __init__(
        self,
        feat_dim,
        hidden_dim=512,
        beta_init=0.1,
        dropout=0.0,
        drop_path=0.0,
        norm_type="BN1d",
    ):
        super().__init__()
        if feat_dim <= 0:
            raise ValueError("ResidualMLPBlock requires positive feat_dim.")
        if hidden_dim <= 0:
            raise ValueError("ResidualMLPBlock requires positive hidden_dim.")

        self.norm_in = _build_vector_norm(norm_type, feat_dim)
        self.fc1 = nn.Linear(feat_dim, hidden_dim)
        self.norm_hidden = _build_vector_norm(norm_type, hidden_dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(p=float(dropout)) if dropout > 0 else nn.Identity()
        self.fc2 = nn.Linear(hidden_dim, feat_dim)
        self.drop_path = DropPath(drop_path) if drop_path > 0 else nn.Identity()
        self.beta = nn.Parameter(torch.tensor(float(beta_init), dtype=torch.float32))

        self.reset_parameters()

    def reset_parameters(self):
        self.fc1.apply(weights_init_kaiming)
        self.fc2.apply(weights_init_kaiming)

    def forward(self, x):
        residual = x
        x = self.norm_in(x)
        x = self.fc1(x)
        x = self.norm_hidden(x)
        x = self.act(x)
        x = self.dropout(x)
        x = self.fc2(x)
        x = self.dropout(x)
        return residual + self.beta.to(dtype=x.dtype) * self.drop_path(x)


class ResidualMLPStack(nn.Module):
    """Stack of residual bottleneck MLP blocks used by the M-series head."""

    def __init__(
        self,
        feat_dim,
        num_blocks=1,
        hidden_dim=512,
        beta_init=0.1,
        dropout=0.0,
        drop_path_rate=0.0,
        norm_type="BN1d",
    ):
        super().__init__()
        if num_blocks <= 0:
            raise ValueError("ResidualMLPStack requires num_blocks > 0.")

        if num_blocks == 1:
            drop_rates = [float(drop_path_rate)]
        else:
            drop_rates = torch.linspace(0, float(drop_path_rate), num_blocks).tolist()

        self.blocks = nn.Sequential(
            *[
                ResidualMLPBlock(
                    feat_dim=feat_dim,
                    hidden_dim=hidden_dim,
                    beta_init=beta_init,
                    dropout=dropout,
                    drop_path=drop_rates[i],
                    norm_type=norm_type,
                )
                for i in range(num_blocks)
            ]
        )

    def forward(self, x):
        return self.blocks(x)
