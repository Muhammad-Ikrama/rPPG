"""
Measurement Sessions, Dual-Channel Data Collection, Video Processing, and Vital Signs API Routes.
"""

from typing import List, Optional, Dict, Any
import json
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
import numpy as np

from app.db.session import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.subject import Subject
from app.models.session import MeasurementSession
from app.models.vital_sign import VitalSignEstimate
from app.schemas.session import SessionCreate, SessionResponse, ManualReferenceReadingRequest
from app.schemas.vital_sign import (
    DashboardVitalSigns,
    VitalSignMetric,
    SessionListItem,
    MeasurementHistoryResponse,
    ManualReferenceSummary,
    SessionSummaryResponse,
)
from app.api.auth import get_current_user
from app.services.video_storage import VideoStorageService
from app.services.monitor_storage import MonitorImageStorageService
from app.rppg.face_roi import FaceROIExtractor
from app.rppg.pos_algorithm import compute_pos_rppg
from app.rppg.hr_estimation import estimate_heart_rate
from app.rppg.rr_estimation import estimate_respiratory_rate
from app.rppg.spo2_estimation import estimate_spo2_research
from app.rppg.bp_estimation import estimate_blood_pressure_experimental
from app.rppg.quality_assessment import evaluate_signal_quality
from app.datasets.loader import generate_synthetic_rppg_stream

router = APIRouter(prefix="/measurements", tags=["Measurements"])


async def _allocate_next_session_code(db: AsyncSession, subject_id: Optional[str]) -> str:
    """Computes sequential SESSION_001, SESSION_002... per subject (or global fallback)."""
    stmt = select(MeasurementSession.session_code)
    if subject_id:
        stmt = stmt.where(MeasurementSession.subject_id == subject_id)
    res = await db.execute(stmt)
    codes = res.scalars().all()
    max_num = 0
    for code in codes:
        m = re.match(r"^SESSION_(\d+)$", code or "")
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
    return f"SESSION_{max_num + 1:03d}"


def _build_dashboard_payload(
    session_obj: MeasurementSession,
    vital: VitalSignEstimate,
    waveform: List[float],
    freqs: List[float],
    psd: List[float],
) -> DashboardVitalSigns:
    manual_ref = None
    if (
        vital.is_manual_reference_verified
        or vital.reference_hr is not None
        or vital.reference_rr is not None
        or vital.reference_spo2 is not None
        or vital.reference_sbp is not None
        or vital.reference_dbp is not None
    ):
        manual_ref = ManualReferenceSummary(
            hr_bpm=vital.reference_hr,
            rr_brpm=vital.reference_rr,
            spo2_percent=vital.reference_spo2,
            sbp_mmhg=vital.reference_sbp,
            dbp_mmhg=vital.reference_dbp,
            measured_at=vital.reference_measured_at,
            monitor_device_name=session_obj.monitor_device_name,
            operator_notes=vital.reference_operator_notes,
            is_verified=bool(vital.is_manual_reference_verified),
        )

    return DashboardVitalSigns(
        session_id=session_obj.id,
        timestamp=session_obj.created_at,
        camera_type=session_obj.camera_type,
        status=session_obj.status,
        subject_id=session_obj.subject_id,
        subject_code=session_obj.subject_code,
        session_code=session_obj.session_code,
        experimental_condition=session_obj.experimental_condition,
        drive_sync_status=session_obj.drive_sync_status,
        monitor_image_uploaded=bool(session_obj.monitor_image_path),
        manual_reference=manual_ref,
        roi_diagnostics={
            "valid_face_ratio": vital.valid_face_ratio,
            "mean_motion_px": vital.mean_motion_px,
            "actual_fps": vital.actual_fps,
        },
        heart_rate=VitalSignMetric(
            value=vital.hr_bpm,
            unit="BPM",
            confidence=vital.hr_confidence,
            status=vital.hr_status,
            uncertainty_range="+/- 2.0 BPM",
        ),
        respiratory_rate=VitalSignMetric(
            value=vital.rr_brpm,
            unit="BrPM",
            confidence=vital.rr_confidence,
            status=vital.rr_status,
            uncertainty_range="+/- 2.5 BrPM",
        ),
        oxygen_saturation=VitalSignMetric(
            value=vital.spo2_percent,
            unit="%",
            confidence=vital.spo2_confidence,
            status=vital.spo2_status,
            is_experimental=True,
            is_calibrated=bool(vital.spo2_is_calibrated),
            disclaimer="Conventional RGB camera - uncalibrated experimental optical proxy.",
        ),
        blood_pressure_sbp=VitalSignMetric(
            value=vital.sbp_mmhg,
            unit="mmHg",
            confidence=vital.bp_confidence,
            status=vital.bp_status,
            is_experimental=True,
            is_calibrated=bool(vital.bp_is_calibrated),
            disclaimer="ISO 81060-2 experimental research objective — not clinically validated.",
        ),
        blood_pressure_dbp=VitalSignMetric(
            value=vital.dbp_mmhg,
            unit="mmHg",
            confidence=vital.bp_confidence,
            status=vital.bp_status,
            is_experimental=True,
            is_calibrated=bool(vital.bp_is_calibrated),
            disclaimer="ISO 81060-2 experimental research objective — not clinically validated.",
        ),
        signal_quality_score=vital.sqi_score,
        signal_quality_status=vital.sqi_status,
        motion_stability=vital.motion_stability,
        illumination_stability=vital.illumination_stability,
        quality_guidance=vital.quality_guidance or "Evaluation complete.",
        rppg_waveform=waveform,
        frequencies_hz=freqs,
        psd_power=psd,
    )


