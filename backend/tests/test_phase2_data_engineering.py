"""
Unit and Integration Tests for Phase 2: Dataset Research, Cloud Infrastructure & Data Engineering.
Tests:
1. Dataset Acquisition & Manifest Lifecycle
2. Video Preprocessor & Cubic Spline Reference Synchronization
3. Participant-Level Zero-Leakage Data Splitting
4. Group Data Collection Protocol Schema
5. Automated Data Quality & Physiological Range Validator
"""

import os
import tempfile
import json
import pytest
import numpy as np

from app.datasets.acquisition import DatasetAcquisitionManager, DatasetStatus, OFFICIAL_DATASET_REGISTRY
from app.datasets.preprocessor import VideoDatasetPreprocessor, VideoPreprocessingResult
from app.datasets.splitting import ZeroLeakageDataSplitter
from app.datasets.group_collection import GroupDataCollectionManager, CLINICAL_PROTOCOL_SPECIFICATION
from app.datasets.quality_validator import BiomedicalDataValidator, PHYSIOLOGICAL_BOUNDS
from app.datasets.cloud_acquisition_pipeline import CloudDatasetAcquisitionEngine


def test_dataset_registry_and_acquisition_manager():
    """Verify registry metadata and manifest generation for all benchmark datasets."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = DatasetAcquisitionManager(data_root=tmp_dir)
        summary = manager.get_summary_report()

        assert summary["registered_datasets_count"] >= 5
        datasets = summary["datasets"]
        assert "UBFC-rPPG" in datasets
        assert "PURE" in datasets
        assert "COHFACE" in datasets
        assert "VIPL-HR" in datasets
        assert "MMPD" in datasets

        # Check UBFC labels (HR=True, RR=False, SpO2=True, BP=False)
        ubfc = datasets["UBFC-rPPG"]
        assert ubfc["labels_available"]["hr"] is True
        assert ubfc["labels_available"]["rr"] is False
        assert ubfc["labels_available"]["bp"] is False
        assert ubfc["status"] == DatasetStatus.RESEARCHED

        # Test inspection of empty/missing directory
        res = manager.inspect_dataset_directory("UBFC-rPPG")
        assert res["status"] == DatasetStatus.RESEARCHED


def test_sha256_integrity_calculation():
    """Verify cryptographic SHA-256 computation on test files."""
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        f.write("rPPG_biomedical_test_data_integrity")
        tmp_name = f.name

    try:
        chk = DatasetAcquisitionManager.compute_sha256(tmp_name)
        assert isinstance(chk, str)
        assert len(chk) == 64  # SHA-256 outputs 64 hex characters
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def test_video_preprocessor_reference_synchronization():
    """Verify cubic spline synchronization of reference signals to video frame timestamps."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        preprocessor = VideoDatasetPreprocessor(output_dir=tmp_dir)

        # 10 video frame timestamps at 30 fps
        target_timestamps = np.arange(10) / 30.0

        # Reference signal sampled at different frequency (e.g., 60 Hz ECG)
        ref_time = np.linspace(0.0, target_timestamps[-1], 20)
        ref_bvp = np.sin(2.0 * np.pi * 1.2 * ref_time)

        ref_data = {
            "time_s": ref_time,
            "bvp": ref_bvp,
            "rr": np.ones_like(ref_time) * 16.0,
        }

        synced = preprocessor._synchronize_reference_signals(ref_data, target_timestamps)
        assert "bvp" in synced
        assert "rr" in synced
        assert len(synced["bvp"]) == 10
        assert len(synced["rr"]) == 10


