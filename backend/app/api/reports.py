"""
Biomedical Measurement Reports API (PDF and CSV Download).
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.session import MeasurementSession
from app.models.vital_sign import VitalSignEstimate
from app.api.auth import get_current_user
from app.services.report_generator import ReportGenerator
from app.core.config import settings

router = APIRouter(prefix="/reports", tags=["Reports"])


async def prepare_report_data(session_id: str, current_user: User, db: AsyncSession):
    result = await db.execute(
        select(MeasurementSession).where(
            (MeasurementSession.id == session_id) & (MeasurementSession.user_id == current_user.id)
        )
    )
    s = result.scalars().first()
    if not s:
        raise HTTPException(status_code=404, detail="Measurement session not found")

    v_res = await db.execute(select(VitalSignEstimate).where(VitalSignEstimate.session_id == session_id))
    v = v_res.scalars().first()

    data = {
        "session_id": s.id,
        "timestamp": s.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if s.created_at else "",
        "pseudonym_id": current_user.pseudonym_id,
        "algorithm_version": s.algorithm_version or "POS-v1.0.0",
        "camera_type": s.camera_type,
        "resolution": s.resolution,
        "fps": s.fps,
        "duration_sec": s.duration_sec,
        "total_frames": s.total_frames,
        "dropped_frames": s.dropped_frames,
        "hr_bpm": v.hr_bpm if v else None,
        "hr_confidence": v.hr_confidence if v else 0.0,
        "hr_status": v.hr_status if v else "N/A",
        "snr_db": v.snr_db if v else -99.0,
        "rr_brpm": v.rr_brpm if v else None,
        "rr_confidence": v.rr_confidence if v else 0.0,
        "rr_status": v.rr_status if v else "N/A",
        "spo2_percent": v.spo2_percent if v else None,
        "spo2_confidence": v.spo2_confidence if v else 0.0,
        "spo2_status": v.spo2_status if v else "N/A",
        "sbp_mmhg": v.sbp_mmhg if v else None,
        "dbp_mmhg": v.dbp_mmhg if v else None,
        "bp_confidence": v.bp_confidence if v else 0.0,
        "bp_status": v.bp_status if v else "N/A",
        "sqi_score": v.sqi_score if v else 0.0,
        "sqi_status": v.sqi_status if v else "N/A",
        "motion_stability": v.motion_stability if v else 0.0,
        "illumination_stability": v.illumination_stability if v else 0.0,
        "quality_guidance": v.quality_guidance if v else "",
        "reference_hr": v.reference_hr if v else None,
        "reference_rr": v.reference_rr if v else None,
        "reference_spo2": v.reference_spo2 if v else None,
        "reference_sbp": v.reference_sbp if v else None,
        "reference_dbp": v.reference_dbp if v else None,
    }
    return data


@router.get("/csv/{session_id}")
async def download_csv_report(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generates and downloads a CSV measurement report."""
    data = await prepare_report_data(session_id, current_user, db)
    csv_content = ReportGenerator.generate_csv_report(data)

    filename = f"rppg_report_{session_id[:8]}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/pdf/{session_id}")
async def download_pdf_report(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generates and downloads a publication-grade PDF measurement report."""
    data = await prepare_report_data(session_id, current_user, db)

    filename = f"rppg_report_{session_id[:8]}.pdf"
    pdf_path = os.path.join(settings.REPORTS_DIR, filename)

    ReportGenerator.generate_pdf_report(data, pdf_path)

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename,
    )
