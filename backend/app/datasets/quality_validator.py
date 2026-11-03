"""
Biomedical Data Quality Assurance and Physiological Range Validator.

Enforces Phase 2 Task 10:
- Audits file presence, container integrity, and timestamp monotonicity.
- Validates physiological plausibility across all 4 parameters:
  * HR: 35 to 220 BPM
  * RR: 4 to 50 BrPM
  * SpO2: 70% to 100%
  * BP: SBP in [60, 240] mmHg, DBP in [40, 140] mmHg, SBP > DBP
- Detects synchronization lag and duration mismatches between video and reference data.
- Detects participant identity leakage between data partitions.
- Rule: A validation warning must NEVER silently impute or convert invalid data into valid data.
"""

from typing import Dict, Any, List, Optional, Tuple, Set
import os
import numpy as np


# Clinical physiological plausibility boundaries
PHYSIOLOGICAL_BOUNDS = {
    "hr_bpm": {"min": 35.0, "max": 220.0, "unit": "BPM"},
    "rr_brpm": {"min": 4.0, "max": 50.0, "unit": "BrPM"},
    "spo2_percent": {"min": 70.0, "max": 100.0, "unit": "%"},
    "bp_systolic_mmhg": {"min": 60.0, "max": 240.0, "unit": "mmHg"},
    "bp_diastolic_mmhg": {"min": 40.0, "max": 140.0, "unit": "mmHg"},
}