async def execute_rppg_pipeline_async(session_id: str, video_path: str):
    """
    Background worker executing the complete biomedical rPPG pipeline:
    1. Video frame decoding and frame-drop / effective FPS analysis.
    2. Computer vision face detection & anatomical ROI extraction (Forehead + Cheeks).
    3. Face presence & ROI quality gating (never fabricates readings without face signal).
    4. Mathematical Plane-Orthogonal-to-Skin (POS) rPPG extraction.
    5. Independent HR, RR, SpO2 (experimental), and BP (experimental) pathways.
    6. Composite Signal Quality Index (SQI) evaluation.
    7. Atomic database upsert (preserving any pre-entered Channel B manual references).
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(MeasurementSession).where(MeasurementSession.id == session_id))
        session_obj = result.scalars().first()
        if not session_obj:
            return

        session_obj.status = "PROCESSING"
        await db.commit()

        try:
            # Step 1: Decode video
            frames, meta = VideoStorageService.decode_video_frames(video_path)
            if not frames or len(frames) < 15:
                session_obj.status = "FAILED"
                session_obj.error_message = f"Insufficient frames decoded ({len(frames)}) for rPPG analysis"
                await db.commit()
                return

            fps = meta.get("effective_fps") or meta["fps"]
            session_obj.fps = fps
            session_obj.resolution = meta["resolution"]
            session_obj.duration_sec = meta["duration_sec"]
            session_obj.total_frames = meta["frames_count"]
            session_obj.dropped_frames = meta["dropped_frames"]

            # Step 2: Facial ROI extraction
            roi_extractor = FaceROIExtractor()
            rgb_signals, diagnostics = roi_extractor.process_video_frames(frames)

            detected_frames = sum(1 for d in diagnostics if d.get("face_detected") and d.get("skin_pixels", 0) > 20)
            valid_face_ratio = detected_frames / max(1, len(diagnostics))
            motions = [float(d.get("motion_magnitude", 0.0)) for d in diagnostics if d.get("face_detected")]
            mean_motion_px = float(np.mean(motions)) if motions else 0.0

            if valid_face_ratio < 0.35:
                session_obj.status = "FAILED"
                session_obj.error_message = (
                    f"No sustained face detected across video ({valid_face_ratio * 100:.1f}% valid frames). "
                    "Please re-record in good lighting with face centered."
                )
                await db.commit()
                return

            # Step 3: POS algorithm
            filtered_rppg, raw_rppg, pos_meta = compute_pos_rppg(rgb_signals, fps=fps)

            # Step 4: HR estimation
            hr_res = estimate_heart_rate(filtered_rppg, fps=fps)

            # Step 5: RR estimation
            rr_res = estimate_respiratory_rate(raw_rppg, filtered_rppg, fps=fps)

            # Step 6: SpO2 research module
            spo2_res = estimate_spo2_research(
                rgb_signals,
                fps=fps,
                signal_snr=hr_res.get("snr_db", 0.0),
                is_calibrated=False,
            )

            # Step 7: Experimental Blood Pressure
            bp_res = estimate_blood_pressure_experimental(
                filtered_rppg,
                fps=fps,
                hr_bpm=hr_res.get("heart_rate_bpm"),
            )

            # Step 8: Signal quality
            sqi_res = evaluate_signal_quality(
                filtered_rppg,
                rgb_signals,
                snr_db=hr_res.get("snr_db", -99.0),
                fps=fps,
            )

            step = max(1, len(filtered_rppg) // 200)
            waveform_downsampled = [round(float(v), 4) for v in filtered_rppg[::step]]

            # Step 9: Upsert VitalSignEstimate (preserve Channel B manual references if already saved)
            existing_res = await db.execute(
                select(VitalSignEstimate).where(VitalSignEstimate.session_id == session_id)
            )
            vital_obj = existing_res.scalars().first()
            if vital_obj is None:
                vital_obj = VitalSignEstimate(session_id=session_id)
                db.add(vital_obj)

            vital_obj.hr_bpm = hr_res.get("heart_rate_bpm")
            vital_obj.hr_confidence = hr_res.get("confidence", 0.0)
            vital_obj.hr_status = hr_res.get("status", "UNRELIABLE")
            vital_obj.snr_db = hr_res.get("snr_db", -99.0)
            vital_obj.time_domain_bpm = hr_res.get("time_domain_bpm")
            vital_obj.rmssd_ms = hr_res.get("rmssd_ms")
            vital_obj.rr_brpm = rr_res.get("respiratory_rate_brpm")
            vital_obj.rr_confidence = rr_res.get("confidence", 0.0)
            vital_obj.rr_status = rr_res.get("status", "UNAVAILABLE")
            vital_obj.spo2_percent = spo2_res.get("spo2_percent")
            vital_obj.spo2_confidence = spo2_res.get("confidence", 0.0)
            vital_obj.spo2_status = spo2_res.get("status", "EXPERIMENTAL_UNCALIBRATED")
            vital_obj.spo2_ratio_of_ratios = spo2_res.get("ratio_of_ratios")
            vital_obj.spo2_is_calibrated = spo2_res.get("is_calibrated", False)
            vital_obj.sbp_mmhg = bp_res.get("sbp_mmhg")
            vital_obj.dbp_mmhg = bp_res.get("dbp_mmhg")
            vital_obj.bp_confidence = bp_res.get("confidence", 0.0)
            vital_obj.bp_status = bp_res.get("status", "EXPERIMENTAL_RESEARCH")
            vital_obj.bp_is_calibrated = bp_res.get("is_calibrated", False)
            vital_obj.sqi_score = sqi_res.get("sqi_score", 0.0)
            vital_obj.sqi_status = sqi_res.get("status", "POOR")
            vital_obj.motion_stability = sqi_res.get("motion_stability", 0.0)
            vital_obj.illumination_stability = sqi_res.get("illumination_stability", 0.0)
            vital_obj.quality_guidance = sqi_res.get("guidance", "")
            vital_obj.valid_face_ratio = round(valid_face_ratio, 4)
            vital_obj.mean_motion_px = round(mean_motion_px, 3)
            vital_obj.actual_fps = round(float(fps), 3)
            vital_obj.rppg_waveform_json = json.dumps(waveform_downsampled)
            vital_obj.psd_frequencies_json = json.dumps(hr_res.get("frequencies_hz", []))
            vital_obj.psd_power_json = json.dumps(hr_res.get("psd", []))
            vital_obj.ibi_series_json = json.dumps(hr_res.get("ibi_ms", []))

            session_obj.status = "COMPLETED"
            session_obj.completed_at = datetime.now(timezone.utc)
            if session_obj.ended_at is None:
                session_obj.ended_at = session_obj.completed_at
            await db.commit()

        except Exception as e:
            session_obj.status = "FAILED"
            session_obj.error_message = f"Pipeline execution error: {str(e)}"
            await db.commit()


@router.post("/session", response_model=SessionResponse)
async def create_measurement_session(
    payload: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initializes a subject-linked rPPG measurement session with experimental conditions.
    Supports client_session_id idempotency to prevent duplicate session creation on retries.
    """
    # Idempotency check
    if payload.client_session_id:
        dup_res = await db.execute(
            select(MeasurementSession).where(MeasurementSession.client_session_id == payload.client_session_id)
        )
        existing = dup_res.scalars().first()
        if existing:
            return SessionResponse(
                session_id=existing.id,
                session_code=existing.session_code,
                subject_id=existing.subject_id,
                subject_code=existing.subject_code,
                experimental_condition=existing.experimental_condition,
                status=existing.status,
                created_at=existing.created_at,
                message="Existing session returned via client_session_id idempotency key.",
                is_duplicate=True,
            )

    subject_obj = None
    if payload.subject_id:
        subj_res = await db.execute(
            select(Subject).where(
                or_(Subject.id == payload.subject_id, Subject.subject_code == payload.subject_id)
            )
        )
        subject_obj = subj_res.scalars().first()
        if not subject_obj:
            raise HTTPException(status_code=404, detail=f"Subject '{payload.subject_id}' not found.")

    session_code = await _allocate_next_session_code(db, subject_obj.id if subject_obj else None)

    session_obj = MeasurementSession(
        user_id=current_user.id,
        subject_id=subject_obj.id if subject_obj else None,
        subject_code=subject_obj.subject_code if subject_obj else None,
        session_code=session_code,
        client_session_id=payload.client_session_id,
        experimental_condition=payload.experimental_condition.value,
        condition_other_detail=payload.condition_other_detail,
        activity_duration_min=payload.activity_duration_min,
        ambient_lighting=payload.ambient_lighting,
        device_model=payload.device_model,
        device_os=payload.device_os,
        consent_verified=payload.consent_verified,
        started_at=payload.started_at or datetime.now(timezone.utc),
        camera_type=payload.camera_type,
        resolution=payload.resolution,
        fps=payload.fps,
        status="CREATED",
    )
    db.add(session_obj)
    await db.flush()

    # Optional legacy inline references (if sent at creation)
    if any(
        v is not None
        for v in (
            payload.reference_hr,
            payload.reference_rr,
            payload.reference_spo2,
            payload.reference_sbp,
            payload.reference_dbp,
        )
    ):
        db.add(
            VitalSignEstimate(
                session_id=session_obj.id,
                reference_hr=payload.reference_hr,
                reference_rr=payload.reference_rr,
                reference_spo2=payload.reference_spo2,
                reference_sbp=payload.reference_sbp,
                reference_dbp=payload.reference_dbp,
                reference_measured_at=datetime.now(timezone.utc),
                is_manual_reference_verified=True,
            )
        )

    await db.commit()
    await db.refresh(session_obj)

    return SessionResponse(
        session_id=session_obj.id,
        session_code=session_obj.session_code,
        subject_id=session_obj.subject_id,
        subject_code=session_obj.subject_code,
        experimental_condition=session_obj.experimental_condition,
        status=session_obj.status,
        created_at=session_obj.created_at,
        message="Measurement session initialized. Ready for Channel A video and Channel B monitor readings.",
        is_duplicate=False,
    )


