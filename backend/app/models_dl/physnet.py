"""
PhysNet: Spatio-Temporal 3D Convolutional Network for rPPG.

Based on:
Yu, Z., Li, X., & Zhao, G. (2019).
"Remote Photoplethysmograph Signal Measurement from Facial Videos Using Spatio-Temporal Networks".
Proceedings of the 30th British Machine Vision Conference (BMVC 2019).
"""

from typing import Dict, Any, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvBlock3D(nn.Module):
    """3D Convolution + Batch Normalization + ELU activation."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: Tuple[int, int, int] = (3, 3, 3),
        stride: Tuple[int, int, int] = (1, 1, 1),
        padding: Tuple[int, int, int] = (1, 1, 1),
    ):
        super().__init__()
        self.conv = nn.Conv3d(
            in_channels,
            out_channels,
            kernel_size=kernel_size,
            stride=stride,
            padding=padding,
            bias=False,
        )
        self.bn = nn.BatchNorm3d(out_channels)
        self.activation = nn.ELU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.activation(self.bn(self.conv(x)))


class ResBlock3D(nn.Module):
    """Residual 3D Convolutional Block."""

    def __init__(self, channels: int):
        super().__init__()
        self.block = nn.Sequential(
            ConvBlock3D(channels, channels, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
            nn.Conv3d(channels, channels, kernel_size=(3, 3, 3), padding=(1, 1, 1), bias=False),
            nn.BatchNorm3d(channels),
        )
        self.activation = nn.ELU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.block(x)
        return self.activation(out + residual)


class PhysNet(nn.Module):
    """
    PhysNet spatio-temporal deep neural network.

    Takes a normalized facial video tensor (B, C=3, T, H, W) and outputs
    a continuous physiological pulse waveform of shape (B, T).

    Architecture:
    1. Spatial Stem: Conv3D with 1x5x5 filter preserving temporal frames.
    2. Spatio-Temporal Encoder: 3 stages with spatial MaxPool3d (1, 2, 2)
       progressively shrinking HxW while retaining full temporal dimension T.
    3. Global Spatial Average Pooling: collapses spatial dimensions to 1x1.
    4. Temporal 1D Convolutional Head: projects latent temporal feature maps to 1D pulse wave.
    """

    def __init__(
        self,
        in_channels: int = 3,
        base_channels: int = 16,
        sequence_length: int = 64,
        spatial_size: int = 32,
    ):
        super().__init__()
        self.sequence_length = sequence_length
        self.spatial_size = spatial_size

        # Stage 1: Spatial filter stem
        self.stem = ConvBlock3D(
            in_channels,
            base_channels,
            kernel_size=(1, 5, 5),
            padding=(0, 2, 2),
        )
        self.pool1 = nn.MaxPool3d(kernel_size=(1, 2, 2), stride=(1, 2, 2))

        # Stage 2: Spatio-temporal residual learning
        self.stage2 = nn.Sequential(
            ConvBlock3D(base_channels, base_channels * 2, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
            ResBlock3D(base_channels * 2),
        )
        self.pool2 = nn.MaxPool3d(kernel_size=(1, 2, 2), stride=(1, 2, 2))

        # Stage 3: High-level feature extraction
        self.stage3 = nn.Sequential(
            ConvBlock3D(base_channels * 2, base_channels * 4, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
            ResBlock3D(base_channels * 4),
        )
        self.pool3 = nn.MaxPool3d(kernel_size=(1, 2, 2), stride=(1, 2, 2))

        # Stage 4: Bottleneck
        self.stage4 = nn.Sequential(
            ConvBlock3D(base_channels * 4, base_channels * 4, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
            ResBlock3D(base_channels * 4),
        )

        # Global spatial adaptive pooling: (B, C, T, H, W) -> (B, C, T, 1, 1)
        self.spatial_pool = nn.AdaptiveAvgPool3d((None, 1, 1))

        # Temporal head
        self.head = nn.Sequential(
            nn.Conv1d(base_channels * 4, base_channels * 2, kernel_size=3, padding=1),
            nn.ELU(inplace=True),
            nn.Conv1d(base_channels * 2, 1, kernel_size=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input video tensor of shape (B, 3, T, H, W).

        Returns:
            waveform: Extracted 1D rPPG pulse signal of shape (B, T).
        """
        # (B, 3, T, H, W) -> (B, 16, T, H/2, W/2)
        out = self.pool1(self.stem(x))

        # -> (B, 32, T, H/4, W/4)
        out = self.pool2(self.stage2(out))

        # -> (B, 64, T, H/8, W/8)
        out = self.pool3(self.stage3(out))

        # -> (B, 64, T, H/8, W/8)
        out = self.stage4(out)

        # Global spatial average pooling over H and W dimensions -> (B, C, T)
        out = torch.mean(out, dim=(-2, -1))

        # Head -> (B, 1, T) -> (B, T)
        waveform = self.head(out).squeeze(1)

        # Normalize waveform across time: zero mean and unit variance per sample
        w_mean = torch.mean(waveform, dim=-1, keepdim=True)
        w_std = torch.std(waveform, dim=-1, keepdim=True) + 1e-7
        norm_waveform = (waveform - w_mean) / w_std

        return norm_waveform
