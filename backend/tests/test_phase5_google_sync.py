"""
Integration Tests for Phase 5: Server-Side Google OAuth 2.0, Drive Resumable Uploads,
Folder Hierarchy, Duplicate Prevention, Progress Tracking, and Master Google Sheet Sync.
Uses httpx.MockTransport to test protocol behavior faithfully without external network calls.
"""

import json
import uuid
import pytest
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.db.session import Base, get_db
import app.models  # noqa: F401
from app.main import app as fastapi_app
from app.models.session import MeasurementSession
from app.models.subject import Subject
from app.models.user import User
from app.models.vital_sign import VitalSignEstimate
from app.core.security import get_password_hash
from app.services.google_sync import GoogleSyncService


@pytest.fixture
def anyio_backend():
    return "asyncio"


class MockGoogleApiState:
    def __init__(self):
        self.folders = []
        self.files = {}
        self.upload_sessions = {}
        self.chunks_received = []
        self.spreadsheet_id = None
        self.sheet_rows = []
        self.id_counter = 1

    def next_id(self, prefix: str) -> str:
        val = f"{prefix}_{self.id_counter}"
        self.id_counter += 1
        return val

    def transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            method = request.method

            # OAuth token refresh / exchange
            if url.startswith("https://oauth2.googleapis.com/token"):
                return httpx.Response(
                    200,
                    json={
                        "access_token": "mock_access_token_xyz",
                        "refresh_token": "mock_refresh_token_secret",
                        "expires_in": 3600,
                    },
                )

            # Drive file/folder search
            if method == "GET" and url.startswith("https://www.googleapis.com/drive/v3/files"):
                q = request.url.params.get("q", "")
                matched = []
                if "folder" in q:
                    for fld in self.folders:
                        if f"name = '{fld['name']}'" in q:
                            parent = fld.get("parent")
                            if parent is None or f"'{parent}' in parents" in q:
                                matched.append({"id": fld["id"], "name": fld["name"]})
                else:
                    for fid, meta in self.files.items():
                        if f"name = '{meta['name']}'" in q and f"'{meta['parent']}' in parents" in q:
                            matched.append({"id": fid, "name": meta["name"]})
                return httpx.Response(200, json={"files": matched})

            # Drive create folder
            if method == "POST" and url.startswith("https://www.googleapis.com/drive/v3/files"):
                body = json.loads(request.content.decode("utf-8"))
                fld_id = self.next_id("folder")
                parent = (body.get("parents") or [None])[0]
                self.folders.append({"id": fld_id, "name": body["name"], "parent": parent})
                return httpx.Response(201, json={"id": fld_id})

            # Drive resumable init (POST or PATCH)
            if url.startswith("https://www.googleapis.com/upload/drive/v3/files"):
                body = json.loads(request.content.decode("utf-8"))
                sess_key = self.next_id("resumable")
                target_id = None
                if method == "PATCH":
                    target_id = request.url.path.split("/")[-1]
                parent = (body.get("parents") or [None])[0]
                self.upload_sessions[sess_key] = {
                    "name": body["name"],
                    "parent": parent,
                    "target_id": target_id,
                    "buffer": bytearray(),
                    "total_expected": int(request.headers.get("X-Upload-Content-Length", "0")),
                }
                return httpx.Response(
                    200,
                    headers={"Location": f"https://upload.mock/session/{sess_key}"},
                )

            # Drive resumable chunk PUT
            if method == "PUT" and url.startswith("https://upload.mock/session/"):
                sess_key = url.split("/")[-1]
                sess = self.upload_sessions[sess_key]
                chunk = request.content
                content_range = request.headers.get("Content-Range", "")
                self.chunks_received.append((sess["name"], content_range, len(chunk)))
                sess["buffer"].extend(chunk)
                if len(sess["buffer"]) < sess["total_expected"]:
                    return httpx.Response(308)
                fid = sess["target_id"] or self.next_id("file")
                self.files[fid] = {
                    "name": sess["name"],
                    "parent": sess["parent"],
                    "bytes": bytes(sess["buffer"]),
                }
                return httpx.Response(201, json={"id": fid})

            # Sheets create
            if method == "POST" and url == "https://sheets.googleapis.com/v4/spreadsheets":
                self.spreadsheet_id = "mock_sheet_001"
                return httpx.Response(200, json={"spreadsheetId": self.spreadsheet_id})

            # Sheets read values
            if method == "GET" and "/values/" in url:
                return httpx.Response(200, json={"values": self.sheet_rows})

            # Sheets write header or update row (PUT)
            if method == "PUT" and "/values/" in url:
                body = json.loads(request.content.decode("utf-8"))
                vals = body.get("values", [])
                if "A1:" in url:
                    if not self.sheet_rows:
                        self.sheet_rows.extend(vals)
                    else:
                        self.sheet_rows[0] = vals[0]
                else:
                    # Extract row index like Sessions!A2:AD2
                    row_num = int(url.split("Sessions!A")[1].split(":")[0])
                    while len(self.sheet_rows) < row_num:
                        self.sheet_rows.append([])
                    self.sheet_rows[row_num - 1] = vals[0]
                return httpx.Response(200, json={"updatedRows": 1})

            # Sheets append row (POST :append)
            if method == "POST" and ":append" in url:
                body = json.loads(request.content.decode("utf-8"))
                self.sheet_rows.extend(body.get("values", []))
                return httpx.Response(200, json={"updates": {"updatedRows": 1}})

            return httpx.Response(404, json={"error": f"Unhandled mock URL {method} {url}"})

        return httpx.MockTransport(handler)


