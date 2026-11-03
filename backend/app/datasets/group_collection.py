"""
Group Data Collection Framework & Clinical Protocol Template.

Enforces Phase 2 Task 9:
- Protocol framework for >= 50 participant paired research cohort.
- Institutional Review Board (IRB) / Ethics Committee compliance guidelines.
- Standardized recording metadata schema.
- Explicit support for missing modalities without artificial label imputation.
- Strict pseudonymization (never stores participant names or personal identifiers).
"""

from typing import Dict, Any, List, Optional
import os
import json
import uuid
from datetime import datetime, timezone


CLINICAL_PROTOCOL_SPECIFICATION: Dict[str, Any] = {
    "protocol_id": "rPPG-CLIN-2026-V1",
    "study_title": "Validation of Remote Photoplethysmography Against Synchronized Clinical Reference Standards",
    "ethical_framework": "Declaration of Helsinki & ISO 14155 Clinical Investigation Guidelines",
    "target_cohort_size": 50,
    "target_demographics": {
        "age_range": "18 - 75 years",
        "gender_ratio": "Approximately 50% Female / 50% Male",
        "skin_type_representation": "Fitzpatrick Phototypes I through VI represented evenly",
    },
    "reference_instrument_standards": {
        "heart_rate": {
            "device_class": "12-Lead Diagnostic ECG / 3-Lead Continuous Monitor",
            "required_accuracy": "+/- 1 BPM or +/- 1% whichever is greater",
            "sampling_frequency_hz": 250.0,
        },
        "respiratory_rate": {
            "device_class": "Piezoelectric Thoracic Strain Gauge Effort Belt",
            "required_accuracy": "+/- 1 Breath/min",
            "sampling_frequency_hz": 100.0,
        },
        "oxygen_saturation": {
            "device_class": "Multi-Wavelength Clinical Pulse CO-Oximeter (e.g. Masimo Radical-7)",
            "required_accuracy": "+/- 2% across 70-100% range",
            "sampling_frequency_hz": 1.0,
        },
        "blood_pressure": {
            "device_class": "ISO 81060-2 Validated Automated Oscillometric Arm Sphygmomanometer",
            "required_accuracy": "Mean error <= +/- 5 mmHg, SD <= 8 mmHg",
            "measurement_cadence": "Triplicate resting baseline prior to video acquisition",
        },
    },
    "privacy_and_data_protection": {
        "anonymization_standard": "HIPAA Safe Harbor / GDPR Pseudonymization",
        "identifier_format": "SUBJ-XXX (Never uses participant names, national IDs, or hospital numbers)",
        "video_retention": "Configurable secure encrypted storage; automatic deletion option after signal extraction",
    },
}


