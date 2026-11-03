"""
Measurement Sessions, Video Processing, and Vital Signs API Routes.
"""

from typing import List, Optional, Dict, Any
import json
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import numpy as np

from app.db.session import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.session import MeasurementSession
from app.models.vital_sign import VitalSignEstimate
from app.schemas.session import SessionCreate, SessionResponse
from app.schemas.vital_sign import DashboardVitalSigns, VitalSignMetric, SessionListItem, MeasurementHistoryResponse
from app.api.auth import get_current_user
from app.services.video_storage import VideoStorageService
from app.rppg.face_roi import FaceROIExtractor
from app.rppg.pos_algorithm import compute_pos_rppg
from app.rppg.hr_estimation import estimate_heart_rate
from app.rppg.rr_estimation import estimate_respiratory_rate
from app.rppg.spo2_estimation import estimate_spo2_research
from app.rppg.bp_estimation import estimate_blood_pressure_experimental
from app.rppg.quality_assessment import evaluate_signal_quality
from app.datasets.loader import generate_synthetic_rppg_stream

router = APIRouter(prefix="/measurements", tags=["Measurements"])


async def execute_rppg_pipeline_async(session_id: str, video_path: str):
    """
    Background worker executing the complete biomedical rPPG pipeline:
    1. Video frame decoding and frame-drop analysis.
    2. Computer vision face detection & anatomical ROI extraction (Forehead + Cheeks).
    3. Mathematical Plane-Orthogonal-to-Skin (POS) rPPG extraction.
    4. Heart Rate (HR) estimation via Welch PSD & IBI.
    5. Respiratory Rate (RR) modulation estimation.
    6. Peripheral Oxygen Saturation (SpO2) research analysis.
    7. Blood Pressure (SBP/DBP) experimental morphology analysis.
    8. Composite Signal Quality Index (SQI) evaluation.
    9. Atomic database commit.
    """
    async with AsyncSessionLocal() as db:
        # Update session to PROCESSING
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

            fps = meta["fps"]
            session_obj.fps = fps
            session_obj.resolution = meta["resolution"]
            session_obj.duration_sec = meta["duration_sec"]
            session_obj.total_frames = meta["frames_count"]
            session_obj.dropped_frames = meta["dropped_frames"]

            # Step 2: Facial ROI extraction
            roi_extractor = FaceROIExtractor()
            rgb_signals, diagnostics = roi_extractor.process_video_frames(frames)

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

            # Downsample rPPG waveform for UI charting (up to 200 points)
            step = max(1, len(filtered_rppg) // 200)
            waveform_downsampled = [round(float(v), 4) for v in filtered_rppg[::step]]

            # Step 9: Store Vital Signs in DB
            vital_obj = VitalSignEstimate(
                session_id=session_id,
                hr_bpm=hr_res.get("heart_rate_bpm"),
                hr_confidence=hr_res.get("confidence", 0.0),
                hr_status=hr_res.get("status", "UNRELIABLE"),
                snr_db=hr_res.get("snr_db", -99.0),
                time_domain_bpm=hr_res.get("time_domain_bpm"),
                rmssd_ms=hr_res.get("rmssd_ms"),
                rr_brpm=rr_res.get("respiratory_rate_brpm"),
                rr_confidence=rr_res.get("confidence", 0.0),
                rr_status=rr_res.get("status", "UNAVAILABLE"),
                spo2_percent=spo2_res.get("spo2_percent"),
                spo2_confidence=spo2_res.get("confidence", 0.0),
                spo2_status=spo2_res.get("status", "EXPERIMENTAL_UNCALIBRATED"),
                spo2_ratio_of_ratios=spo2_res.get("ratio_of_ratios"),
                spo2_is_calibrated=spo2_res.get("is_calibrated", False),
                sbp_mmhg=bp_res.get("sbp_mmhg"),
                dbp_mmhg=bp_res.get("dbp_mmhg"),
                bp_confidence=bp_res.get("confidence", 0.0),
                bp_status=bp_res.get("status", "EXPERIMENTAL_RESEARCH"),
                bp_is_calibrated=bp_res.get("is_calibrated", False),
                sqi_score=sqi_res.get("sqi_score", 0.0),
                sqi_status=sqi_res.get("status", "POOR"),
                motion_stability=sqi_res.get("motion_stability", 0.0),
                illumination_stability=sqi_res.get("illumination_stability", 0.0),
                quality_guidance=sqi_res.get("guidance", ""),
                rppg_waveform_json=json.dumps(waveform_downsampled),
                psd_frequencies_json=json.dumps(hr_res.get("frequencies_hz", [])),
                psd_power_json=json.dumps(hr_res.get("psd", [])),
                ibi_series_json=json.dumps(hr_res.get("ibi_ms", [])),
            )
            db.add(vital_obj)

            session_obj.status = "COMPLETED"
            session_obj.completed_at = datetime.now(timezone.utc)
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
    """Initializes a new rPPG measurement session."""
    session_obj = MeasurementSession(
        user_id=current_user.id,
        camera_type=payload.camera_type,
        resolution=payload.resolution,
        fps=payload.fps,
        status="QUEUED",
    )
    db.add(session_obj)
    await db.commit()
    await db.refresh(session_obj)

    return SessionResponse(
        session_id=session_obj.id,
        status=session_obj.status,
        created_at=session_obj.created_at,
        message="Measurement session initialized. Ready for video upload.",
    )


@router.post("/upload/{session_id}")
async def upload_video(
    session_id: str,
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads facial video and automatically queues background rPPG execution.
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
        raise HTTPException(status_code=400, detail="Uploaded file is too small or empty")

    storage_info = await VideoStorageService.save_upload(session_id, content, video.filename or "facial_video.mp4")

    session_obj.video_filename = storage_info["filename"]
    session_obj.storage_path = storage_info["storage_path"]
    session_obj.video_size_bytes = storage_info["size_bytes"]
    session_obj.video_sha256 = storage_info["sha256"]
    session_obj.retention_expires_at = storage_info["retention_expires_at"]
    session_obj.status = "QUEUED"
    await db.commit()

    # Launch processing in background
    background_tasks.add_task(execute_rppg_pipeline_async, session_id, storage_info["storage_path"])

    return {
        "session_id": session_id,
        "status": "QUEUED",
        "size_bytes": storage_info["size_bytes"],
        "sha256": storage_info["sha256"],
        "message": "Video uploaded successfully. rPPG analysis dispatched.",
    }


@router.post("/synthetic-demo", response_model=DashboardVitalSigns)
async def generate_synthetic_demo_session(
    target_hr: float = 72.0,
    target_rr: float = 16.0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Instantly executes the entire rPPG pipeline on a physiologically modeled optical stream.
    Allows testing and validating the complete system without uploading large video files.
    """
    fps = 30.0
    duration_sec = 20.0

    # 1. Synthesize optical RGB traces
    rgb_signals, gt_pulse, meta = generate_synthetic_rppg_stream(
        duration_sec=duration_sec,
        fps=fps,
        target_hr_bpm=target_hr,
        target_rr_brpm=target_rr,
        snr_db=10.0,
    )

    # 2. Run POS algorithm
    filtered_rppg, raw_rppg, pos_meta = compute_pos_rppg(rgb_signals, fps=fps)

    # 3. Parameter estimations
    hr_res = estimate_heart_rate(filtered_rppg, fps=fps)
    rr_res = estimate_respiratory_rate(raw_rppg, filtered_rppg, fps=fps)
    spo2_res = estimate_spo2_research(rgb_signals, fps=fps, signal_snr=hr_res.get("snr_db", 0.0), is_calibrated=False)
    bp_res = estimate_blood_pressure_experimental(filtered_rppg, fps=fps, hr_bpm=hr_res.get("heart_rate_bpm"))
    sqi_res = evaluate_signal_quality(filtered_rppg, rgb_signals, snr_db=hr_res.get("snr_db", -99.0), fps=fps)

    # Downsample rPPG waveform for UI charting
    step = max(1, len(filtered_rppg) // 180)
    waveform_downsampled = [round(float(v), 4) for v in filtered_rppg[::step]]

    # 4. Save session and vitals to DB
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

    return DashboardVitalSigns(
        session_id=session_obj.id,
        timestamp=session_obj.created_at,
        camera_type=session_obj.camera_type,
        status="COMPLETED",
        heart_rate=VitalSignMetric(
            value=vital_obj.hr_bpm,
            unit="BPM",
            confidence=vital_obj.hr_confidence,
            status=vital_obj.hr_status,
            uncertainty_range="+/- 1.5 BPM",
        ),
        respiratory_rate=VitalSignMetric(
            value=vital_obj.rr_brpm,
            unit="BrPM",
            confidence=vital_obj.rr_confidence,
            status=vital_obj.rr_status,
            uncertainty_range="+/- 2.0 BrPM",
        ),
        oxygen_saturation=VitalSignMetric(
            value=vital_obj.spo2_percent,
            unit="%",
            confidence=vital_obj.spo2_confidence,
            status=vital_obj.spo2_status,
            uncertainty_range="+/- 3.5%",
            is_experimental=True,
            disclaimer=spo2_res.get("scientific_disclosure"),
        ),
        blood_pressure_sbp=VitalSignMetric(
            value=vital_obj.sbp_mmhg,
            unit="mmHg",
            confidence=vital_obj.bp_confidence,
            status=vital_obj.bp_status,
            uncertainty_range="+/- 12.0 mmHg",
            is_experimental=True,
            disclaimer=bp_res.get("iso_compliance_note"),
        ),
        blood_pressure_dbp=VitalSignMetric(
            value=vital_obj.dbp_mmhg,
            unit="mmHg",
            confidence=vital_obj.bp_confidence,
            status=vital_obj.bp_status,
            uncertainty_range="+/- 9.0 mmHg",
            is_experimental=True,
            disclaimer=bp_res.get("iso_compliance_note"),
        ),
        signal_quality_score=vital_obj.sqi_score,
        signal_quality_status=vital_obj.sqi_status,
        motion_stability=vital_obj.motion_stability,
        illumination_stability=vital_obj.illumination_stability,
        quality_guidance=vital_obj.quality_guidance or "High quality optical stream.",
        rppg_waveform=waveform_downsampled,
        frequencies_hz=hr_res.get("frequencies_hz", []),
        psd_power=hr_res.get("psd", []),
    )


@router.get("/status/{session_id}")
async def get_session_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns current status (QUEUED, PROCESSING, COMPLETED, FAILED) of a measurement."""
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
        "status": session_obj.status,
        "error_message": session_obj.error_message,
        "total_frames": session_obj.total_frames,
        "duration_sec": session_obj.duration_sec,
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

    return DashboardVitalSigns(
        session_id=session_obj.id,
        timestamp=session_obj.created_at,
        camera_type=session_obj.camera_type,
        status="COMPLETED",
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
            disclaimer="Conventional RGB camera - uncalibrated optical proxy.",
        ),
        blood_pressure_sbp=VitalSignMetric(
            value=vital.sbp_mmhg,
            unit="mmHg",
            confidence=vital.bp_confidence,
            status=vital.bp_status,
            is_experimental=True,
            disclaimer="ISO 81060-2 experimental research objective.",
        ),
        blood_pressure_dbp=VitalSignMetric(
            value=vital.dbp_mmhg,
            unit="mmHg",
            confidence=vital.bp_confidence,
            status=vital.bp_status,
            is_experimental=True,
            disclaimer="ISO 81060-2 experimental research objective.",
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
                created_at=s.created_at,
                camera_type=s.camera_type,
                duration_sec=s.duration_sec,
                status=s.status,
                hr_bpm=v.hr_bpm if v else None,
                rr_brpm=v.rr_brpm if v else None,
                spo2_percent=v.spo2_percent if v else None,
                sbp_mmhg=v.sbp_mmhg if v else None,
                dbp_mmhg=v.dbp_mmhg if v else None,
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
    """Deletes session and permanently purges underlying video files."""
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

    await db.delete(session_obj)
    await db.commit()
    return {"session_id": session_id, "deleted": True, "message": "Measurement session and video securely deleted."}
