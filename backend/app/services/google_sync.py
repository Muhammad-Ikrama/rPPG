"""
Server-Side Google OAuth 2.0, Google Drive API v3 (Resumable Uploads),
and Google Sheets API v4 (Master Sheet Upsert) Integration Service (Phase 5).

Security Guarantee:
- Client secrets and OAuth refresh tokens are stored ONLY server-side in
  settings.GOOGLE_CLIENT_SECRETS_FILE and settings.GOOGLE_TOKEN_FILE (secrets/).
- Zero Google credentials are ever sent to mobile clients or committed to GitHub.
"""

import asyncio
import csv
import io
import json
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.session import MeasurementSession
from app.models.subject import Subject
from app.models.vital_sign import VitalSignEstimate

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_RESUMABLE_URL = "https://www.googleapis.com/upload/drive/v3/files"
SHEETS_BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]

MASTER_SHEET_HEADERS = [
    "Subject Code",
    "Session Code",
    "Session UUID",
    "Experimental Condition",
    "Condition Detail",
    "Activity Duration (min)",
    "Ambient Lighting",
    "Device Model",
    "Recording Started (UTC)",
    "Recording Ended (UTC)",
    "rPPG HR (BPM)",
    "rPPG RR (BrPM)",
    "rPPG SpO2 (%) [Experimental]",
    "rPPG SBP (mmHg) [Experimental]",
    "rPPG DBP (mmHg) [Experimental]",
    "SQI Score",
    "SQI Status",
    "Valid Face Ratio",
    "Ref HR (BPM)",
    "Ref RR (BrPM)",
    "Ref SpO2 (%)",
    "Ref SBP (mmHg)",
    "Ref DBP (mmHg)",
    "Monitor Device",
    "Manual Reference Verified",
    "Drive Folder Link",
    "Video Drive Link",
    "Monitor Image Drive Link",
    "Metadata Drive Link",
    "Synced At (UTC)",
]

# In-memory live progress registry per session_id
_UPLOAD_PROGRESS: Dict[str, Dict[str, Any]] = {}


def get_session_upload_progress(session_id: str) -> Dict[str, Any]:
    return _UPLOAD_PROGRESS.get(
        session_id,
        {
            "session_id": session_id,
            "stage": "IDLE",
            "percent": 0.0,
            "bytes_uploaded": 0,
            "bytes_total": 0,
            "current_file": None,
        },
    )


class GoogleSyncError(RuntimeError):
    """Raised when Google OAuth, Drive, or Sheets synchronization fails."""


