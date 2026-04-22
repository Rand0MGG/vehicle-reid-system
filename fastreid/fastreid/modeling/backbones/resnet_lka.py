# encoding: utf-8

import torch
from torch import nn
import torch.nn.functional as F

from .build import BACKBONE_REGISTRY
from .resnet import build_resnet_backbone


class LargeKernelAttention(nn.Module):
    """LKA block used as a late-stage feature enhancer."""

    def __init__(self, channels):
        super().__init__()
        self.dw_conv = nn.Conv2d(
            channels, channels, kernel_size=5, padding=2, groups=channels
        )
        self.dw_dilated_conv = nn.Conv2d(
            channels, channels, kernel_size=7, padding=9, dilation=3, groups=channels
        )
        self.pw_conv = nn.Conv2d(channels, channels, kernel_size=1)

    def forward(self, x):
        attention = self.dw_conv(x)
        attention = self.dw_dilated_conv(attention)
        attention = self.pw_conv(attention)
        return x * attention


class ResidualLKA(nn.Module):
    """LKA wrapper with selectable output behavior for isolated ablations."""

    _VALID_OUTPUT_MODES = {"gated_residual", "fixed_residual", "replace"}
    _VALID_RESIDUAL_NORMS = {"none", "ratio_clamp"}
    _VALID_GAMMA_PARAMETERIZATIONS = {"direct", "sigmoid_range"}

    def __init__(
        self,
        channels,
        gamma_init=1e-6,
        alpha=0.05,
        output_mode="gated_residual",
        residual_norm="none",
        max_raw_norm_ratio=2.0,
        norm_eps=1e-6,
        gamma_warmup_enabled=False,
        gamma_warmup_start=0.0,
        gamma_warmup_end=1.0,
        gamma_parameterization="direct",
        gamma_clamp_min=0.0,
        gamma_clamp_max=-1.0,
    ):
        super().__init__()
        if output_mode not in self._VALID_OUTPUT_MODES:
            raise ValueError(
                f"Unsupported LKA OUTPUT_MODE={output_mode!r}. "
                f"Choose one of {sorted(self._VALID_OUTPUT_MODES)}."
            )
        if residual_norm not in self._VALID_RESIDUAL_NORMS:
            raise ValueError(
                f"Unsupported LKA RESIDUAL_NORM={residual_norm!r}. "
                f"Choose one of {sorted(self._VALID_RESIDUAL_NORMS)}."
            )
        if max_raw_norm_ratio <= 0:
            raise ValueError("LKA.MAX_RAW_NORM_RATIO must be positive.")
        if gamma_warmup_enabled and output_mode != "gated_residual":
            raise ValueError("LKA gamma warmup requires OUTPUT_MODE='gated_residual'.")
        if gamma_parameterization not in self._VALID_GAMMA_PARAMETERIZATIONS:
            raise ValueError(
                f"Unsupported LKA GAMMA_PARAMETERIZATION={gamma_parameterization!r}. "
                f"Choose one of {sorted(self._VALID_GAMMA_PARAMETERIZATIONS)}."
            )
        if gamma_clamp_max >= 0 and gamma_clamp_min > gamma_clamp_max:
            raise ValueError("LKA.GAMMA_CLAMP_MIN must be <= LKA.GAMMA_CLAMP_MAX.")
        if gamma_parameterization == "sigmoid_range":
            if output_mode != "gated_residual":
                raise ValueError("sigmoid_range gamma requires OUTPUT_MODE='gated_residual'.")
            if gamma_clamp_max <= gamma_clamp_min:
                raise ValueError(
                    "sigmoid_range gamma requires GAMMA_CLAMP_MAX > GAMMA_CLAMP_MIN."
                )
        self.output_mode = output_mode
        self.alpha = float(alpha)
        self.residual_norm = residual_norm
        self.max_raw_norm_ratio = float(max_raw_norm_ratio)
        self.norm_eps = float(norm_eps)
        self.gamma_warmup_enabled = bool(gamma_warmup_enabled)
        self.gamma_warmup_start = float(gamma_warmup_start)
        self.gamma_warmup_end = float(gamma_warmup_end)
        self.gamma_parameterization = gamma_parameterization
        self.gamma_clamp_min = float(gamma_clamp_min)
        self.gamma_clamp_max = float(gamma_clamp_max)
        self.gamma_clamp_enabled = gamma_clamp_max >= 0
        if self.gamma_warmup_enabled:
            self.register_buffer(
                "gamma_warmup_factor",
                torch.tensor(float(self.gamma_warmup_start), dtype=torch.float32),
            )
        self.proj_in = nn.Sequential(
            nn.Conv2d(channels, channels, kernel_size=1),
            nn.GELU(),
        )
        self.attention = LargeKernelAttention(channels)
        self.proj_out = nn.Conv2d(channels, channels, kernel_size=1)
        if output_mode == "gated_residual":
            if gamma_parameterization == "sigmoid_range":
                normalized = (float(gamma_init) - self.gamma_clamp_min) / (
                    self.gamma_clamp_max - self.gamma_clamp_min
                )
                normalized = min(max(normalized, 1e-6), 1.0 - 1e-6)
                gamma_logit = torch.logit(torch.tensor(normalized, dtype=torch.float32))
                self.gamma_logit = nn.Parameter(
                    torch.full((1, channels, 1, 1), float(gamma_logit))
                )
                self.gamma = None
            else:
                self.gamma = nn.Parameter(torch.full((1, channels, 1, 1), gamma_init))
        else:
            self.gamma = None

    def set_gamma_warmup_factor(self, factor):
        if self.output_mode != "gated_residual":
            return
        if hasattr(self, "gamma_warmup_factor"):
            self.gamma_warmup_factor.fill_(float(factor))

    def _apply_residual_norm(self, x, out):
        if self.residual_norm == "none":
            return out

        # Safety valve: only shrink an oversized LKA branch. The scale is
        # detached so LKA cannot optimize by manipulating the norm denominator.
        norm_dims = tuple(range(1, x.dim()))
        x_norm = torch.linalg.vector_norm(
            x.detach(), ord=2, dim=norm_dims, dtype=torch.float32
        ).clamp_min(self.norm_eps)
        out_norm = torch.linalg.vector_norm(
            out.detach(), ord=2, dim=norm_dims, dtype=torch.float32
        ).clamp_min(self.norm_eps)
        scale = self.max_raw_norm_ratio * x_norm / out_norm
        scale = scale.clamp(max=1.0)
        scale = scale.to(device=out.device, dtype=out.dtype)
        view_shape = (out.shape[0],) + (1,) * (out.dim() - 1)
        return out * scale.view(view_shape)

    def _effective_gamma(self):
        if self.gamma_parameterization == "sigmoid_range":
            gamma = self.gamma_clamp_min + (
                self.gamma_clamp_max - self.gamma_clamp_min
            ) * torch.sigmoid(self.gamma_logit)
        else:
            gamma = self.gamma
        if self.gamma_clamp_enabled and self.gamma_parameterization == "direct":
            gamma = gamma.clamp(min=self.gamma_clamp_min, max=self.gamma_clamp_max)
        if self.gamma_warmup_enabled:
            factor = self.gamma_warmup_factor.to(device=gamma.device, dtype=gamma.dtype)
            gamma = gamma * factor
        return gamma

    def forward(self, x):
        out = self.proj_in(x)
        out = self.attention(out)
        out = self.proj_out(out)
        if self.output_mode == "replace":
            return out
        out = self._apply_residual_norm(x, out)
        if self.output_mode == "fixed_residual":
            return x + self.alpha * out
        return x + self._effective_gamma() * out