@router.post("/upload/{session_id}")
async def upload_video(
    session_id: str,
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    ended_at: Optional[datetime] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Channel A: Uploads facial video and dispatches background rPPG execution.
    """
    result = await db.execute(
        select(MeasurementSession).where(
            (MeasurementSession.id == session_id) & (MeasurementSession.user_id == current_user.id)
        )
    )
    session_obj = result.scalars().first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Measurement session not found")

    content = await video.read()
    if len(content) < 1000:
        raise HTTPException(status_code=400, detail="Uploaded video file is too small or empty")

    storage_info = await VideoStorageService.save_upload(session_id, content, video.filename or "facial_video.mp4")

    session_obj.video_filename = storage_info["filename"]
    session_obj.storage_path = storage_info["storage_path"]
    session_obj.video_size_bytes = storage_info["size_bytes"]
    session_obj.video_sha256 = storage_info["sha256"]
    session_obj.retention_expires_at = storage_info["retention_expires_at"]
    session_obj.ended_at = ended_at or datetime.now(timezone.utc)
    session_obj.status = "QUEUED"
    session_obj.error_message = None
    await db.commit()

    background_tasks.add_task(execute_rppg_pipeline_async, session_id, storage_info["storage_path"])

    return {
        "session_id": session_id,
        "session_code": session_obj.session_code,
        "status": "QUEUED",
        "filename": storage_info["filename"],
        "size_bytes": storage_info["size_bytes"],
        "sha256": storage_info["sha256"],
        "message": "Video uploaded successfully. rPPG analysis dispatched.",
    }


@router.post("/{session_id}/monitor-image")
async def upload_monitor_image(
    session_id: str,
    image: UploadFile = File(...),
    captured_at: Optional[datetime] = Form(None),
    monitor_device_name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Channel B: Captures or uploads reference patient monitor photograph for the session.
    """
    result = await db.execute(
        select(MeasurementSession).where(
            (MeasurementSession.id == session_id) & (MeasurementSession.user_id == current_user.id)
        )
    )
    session_obj = result.scalars().first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Measurement session not found")

    raw_bytes = await image.read()
    try:
        info = await MonitorImageStorageService.save_monitor_image(
            session_id, raw_bytes, image.filename or "monitor.jpg"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    session_obj.monitor_image_filename = info["filename"]
    session_obj.monitor_image_path = info["storage_path"]
    session_obj.monitor_image_sha256 = info["sha256"]
    session_obj.monitor_image_size_bytes = info["size_bytes"]
    session_obj.monitor_image_captured_at = captured_at or datetime.now(timezone.utc)
    if monitor_device_name:
        session_obj.monitor_device_name = monitor_device_name.strip()

    await db.commit()
    return {
        "session_id": session_id,
        "filename": info["filename"],
        "size_bytes": info["size_bytes"],
        "sha256": info["sha256"],
        "width": info["width"],
        "height": info["height"],
        "format": info["format"],
        "captured_at": session_obj.monitor_image_captured_at.isoformat(),
        "message": "Patient monitor image saved and linked to session.",
    }


@router.post("/{session_id}/reference-readings")
async def submit_manual_reference_readings(
    session_id: str,
    payload: ManualReferenceReadingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Channel B: Records manually entered and verified patient monitor reference values.
    Values are entered explicitly by the researcher — never invented or auto-extracted without verification.
    """
    result = await db.execute(
        select(MeasurementSession).where(
            (MeasurementSession.id == session_id) & (MeasurementSession.user_id == current_user.id)
        )
    )
    session_obj = result.scalars().first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Measurement session not found")

    if payload.monitor_device_name:
        session_obj.monitor_device_name = payload.monitor_device_name.strip()

    v_res = await db.execute(select(VitalSignEstimate).where(VitalSignEstimate.session_id == session_id))
    vital_obj = v_res.scalars().first()
    if vital_obj is None:
        vital_obj = VitalSignEstimate(session_id=session_id)
        db.add(vital_obj)

    vital_obj.reference_hr = payload.hr_bpm
    vital_obj.reference_rr = payload.rr_brpm
    vital_obj.reference_spo2 = payload.spo2_percent
    vital_obj.reference_sbp = payload.sbp_mmhg
    vital_obj.reference_dbp = payload.dbp_mmhg
    vital_obj.reference_measured_at = payload.measured_at
    vital_obj.reference_operator_notes = payload.operator_notes
    vital_obj.is_manual_reference_verified = True

    await db.commit()
    return {
        "session_id": session_id,
        "is_manual_reference_verified": True,
        "measured_at": payload.measured_at.isoformat(),
        "reference_readings": {
            "hr_bpm": payload.hr_bpm,
            "rr_brpm": payload.rr_brpm,
            "spo2_percent": payload.spo2_percent,
            "sbp_mmhg": payload.sbp_mmhg,
            "dbp_mmhg": payload.dbp_mmhg,
        },
        "message": "Manual patient monitor reference readings verified and linked to session.",
    }


@router.get("/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns full dual-channel session summary comparing Channel A rPPG and Channel B reference."""
    result = await db.execute(
        select(MeasurementSession).where(
            (MeasurementSession.id == session_id) & (MeasurementSession.user_id == current_user.id)
        )
    )
    session_obj = result.scalars().first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Measurement session not found")

    v_res = await db.execute(select(VitalSignEstimate).where(VitalSignEstimate.session_id == session_id))
    vital = v_res.scalars().first()

    rppg_payload = None
    manual_ref = None
    deltas: Dict[str, Optional[float]] = {}

    if vital:
        if vital.hr_bpm is not None or session_obj.status == "COMPLETED":
            waveform = json.loads(vital.rppg_waveform_json) if vital.rppg_waveform_json else []
            freqs = json.loads(vital.psd_frequencies_json) if vital.psd_frequencies_json else []
            psd = json.loads(vital.psd_power_json) if vital.psd_power_json else []
            rppg_payload = _build_dashboard_payload(session_obj, vital, waveform, freqs, psd)

        if (
            vital.is_manual_reference_verified
            or vital.reference_hr is not None
            or vital.reference_rr is not None
            or vital.reference_spo2 is not None
            or vital.reference_sbp is not None
            or vital.reference_dbp is not None
        ):
            manual_ref = ManualReferenceSummary(
                hr_bpm=vital.reference_hr,
                rr_brpm=vital.reference_rr,
                spo2_percent=vital.reference_spo2,
                sbp_mmhg=vital.reference_sbp,
                dbp_mmhg=vital.reference_dbp,
                measured_at=vital.reference_measured_at,
                monitor_device_name=session_obj.monitor_device_name,
                operator_notes=vital.reference_operator_notes,
                is_verified=bool(vital.is_manual_reference_verified),
            )

        def _delta(est: Optional[float], ref: Optional[float]) -> Optional[float]:
            if est is None or ref is None:
                return None
            return round(float(est - ref), 2)

        deltas = {
            "hr_bpm_error": _delta(vital.hr_bpm, vital.reference_hr),
            "rr_brpm_error": _delta(vital.rr_brpm, vital.reference_rr),
            "spo2_percent_error": _delta(vital.spo2_percent, vital.reference_spo2),
            "sbp_mmhg_error": _delta(vital.sbp_mmhg, vital.reference_sbp),
            "dbp_mmhg_error": _delta(vital.dbp_mmhg, vital.reference_dbp),
        }

    return SessionSummaryResponse(
        session_id=session_obj.id,
        session_code=session_obj.session_code,
        subject_id=session_obj.subject_id,
        subject_code=session_obj.subject_code,
        status=session_obj.status,
        error_message=session_obj.error_message,
        experimental_condition=session_obj.experimental_condition,
        condition_other_detail=session_obj.condition_other_detail,
        activity_duration_min=session_obj.activity_duration_min,
        ambient_lighting=session_obj.ambient_lighting,
        device_model=session_obj.device_model,
        device_os=session_obj.device_os,
        consent_verified=session_obj.consent_verified,
        started_at=session_obj.started_at,
        ended_at=session_obj.ended_at,
        created_at=session_obj.created_at,
        completed_at=session_obj.completed_at,
        camera_type=session_obj.camera_type,
        resolution=session_obj.resolution,
        fps=session_obj.fps,
        duration_sec=session_obj.duration_sec,
        total_frames=session_obj.total_frames,
        dropped_frames=session_obj.dropped_frames,
        has_video=bool(session_obj.storage_path),
        video_filename=session_obj.video_filename,
        video_sha256=session_obj.video_sha256,
        video_size_bytes=session_obj.video_size_bytes or 0,
        has_monitor_image=bool(session_obj.monitor_image_path),
        monitor_image_filename=session_obj.monitor_image_filename,
        monitor_image_sha256=session_obj.monitor_image_sha256,
        monitor_image_size_bytes=session_obj.monitor_image_size_bytes or 0,
        monitor_image_captured_at=session_obj.monitor_image_captured_at,
        monitor_device_name=session_obj.monitor_device_name,
        rppg_vitals=rppg_payload,
        manual_reference=manual_ref,
        comparison_deltas=deltas,
        drive_sync_status=session_obj.drive_sync_status,
        drive_folder_id=session_obj.drive_folder_id,
        drive_video_file_id=session_obj.drive_video_file_id,
        drive_monitor_image_file_id=session_obj.drive_monitor_image_file_id,
        drive_reference_csv_file_id=session_obj.drive_reference_csv_file_id,
        drive_metadata_json_file_id=session_obj.drive_metadata_json_file_id,
        sheets_synced=session_obj.sheets_synced,
        last_sync_error=session_obj.last_sync_error,
        synced_at=session_obj.synced_at,
    )


@router.post("/synthetic-demo", response_model=DashboardVitalSigns)
async def generate_synthetic_demo_session(
    target_hr: float = 72.0,
    target_rr: float = 16.0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes the rPPG pipeline on a labeled physiologically modeled stream for optical verification.
    """
    fps = 30.0
    duration_sec = 20.0

    rgb_signals, gt_pulse, meta = generate_synthetic_rppg_stream(
        duration_sec=duration_sec,
        fps=fps,
        target_hr_bpm=target_hr,
        target_rr_brpm=target_rr,
        snr_db=10.0,
    )

    filtered_rppg, raw_rppg, pos_meta = compute_pos_rppg(rgb_signals, fps=fps)
    hr_res = estimate_heart_rate(filtered_rppg, fps=fps)
    rr_res = estimate_respiratory_rate(raw_rppg, filtered_rppg, fps=fps)
    spo2_res = estimate_spo2_research(rgb_signals, fps=fps, signal_snr=hr_res.get("snr_db", 0.0), is_calibrated=False)
    bp_res = estimate_blood_pressure_experimental(filtered_rppg, fps=fps, hr_bpm=hr_res.get("heart_rate_bpm"))
    sqi_res = evaluate_signal_quality(filtered_rppg, rgb_signals, snr_db=hr_res.get("snr_db", -99.0), fps=fps)

    step = max(1, len(filtered_rppg) // 180)
    waveform_downsampled = [round(float(v), 4) for v in filtered_rppg[::step]]

    session_obj = MeasurementSession(
        user_id=current_user.id,
        camera_type="synthetic_optical_generator",
        resolution="1280x720",
        fps=fps,
        duration_sec=duration_sec,
        total_frames=len(rgb_signals),
        status="COMPLETED",
        completed_at=datetime.now(timezone.utc),
    )
    db.add(session_obj)
    await db.flush()

    vital_obj = VitalSignEstimate(
        session_id=session_obj.id,
        hr_bpm=hr_res.get("heart_rate_bpm"),
        hr_confidence=hr_res.get("confidence", 0.0),
        hr_status=hr_res.get("status", "GOOD"),
        snr_db=hr_res.get("snr_db", 0.0),
        time_domain_bpm=hr_res.get("time_domain_bpm"),
        rmssd_ms=hr_res.get("rmssd_ms"),
        rr_brpm=rr_res.get("respiratory_rate_brpm"),
        rr_confidence=rr_res.get("confidence", 0.0),
        rr_status=rr_res.get("status", "GOOD"),
        spo2_percent=spo2_res.get("spo2_percent"),
        spo2_confidence=spo2_res.get("confidence", 0.0),
        spo2_status=spo2_res.get("status", "EXPERIMENTAL_UNCALIBRATED"),
        spo2_ratio_of_ratios=spo2_res.get("ratio_of_ratios"),
        sbp_mmhg=bp_res.get("sbp_mmhg"),
        dbp_mmhg=bp_res.get("dbp_mmhg"),
        bp_confidence=bp_res.get("confidence", 0.0),
        bp_status=bp_res.get("status", "EXPERIMENTAL_RESEARCH"),
        sqi_score=sqi_res.get("sqi_score", 0.0),
        sqi_status=sqi_res.get("status", "GOOD"),
        motion_stability=sqi_res.get("motion_stability", 0.0),
        illumination_stability=sqi_res.get("illumination_stability", 0.0),
        quality_guidance=sqi_res.get("guidance", ""),
        reference_hr=target_hr,
        reference_rr=target_rr,
        rppg_waveform_json=json.dumps(waveform_downsampled),
        psd_frequencies_json=json.dumps(hr_res.get("frequencies_hz", [])),
        psd_power_json=json.dumps(hr_res.get("psd", [])),
        ibi_series_json=json.dumps(hr_res.get("ibi_ms", [])),
    )
    db.add(vital_obj)
    await db.commit()

    return _build_dashboard_payload(
        session_obj,
        vital_obj,
        waveform_downsampled,
        hr_res.get("frequencies_hz", []),
        hr_res.get("psd", []),
    )


@router.get("/status/{session_id}")
async def get_session_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns current status (CREATED, QUEUED, PROCESSING, COMPLETED, FAILED) of a measurement."""
    result = await db.execute(
        select(MeasurementSession).where(
            (MeasurementSession.id == session_id) & (MeasurementSession.user_id == current_user.id)
        )
    )
    session_obj = result.scalars().first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Measurement session not found")

    return {
        "session_id": session_obj.id,
        "session_code": session_obj.session_code,
        "subject_code": session_obj.subject_code,
        "status": session_obj.status,
        "error_message": session_obj.error_message,
        "total_frames": session_obj.total_frames,
        "duration_sec": session_obj.duration_sec,
        "drive_sync_status": session_obj.drive_sync_status,
    }


@router.get("/results/{session_id}", response_model=DashboardVitalSigns)
async def get_measurement_results(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns complete 4-card vital signs dashboard payload for a completed measurement."""
    result = await db.execute(
        select(MeasurementSession).where(
            (MeasurementSession.id == session_id) & (MeasurementSession.user_id == current_user.id)
        )
    )
    session_obj = result.scalars().first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Measurement session not found")

    if session_obj.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=f"Session is in {session_obj.status} state, not COMPLETED. (Error: {session_obj.error_message})",
        )

    vital_res = await db.execute(select(VitalSignEstimate).where(VitalSignEstimate.session_id == session_id))
    vital = vital_res.scalars().first()
    if not vital:
        raise HTTPException(status_code=404, detail="Vital signs record not found for session")

    waveform = json.loads(vital.rppg_waveform_json) if vital.rppg_waveform_json else []
    freqs = json.loads(vital.psd_frequencies_json) if vital.psd_frequencies_json else []
    psd = json.loads(vital.psd_power_json) if vital.psd_power_json else []

    return _build_dashboard_payload(session_obj, vital, waveform, freqs, psd)


@router.get("/history", response_model=MeasurementHistoryResponse)
async def get_measurement_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves chronological measurement history for current user."""
    query = (
        select(MeasurementSession)
        .where(MeasurementSession.user_id == current_user.id)
        .order_by(desc(MeasurementSession.created_at))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    sessions = result.scalars().all()

    items = []
    for s in sessions:
        v_res = await db.execute(select(VitalSignEstimate).where(VitalSignEstimate.session_id == s.id))
        v = v_res.scalars().first()

        items.append(
            SessionListItem(
                id=s.id,
                subject_code=s.subject_code,
                session_code=s.session_code,
                experimental_condition=s.experimental_condition,
                created_at=s.created_at,
                camera_type=s.camera_type,
                duration_sec=s.duration_sec,
                status=s.status,
                hr_bpm=v.hr_bpm if v else None,
                rr_brpm=v.rr_brpm if v else None,
                spo2_percent=v.spo2_percent if v else None,
                sbp_mmhg=v.sbp_mmhg if v else None,
                dbp_mmhg=v.dbp_mmhg if v else None,
                reference_hr=v.reference_hr if v else None,
                has_monitor_image=bool(s.monitor_image_path),
                drive_sync_status=s.drive_sync_status,
                sqi_status=v.sqi_status if v else "N/A",
            )
        )

    return MeasurementHistoryResponse(total_count=len(items), sessions=items)


@router.delete("/{session_id}")
async def delete_measurement_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes session and permanently purges underlying video and monitor image files."""
    result = await db.execute(
        select(MeasurementSession).where(
            (MeasurementSession.id == session_id) & (MeasurementSession.user_id == current_user.id)
        )
    )
    session_obj = result.scalars().first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Measurement session not found")

    if session_obj.storage_path:
        VideoStorageService.delete_video_file(session_obj.storage_path)
    if session_obj.monitor_image_path:
        MonitorImageStorageService.delete_monitor_image(session_obj.monitor_image_path)

    await db.delete(session_obj)
    await db.commit()
    return {"session_id": session_id, "deleted": True, "message": "Measurement session and media securely deleted."}
