# encoding: utf-8
"""
Weighted Regularized Triplet loss for vehicle re-identification.
"""

import torch
import torch.nn.functional as F

from .utils import cosine_dist, euclidean_dist


def _masked_softmax(logits: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    masked_logits = logits.masked_fill(~mask, torch.finfo(logits.dtype).min)
    return F.softmax(masked_logits, dim=1) * mask.float()


def wrt_loss(embedding: torch.Tensor, targets: torch.Tensor, norm_feat: bool = False) -> torch.Tensor:
    """Compute Weighted Regularized Triplet loss.

    The implementation follows the MDFE-Net WRT formulation:
    softplus(weighted positive distance - weighted negative distance).
    """

    if norm_feat:
        dist_mat = cosine_dist(embedding, embedding)
    else:
        dist_mat = euclidean_dist(embedding, embedding)

    targets = targets.view(-1)
    num_samples = dist_mat.size(0)
    same_identity = targets.view(num_samples, 1).eq(targets.view(1, num_samples))
    eye = torch.eye(num_samples, dtype=torch.bool, device=dist_mat.device)

    is_pos = same_identity & ~eye
    is_neg = ~same_identity
    valid_anchor = is_pos.any(dim=1) & is_neg.any(dim=1)

    if not valid_anchor.any():
        return embedding.sum() * 0.0

    dist_mat = dist_mat[valid_anchor]
    is_pos = is_pos[valid_anchor]
    is_neg = is_neg[valid_anchor]

    positive_weights = _masked_softmax(dist_mat, is_pos)
    negative_weights = _masked_softmax(-dist_mat, is_neg)

    weighted_positive = torch.sum(dist_mat * positive_weights, dim=1)
    weighted_negative = torch.sum(dist_mat * negative_weights, dim=1)

    return F.softplus(weighted_positive - weighted_negative).mean()