class ResidualLKAStack(nn.Module):
    """Stack gated residual LKA blocks with shared config hyperparameters."""

    def __init__(
        self,
        channels,
        num_blocks=3,
        gamma_init=1e-6,
        alpha=0.05,
        output_mode="gated_residual",
        residual_norm="none",
        max_raw_norm_ratio=2.0,
        norm_eps=1e-6,
        gamma_warmup_enabled=False,
        gamma_warmup_start=0.0,
        gamma_warmup_end=1.0,
        gamma_parameterization="direct",
        gamma_clamp_min=0.0,
        gamma_clamp_max=-1.0,
    ):
        super().__init__()
        if num_blocks <= 0:
            raise ValueError("LKA.NUM_BLOCKS must be positive.")
        self.blocks = nn.Sequential(
            *[
                ResidualLKA(
                    channels,
                    gamma_init=gamma_init,
                    alpha=alpha,
                    output_mode=output_mode,
                    residual_norm=residual_norm,
                    max_raw_norm_ratio=max_raw_norm_ratio,
                    norm_eps=norm_eps,
                    gamma_warmup_enabled=gamma_warmup_enabled,
                    gamma_warmup_start=gamma_warmup_start,
                    gamma_warmup_end=gamma_warmup_end,
                    gamma_parameterization=gamma_parameterization,
                    gamma_clamp_min=gamma_clamp_min,
                    gamma_clamp_max=gamma_clamp_max,
                )
                for _ in range(num_blocks)
            ]
        )

    def forward(self, x):
        return self.blocks(x)