def test_preprocessor_result_export():
    """Verify preprocessed result export does not corrupt or mutate source data."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        preprocessor = VideoDatasetPreprocessor(output_dir=tmp_dir)
        mock_rgb = np.zeros((150, 3))

        res = VideoPreprocessingResult(
            video_id="TEST_VID_001",
            total_frames=150,
            fps=30.0,
            resolution=(640, 480),
            duration_sec=5.0,
            spatially_averaged_rgb=mock_rgb,
            illumination_stability=0.95,
            motion_displacement_mean=1.2,
            blur_score_laplacian=120.0,
            frame_drops_detected=0,
            quality_status="VALID",
        )

        out_path = preprocessor.export_processed_archive(res, subfolder="test_cohort")
        assert os.path.exists(out_path)

        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["metadata"]["video_id"] == "TEST_VID_001"
        assert data["metadata"]["fps"] == 30.0
        assert len(data["rgb_traces"]) == 150


def test_zero_leakage_participant_splitting():
    """Verify zero participant leakage across Train, Val, and Test partitions."""
    splitter = ZeroLeakageDataSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, random_seed=42)
    subjects = [f"SUBJ-{i:03d}" for i in range(1, 41)]  # 40 subjects

    splits = splitter.split_participants(subjects)

    s_train = set(splits["train"])
    s_val = set(splits["val"])
    s_test = set(splits["test"])

    # Strict disjointness
    assert len(s_train.intersection(s_val)) == 0
    assert len(s_train.intersection(s_test)) == 0
    assert len(s_val.intersection(s_test)) == 0

    # Total coverage
    assert len(s_train) + len(s_val) + len(s_test) == 40
    assert len(s_train) >= 25
    assert len(s_val) >= 5
    assert len(s_test) >= 5

    # Split hash repeatability
    hash1 = splitter.compute_split_hash(splits, seed=42)
    hash2 = splitter.compute_split_hash(splits, seed=42)
    assert hash1 == hash2


def test_group_data_collection_template_generation():
    """Verify clinical data collection template metadata schema and blank CSV export."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = GroupDataCollectionManager(template_dir=tmp_dir)

        # Create valid entry
        entry = manager.create_recording_entry(
            participant_id="SUBJ-001",
            video_filename="trial_01.mp4",
            fps=30.0,
            duration_sec=15.0,
            ref_hr_bpm=74.5,
            ref_rr_brpm=15.0,
            ref_spo2_percent=98.0,
            ref_bp_systolic_mmhg=120.0,
            ref_bp_diastolic_mmhg=78.0,
            consent_verified=True,
        )

        assert entry["participant_id"] == "SUBJ-001"
        assert entry["recording_id"].startswith("REC-")
        assert entry["reference_standards"]["heart_rate"]["value_bpm"] == 74.5

        # Check unconsented rejection
        with pytest.raises(PermissionError):
            manager.create_recording_entry(
                participant_id="SUBJ-002",
                video_filename="trial_02.mp4",
                consent_verified=False,
            )

        # Check invalid format rejection
        with pytest.raises(ValueError):
            manager.create_recording_entry(
                participant_id="John_Doe",
                video_filename="trial_03.mp4",
                consent_verified=True,
            )

        csv_path = manager.generate_blank_csv_template()
        assert os.path.exists(csv_path)


def test_biomedical_data_quality_validator():
    """Verify physiological range bounds, blood pressure pairing, and leakage auditing."""
    validator = BiomedicalDataValidator()

    # HR Checks
    v_hr, err = validator.validate_physiological_value("hr_bpm", 72.0)
    assert v_hr is True
    v_hr_bad, err = validator.validate_physiological_value("hr_bpm", 280.0)
    assert v_hr_bad is False

    # SpO2 Checks
    v_spo2, err = validator.validate_physiological_value("spo2_percent", 98.0)
    assert v_spo2 is True
    v_spo2_bad, err = validator.validate_physiological_value("spo2_percent", 65.0)
    assert v_spo2_bad is False

    # Blood Pressure checks
    v_bp, err = validator.validate_blood_pressure_pair(120.0, 80.0)
    assert v_bp is True

    # SBP <= DBP error
    v_bp_inverted, err = validator.validate_blood_pressure_pair(80.0, 120.0)
    assert v_bp_inverted is False

    # Narrow pulse pressure (< 15 mmHg)
    v_bp_narrow, err = validator.validate_blood_pressure_pair(110.0, 105.0)
    assert v_bp_narrow is False

    # Participant leakage audit
    tr = ["SUBJ-001", "SUBJ-002", "SUBJ-003"]
    va = ["SUBJ-004", "SUBJ-005"]
    te = ["SUBJ-006", "SUBJ-007"]
    no_leak, logs = validator.audit_participant_leakage(tr, va, te)
    assert no_leak is True

    # Artificially introduce leakage
    tr_leaky = ["SUBJ-001", "SUBJ-002", "SUBJ-004"]
    leak, logs = validator.audit_participant_leakage(tr_leaky, va, te)
    assert leak is False
    assert len(logs) == 1


def test_cloud_dataset_acquisition_engine():
    """Verify Google Drive directory structure setup and storage quota auditing."""
    with tempfile.TemporaryDirectory() as tmp_drive:
        engine = CloudDatasetAcquisitionEngine(drive_root=tmp_drive)
        paths = engine.setup_google_drive_structure()

        assert "01_RAW_DATASETS" in paths
        assert "02_DATASET_METADATA" in paths
        assert "RAW_UBFC-rPPG" in paths
        assert "RAW_MMPD" in paths

        # Check all 8 folders exist
        for f in ["01_RAW_DATASETS", "02_DATASET_METADATA", "03_PROCESSED_DATASETS",
                  "04_TRAINING_DATA", "05_MODELS", "06_EXPERIMENTS",
                  "07_VALIDATION_RESULTS", "08_DOCUMENTATION"]:
            assert os.path.exists(os.path.join(tmp_drive, f))

        # Check drive storage checker
        storage = engine.check_drive_storage(tmp_drive)
        assert storage["mounted"] is True
        assert storage["total_gb"] > 0
        assert "free_gb" in storage

        # Check dataset folder audit
        audit = engine.audit_downloaded_dataset(paths["RAW_UBFC-rPPG"])
        assert audit["exists"] is True
        assert audit["video_count"] == 0
        assert audit["integrity_status"] == "EMPTY_OR_NO_VIDEOS"


