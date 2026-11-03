"""
REST API Endpoints for Deep Learning rPPG Models, Training Experiments, and Comparisons.
"""

from typing import Dict, Any, List, Optional
import os
import time
import torch
import numpy as np
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.models_dl.physnet import PhysNet
from app.models_dl.trainer import PhysNetTrainer, ModelExperimentTracker
from app.rppg.multi_algorithm_runner import run_traditional_comparison
from app.rppg.hr_estimation import estimate_heart_rate

router = APIRouter(prefix="/models", tags=["Deep Learning & Experiments"])
tracker = ModelExperimentTracker()


class TrainExperimentRequest(BaseModel):
    experiment_name: str = Field(default="PhysNet_Cohort_Training")
    num_epochs: int = Field(default=3, ge=1, le=50)
    num_subjects: int = Field(default=10, ge=2, le=100)
    batch_size: int = Field(default=2, ge=1, le=16)
    learning_rate: float = Field(default=1e-3, gt=0)
    random_seed: int = Field(default=42)


class DeepLearningCompareRequest(BaseModel):
    rgb_signals: List[List[float]]  # (N, 3) spatially averaged RGB traces
    fps: float = Field(default=30.0, gt=0)
    reference_hr_bpm: Optional[float] = None


@router.get("/experiments", response_model=List[Dict[str, Any]])
async def list_model_experiments():
    """
    Retrieves the complete history of real executed deep learning training experiments.
    Never fabricates training results.
    """
    return tracker.list_experiments()


@router.post("/train", response_model=Dict[str, Any])
async def trigger_training_experiment(payload: TrainExperimentRequest):
    """
    Executes a real deep learning model training run for PhysNet.
    Partitions participants strictly to avoid data leakage, records loss curves,
    saves PyTorch checkpoint (.pt), and exports ONNX artifact.
    """
    try:
        model = PhysNet(in_channels=3, base_channels=8)
        trainer = PhysNetTrainer(
            model=model,
            lr=payload.learning_rate,
            device="cpu",
        )
        summary = trainer.run_training_experiment(
            num_epochs=payload.num_epochs,
            num_subjects=payload.num_subjects,
            batch_size=payload.batch_size,
            experiment_name=payload.experiment_name,
            random_seed=payload.random_seed,
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.post("/compare-all", response_model=Dict[str, Any])
async def compare_all_algorithms(payload: DeepLearningCompareRequest):
    """
    Performs simultaneous head-to-head evaluation across:
    1. POS (Wang et al. 2017)
    2. CHROM (de Haan & Jeanne 2013)
    3. GREEN (Verkruysse et al. 2008)
    4. ICA (Poh et al. 2010)
    5. PhysNet (Deep Learning 3D-CNN, Yu et al. 2019)
    """
    rgb_arr = np.array(payload.rgb_signals, dtype=np.float64)
    if rgb_arr.ndim != 2 or rgb_arr.shape[1] != 3:
        raise HTTPException(status_code=400, detail="Expected rgb_signals shape (N, 3)")

    # 1. Run 4 traditional methods
    traditional_results = run_traditional_comparison(
        rgb_arr,
        fps=payload.fps,
        reference_hr_bpm=payload.reference_hr_bpm,
    )

    # 2. Run PhysNet inference
    n_frames = len(rgb_arr)
    dl_status = "PENDING_CHECKPOINT"
    dl_hr = None
    dl_confidence = 0.0
    dl_error = None
    dl_waveform: List[float] = []

    # Check if a trained checkpoint exists
    experiments = tracker.list_experiments()
    latest_checkpoint = None
    for exp in reversed(experiments):
        ckpt = exp.get("artifacts", {}).get("checkpoint_path")
        if ckpt and os.path.exists(ckpt):
            latest_checkpoint = ckpt
            break

    t_dl0 = time.perf_counter()
    dl_elapsed_ms = 0.0
    try:
        model = PhysNet(in_channels=3, base_channels=8)
        if latest_checkpoint:
            checkpoint = torch.load(latest_checkpoint, map_location="cpu")
            model.load_state_dict(checkpoint["model_state_dict"])
            dl_status = "TRAINED_INFERENCE"
        else:
            dl_status = "INITIALIZED_UNWEIGHTED"

        model.eval()

        # Construct spatio-temporal video volume from spatial RGB traces: (1, 3, T, 32, 32)
        spatial_patch = np.tile(rgb_arr.T[:, :, np.newaxis, np.newaxis], (1, 1, 32, 32))
        patch_tensor = torch.tensor(spatial_patch, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            dl_waveform_tensor = model(patch_tensor).squeeze(0)
            dl_waveform_np = dl_waveform_tensor.cpu().numpy()

        dl_elapsed_ms = (time.perf_counter() - t_dl0) * 1000.0
        hr_res = estimate_heart_rate(dl_waveform_np, fps=payload.fps)
        dl_hr = hr_res.get("heart_rate_bpm")
        dl_confidence = hr_res.get("confidence", 0.0)
        if payload.reference_hr_bpm is not None and dl_hr is not None:
            dl_error = round(abs(dl_hr - payload.reference_hr_bpm), 2)

        dl_waveform = [round(float(v), 4) for v in dl_waveform_np.tolist()]
    except Exception as e:
        dl_elapsed_ms = (time.perf_counter() - t_dl0) * 1000.0
        dl_status = f"FAILED: {str(e)}"

    traditional_results["algorithms"]["PhysNet (Deep Learning)"] = {
        "algorithm": "PhysNet (3D-CNN)",
        "status": dl_status,
        "execution_time_ms": round(dl_elapsed_ms, 2),
        "latency_ms": round(dl_elapsed_ms, 2),
        "heart_rate_bpm": dl_hr,
        "confidence": dl_confidence,
        "snr_db": hr_res.get("snr_db", -99.0) if 'hr_res' in locals() else -99.0,
        "error_against_reference_bpm": dl_error,
        "error_bpm": dl_error,
        "waveform_filtered": dl_waveform,
        "checkpoint_used": latest_checkpoint,
    }

    return traditional_results

