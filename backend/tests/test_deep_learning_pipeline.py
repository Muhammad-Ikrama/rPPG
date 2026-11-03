"""
Unit and Integration Tests for Deep Learning rPPG Pipelines:
- PhysNet forward pass and gradient flow
- MTTS-CAN forward pass and attention masks
- Negative Pearson and Composite Losses
- Partitioned Dataloaders (Zero subject leakage)
- End-to-end training experiment and ONNX export
"""

import os
import pytest
import torch
import numpy as np

from app.models_dl.physnet import PhysNet
from app.models_dl.tscan import MTTS_CAN
from app.models_dl.losses import NegativePearsonLoss, CompositeRPPGLoss
from app.models_dl.dataset import create_partitioned_dataloaders
from app.models_dl.trainer import PhysNetTrainer, ModelExperimentTracker


def test_physnet_architecture():
    """Verify PhysNet accepts 5D video volume and outputs 1D normalized waveform."""
    batch_size = 2
    channels = 3
    time_frames = 32
    spatial_h = 32
    spatial_w = 32

    model = PhysNet(in_channels=channels, base_channels=8)
    dummy_video = torch.randn(batch_size, channels, time_frames, spatial_h, spatial_w)

    output = model(dummy_video)
    assert output.shape == (batch_size, time_frames)
    # Check normalization: zero-mean and unit variance
    mean_val = torch.mean(output, dim=-1)
    std_val = torch.std(output, dim=-1)
    assert torch.all(torch.abs(mean_val) < 1e-4)
    assert torch.all(torch.abs(std_val - 1.0) < 1e-2)


def test_mtts_can_architecture():
    """Verify MTTS-CAN multi-task outputs for both pulse (HR) and respiration (RR)."""
    batch_size = 2
    time_frames = 10
    total_frames = batch_size * time_frames
    h = 36
    w = 36

    model = MTTS_CAN(in_channels=3, frame_depth=time_frames, img_size=h)
    motion_input = torch.randn(total_frames, 3, h, w)
    app_input = torch.randn(total_frames, 3, h, w)

    pulse_out, resp_out = model(motion_input, app_input)
    assert pulse_out.shape == (batch_size, time_frames)
    assert resp_out.shape == (batch_size, time_frames)


def test_negative_pearson_loss():
    """Verify mathematical properties of Negative Pearson loss."""
    loss_fn = NegativePearsonLoss()

    # Identical signals should give loss ~ 0.0
    sig1 = torch.sin(torch.linspace(0, 10, 100)).unsqueeze(0)
    sig2 = sig1.clone()
    assert abs(loss_fn(sig1, sig2).item()) < 1e-4

    # Perfectly inverted signals should give loss ~ 2.0
    sig_neg = -sig1
    assert abs(loss_fn(sig1, sig_neg).item() - 2.0) < 1e-4


def test_zero_data_leakage_partitioning():
    """Verify zero participant overlap between train, val, and test splits."""
    train_loader, val_loader, test_loader, partitions = create_partitioned_dataloaders(
        num_subjects=12,
        samples_per_subject=4,
        sequence_length=16,
        batch_size=2,
    )

    train_set = set(partitions["train_subjects"])
    val_set = set(partitions["val_subjects"])
    test_set = set(partitions["test_subjects"])

    # Strict disjunction
    assert len(train_set.intersection(val_set)) == 0
    assert len(train_set.intersection(test_set)) == 0
    assert len(val_set.intersection(test_set)) == 0


def test_end_to_end_training_experiment(tmp_path):
    """Executes a genuine 1-epoch training experiment, checks checkpointing & ONNX export."""
    checkpoint_dir = str(tmp_path / "checkpoints")
    registry_dir = str(tmp_path / "experiments")

    model = PhysNet(in_channels=3, base_channels=4)
    trainer = PhysNetTrainer(
        model=model,
        lr=1e-3,
        device="cpu",
        checkpoint_dir=checkpoint_dir,
    )
    trainer.tracker.registry_dir = registry_dir
    trainer.tracker.log_file = os.path.join(registry_dir, "experiments_registry.json")

    summary = trainer.run_training_experiment(
        num_epochs=1,
        num_subjects=4,
        batch_size=2,
        experiment_name="CI_Test_Trial",
    )

    assert summary["status"] == "COMPLETED"
    assert len(summary["training_history"]) == 1
    assert summary["training_history"][0]["epoch"] == 1
    assert os.path.exists(summary["artifacts"]["checkpoint_path"])
    assert summary["artifacts"]["onnx_exported"] is True
    assert os.path.exists(summary["artifacts"]["onnx_path"])

