"""
Subject-Wise Research Participant Management API (Phase 4).
Assigns sequential SUBJECT_001, SUBJECT_002... identifiers and enforces informed consent.
"""

import re
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_

from app.db.session import get_db
from app.models.user import User
from app.models.subject import Subject
from app.models.session import MeasurementSession
from app.models.vital_sign import VitalSignEstimate
from app.schemas.subject import SubjectCreate, SubjectUpdate, SubjectResponse, SubjectSessionBrief
from app.api.auth import get_current_user

router = APIRouter(prefix="/subjects", tags=["Subjects"])


async def _allocate_next_subject_code(db: AsyncSession) -> str:
    """Computes the next canonical sequential SUBJECT_NNN identifier."""
    res = await db.execute(select(Subject.subject_code))
    codes = res.scalars().all()
    max_num = 0
    for code in codes:
        m = re.match(r"^SUBJECT_(\d+)$", code or "")
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
    return f"SUBJECT_{max_num + 1:03d}"


async def _build_subject_response(
    db: AsyncSession,
    subj: Subject,
    include_sessions: bool = False,
) -> SubjectResponse:
    sess_res = await db.execute(
        select(MeasurementSession)
        .where(MeasurementSession.subject_id == subj.id)
        .order_by(desc(MeasurementSession.created_at))
    )
    sessions = sess_res.scalars().all()

    briefs: List[SubjectSessionBrief] = []
    if include_sessions:
        for s in sessions:
            v_res = await db.execute(
                select(VitalSignEstimate).where(VitalSignEstimate.session_id == s.id)
            )
            v = v_res.scalars().first()
            briefs.append(
                SubjectSessionBrief(
                    id=s.id,
                    session_code=s.session_code,
                    experimental_condition=s.experimental_condition,
                    status=s.status,
                    drive_sync_status=s.drive_sync_status,
                    created_at=s.created_at,
                    hr_bpm=v.hr_bpm if v else None,
                    rr_brpm=v.rr_brpm if v else None,
                    spo2_percent=v.spo2_percent if v else None,
                    sbp_mmhg=v.sbp_mmhg if v else None,
                    dbp_mmhg=v.dbp_mmhg if v else None,
                    sqi_status=v.sqi_status if v else None,
                    reference_hr=v.reference_hr if v else None,
                    reference_rr=v.reference_rr if v else None,
                    reference_spo2=v.reference_spo2 if v else None,
                    reference_sbp=v.reference_sbp if v else None,
                    reference_dbp=v.reference_dbp if v else None,
                    has_video=bool(s.storage_path),
                    has_monitor_image=bool(s.monitor_image_path),
                    is_manual_reference_verified=bool(v.is_manual_reference_verified) if v else False,
                )
            )

    return SubjectResponse(
        id=subj.id,
        subject_code=subj.subject_code,
        age=subj.age,
        gender=subj.gender,
        fitzpatrick_skin_type=subj.fitzpatrick_skin_type,
        consent_signed=subj.consent_signed,
        consent_timestamp=subj.consent_timestamp,
        notes=subj.notes,
        drive_folder_id=subj.drive_folder_id,
        created_at=subj.created_at,
        session_count=len(sessions),
        sessions=briefs,
    )


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    payload: SubjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registers a research subject with sequential SUBJECT_NNN ID and informed consent."""
    if not payload.consent_signed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signed participant informed consent is mandatory before subject registration.",
        )

    subject_code = await _allocate_next_subject_code(db)
    subj = Subject(
        subject_code=subject_code,
        created_by_user_id=current_user.id,
        age=payload.age,
        gender=payload.gender,
        fitzpatrick_skin_type=payload.fitzpatrick_skin_type,
        consent_signed=True,
        consent_timestamp=datetime.now(timezone.utc),
        notes=payload.notes,
    )
    db.add(subj)
    await db.commit()
    await db.refresh(subj)
    return await _build_subject_response(db, subj, include_sessions=False)


@router.get("", response_model=List[SubjectResponse])
async def list_subjects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all registered subjects ordered by subject_code."""
    res = await db.execute(select(Subject).order_by(Subject.subject_code))
    subjects = res.scalars().all()
    results = []
    for subj in subjects:
        results.append(await _build_subject_response(db, subj, include_sessions=False))
    return results


@router.get("/{subject_identifier}", response_model=SubjectResponse)
async def get_subject(
    subject_identifier: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves a subject by UUID or subject_code (e.g., SUBJECT_001) including sessions."""
    res = await db.execute(
        select(Subject).where(
            or_(Subject.id == subject_identifier, Subject.subject_code == subject_identifier)
        )
    )
    subj = res.scalars().first()
    if not subj:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_identifier}' not found.")
    return await _build_subject_response(db, subj, include_sessions=True)


@router.patch("/{subject_identifier}", response_model=SubjectResponse)
async def update_subject(
    subject_identifier: str,
    payload: SubjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates subject demographic or research notes metadata."""
    res = await db.execute(
        select(Subject).where(
            or_(Subject.id == subject_identifier, Subject.subject_code == subject_identifier)
        )
    )
    subj = res.scalars().first()
    if not subj:
        raise HTTPException(status_code=404, detail=f"Subject '{subject_identifier}' not found.")

    if payload.age is not None:
        subj.age = payload.age
    if payload.gender is not None:
        subj.gender = payload.gender
    if payload.fitzpatrick_skin_type is not None:
        subj.fitzpatrick_skin_type = payload.fitzpatrick_skin_type
    if payload.notes is not None:
        subj.notes = payload.notes

    await db.commit()
    await db.refresh(subj)
    return await _build_subject_response(db, subj, include_sessions=True)