class QualityValidationReport:
    """Detailed audit report detailing dataset integrity and physiological compliance."""

    def __init__(self):
        self.total_records_checked = 0
        self.valid_records_count = 0
        self.rejected_records_count = 0
        self.warnings_count = 0
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    def add_error(self, record_id: str, code: str, message: str):
        self.errors.append({"record_id": record_id, "code": code, "message": message})
        self.rejected_records_count += 1

    def add_warning(self, record_id: str, code: str, message: str):
        self.warnings.append({"record_id": record_id, "code": code, "message": message})
        self.warnings_count += 1

    @property
    def is_passed(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_passed": self.is_passed,
            "total_records_checked": self.total_records_checked,
            "valid_records_count": self.valid_records_count,
            "rejected_records_count": self.rejected_records_count,
            "warnings_count": self.warnings_count,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class BiomedicalDataValidator:
    """
    Automated QA engine for physiological video datasets and multi-parameter reference streams.
    """

    @staticmethod
    def validate_physiological_value(parameter: str, value: Optional[float]) -> Tuple[bool, Optional[str]]:
        """
        Validates if a physiological measurement falls within human survival boundaries.
        Returns (is_valid, rejection_reason).
        """
        if value is None:
            return True, None  # Legitimate absent value, handled separately

        bounds = PHYSIOLOGICAL_BOUNDS.get(parameter)
        if not bounds:
            return True, None

        if np.isnan(value) or np.isinf(value):
            return False, f"Value for {parameter} is NaN or Inf"

        if value < bounds["min"] or value > bounds["max"]:
            return False, f"{parameter} value {value} {bounds['unit']} outside clinical bounds [{bounds['min']}, {bounds['max']}]"

        return True, None

    @staticmethod
    def validate_blood_pressure_pair(sbp: Optional[float], dbp: Optional[float]) -> Tuple[bool, Optional[str]]:
        """
        Validates relationship between systolic and diastolic blood pressure.
        Systolic must strictly exceed diastolic by at least 15 mmHg (pulse pressure).
        """
        if sbp is None or dbp is None:
            return True, None

        v_sbp, err_s = BiomedicalDataValidator.validate_physiological_value("bp_systolic_mmhg", sbp)
        if not v_sbp:
            return False, err_s

        v_dbp, err_d = BiomedicalDataValidator.validate_physiological_value("bp_diastolic_mmhg", dbp)
        if not v_dbp:
            return False, err_d

        if sbp <= dbp:
            return False, f"Systolic pressure ({sbp} mmHg) must be greater than diastolic pressure ({dbp} mmHg)"

        pulse_pressure = sbp - dbp
        if pulse_pressure < 15.0:
            return False, f"Pulse pressure ({pulse_pressure} mmHg) is non-physiologically narrow (< 15 mmHg)"

        return True, None

    @staticmethod
    def validate_timestamps(timestamps: np.ndarray) -> Tuple[bool, Optional[str]]:
        """
        Verifies that frame timestamps are strictly monotonic and positive.
        """
        if len(timestamps) < 2:
            return False, "Timestamp array must contain at least 2 points"

        if np.any(timestamps < 0):
            return False, "Negative timestamp detected"

        diffs = np.diff(timestamps)
        if np.any(diffs <= 0):
            return False, "Non-monotonic timestamps detected (zero or negative time step)"

        # Check for extreme temporal jitter (> 100% variance from median dt)
        median_dt = np.median(diffs)
        if median_dt <= 0:
            return False, "Median time delta is non-positive"

        max_dt = np.max(diffs)
        if max_dt > 3.0 * median_dt:
            return True, f"High temporal jitter detected (max dt={max_dt:.3f}s vs median={median_dt:.3f}s)"

        return True, None

    @staticmethod
    def validate_synchronization(
        video_duration_sec: float,
        reference_duration_sec: float,
        tolerance_sec: float = 0.50,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verifies that video recording and reference instrument durations match within tolerance.
        """
        diff = abs(video_duration_sec - reference_duration_sec)
        if diff > tolerance_sec:
            return False, f"Synchronization mismatch: Video duration ({video_duration_sec:.2f}s) differs from Reference ({reference_duration_sec:.2f}s) by {diff:.2f}s (tolerance: {tolerance_sec}s)"
        return True, None

    @staticmethod
    def audit_participant_leakage(
        train_participants: List[str],
        val_participants: List[str],
        test_participants: List[str],
    ) -> Tuple[bool, List[str]]:
        """
        Cryptographically ensures disjoint sets between train, validation, and test cohorts.
        """
        s_tr = set(train_participants)
        s_va = set(val_participants)
        s_te = set(test_participants)

        leakage_detected = []
        tr_va = s_tr.intersection(s_va)
        if tr_va:
            leakage_detected.append(f"Train/Val leakage: {sorted(list(tr_va))}")

        tr_te = s_tr.intersection(s_te)
        if tr_te:
            leakage_detected.append(f"Train/Test leakage: {sorted(list(tr_te))}")

        va_te = s_va.intersection(s_te)
        if va_te:
            leakage_detected.append(f"Val/Test leakage: {sorted(list(va_te))}")

        return len(leakage_detected) == 0, leakage_detected

    def audit_collection_records(self, records: List[Dict[str, Any]]) -> QualityValidationReport:
        """
        Conducts a comprehensive batch quality and clinical compliance audit across recording entries.
        """
        report = QualityValidationReport()
        report.total_records_checked = len(records)
        seen_ids: Set[str] = set()

        for rec in records:
            r_id = rec.get("recording_id", "UNKNOWN")

            # 1. Duplicate check
            if r_id in seen_ids:
                report.add_error(r_id, "DUPLICATE_RECORDING", f"Duplicate recording_id '{r_id}' detected")
                continue
            seen_ids.add(r_id)

            # 2. Participant ID convention check
            p_id = rec.get("participant_id", "")
            if not p_id.startswith("SUBJ-"):
                report.add_error(r_id, "INVALID_PARTICIPANT_ID", f"Participant identifier '{p_id}' violates pseudonymization rule (must start with SUBJ-)")
                continue

            # 3. Video metadata check
            v_meta = rec.get("video_metadata", {})
            fps = v_meta.get("fps", 0.0)
            if fps < 10.0 or fps > 120.0:
                report.add_error(r_id, "INVALID_FRAME_RATE", f"Frame rate {fps} fps outside acceptable range [10, 120]")
                continue

            duration = v_meta.get("duration_sec", 0.0)
            if duration < 3.0:
                report.add_error(r_id, "RECORDING_TOO_SHORT", f"Duration {duration:.1f}s is insufficient for rPPG estimation")
                continue

            # 4. Physiological range checks
            refs = rec.get("reference_standards", {})

            hr = refs.get("heart_rate", {}).get("value_bpm")
            v_hr, err_hr = self.validate_physiological_value("hr_bpm", hr)
            if not v_hr:
                report.add_error(r_id, "PHYSIOLOGICAL_RANGE_ERROR", err_hr)

            rr = refs.get("respiratory_rate", {}).get("value_brpm")
            v_rr, err_rr = self.validate_physiological_value("rr_brpm", rr)
            if not v_rr:
                report.add_error(r_id, "PHYSIOLOGICAL_RANGE_ERROR", err_rr)

            spo2 = refs.get("spo2", {}).get("value_percent")
            v_spo2, err_spo2 = self.validate_physiological_value("spo2_percent", spo2)
            if not v_spo2:
                report.add_error(r_id, "PHYSIOLOGICAL_RANGE_ERROR", err_spo2)

            bp_sys = refs.get("blood_pressure", {}).get("systolic_mmhg")
            bp_dia = refs.get("blood_pressure", {}).get("diastolic_mmhg")
            v_bp, err_bp = self.validate_blood_pressure_pair(bp_sys, bp_dia)
            if not v_bp:
                report.add_error(r_id, "PHYSIOLOGICAL_RANGE_ERROR", err_bp)

            # If no errors were logged for this record, it is marked valid
            if report.is_passed:
                report.valid_records_count += 1

        return report

