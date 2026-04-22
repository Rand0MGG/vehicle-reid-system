# encoding: utf-8
"""
Center loss for identity-discriminative feature learning.
"""

import torch
from torch import nn


class CenterLoss(nn.Module):
    """Maintain one trainable feature center per identity class."""

    def __init__(self, num_classes: int, feat_dim: int):
        super().__init__()
        self.centers = nn.Parameter(torch.randn(num_classes, feat_dim))

    def forward(self, features: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        targets = targets.long().view(-1)
        batch_centers = self.centers.index_select(0, targets)
        return 0.5 * torch.sum((features - batch_centers) ** 2, dim=1).mean()
