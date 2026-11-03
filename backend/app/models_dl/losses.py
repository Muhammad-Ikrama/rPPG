"""
Biomedical Loss Functions for Deep Learning rPPG Signal Extraction.

Implements:
1. Negative Pearson Correlation Loss (Yu et al. 2019, Liu et al. 2020)
2. Frequency Domain SNR / Spectral Peak Loss
3. Normalized Derivative (First-Order Difference) Loss
4. Composite Multi-Objective rPPG Loss
"""

from typing import Dict, Any, Optional
import torch
import torch.nn as nn
import torch.nn.functional as F


class NegativePearsonLoss(nn.Module):
    """
    Negative Pearson Correlation Loss.

    Loss = 1.0 - Pearson(y_pred, y_true)
    Values range from 0.0 (perfect correlation) to 2.0 (perfect anti-correlation).
    """

    def __init__(self, eps: float = 1e-7):
        super().__init__()
        self.eps = eps

    def forward(self, y_pred: torch.Tensor, y_true: torch.Tensor) -> torch.Tensor:
        """
        Args:
            y_pred: Predicted waveform of shape (Batch, Time).
            y_true: Ground truth waveform of shape (Batch, Time).

        Returns:
            Scalar loss.
        """
        # Ensure 2D (Batch, Time)
        if y_pred.dim() > 2:
            y_pred = y_pred.squeeze(1)
        if y_true.dim() > 2:
            y_true = y_true.squeeze(1)

        pred_mean = torch.mean(y_pred, dim=-1, keepdim=True)
        true_mean = torch.mean(y_true, dim=-1, keepdim=True)

        pred_centered = y_pred - pred_mean
        true_centered = y_true - true_mean

        numerator = torch.sum(pred_centered * true_centered, dim=-1)
        denominator = torch.sqrt(
            torch.sum(pred_centered ** 2, dim=-1) * torch.sum(true_centered ** 2, dim=-1) + self.eps
        )

        pearson = numerator / denominator
        loss = 1.0 - torch.mean(pearson)
        return loss


class SpectralSNRLoss(nn.Module):
    """
    Frequency-domain spectral loss encouraging energy profile agreement
    between predicted and reference cardiac power spectra.
    """

    def __init__(self, fs: float = 30.0, lowcut: float = 0.7, highcut: float = 3.5):
        super().__init__()
        self.fs = fs
        self.lowcut = lowcut
        self.highcut = highcut

    def forward(self, y_pred: torch.Tensor, y_true: torch.Tensor) -> torch.Tensor:
        if y_pred.dim() > 2:
            y_pred = y_pred.squeeze(1)
        if y_true.dim() > 2:
            y_true = y_true.squeeze(1)

        # Real FFT
        pred_fft = torch.fft.rfft(y_pred, dim=-1)
        true_fft = torch.fft.rfft(y_true, dim=-1)

        pred_psd = torch.abs(pred_fft) ** 2
        true_psd = torch.abs(true_fft) ** 2

        # Cosine spectral distance: 1.0 - CosineSimilarity(PSD_pred, PSD_true)
        cos_sim = F.cosine_similarity(pred_psd + 1e-8, true_psd + 1e-8, dim=-1)
        loss = 1.0 - torch.mean(cos_sim)
        return loss


class CompositeRPPGLoss(nn.Module):
    """
    Multi-objective rPPG loss combining:
    1. Temporal waveform correlation (Negative Pearson)
    2. Spectral profile agreement (Spectral SNR)
    3. Derivative consistency (First-order derivative MSE)
    """

    def __init__(
        self,
        weight_pearson: float = 1.0,
        weight_spectral: float = 0.1,
        weight_derivative: float = 0.2,
        fs: float = 30.0,
    ):
        super().__init__()
        self.weight_pearson = weight_pearson
        self.weight_spectral = weight_spectral
        self.weight_derivative = weight_derivative

        self.pearson_loss = NegativePearsonLoss()
        self.spectral_loss = SpectralSNRLoss(fs=fs)

    def forward(self, y_pred: torch.Tensor, y_true: torch.Tensor) -> Dict[str, torch.Tensor]:
        if y_pred.dim() > 2:
            y_pred = y_pred.squeeze(1)
        if y_true.dim() > 2:
            y_true = y_true.squeeze(1)

        loss_p = self.pearson_loss(y_pred, y_true)
        loss_s = self.spectral_loss(y_pred, y_true)

        # First-order temporal difference
        d_pred = y_pred[:, 1:] - y_pred[:, :-1]
        d_true = y_true[:, 1:] - y_true[:, :-1]
        loss_d = F.mse_loss(d_pred, d_true)

        total_loss = (
            self.weight_pearson * loss_p
            + self.weight_spectral * loss_s
            + self.weight_derivative * loss_d
        )

        return {
            "loss": total_loss,
            "pearson_loss": loss_p,
            "spectral_loss": loss_s,
            "derivative_loss": loss_d,
        }