class GoogleSyncService:
    """
    Async Google Drive & Sheets synchronizer powered by httpx.AsyncClient.
    Supports transport injection for deterministic testing.
    """

    def __init__(
        self,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        chunk_size: int = 256 * 1024,  # 256 KB minimum Drive chunk multiple
    ):
        self.transport = transport
        self.chunk_size = max(256 * 1024, (chunk_size // (256 * 1024)) * 256 * 1024)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self.transport, timeout=60.0)

    @staticmethod
    def load_client_secrets() -> Dict[str, str]:
        """Loads server-side Google OAuth client config from file or environment."""
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if client_id and client_secret:
            return {"client_id": client_id, "client_secret": client_secret}

        path = settings.GOOGLE_CLIENT_SECRETS_FILE
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            block = raw.get("web") or raw.get("installed") or raw
            if block.get("client_id") and block.get("client_secret"):
                return {
                    "client_id": block["client_id"],
                    "client_secret": block["client_secret"],
                }

        raise GoogleSyncError(
            "Google OAuth client credentials not configured on server. "
            f"Place client JSON at {path} or set GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET."
        )

    @staticmethod
    def load_saved_tokens() -> Optional[Dict[str, Any]]:
        path = settings.GOOGLE_TOKEN_FILE
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_tokens(token_data: Dict[str, Any]) -> None:
        path = settings.GOOGLE_TOKEN_FILE
        os.makedirs(os.path.dirname(path), exist_ok=True)
        existing = GoogleSyncService.load_saved_tokens() or {}
        merged = {**existing, **token_data}
        if "expires_in" in token_data:
            exp = datetime.now(timezone.utc) + timedelta(seconds=int(token_data["expires_in"]))
            merged["expires_at"] = exp.isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)

    @staticmethod
    def get_oauth_status() -> Dict[str, Any]:
        client_configured = True
        try:
            GoogleSyncService.load_client_secrets()
        except GoogleSyncError:
            client_configured = False

        tokens = GoogleSyncService.load_saved_tokens()
        authorized = bool(tokens and (tokens.get("refresh_token") or tokens.get("access_token")))
        spreadsheet_id = (
            settings.GOOGLE_SHEETS_SPREADSHEET_ID
            or (tokens.get("master_spreadsheet_id") if tokens else None)
        )
        return {
            "client_configured": client_configured,
            "authorized": authorized,
            "has_refresh_token": bool(tokens and tokens.get("refresh_token")),
            "token_expires_at": tokens.get("expires_at") if tokens else None,
            "drive_root_folder": settings.GOOGLE_DRIVE_ROOT_FOLDER,
            "master_spreadsheet_id": spreadsheet_id,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        }

    def build_authorization_url(self, state: str = "rppg_fyp_state") -> str:
        secrets_cfg = self.load_client_secrets()
        params = {
            "client_id": secrets_cfg["client_id"],
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(GOOGLE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        secrets_cfg = self.load_client_secrets()
        async with self._client() as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": secrets_cfg["client_id"],
                    "client_secret": secrets_cfg["client_secret"],
                    "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
        if resp.status_code != 200:
            raise GoogleSyncError(f"OAuth token exchange failed ({resp.status_code}): {resp.text}")
        token_data = resp.json()
        self.save_tokens(token_data)
        return token_data

    async def ensure_valid_access_token(self) -> str:
        tokens = self.load_saved_tokens()
        if not tokens:
            raise GoogleSyncError("Google OAuth is not authorized yet. Complete /sync/google/auth-url flow first.")

        access_token = tokens.get("access_token")
        expires_at_str = tokens.get("expires_at")
        needs_refresh = not access_token

        if expires_at_str and not needs_refresh:
            try:
                exp_dt = datetime.fromisoformat(expires_at_str)
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) >= (exp_dt - timedelta(minutes=2)):
                    needs_refresh = True
            except Exception:
                needs_refresh = True

        if not needs_refresh:
            return access_token

        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise GoogleSyncError("Google access token expired and no refresh token is available.")

        secrets_cfg = self.load_client_secrets()
        async with self._client() as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": secrets_cfg["client_id"],
                    "client_secret": secrets_cfg["client_secret"],
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        if resp.status_code != 200:
            raise GoogleSyncError(f"Google OAuth refresh failed ({resp.status_code}): {resp.text}")
        new_data = resp.json()
        self.save_tokens(new_data)
        return new_data["access_token"]

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        max_retries: int = 3,
        **kwargs,
    ) -> httpx.Response:
        last_exc = None
        for attempt in range(max_retries):
            try:
                resp = await client.request(method, url, **kwargs)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                    await asyncio.sleep(0.2 * (2 ** attempt))
                    continue
                return resp
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.2 * (2 ** attempt))
                    continue
        raise GoogleSyncError(f"HTTP request to {url} failed after retries: {last_exc}")

    async def ensure_drive_folder(
        self,
        client: httpx.AsyncClient,
        headers: Dict[str, str],
        folder_name: str,
        parent_id: Optional[str] = None,
    ) -> str:
        """Finds an existing non-trashed Drive folder or creates one (duplicate-safe)."""
        safe_name = folder_name.replace("'", "\\'")
        q_parts = [
            f"name = '{safe_name}'",
            "mimeType = 'application/vnd.google-apps.folder'",
            "trashed = false",
        ]
        if parent_id:
            q_parts.append(f"'{parent_id}' in parents")

        search_resp = await self._request_with_retry(
            client,
            "GET",
            DRIVE_FILES_URL,
            headers=headers,
            params={"q": " and ".join(q_parts), "fields": "files(id,name)", "pageSize": 5},
        )
        if search_resp.status_code == 200:
            files = search_resp.json().get("files", [])
            if files:
                return files[0]["id"]

        metadata: Dict[str, Any] = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]

        create_resp = await self._request_with_retry(
            client,
            "POST",
            DRIVE_FILES_URL,
            headers={**headers, "Content-Type": "application/json"},
            json=metadata,
            params={"fields": "id"},
        )
        if create_resp.status_code not in (200, 201):
            raise GoogleSyncError(f"Failed creating Drive folder '{folder_name}': {create_resp.text}")
        return create_resp.json()["id"]

    async def _find_existing_file(
        self,
        client: httpx.AsyncClient,
        headers: Dict[str, str],
        filename: str,
        parent_id: str,
    ) -> Optional[str]:
        safe_name = filename.replace("'", "\\'")
        q = f"name = '{safe_name}' and '{parent_id}' in parents and trashed = false"
        resp = await self._request_with_retry(
            client,
            "GET",
            DRIVE_FILES_URL,
            headers=headers,
            params={"q": q, "fields": "files(id,name)", "pageSize": 1},
        )
        if resp.status_code == 200:
            files = resp.json().get("files", [])
            if files:
                return files[0]["id"]
        return None

    async def upload_bytes_resumable(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        filename: str,
        content_bytes: bytes,
        mime_type: str,
        parent_id: str,
        existing_file_id: Optional[str] = None,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """
        Uploads bytes to Google Drive using uploadType=resumable with Content-Range chunking.
        Prevents duplicate files via existing_file_id / Drive folder search.
        """
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        total_size = len(content_bytes)

        # Duplicate check inside parent folder
        target_file_id = existing_file_id or await self._find_existing_file(
            client, auth_headers, filename, parent_id
        )

        # 1. Initiate resumable session URI
        if target_file_id:
            init_method = "PATCH"
            init_url = f"{DRIVE_UPLOAD_RESUMABLE_URL}/{target_file_id}"
            metadata = {"name": filename, "mimeType": mime_type}
        else:
            init_method = "POST"
            init_url = DRIVE_UPLOAD_RESUMABLE_URL
            metadata = {"name": filename, "parents": [parent_id], "mimeType": mime_type}

        init_resp = await self._request_with_retry(
            client,
            init_method,
            init_url,
            params={"uploadType": "resumable", "fields": "id"},
            headers={
                **auth_headers,
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": mime_type,
                "X-Upload-Content-Length": str(total_size),
            },
            json=metadata,
        )
        if init_resp.status_code not in (200, 201):
            raise GoogleSyncError(
                f"Failed to initiate resumable upload for {filename} ({init_resp.status_code}): {init_resp.text}"
            )

        upload_uri = init_resp.headers.get("Location") or init_resp.headers.get("location")
        if not upload_uri:
            # Some test mocks return ID directly without Location
            if init_resp.content:
                data = init_resp.json()
                if data.get("id"):
                    if progress_cb:
                        progress_cb(total_size, total_size)
                    return data["id"]
            raise GoogleSyncError(f"Drive resumable init response missing Location header for {filename}")

        # 2. Stream byte chunks with Content-Range
        if total_size == 0:
            raise GoogleSyncError(f"Cannot upload empty file {filename}")

        offset = 0
        file_id: Optional[str] = None
        while offset < total_size:
            end = min(offset + self.chunk_size, total_size)
            chunk = content_bytes[offset:end]
            chunk_headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {offset}-{end - 1}/{total_size}",
                "Content-Type": mime_type,
            }
            put_resp = await self._request_with_retry(
                client,
                "PUT",
                upload_uri,
                headers=chunk_headers,
                content=chunk,
            )
            if put_resp.status_code in (200, 201):
                file_id = put_resp.json().get("id") or target_file_id
                offset = end
                if progress_cb:
                    progress_cb(offset, total_size)
                break
            elif put_resp.status_code == 308:
                offset = end
                if progress_cb:
                    progress_cb(offset, total_size)
            else:
                raise GoogleSyncError(
                    f"Resumable chunk upload failed for {filename} ({put_resp.status_code}): {put_resp.text}"
                )

        if not file_id:
            raise GoogleSyncError(f"Resumable upload completed without returning Drive file ID for {filename}")
        return file_id

    @staticmethod
    def build_reference_csv_bytes(
        session_obj: MeasurementSession,
        vital: Optional[VitalSignEstimate],
    ) -> bytes:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "subject_code",
            "session_code",
            "session_id",
            "experimental_condition",
            "hr_bpm_ref",
            "rr_brpm_ref",
            "spo2_percent_ref",
            "sbp_mmhg_ref",
            "dbp_mmhg_ref",
            "measured_at_utc",
            "monitor_device_name",
            "is_manual_reference_verified",
            "operator_notes",
        ])
        writer.writerow([
            session_obj.subject_code or "",
            session_obj.session_code or "",
            session_obj.id,
            session_obj.experimental_condition,
            vital.reference_hr if vital else "",
            vital.reference_rr if vital else "",
            vital.reference_spo2 if vital else "",
            vital.reference_sbp if vital else "",
            vital.reference_dbp if vital else "",
            vital.reference_measured_at.isoformat() if (vital and vital.reference_measured_at) else "",
            session_obj.monitor_device_name or "",
            bool(vital.is_manual_reference_verified) if vital else False,
            vital.reference_operator_notes if vital else "",
        ])
        return buf.getvalue().encode("utf-8")

    @staticmethod
    def build_metadata_json_bytes(
        session_obj: MeasurementSession,
        subject_obj: Optional[Subject],
        vital: Optional[VitalSignEstimate],
    ) -> bytes:
        payload = {
            "subject": {
                "subject_id": subject_obj.id if subject_obj else None,
                "subject_code": session_obj.subject_code,
                "age": subject_obj.age if subject_obj else None,
                "gender": subject_obj.gender if subject_obj else None,
                "fitzpatrick_skin_type": subject_obj.fitzpatrick_skin_type if subject_obj else None,
                "consent_signed": subject_obj.consent_signed if subject_obj else session_obj.consent_verified,
            },
            "session": {
                "session_id": session_obj.id,
                "session_code": session_obj.session_code,
                "client_session_id": session_obj.client_session_id,
                "experimental_condition": session_obj.experimental_condition,
                "condition_other_detail": session_obj.condition_other_detail,
                "activity_duration_min": session_obj.activity_duration_min,
                "ambient_lighting": session_obj.ambient_lighting,
                "device_model": session_obj.device_model,
                "device_os": session_obj.device_os,
                "consent_verified": session_obj.consent_verified,
                "started_at": session_obj.started_at.isoformat() if session_obj.started_at else None,
                "ended_at": session_obj.ended_at.isoformat() if session_obj.ended_at else None,
                "created_at": session_obj.created_at.isoformat() if session_obj.created_at else None,
            },
            "channel_a_video": {
                "filename": session_obj.video_filename,
                "sha256": session_obj.video_sha256,
                "size_bytes": session_obj.video_size_bytes,
                "fps": session_obj.fps,
                "resolution": session_obj.resolution,
                "duration_sec": session_obj.duration_sec,
                "total_frames": session_obj.total_frames,
                "dropped_frames": session_obj.dropped_frames,
            },
            "channel_b_monitor": {
                "filename": session_obj.monitor_image_filename,
                "sha256": session_obj.monitor_image_sha256,
                "size_bytes": session_obj.monitor_image_size_bytes,
                "captured_at": session_obj.monitor_image_captured_at.isoformat()
                if session_obj.monitor_image_captured_at
                else None,
                "device_name": session_obj.monitor_device_name,
            },
            "rppg_estimates": {
                "algorithm_version": session_obj.algorithm_version,
                "hr_bpm": vital.hr_bpm if vital else None,
                "hr_confidence": vital.hr_confidence if vital else None,
                "rr_brpm": vital.rr_brpm if vital else None,
                "spo2_percent_experimental": vital.spo2_percent if vital else None,
                "sbp_mmhg_experimental": vital.sbp_mmhg if vital else None,
                "dbp_mmhg_experimental": vital.dbp_mmhg if vital else None,
                "sqi_score": vital.sqi_score if vital else None,
                "sqi_status": vital.sqi_status if vital else None,
                "valid_face_ratio": vital.valid_face_ratio if vital else None,
                "mean_motion_px": vital.mean_motion_px if vital else None,
            },
        }
        return json.dumps(payload, indent=2).encode("utf-8")

    async def ensure_master_spreadsheet(
        self,
        client: httpx.AsyncClient,
        access_token: str,
    ) -> str:
        """Ensures master Google Sheet exists and row 1 contains canonical headers."""
        headers = {"Authorization": f"Bearer {access_token}"}
        tokens = self.load_saved_tokens() or {}
        spreadsheet_id = settings.GOOGLE_SHEETS_SPREADSHEET_ID or tokens.get("master_spreadsheet_id")

        if not spreadsheet_id:
            create_resp = await self._request_with_retry(
                client,
                "POST",
                SHEETS_BASE_URL,
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "properties": {"title": f"{settings.GOOGLE_DRIVE_ROOT_FOLDER}_MASTER_SHEET"},
                    "sheets": [{"properties": {"title": "Sessions"}}],
                },
            )
            if create_resp.status_code not in (200, 201):
                raise GoogleSyncError(f"Failed creating Master Google Sheet: {create_resp.text}")
            spreadsheet_id = create_resp.json()["spreadsheetId"]
            self.save_tokens({"master_spreadsheet_id": spreadsheet_id})

        # Ensure header row
        range_url = f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/Sessions!A1:AD1"
        get_hdr = await self._request_with_retry(client, "GET", range_url, headers=headers)
        existing_rows = get_hdr.json().get("values", []) if get_hdr.status_code == 200 else []
        if not existing_rows or existing_rows[0] != MASTER_SHEET_HEADERS:
            await self._request_with_retry(
                client,
                "PUT",
                range_url,
                headers={**headers, "Content-Type": "application/json"},
                params={"valueInputOption": "RAW"},
                json={"values": [MASTER_SHEET_HEADERS]},
            )
        return spreadsheet_id

    async def upsert_session_sheet_row(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        spreadsheet_id: str,
        session_obj: MeasurementSession,
        vital: Optional[VitalSignEstimate],
    ) -> None:
        headers = {"Authorization": f"Bearer {access_token}"}
        read_url = f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/Sessions!A:C"
        read_resp = await self._request_with_retry(client, "GET", read_url, headers=headers)
        rows = read_resp.json().get("values", []) if read_resp.status_code == 200 else []

        target_row_index = None
        for idx, row in enumerate(rows, start=1):
            if idx == 1:
                continue
            if len(row) >= 3 and row[2] == session_obj.id:
                target_row_index = idx
                break

        def _drive_link(fid: Optional[str]) -> str:
            return f"https://drive.google.com/file/d/{fid}/view" if fid else ""

        folder_link = (
            f"https://drive.google.com/drive/folders/{session_obj.drive_folder_id}"
            if session_obj.drive_folder_id
            else ""
        )
        now_iso = datetime.now(timezone.utc).isoformat()
        row_values = [
            session_obj.subject_code or "UNASSIGNED",
            session_obj.session_code or session_obj.id[:8],
            session_obj.id,
            session_obj.experimental_condition,
            session_obj.condition_other_detail or "",
            session_obj.activity_duration_min if session_obj.activity_duration_min is not None else "",
            session_obj.ambient_lighting or "",
            session_obj.device_model or "",
            session_obj.started_at.isoformat() if session_obj.started_at else "",
            session_obj.ended_at.isoformat() if session_obj.ended_at else "",
            vital.hr_bpm if (vital and vital.hr_bpm is not None) else "",
            vital.rr_brpm if (vital and vital.rr_brpm is not None) else "",
            vital.spo2_percent if (vital and vital.spo2_percent is not None) else "",
            vital.sbp_mmhg if (vital and vital.sbp_mmhg is not None) else "",
            vital.dbp_mmhg if (vital and vital.dbp_mmhg is not None) else "",
            vital.sqi_score if vital else "",
            vital.sqi_status if vital else "",
            vital.valid_face_ratio if vital else "",
            vital.reference_hr if (vital and vital.reference_hr is not None) else "",
            vital.reference_rr if (vital and vital.reference_rr is not None) else "",
            vital.reference_spo2 if (vital and vital.reference_spo2 is not None) else "",
            vital.reference_sbp if (vital and vital.reference_sbp is not None) else "",
            vital.reference_dbp if (vital and vital.reference_dbp is not None) else "",
            session_obj.monitor_device_name or "",
            bool(vital.is_manual_reference_verified) if vital else False,
            folder_link,
            _drive_link(session_obj.drive_video_file_id),
            _drive_link(session_obj.drive_monitor_image_file_id),
            _drive_link(session_obj.drive_metadata_json_file_id),
            now_iso,
        ]

        if target_row_index:
            update_url = f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/Sessions!A{target_row_index}:AD{target_row_index}"
            resp = await self._request_with_retry(
                client,
                "PUT",
                update_url,
                headers={**headers, "Content-Type": "application/json"},
                params={"valueInputOption": "USER_ENTERED"},
                json={"values": [row_values]},
            )
        else:
            append_url = f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/Sessions!A:AD:append"
            resp = await self._request_with_retry(
                client,
                "POST",
                append_url,
                headers={**headers, "Content-Type": "application/json"},
                params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
                json={"values": [row_values]},
            )

        if resp.status_code not in (200, 201):
            raise GoogleSyncError(f"Failed updating Master Google Sheet ({resp.status_code}): {resp.text}")

    async def sync_session(
        self,
        db: AsyncSession,
        session_id: str,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Synchronizes one complete session hierarchy:
          RPPG_FYP / SUBJECT_XXX / SESSION_XXX / {VIDEO.mp4, MONITOR_IMAGE.jpg, REFERENCE.csv, METADATA.json}
        and upserts its row into the Master Google Sheet.
        """
        s_res = await db.execute(select(MeasurementSession).where(MeasurementSession.id == session_id))
        session_obj = s_res.scalars().first()
        if not session_obj:
            raise GoogleSyncError(f"Session '{session_id}' not found.")

        subject_obj = None
        if session_obj.subject_id:
            subj_res = await db.execute(select(Subject).where(Subject.id == session_obj.subject_id))
            subject_obj = subj_res.scalars().first()

        v_res = await db.execute(select(VitalSignEstimate).where(VitalSignEstimate.session_id == session_id))
        vital_obj = v_res.scalars().first()

        access_token = await self.ensure_valid_access_token()
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        # Prepare file payloads to measure total bytes for accurate progress
        files_to_upload: List[Tuple[str, bytes, str, str]] = []
        if session_obj.storage_path and os.path.exists(session_obj.storage_path):
            if force or not session_obj.drive_video_file_id:
                with open(session_obj.storage_path, "rb") as vf:
                    files_to_upload.append(("VIDEO.mp4", vf.read(), "video/mp4", "video"))

        if session_obj.monitor_image_path and os.path.exists(session_obj.monitor_image_path):
            if force or not session_obj.drive_monitor_image_file_id:
                ext = os.path.splitext(session_obj.monitor_image_path)[1].lower() or ".jpg"
                mime = "image/png" if ext == ".png" else ("image/webp" if ext == ".webp" else "image/jpeg")
                with open(session_obj.monitor_image_path, "rb") as mf:
                    files_to_upload.append((f"MONITOR_IMAGE{ext}", mf.read(), mime, "monitor_image"))

        ref_csv_bytes = self.build_reference_csv_bytes(session_obj, vital_obj)
        meta_json_bytes = self.build_metadata_json_bytes(session_obj, subject_obj, vital_obj)
        files_to_upload.append(("REFERENCE.csv", ref_csv_bytes, "text/csv", "reference_csv"))
        files_to_upload.append(("METADATA.json", meta_json_bytes, "application/json", "metadata_json"))

        total_bytes = sum(len(item[1]) for item in files_to_upload) or 1
        completed_bytes_before_file = 0

        session_obj.drive_sync_status = "UPLOADING"
        session_obj.last_sync_error = None
        await db.commit()

        _UPLOAD_PROGRESS[session_id] = {
            "session_id": session_id,
            "stage": "PREPARING_FOLDERS",
            "percent": 0.0,
            "bytes_uploaded": 0,
            "bytes_total": total_bytes,
            "current_file": None,
        }

        try:
            async with self._client() as client:
                root_id = await self.ensure_drive_folder(
                    client, auth_headers, settings.GOOGLE_DRIVE_ROOT_FOLDER
                )
                subject_folder_name = session_obj.subject_code or "UNASSIGNED_SUBJECT"
                subject_folder_id = (
                    subject_obj.drive_folder_id
                    if (subject_obj and subject_obj.drive_folder_id)
                    else await self.ensure_drive_folder(client, auth_headers, subject_folder_name, root_id)
                )
                if subject_obj and not subject_obj.drive_folder_id:
                    subject_obj.drive_folder_id = subject_folder_id

                session_folder_name = session_obj.session_code or f"SESSION_{session_obj.id[:8]}"
                session_folder_id = (
                    session_obj.drive_folder_id
                    or await self.ensure_drive_folder(client, auth_headers, session_folder_name, subject_folder_id)
                )
                session_obj.drive_folder_id = session_folder_id

                for fname, payload_bytes, mime, kind in files_to_upload:
                    existing_id = {
                        "video": session_obj.drive_video_file_id,
                        "monitor_image": session_obj.drive_monitor_image_file_id,
                        "reference_csv": session_obj.drive_reference_csv_file_id,
                        "metadata_json": session_obj.drive_metadata_json_file_id,
                    }.get(kind)

                    def _on_progress(uploaded_in_file: int, file_total: int, cur_name=fname, base=completed_bytes_before_file):
                        cur_total = base + uploaded_in_file
                        _UPLOAD_PROGRESS[session_id] = {
                            "session_id": session_id,
                            "stage": "UPLOADING",
                            "percent": round(min(95.0, (cur_total / total_bytes) * 95.0), 1),
                            "bytes_uploaded": cur_total,
                            "bytes_total": total_bytes,
                            "current_file": cur_name,
                        }

                    drive_id = await self.upload_bytes_resumable(
                        client=client,
                        access_token=access_token,
                        filename=fname,
                        content_bytes=payload_bytes,
                        mime_type=mime,
                        parent_id=session_folder_id,
                        existing_file_id=existing_id,
                        progress_cb=_on_progress,
                    )
                    completed_bytes_before_file += len(payload_bytes)

                    if kind == "video":
                        session_obj.drive_video_file_id = drive_id
                    elif kind == "monitor_image":
                        session_obj.drive_monitor_image_file_id = drive_id
                    elif kind == "reference_csv":
                        session_obj.drive_reference_csv_file_id = drive_id
                    elif kind == "metadata_json":
                        session_obj.drive_metadata_json_file_id = drive_id

                # Google Sheets Master Sheet Update
                _UPLOAD_PROGRESS[session_id] = {
                    "session_id": session_id,
                    "stage": "UPDATING_SHEET",
                    "percent": 97.0,
                    "bytes_uploaded": total_bytes,
                    "bytes_total": total_bytes,
                    "current_file": "Master Google Sheet",
                }
                sheet_id = await self.ensure_master_spreadsheet(client, access_token)
                await self.upsert_session_sheet_row(client, access_token, sheet_id, session_obj, vital_obj)

            session_obj.drive_sync_status = "SYNCED"
            session_obj.sheets_synced = True
            session_obj.last_sync_error = None
            session_obj.synced_at = datetime.now(timezone.utc)
            await db.commit()

            _UPLOAD_PROGRESS[session_id] = {
                "session_id": session_id,
                "stage": "SYNCED",
                "percent": 100.0,
                "bytes_uploaded": total_bytes,
                "bytes_total": total_bytes,
                "current_file": None,
            }

            return {
                "session_id": session_id,
                "drive_sync_status": "SYNCED",
                "drive_folder_id": session_obj.drive_folder_id,
                "files": {
                    "video_file_id": session_obj.drive_video_file_id,
                    "monitor_image_file_id": session_obj.drive_monitor_image_file_id,
                    "reference_csv_file_id": session_obj.drive_reference_csv_file_id,
                    "metadata_json_file_id": session_obj.drive_metadata_json_file_id,
                },
                "spreadsheet_id": sheet_id,
                "sheets_synced": True,
                "synced_at": session_obj.synced_at.isoformat(),
            }

        except Exception as exc:
            session_obj.drive_sync_status = "FAILED"
            session_obj.last_sync_error = str(exc)
            await db.commit()
            _UPLOAD_PROGRESS[session_id] = {
                "session_id": session_id,
                "stage": "FAILED",
                "percent": _UPLOAD_PROGRESS.get(session_id, {}).get("percent", 0.0),
                "bytes_uploaded": completed_bytes_before_file,
                "bytes_total": total_bytes,
                "error": str(exc),
            }
            raise