@pytest.mark.anyio
async def test_google_drive_hierarchy_resumable_and_sheets_sync(tmp_path, monkeypatch):
    # Configure temporary secrets and media files
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    client_file = secrets_dir / "google_client_secret.json"
    token_file = secrets_dir / "google_oauth_token.json"
    client_file.write_text(
        json.dumps({"web": {"client_id": "test_cid", "client_secret": "test_csecret_never_leak"}}),
        encoding="utf-8",
    )
    token_file.write_text(
        json.dumps({"access_token": "expired_tok", "refresh_token": "secret_ref_tok", "expires_at": "2020-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRETS_FILE", str(client_file))
    monkeypatch.setattr(settings, "GOOGLE_TOKEN_FILE", str(token_file))
    monkeypatch.setattr(settings, "GOOGLE_SHEETS_SPREADSHEET_ID", None)

    video_path = tmp_path / "VIDEO.mp4"
    video_bytes = b"V" * (300 * 1024)  # 300 KB -> forces >= 2 resumable chunks at 256 KB
    video_path.write_bytes(video_bytes)

    monitor_path = tmp_path / "MONITOR_IMAGE.jpg"
    monitor_path.write_bytes(b"\xff\xd8\xff\xe0" + b"M" * 4096)

    # Set up isolated DB
    sync_db_path = tmp_path / "test_sync.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{sync_db_path.as_posix()}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with TestSessionLocal() as db:
        user = User(
            id=str(uuid.uuid4()),
            email="sync_tester@fyp.edu",
            hashed_password=get_password_hash("Pass1234!"),
            full_name="Sync Tester",
            pseudonym_id="RES-001",
            consent_accepted=True,
        )
        subj = Subject(
            id=str(uuid.uuid4()),
            subject_code="SUBJECT_001",
            created_by_user_id=user.id,
            consent_signed=True,
        )
        sess = MeasurementSession(
            id=str(uuid.uuid4()),
            user_id=user.id,
            subject_id=subj.id,
            subject_code="SUBJECT_001",
            session_code="SESSION_001",
            experimental_condition="Normal Resting",
            storage_path=str(video_path),
            video_filename="VIDEO.mp4",
            video_size_bytes=len(video_bytes),
            monitor_image_path=str(monitor_path),
            monitor_image_filename="MONITOR_IMAGE.jpg",
            status="COMPLETED",
        )
        vital = VitalSignEstimate(
            session_id=sess.id,
            hr_bpm=72.4,
            rr_brpm=15.0,
            sqi_score=0.91,
            sqi_status="EXCELLENT",
            reference_hr=72.0,
            is_manual_reference_verified=True,
        )
        db.add_all([user, subj, sess, vital])
        await db.commit()

        # Verify oauth status never leaks secrets
        status_info = GoogleSyncService.get_oauth_status()
        assert status_info["authorized"] is True
        assert "client_secret" not in json.dumps(status_info)
        assert "secret_ref_tok" not in json.dumps(status_info)

        mock_google = MockGoogleApiState()
        sync_svc = GoogleSyncService(transport=mock_google.transport(), chunk_size=256 * 1024)

        res1 = await sync_svc.sync_session(db, sess.id)
        assert res1["drive_sync_status"] == "SYNCED"
        assert res1["sheets_synced"] is True
        assert res1["files"]["video_file_id"] is not None
        assert res1["files"]["monitor_image_file_id"] is not None
        assert res1["files"]["reference_csv_file_id"] is not None
        assert res1["files"]["metadata_json_file_id"] is not None

        # Verify multi-chunk upload occurred for VIDEO.mp4
        video_chunks = [c for c in mock_google.chunks_received if c[0] == "VIDEO.mp4"]
        assert len(video_chunks) == 2

        # Verify folder hierarchy created: RPPG_FYP -> SUBJECT_001 -> SESSION_001
        folder_names = [f["name"] for f in mock_google.folders]
        assert folder_names == ["RPPG_FYP", "SUBJECT_001", "SESSION_001"]

        # Verify Sheet header + 1 session row
        assert len(mock_google.sheet_rows) == 2
        assert mock_google.sheet_rows[1][0] == "SUBJECT_001"
        assert mock_google.sheet_rows[1][1] == "SESSION_001"

        # Re-sync must reuse folders & update existing sheet row without duplicating
        res2 = await sync_svc.sync_session(db, sess.id, force=False)
        assert len(mock_google.folders) == 3  # no duplicate folders created!
        assert len(mock_google.sheet_rows) == 2  # updated in-place, not duplicated!
        assert res2["files"]["video_file_id"] == res1["files"]["video_file_id"]

    await engine.dispose()
