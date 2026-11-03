"""
Multi-Task Temporal Shift Convolutional Attention Network (MTTS-CAN).

Based on:
Liu, X., Fromm, J., Patel, S., & McDuff, D. (2020).
"Multi-Task Temporal Shift Attention Networks for On-Device Contactless Vitals Measurement".
Advances in Neural Information Processing Systems (NeurIPS 2020).
"""

from typing import Dict, Any, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class TemporalShift(nn.Module):
    """
    Temporal Shift Module (TSM).

    Shifts 1/4 of channels backward in time (-1) and 1/4 forward (+1)
    along the sequence dimension, enabling 2D convolutions to model
    spatio-temporal dynamics without 3D convolution overhead.
    """

    def __init__(self, n_segment: int = 10, fold_div: int = 4):
        super().__init__()
        self.n_segment = n_segment
        self.fold_div = fold_div

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape (Batch * Time, Channels, Height, Width).
        """
        nt, c, h, w = x.size()
        n_batch = nt // self.n_segment
        if n_batch == 0 or self.n_segment == 0:
            return x

        x = x.view(n_batch, self.n_segment, c, h, w)
        fold = c // self.fold_div

        out = torch.zeros_like(x)
        # Shift backward
        out[:, :-1, :fold] = x[:, 1:, :fold]
        # Shift forward
        out[:, 1:, fold: 2 * fold] = x[:, :-1, fold: 2 * fold]
        # Identity for remaining channels
        out[:, :, 2 * fold:] = x[:, :, 2 * fold:]

        return out.view(nt, c, h, w)


class AttentionMask(nn.Module):
    """Spatial attention generation block from the Appearance model branch."""

    def __init__(self, in_channels: int):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, 1, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Sigmoid spatial gating normalized across (H, W)
        mask = torch.sigmoid(self.conv(x))
        b, _, h, w = mask.shape
        # Scale to ensure stable gradients
        norm = 2.0 * mask / (torch.mean(mask.view(b, -1), dim=1, keepdim=True).view(b, 1, 1, 1) + 1e-7)
        return norm


class MTTS_CAN(nn.Module):
    """
    Multi-Task Temporal Shift Convolutional Attention Network (MTTS-CAN).

    Features:
    - Dual branches: Appearance Model (learns skin spatial weights) and Motion Model (processes frame differences).
    - TSM layers embedded within 2D Conv stages for temporal modeling.
    - Multi-task output heads: simultaneous prediction of Cardiac Pulse Wave (HR)
      and Respiratory Wave (RR).
    """

    def __init__(
        self,
        in_channels: int = 3,
        frame_depth: int = 10,
        img_size: int = 36,
    ):
        super().__init__()
        self.frame_depth = frame_depth
        self.img_size = img_size

        # --- Appearance Branch (Raw Frames) ---
        self.app_conv1 = nn.Conv2d(in_channels, 32, kernel_size=3, padding=1)
        self.app_conv2 = nn.Conv2d(32, 32, kernel_size=3, padding=1)
        self.app_attn1 = AttentionMask(32)

        self.app_conv3 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.app_conv4 = nn.Conv2d(64, 64, kernel_size=3, padding=1)
        self.app_attn2 = AttentionMask(64)

        # --- Motion Branch (Normalized Frame Differences) ---
        self.tsm1 = TemporalShift(n_segment=frame_depth)
        self.motion_conv1 = nn.Conv2d(in_channels, 32, kernel_size=3, padding=1)
        self.tsm2 = TemporalShift(n_segment=frame_depth)
        self.motion_conv2 = nn.Conv2d(32, 32, kernel_size=3, padding=1)

        self.tsm3 = TemporalShift(n_segment=frame_depth)
        self.motion_conv3 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.tsm4 = TemporalShift(n_segment=frame_depth)
        self.motion_conv4 = nn.Conv2d(64, 64, kernel_size=3, padding=1)

        self.pool = nn.AvgPool2d(2, 2)
        self.dropout1 = nn.Dropout2d(0.25)
        self.dropout2 = nn.Dropout2d(0.50)

        # Shared Latent Representation
        # Flattened dimension after 2 pooling layers on 36x36 input: 36 -> 18 -> 9
        feat_dim = 64 * (img_size // 4) * (img_size // 4)
        self.shared_fc = nn.Linear(feat_dim, 128)

        # Multi-Task Heads
        # Head 1: Cardiac Pulse (HR)
        self.head_hr = nn.Sequential(
            nn.Linear(128, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )

        # Head 2: Respiration (RR)
        self.head_rr = nn.Sequential(
            nn.Linear(128, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )

    def forward(
        self,
        motion_input: torch.Tensor,
        appearance_input: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            motion_input: Normalized difference frames of shape (Batch * Time, 3, H, W).
            appearance_input: Raw video frames of shape (Batch * Time, 3, H, W).

        Returns:
            pulse_pred: Predicted cardiac pulse wave of shape (Batch, Time).
            resp_pred: Predicted respiratory wave of shape (Batch, Time).
        """
        # Appearance Branch -> Spatial Attention Mask 1
        a = F.tanh(self.app_conv1(appearance_input))
        a = F.tanh(self.app_conv2(a))
        attn1 = self.app_attn1(a)
        a = self.pool(a)

        # Motion Branch Stage 1 conditioned on Attention Mask 1
        m = F.tanh(self.motion_conv1(self.tsm1(motion_input)))
        m = F.tanh(self.motion_conv2(self.tsm2(m)))
        m = m * attn1
        m = self.pool(m)
        m = self.dropout1(m)

        # Appearance Branch Stage 2 -> Spatial Attention Mask 2
        a = F.tanh(self.app_conv3(a))
        a = F.tanh(self.app_conv4(a))
        attn2 = self.app_attn2(a)
        a = self.pool(a)

        # Motion Branch Stage 2 conditioned on Attention Mask 2
        m = F.tanh(self.motion_conv3(self.tsm3(m)))
        m = F.tanh(self.motion_conv4(self.tsm4(m)))
        m = m * attn2
        m = self.pool(m)
        m = self.dropout2(m)

        # Flatten
        nt = m.size(0)
        feat = m.view(nt, -1)
        shared = F.tanh(self.shared_fc(feat))

        # Predict per-frame derivatives
        pulse_pts = self.head_hr(shared)  # (NT, 1)
        resp_pts = self.head_rr(shared)   # (NT, 1)

        # Reshape to (Batch, Time)
        n_batch = nt // self.frame_depth
        pulse_wave = pulse_pts.view(n_batch, self.frame_depth)
        resp_wave = resp_pts.view(n_batch, self.frame_depth)

        # Temporal cumulative sum / integration to convert derivatives into continuous waveform
        pulse_continuous = torch.cumsum(pulse_wave, dim=-1)
        resp_continuous = torch.cumsum(resp_wave, dim=-1)

        # Zero-mean & unit variance normalization
        pulse_norm = (pulse_continuous - torch.mean(pulse_continuous, dim=-1, keepdim=True)) / (
            torch.std(pulse_continuous, dim=-1, keepdim=True) + 1e-7
        )
        resp_norm = (resp_continuous - torch.mean(resp_continuous, dim=-1, keepdim=True)) / (
            torch.std(resp_continuous, dim=-1, keepdim=True) + 1e-7
        )

        return pulse_norm, resp_norm