class PaperStyleLKABlock(nn.Module):
    """Paper-style LKA block: residual add without gamma/warmup/clamp."""

    def __init__(self, channels):
        super().__init__()
        self.proj_in = nn.Sequential(
            nn.Conv2d(channels, channels, kernel_size=1),
            nn.GELU(),
        )
        self.attention = LargeKernelAttention(channels)
        self.proj_out = nn.Conv2d(channels, channels, kernel_size=1)

    def forward(self, x):
        out = self.proj_in(x)
        out = self.attention(out)
        out = self.proj_out(out)
        return x + out


class PaperStyleLKAStack(nn.Module):
    """Stack paper-style LKA blocks as LKA -> LKA -> LKA."""

    def __init__(self, channels, num_blocks=3):
        super().__init__()
        if num_blocks <= 0:
            raise ValueError("PAPER_LKA.NUM_BLOCKS must be positive.")
        self.blocks = nn.Sequential(
            *[PaperStyleLKABlock(channels) for _ in range(num_blocks)]
        )

    def forward(self, x):
        return self.blocks(x)


class HybridChannelAttention(nn.Module):
    """Channel attention mixing local pooled grids and global context."""

    def __init__(self, channels, local_size=5, local_weight=0.5, kernel_size=5):
        super().__init__()
        if kernel_size % 2 == 0:
            raise ValueError("HCA.KERNEL_SIZE must be odd for same-length Conv1d.")

        self.channels = channels
        self.local_size = local_size
        self.local_weight = local_weight
        self.local_pool = nn.AdaptiveAvgPool2d((local_size, local_size))
        self.global_pool = nn.AdaptiveAvgPool2d(1)
        self.local_conv = nn.Conv1d(
            1, 1, kernel_size=kernel_size, padding=kernel_size // 2, bias=False
        )
        self.global_conv = nn.Conv1d(
            1, 1, kernel_size=kernel_size, padding=kernel_size // 2, bias=False
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        b, c, h, w = x.shape
        if c != self.channels:
            raise ValueError(f"HCA expected {self.channels} channels, got {c}.")

        local_context = self.local_pool(x)
        local_attention = local_context.permute(0, 2, 3, 1).reshape(b, 1, -1)
        local_attention = self.local_conv(local_attention)
        local_attention = local_attention.reshape(
            b, self.local_size, self.local_size, c
        ).permute(0, 3, 1, 2)

        global_context = self.global_pool(x).reshape(b, 1, c)
        global_attention = self.global_conv(global_context).reshape(b, c, 1, 1)

        attention = (
            self.local_weight * local_attention
            + (1.0 - self.local_weight) * global_attention
        )
        attention = F.interpolate(
            attention, size=(h, w), mode="bilinear", align_corners=False
        )
        return x * self.sigmoid(attention)


class ResidualHCA(nn.Module):
    """Residual HCA gate kept near identity unless explicitly enabled."""

    def __init__(
        self,
        channels,
        gamma_init=1e-6,
        local_size=5,
        local_weight=0.5,
        kernel_size=5,
    ):
        super().__init__()
        self.attention = HybridChannelAttention(
            channels,
            local_size=local_size,
            local_weight=local_weight,
            kernel_size=kernel_size,
        )
        self.gamma = nn.Parameter(torch.full((1, channels, 1, 1), gamma_init))

    def forward(self, x):
        attended = self.attention(x)
        return x + self.gamma * (attended - x)


class ResNetLKA(nn.Module):
    """Keep the original ResNet intact and append opt-in enhancers."""

    def __init__(
        self,
        backbone,
        channels,
        lka_gamma_init=1e-6,
        lka_alpha=0.05,
        lka_output_mode="gated_residual",
        lka_residual_norm="none",
        lka_max_raw_norm_ratio=2.0,
        lka_norm_eps=1e-6,
        lka_gamma_warmup_enabled=False,
        lka_gamma_warmup_start=0.0,
        lka_gamma_warmup_end=1.0,
        lka_gamma_parameterization="direct",
        lka_gamma_clamp_min=0.0,
        lka_gamma_clamp_max=-1.0,
        hca_enabled=False,
        hca_gamma_init=1e-6,
        hca_local_size=5,
        hca_local_weight=0.5,
        hca_kernel_size=5,
    ):
        super().__init__()
        self.backbone = backbone
        self.lka = ResidualLKA(
            channels,
            gamma_init=lka_gamma_init,
            alpha=lka_alpha,
            output_mode=lka_output_mode,
            residual_norm=lka_residual_norm,
            max_raw_norm_ratio=lka_max_raw_norm_ratio,
            norm_eps=lka_norm_eps,
            gamma_warmup_enabled=lka_gamma_warmup_enabled,
            gamma_warmup_start=lka_gamma_warmup_start,
            gamma_warmup_end=lka_gamma_warmup_end,
            gamma_parameterization=lka_gamma_parameterization,
            gamma_clamp_min=lka_gamma_clamp_min,
            gamma_clamp_max=lka_gamma_clamp_max,
        )
        if hca_enabled:
            self.hca = ResidualHCA(
                channels,
                gamma_init=hca_gamma_init,
                local_size=hca_local_size,
                local_weight=hca_local_weight,
                kernel_size=hca_kernel_size,
            )
        else:
            self.hca = None

    def forward(self, x):
        x = self.backbone(x)
        x = self.lka(x)
        if self.hca is not None:
            x = self.hca(x)
        return x


class ResNetLKAStack(nn.Module):
    """Append a stack of gated residual LKA blocks after the ResNet output."""

    def __init__(
        self,
        backbone,
        channels,
        num_blocks=3,
        lka_gamma_init=1e-6,
        lka_alpha=0.05,
        lka_output_mode="gated_residual",
        lka_residual_norm="none",
        lka_max_raw_norm_ratio=2.0,
        lka_norm_eps=1e-6,
        lka_gamma_warmup_enabled=False,
        lka_gamma_warmup_start=0.0,
        lka_gamma_warmup_end=1.0,
        lka_gamma_parameterization="direct",
        lka_gamma_clamp_min=0.0,
        lka_gamma_clamp_max=-1.0,
        hca_enabled=False,
        hca_gamma_init=1e-6,
        hca_local_size=5,
        hca_local_weight=0.5,
        hca_kernel_size=5,
    ):
        super().__init__()
        self.backbone = backbone
        self.lka = ResidualLKAStack(
            channels,
            num_blocks=num_blocks,
            gamma_init=lka_gamma_init,
            alpha=lka_alpha,
            output_mode=lka_output_mode,
            residual_norm=lka_residual_norm,
            max_raw_norm_ratio=lka_max_raw_norm_ratio,
            norm_eps=lka_norm_eps,
            gamma_warmup_enabled=lka_gamma_warmup_enabled,
            gamma_warmup_start=lka_gamma_warmup_start,
            gamma_warmup_end=lka_gamma_warmup_end,
            gamma_parameterization=lka_gamma_parameterization,
            gamma_clamp_min=lka_gamma_clamp_min,
            gamma_clamp_max=lka_gamma_clamp_max,
        )
        if hca_enabled:
            self.hca = ResidualHCA(
                channels,
                gamma_init=hca_gamma_init,
                local_size=hca_local_size,
                local_weight=hca_local_weight,
                kernel_size=hca_kernel_size,
            )
        else:
            self.hca = None

    def forward(self, x):
        x = self.backbone(x)
        x = self.lka(x)
        if self.hca is not None:
            x = self.hca(x)
        return x


class ResNetPaperLKA(nn.Module):
    """Append a paper-style LKA stack after the ResNet backbone output."""

    def __init__(self, backbone, channels, num_blocks=3):
        super().__init__()
        self.backbone = backbone
        self.paper_lka = PaperStyleLKAStack(channels, num_blocks=num_blocks)

    def forward(self, x):
        x = self.backbone(x)
        x = self.paper_lka(x)
        return x


def _get_stage_out_channels(stage):
    last_block = stage[-1]
    for norm_name in ("bn3", "bn2"):
        norm = getattr(last_block, norm_name, None)
        if norm is not None and hasattr(norm, "num_features"):
            return norm.num_features
    raise ValueError("Cannot infer ResNet stage output channels for LKA.")


class ResNetLKAMultiStage(nn.Module):
    """S5-only wrapper that inserts LKA after layer3 and layer4."""

    def __init__(
        self,
        backbone,
        layer3_channels,
        layer4_channels,
        lka_gamma_init=1e-6,
        lka_alpha=0.05,
        lka_output_mode="gated_residual",
        lka_residual_norm="none",
        lka_max_raw_norm_ratio=2.0,
        lka_norm_eps=1e-6,
        lka_gamma_warmup_enabled=False,
        lka_gamma_warmup_start=0.0,
        lka_gamma_warmup_end=1.0,
        lka_gamma_parameterization="direct",
        lka_gamma_clamp_min=0.0,
        lka_gamma_clamp_max=-1.0,
        hca_enabled=False,
        hca_gamma_init=1e-6,
        hca_local_size=5,
        hca_local_weight=0.5,
        hca_kernel_size=5,
    ):
        super().__init__()
        self.backbone = backbone
        self.lka3 = ResidualLKA(
            layer3_channels,
            gamma_init=lka_gamma_init,
            alpha=lka_alpha,
            output_mode=lka_output_mode,
            residual_norm=lka_residual_norm,
            max_raw_norm_ratio=lka_max_raw_norm_ratio,
            norm_eps=lka_norm_eps,
            gamma_warmup_enabled=lka_gamma_warmup_enabled,
            gamma_warmup_start=lka_gamma_warmup_start,
            gamma_warmup_end=lka_gamma_warmup_end,
            gamma_parameterization=lka_gamma_parameterization,
            gamma_clamp_min=lka_gamma_clamp_min,
            gamma_clamp_max=lka_gamma_clamp_max,
        )
        self.lka4 = ResidualLKA(
            layer4_channels,
            gamma_init=lka_gamma_init,
            alpha=lka_alpha,
            output_mode=lka_output_mode,
            residual_norm=lka_residual_norm,
            max_raw_norm_ratio=lka_max_raw_norm_ratio,
            norm_eps=lka_norm_eps,
            gamma_warmup_enabled=lka_gamma_warmup_enabled,
            gamma_warmup_start=lka_gamma_warmup_start,
            gamma_warmup_end=lka_gamma_warmup_end,
            gamma_parameterization=lka_gamma_parameterization,
            gamma_clamp_min=lka_gamma_clamp_min,
            gamma_clamp_max=lka_gamma_clamp_max,
        )
        if hca_enabled:
            self.hca = ResidualHCA(
                layer4_channels,
                gamma_init=hca_gamma_init,
                local_size=hca_local_size,
                local_weight=hca_local_weight,
                kernel_size=hca_kernel_size,
            )
        else:
            self.hca = None

    @staticmethod
    def _forward_stage(x, layer, nl_modules, nl_idx):
        if len(nl_idx) == 0 or (len(nl_idx) == 1 and nl_idx[0] == -1):
            for block in layer:
                x = block(x)
            return x

        if nl_modules is None:
            raise ValueError("Non-local indices exist, but the stage has no NL modules.")

        nl_counter = 0
        for i in range(len(layer)):
            x = layer[i](x)
            if nl_counter < len(nl_idx) and i == nl_idx[nl_counter]:
                x = nl_modules[nl_counter](x)
                nl_counter += 1
        return x

    def forward(self, x):
        backbone = self.backbone
        x = backbone.conv1(x)
        x = backbone.bn1(x)
        x = backbone.relu(x)
        x = backbone.maxpool(x)

        x = self._forward_stage(
            x, backbone.layer1, getattr(backbone, "NL_1", None), backbone.NL_1_idx
        )
        x = self._forward_stage(
            x, backbone.layer2, getattr(backbone, "NL_2", None), backbone.NL_2_idx
        )
        x = self._forward_stage(
            x, backbone.layer3, getattr(backbone, "NL_3", None), backbone.NL_3_idx
        )
        x = self.lka3(x)
        x = self._forward_stage(
            x, backbone.layer4, getattr(backbone, "NL_4", None), backbone.NL_4_idx
        )
        x = self.lka4(x)
        if self.hca is not None:
            x = self.hca(x)
        return x


@BACKBONE_REGISTRY.register()
def build_resnet_lka_backbone(cfg):
    """Build a ResNet backbone with an opt-in LKA layer4 feature enhancer."""

    lka_cfg = cfg.MODEL.BACKBONE.LKA
    hca_cfg = cfg.MODEL.BACKBONE.HCA
    backbone = build_resnet_backbone(cfg)

    if not lka_cfg.ENABLED:
        if hca_cfg.ENABLED:
            raise ValueError("HCA requires LKA.ENABLED=True in this backbone.")
        return backbone

    stages = tuple(lka_cfg.STAGES)
    if stages != ("layer4",):
        raise ValueError("ResidualLKA currently supports only STAGES=('layer4',).")

    return ResNetLKA(
        backbone,
        channels=cfg.MODEL.BACKBONE.FEAT_DIM,
        lka_gamma_init=lka_cfg.GAMMA_INIT,
        lka_alpha=lka_cfg.ALPHA,
        lka_output_mode=lka_cfg.OUTPUT_MODE,
        lka_residual_norm=lka_cfg.RESIDUAL_NORM,
        lka_max_raw_norm_ratio=lka_cfg.MAX_RAW_NORM_RATIO,
        lka_norm_eps=lka_cfg.NORM_EPS,
        lka_gamma_warmup_enabled=lka_cfg.GAMMA_WARMUP_ENABLED,
        lka_gamma_warmup_start=lka_cfg.GAMMA_WARMUP_START,
        lka_gamma_warmup_end=lka_cfg.GAMMA_WARMUP_END,
        lka_gamma_parameterization=lka_cfg.GAMMA_PARAMETERIZATION,
        lka_gamma_clamp_min=lka_cfg.GAMMA_CLAMP_MIN,
        lka_gamma_clamp_max=lka_cfg.GAMMA_CLAMP_MAX,
        hca_enabled=hca_cfg.ENABLED,
        hca_gamma_init=hca_cfg.GAMMA_INIT,
        hca_local_size=hca_cfg.LOCAL_SIZE,
        hca_local_weight=hca_cfg.LOCAL_WEIGHT,
        hca_kernel_size=hca_cfg.KERNEL_SIZE,
    )


@BACKBONE_REGISTRY.register()
def build_resnet_lka_multistage_backbone(cfg):
    """Build the S5 backbone with opt-in LKA after layer3 and layer4."""

    lka_cfg = cfg.MODEL.BACKBONE.LKA
    hca_cfg = cfg.MODEL.BACKBONE.HCA
    backbone = build_resnet_backbone(cfg)

    if not lka_cfg.ENABLED:
        if hca_cfg.ENABLED:
            raise ValueError("HCA requires LKA.ENABLED=True in this backbone.")
        return backbone

    stages = tuple(lka_cfg.STAGES)
    if stages != ("layer3", "layer4"):
        raise ValueError(
            "S5 ResidualLKA requires STAGES=('layer3', 'layer4') in this backbone."
        )

    return ResNetLKAMultiStage(
        backbone,
        layer3_channels=_get_stage_out_channels(backbone.layer3),
        layer4_channels=_get_stage_out_channels(backbone.layer4),
        lka_gamma_init=lka_cfg.GAMMA_INIT,
        lka_alpha=lka_cfg.ALPHA,
        lka_output_mode=lka_cfg.OUTPUT_MODE,
        lka_residual_norm=lka_cfg.RESIDUAL_NORM,
        lka_max_raw_norm_ratio=lka_cfg.MAX_RAW_NORM_RATIO,
        lka_norm_eps=lka_cfg.NORM_EPS,
        lka_gamma_warmup_enabled=lka_cfg.GAMMA_WARMUP_ENABLED,
        lka_gamma_warmup_start=lka_cfg.GAMMA_WARMUP_START,
        lka_gamma_warmup_end=lka_cfg.GAMMA_WARMUP_END,
        lka_gamma_parameterization=lka_cfg.GAMMA_PARAMETERIZATION,
        lka_gamma_clamp_min=lka_cfg.GAMMA_CLAMP_MIN,
        lka_gamma_clamp_max=lka_cfg.GAMMA_CLAMP_MAX,
        hca_enabled=hca_cfg.ENABLED,
        hca_gamma_init=hca_cfg.GAMMA_INIT,
        hca_local_size=hca_cfg.LOCAL_SIZE,
        hca_local_weight=hca_cfg.LOCAL_WEIGHT,
        hca_kernel_size=hca_cfg.KERNEL_SIZE,
    )


@BACKBONE_REGISTRY.register()
def build_resnet_lka_stack_backbone(cfg):
    """Build ResNet followed by a gated residual LKA stack after layer4."""

    lka_cfg = cfg.MODEL.BACKBONE.LKA
    hca_cfg = cfg.MODEL.BACKBONE.HCA
    backbone = build_resnet_backbone(cfg)

    if not lka_cfg.ENABLED:
        if hca_cfg.ENABLED:
            raise ValueError("HCA requires LKA.ENABLED=True in this backbone.")
        return backbone

    stages = tuple(lka_cfg.STAGES)
    if stages != ("layer4",):
        raise ValueError("Stacked ResidualLKA supports only STAGES=('layer4',).")

    return ResNetLKAStack(
        backbone,
        channels=cfg.MODEL.BACKBONE.FEAT_DIM,
        num_blocks=lka_cfg.NUM_BLOCKS,
        lka_gamma_init=lka_cfg.GAMMA_INIT,
        lka_alpha=lka_cfg.ALPHA,
        lka_output_mode=lka_cfg.OUTPUT_MODE,
        lka_residual_norm=lka_cfg.RESIDUAL_NORM,
        lka_max_raw_norm_ratio=lka_cfg.MAX_RAW_NORM_RATIO,
        lka_norm_eps=lka_cfg.NORM_EPS,
        lka_gamma_warmup_enabled=lka_cfg.GAMMA_WARMUP_ENABLED,
        lka_gamma_warmup_start=lka_cfg.GAMMA_WARMUP_START,
        lka_gamma_warmup_end=lka_cfg.GAMMA_WARMUP_END,
        lka_gamma_parameterization=lka_cfg.GAMMA_PARAMETERIZATION,
        lka_gamma_clamp_min=lka_cfg.GAMMA_CLAMP_MIN,
        lka_gamma_clamp_max=lka_cfg.GAMMA_CLAMP_MAX,
        hca_enabled=hca_cfg.ENABLED,
        hca_gamma_init=hca_cfg.GAMMA_INIT,
        hca_local_size=hca_cfg.LOCAL_SIZE,
        hca_local_weight=hca_cfg.LOCAL_WEIGHT,
        hca_kernel_size=hca_cfg.KERNEL_SIZE,
    )


@BACKBONE_REGISTRY.register()
def build_resnet_paper_lka_backbone(cfg):
    """Build ResNet followed by paper-style LKA x N after layer4."""

    paper_lka_cfg = cfg.MODEL.BACKBONE.PAPER_LKA
    backbone = build_resnet_backbone(cfg)

    if not paper_lka_cfg.ENABLED:
        return backbone

    stages = tuple(paper_lka_cfg.STAGES)
    if stages != ("layer4",):
        raise ValueError("PaperStyleLKA currently supports only STAGES=('layer4',).")

    return ResNetPaperLKA(
        backbone,
        channels=cfg.MODEL.BACKBONE.FEAT_DIM,
        num_blocks=paper_lka_cfg.NUM_BLOCKS,
    )
