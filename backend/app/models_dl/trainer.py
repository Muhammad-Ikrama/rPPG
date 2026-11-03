"""
Deep Learning Training Harness, Checkpoint Registry, and Experiment Tracker.

Complies strictly with Section 8:
- Real loss computation and gradient descent.
- Complete metadata logging (seed, learning rate, epoch loss, checkpoints).
- No fabricated results; experiments record actual numerical outcomes.
- ONNX model export for edge deployment transitions.
"""

from typing import Dict, Any, List, Optional
import os
import json
import time
import shutil
import warnings
from datetime import datetime, timezone
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from app.models_dl.physnet import PhysNet
from app.models_dl.losses import NegativePearsonLoss, CompositeRPPGLoss
from app.models_dl.dataset import create_partitioned_dataloaders


class ModelExperimentTracker:
    """Persistent JSON-based experiment registry and metric tracker."""

    def __init__(self, registry_dir: str = "./storage/experiments"):
        self.registry_dir = registry_dir
        os.makedirs(self.registry_dir, exist_ok=True)
        self.log_file = os.path.join(self.registry_dir, "experiments_registry.json")
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                json.dump([], f)

    def log_experiment(self, experiment_record: Dict[str, Any]) -> str:
        """Appends a completed training experiment record."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            records = []
        else:
            with open(self.log_file, "r") as f:
                try:
                    records = json.load(f)
                except Exception:
                    records = []
        records.append(experiment_record)
        with open(self.log_file, "w") as f:
            json.dump(records, f, indent=2)
        return experiment_record["experiment_id"]

    def list_experiments(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.log_file):
            return []
        with open(self.log_file, "r") as f:
            return json.load(f)


class PhysNetTrainer:
    """
    Dedicated training and validation harness for PhysNet.
    """

    def __init__(
        self,
        model: Optional[PhysNet] = None,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        device: Optional[str] = None,
        checkpoint_dir: str = "./storage/checkpoints",
    ):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        self.model = model.to(self.device) if model else PhysNet().to(self.device)
        self.lr = lr
        self.weight_decay = weight_decay
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(self.checkpoint_dir, exist_ok=True)

        self.criterion = CompositeRPPGLoss()
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.lr,
            weight_decay=self.weight_decay,
        )
        self.tracker = ModelExperimentTracker()

    def train_epoch(self, dataloader: DataLoader) -> Dict[str, float]:
        self.model.train()
        total_loss = 0.0
        total_pearson = 0.0
        n_batches = 0

        for batch in dataloader:
            videos = batch["video"].to(self.device)
            gt_bvp = batch["bvp"].to(self.device)

            self.optimizer.zero_grad()
            pred_bvp = self.model(videos)

            loss_dict = self.criterion(pred_bvp, gt_bvp)
            loss = loss_dict["loss"]
            loss.backward()

            # Gradient clipping for stable convergence
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()

            total_loss += loss.item()
            total_pearson += loss_dict["pearson_loss"].item()
            n_batches += 1

        avg_loss = total_loss / max(1, n_batches)
        avg_pearson = total_pearson / max(1, n_batches)
        return {"train_loss": avg_loss, "train_pearson_loss": avg_pearson}

    def validate(self, dataloader: DataLoader) -> Dict[str, float]:
        self.model.eval()
        total_loss = 0.0
        total_pearson = 0.0
        n_batches = 0

        with torch.no_grad():
            for batch in dataloader:
                videos = batch["video"].to(self.device)
                gt_bvp = batch["bvp"].to(self.device)

                pred_bvp = self.model(videos)
                loss_dict = self.criterion(pred_bvp, gt_bvp)

                total_loss += loss_dict["loss"].item()
                total_pearson += loss_dict["pearson_loss"].item()
                n_batches += 1

        avg_loss = total_loss / max(1, n_batches)
        avg_pearson = total_pearson / max(1, n_batches)
        return {"val_loss": avg_loss, "val_pearson_loss": avg_pearson}

    def run_training_experiment(
        self,
        num_epochs: int = 3,
        num_subjects: int = 10,
        batch_size: int = 2,
        experiment_name: str = "PhysNet_Baseline_Trial",
        random_seed: int = 42,
        resume_checkpoint: Optional[str] = None,
        backup_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a genuine end-to-end training and evaluation experiment.
        Supports resume after disconnection (Google Colab / Kaggle 12h/9h runtime caps)
        and atomic backup to Google Drive or persistent storage.
        """
        torch.manual_seed(random_seed)
        start_time = time.time()
        exp_id = f"EXP-PHYSNET-{int(time.time())}"
        start_epoch = 1
        history: List[Dict[str, Any]] = []
        best_val_loss = float("inf")
        best_checkpoint_path = ""
        latest_checkpoint_path = ""

        if backup_dir:
            os.makedirs(backup_dir, exist_ok=True)

        # Resume logic for runtime disconnect recovery
        if resume_checkpoint and os.path.exists(resume_checkpoint):
            ckpt = torch.load(resume_checkpoint, map_location=self.device)
            self.model.load_state_dict(ckpt["model_state_dict"])
            if "optimizer_state_dict" in ckpt:
                self.optimizer.load_state_dict(ckpt["optimizer_state_dict"])
            start_epoch = ckpt.get("epoch", 0) + 1
            best_val_loss = ckpt.get("val_loss", float("inf"))
            exp_id = ckpt.get("experiment_id", exp_id)
            history = ckpt.get("history", [])

        train_loader, val_loader, test_loader, partitions = create_partitioned_dataloaders(
            num_subjects=num_subjects,
            batch_size=batch_size,
            random_seed=random_seed,
        )

        for epoch in range(start_epoch, num_epochs + 1):
            t_epoch_start = time.time()
            train_metrics = self.train_epoch(train_loader)
            val_metrics = self.validate(val_loader)
            epoch_duration = time.time() - t_epoch_start

            record = {
                "epoch": epoch,
                "train_loss": round(train_metrics["train_loss"], 4),
                "val_loss": round(val_metrics["val_loss"], 4),
                "train_pearson_loss": round(train_metrics["train_pearson_loss"], 4),
                "val_pearson_loss": round(val_metrics["val_pearson_loss"], 4),
                "duration_seconds": round(epoch_duration, 2),
            }
            history.append(record)

            # 1. Save latest checkpoint every epoch for disconnect recovery
            latest_checkpoint_path = os.path.join(self.checkpoint_dir, f"{exp_id}_latest.pt")
            checkpoint_state = {
                "experiment_id": exp_id,
                "epoch": epoch,
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "val_loss": val_metrics["val_loss"],
                "best_val_loss": best_val_loss,
                "history": history,
                "hyperparameters": {
                    "lr": self.lr,
                    "weight_decay": self.weight_decay,
                    "seed": random_seed,
                },
            }
            torch.save(checkpoint_state, latest_checkpoint_path)

            # 2. Checkpoint best model if improved
            if val_metrics["val_loss"] < best_val_loss:
                best_val_loss = val_metrics["val_loss"]
                best_checkpoint_path = os.path.join(self.checkpoint_dir, f"{exp_id}_best.pt")
                torch.save(checkpoint_state, best_checkpoint_path)

            # 3. Synchronize to external backup (e.g. Google Drive) if configured
            if backup_dir:
                try:
                    shutil.copy2(latest_checkpoint_path, os.path.join(backup_dir, f"{exp_id}_latest.pt"))
                    if best_checkpoint_path and os.path.exists(best_checkpoint_path):
                        shutil.copy2(best_checkpoint_path, os.path.join(backup_dir, f"{exp_id}_best.pt"))
                except Exception:
                    pass

        # Independent test evaluation
        test_metrics = self.validate(test_loader)
        total_training_duration = time.time() - start_time

        # Export ONNX for edge-readiness
        onnx_path = os.path.join(self.checkpoint_dir, f"{exp_id}.onnx")
        try:
            self.model.eval()
            dummy_input = torch.randn(1, 3, 64, 32, 32, device=self.device)
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                torch.onnx.export(
                    self.model,
                    dummy_input,
                    onnx_path,
                    input_names=["video_frames"],
                    output_names=["rppg_waveform"],
                    dynamic_axes={
                        "video_frames": {0: "batch", 2: "time"},
                        "rppg_waveform": {0: "batch", 1: "time"},
                    },
                    opset_version=14,
                    dynamo=False,
                )
            onnx_exported = os.path.exists(onnx_path)
            if onnx_exported and backup_dir:
                try:
                    shutil.copy2(onnx_path, os.path.join(backup_dir, f"{exp_id}.onnx"))
                except Exception:
                    pass
        except Exception:
            onnx_exported = False
            onnx_path = None

        experiment_summary = {
            "experiment_id": exp_id,
            "experiment_name": experiment_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_architecture": "PhysNet (Yu et al. BMVC 2019)",
            "device": str(self.device),
            "status": "COMPLETED",
            "hyperparameters": {
                "initial_lr": self.lr,
                "weight_decay": self.weight_decay,
                "batch_size": batch_size,
                "epochs": num_epochs,
                "random_seed": random_seed,
                "optimizer": "AdamW",
                "loss_function": "CompositeRPPGLoss (Pearson + Spectral SNR + Derivative)",
            },
            "data_partitions": partitions,
            "training_history": history,
            "final_metrics": {
                "best_val_loss": round(best_val_loss, 4),
                "test_loss": round(test_metrics["val_loss"], 4),
                "test_pearson_loss": round(test_metrics["val_pearson_loss"], 4),
                "total_training_duration_seconds": round(total_training_duration, 2),
            },
            "artifacts": {
                "checkpoint_path": best_checkpoint_path,
                "onnx_exported": onnx_exported,
                "onnx_path": onnx_path,
            },
        }

        self.tracker.log_experiment(experiment_summary)
        return experiment_summary
