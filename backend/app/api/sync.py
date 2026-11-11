"""
Google Drive & Google Sheets Synchronization API Routes (Phase 5).
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.session import MeasurementSession
from app.api.auth import get_current_user
from app.services.google_sync import (
    GoogleSyncService,
    GoogleSyncError,
    get_session_upload_progress,
)

router = APIRouter(prefix="/sync", tags=["Google Drive & Sheets Sync"])


@router.get("/google/status")
async def get_google_oauth_status(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Reports server-side Google OAuth configuration & authorization status (zero secrets exposed)."""
    return GoogleSyncService.get_oauth_status()


@router.get("/google/auth-url")
async def get_google_auth_url(current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    """Builds Google OAuth 2.0 consent URL using server-side client credentials."""
    svc = GoogleSyncService()
    try:
        url = svc.build_authorization_url()
        return {"authorization_url": url}
    except GoogleSyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/google/callback")
async def handle_google_oauth_callback(
    code: str = Query(..., description="Authorization code from Google OAuth 2.0 consent redirect"),
) -> Dict[str, Any]:
    """Exchanges OAuth authorization code for server-side refresh/access tokens."""
    svc = GoogleSyncService()
    try:
        await svc.exchange_code_for_tokens(code)
        return {
            "status": "AUTHORIZED",
            "message": "Google Drive & Sheets OAuth 2.0 tokens saved securely on server.",
        }
    except GoogleSyncError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/session/{session_id}")
async def sync_single_session(
    session_id: str,
    force: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Synchronizes a single session (folder hierarchy + resumable uploads + Master Sheet row)."""
    s_res = await db.execute(
        select(MeasurementSession).where(
            (MeasurementSession.id == session_id) & (MeasurementSession.user_id == current_user.id)
        )
    )
    if not s_res.scalars().first():
        raise HTTPException(status_code=404, detail="Measurement session not found")

    svc = GoogleSyncService()
    try:
        return await svc.sync_session(db, session_id, force=force)
    except GoogleSyncError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/session/{session_id}/progress")
async def get_sync_progress(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Returns real-time resumable upload progress and persisted Drive sync status for a session."""
    s_res = await db.execute(
        select(MeasurementSession).where(
            (MeasurementSession.id == session_id) & (MeasurementSession.user_id == current_user.id)
        )
    )
    sess = s_res.scalars().first()
    if not sess:
        raise HTTPException(status_code=404, detail="Measurement session not found")

    prog = get_session_upload_progress(session_id)
    return {
        **prog,
        "drive_sync_status": sess.drive_sync_status,
        "sheets_synced": sess.sheets_synced,
        "last_sync_error": sess.last_sync_error,
        "synced_at": sess.synced_at.isoformat() if sess.synced_at else None,
    }


@router.get("/pending")
async def list_pending_sync_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Lists all sessions awaiting Google Drive/Sheets sync or needing retry."""
    res = await db.execute(
        select(MeasurementSession)
        .where(MeasurementSession.user_id == current_user.id)
        .order_by(desc(MeasurementSession.created_at))
    )
    sessions = res.scalars().all()
    items: List[Dict[str, Any]] = []
    for s in sessions:
        items.append({
            "session_id": s.id,
            "subject_code": s.subject_code,
            "session_code": s.session_code,
            "experimental_condition": s.experimental_condition,
            "status": s.status,
            "drive_sync_status": s.drive_sync_status,
            "sheets_synced": s.sheets_synced,
            "last_sync_error": s.last_sync_error,
            "has_video": bool(s.storage_path),
            "has_monitor_image": bool(s.monitor_image_path),
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "synced_at": s.synced_at.isoformat() if s.synced_at else None,
        })
    pending_count = sum(1 for i in items if i["drive_sync_status"] != "SYNCED")
    return {"total": len(items), "pending_count": pending_count, "sessions": items}


@router.post("/process-pending")
async def process_pending_sync_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retries synchronization for all PENDING or FAILED sessions belonging to current researcher."""
    res = await db.execute(
        select(MeasurementSession).where(
            (MeasurementSession.user_id == current_user.id)
            & (MeasurementSession.drive_sync_status.in_(["PENDING", "FAILED"]))
        )
    )
    sessions = res.scalars().all()
    svc = GoogleSyncService()
    synced, failed = [], []

    for s in sessions:
        try:
            r = await svc.sync_session(db, s.id, force=False)
            synced.append(r)
        except Exception as exc:
            failed.append({"session_id": s.id, "error": str(exc)})

    return {
        "processed": len(sessions),
        "synced_count": len(synced),
        "failed_count": len(failed),
        "synced": synced,
        "failed": failed,
    }