class GroupDataCollectionManager:
    """
    Manages clinical trial participant intake, informed consent status,
    and paired multimodal recording metadata.
    """

    def __init__(self, template_dir: str = "./storage/cohort_templates"):
        self.template_dir = template_dir
        os.makedirs(self.template_dir, exist_ok=True)
        self.collection_file = os.path.join(self.template_dir, "cohort_collection_metadata.json")
        self.records: List[Dict[str, Any]] = self._load_records()

    def _load_records(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.collection_file):
            try:
                with open(self.collection_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_records(self):
        with open(self.collection_file, "w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2)

    def create_recording_entry(
        self,
        participant_id: str,
        video_filename: str,
        fps: float = 30.0,
        resolution: str = "1920x1080",
        duration_sec: float = 15.0,
        camera_hardware: str = "Front Camera (1080p)",
        lighting_condition: str = "Ambient Laboratory (350 lux)",
        motion_condition: str = "Resting Stationary",
        ref_hr_bpm: Optional[float] = None,
        ref_hr_device: str = "12-Lead Diagnostic ECG",
        ref_rr_brpm: Optional[float] = None,
        ref_rr_device: str = "Piezoelectric Effort Belt",
        ref_spo2_percent: Optional[float] = None,
        ref_spo2_device: str = "Masimo Radical-7 CO-Oximeter",
        ref_bp_systolic_mmhg: Optional[float] = None,
        ref_bp_diastolic_mmhg: Optional[float] = None,
        ref_bp_device: str = "Digital Sphygmomanometer (ISO 81060-2)",
        missing_labels_reason: Optional[str] = None,
        consent_verified: bool = True,
    ) -> Dict[str, Any]:
        """
        Creates a verified recording metadata record.
        Strict rule: Missing ground-truth references are recorded as None with an explicit reason,
        never fabricated or defaulted.
        """
        if not participant_id.startswith("SUBJ-"):
            raise ValueError(f"Invalid participant identifier format '{participant_id}'. Must follow 'SUBJ-XXX' convention.")

        if not consent_verified:
            raise PermissionError(f"Informed consent must be confirmed for participant '{participant_id}'.")

        recording_id = f"REC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        entry = {
            "recording_id": recording_id,
            "participant_id": participant_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "video_metadata": {
                "filename": video_filename,
                "fps": float(fps),
                "resolution": resolution,
                "duration_sec": float(duration_sec),
                "camera_hardware": camera_hardware,
            },
            "environmental_conditions": {
                "lighting": lighting_condition,
                "motion": motion_condition,
            },
            "reference_standards": {
                "heart_rate": {
                    "value_bpm": ref_hr_bpm,
                    "instrument": ref_hr_device if ref_hr_bpm is not None else None,
                    "status": "RECORDED" if ref_hr_bpm is not None else "MISSING",
                },
                "respiratory_rate": {
                    "value_brpm": ref_rr_brpm,
                    "instrument": ref_rr_device if ref_rr_brpm is not None else None,
                    "status": "RECORDED" if ref_rr_brpm is not None else "MISSING",
                },
                "spo2": {
                    "value_percent": ref_spo2_percent,
                    "instrument": ref_spo2_device if ref_spo2_percent is not None else None,
                    "status": "RECORDED" if ref_spo2_percent is not None else "MISSING",
                },
                "blood_pressure": {
                    "systolic_mmhg": ref_bp_systolic_mmhg,
                    "diastolic_mmhg": ref_bp_diastolic_mmhg,
                    "instrument": ref_bp_device if ref_bp_systolic_mmhg is not None else None,
                    "status": "RECORDED" if ref_bp_systolic_mmhg is not None else "MISSING",
                },
            },
            "missing_labels_reason": missing_labels_reason,
            "data_quality_status": "PENDING_VALIDATION",
            "consent_verified": consent_verified,
        }

        self.records.append(entry)
        self._save_records()
        return entry

    def generate_blank_csv_template(self) -> str:
        """Exports a standardized clinical data collection CSV template for field researchers."""
        csv_path = os.path.join(self.template_dir, "clinical_collection_template.csv")
        headers = [
            "participant_id",
            "consent_signed",
            "fitzpatrick_skin_type",
            "age",
            "gender",
            "video_filename",
            "camera_hardware",
            "lighting_condition",
            "motion_condition",
            "ref_hr_bpm",
            "ref_hr_device",
            "ref_rr_brpm",
            "ref_rr_device",
            "ref_spo2_percent",
            "ref_spo2_device",
            "ref_bp_systolic_mmhg",
            "ref_bp_diastolic_mmhg",
            "ref_bp_device",
            "missing_labels_reason",
            "notes",
        ]
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(",".join(headers) + "\n")
            f.write("SUBJ-001,TRUE,3,28,Female,SUBJ001_trial1.mp4,Front Phone 1080p,Ambient Office (350 lux),Resting,72.4,12-Lead ECG,16.0,Chest Belt,98.5,Masimo Radical-7,118.0,76.0,Digital Cuff,,Baseline trial\n")
        return csv_path

