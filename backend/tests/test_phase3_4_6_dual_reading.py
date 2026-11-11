"""
Integration Tests for Phase 3 (Dual Reading Collection), Phase 4 (Subject-Wise Data),
and Phase 6 (Experimental Condition Form).
"""

import io
import uuid
import pytest
import httpx
from PIL import Image
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.db.session import Base, get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_client(tmp_path):
    db_path = tmp_path / "test_dual.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    transport = httpx.ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


async def _register_and_auth(client: httpx.AsyncClient) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"researcher_{uuid.uuid4().hex[:6]}@fyp.edu",
            "password": "StrongPassword123!",
            "full_name": "Dr. Researcher",
            "consent_accepted": True,
            "device_id": "dev-1",
        },
    )
    assert resp.status_code in (200, 201)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_valid_jpeg_bytes(width: int = 120, height: int = 90) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(20, 40, 80))
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.anyio
async def test_subject_sequence_and_consent_enforcement(async_client):
    headers = await _register_and_auth(async_client)

    # Unconsented subject must be rejected
    bad = await async_client.post(
        "/api/v1/subjects",
        json={"age": 24, "gender": "Male", "fitzpatrick_skin_type": 3, "consent_signed": False},
        headers=headers,
    )
    assert bad.status_code == 400

    # First valid subject -> SUBJECT_001
    s1 = await async_client.post(
        "/api/v1/subjects",
        json={"age": 24, "gender": "Male", "fitzpatrick_skin_type": 3, "consent_signed": True},
        headers=headers,
    )
    assert s1.status_code == 201
    assert s1.json()["subject_code"] == "SUBJECT_001"

    # Second valid subject -> SUBJECT_002
    s2 = await async_client.post(
        "/api/v1/subjects",
        json={"age": 28, "gender": "Female", "fitzpatrick_skin_type": 4, "consent_signed": True},
        headers=headers,
    )
    assert s2.status_code == 201
    assert s2.json()["subject_code"] == "SUBJECT_002"

    list_resp = await async_client.get("/api/v1/subjects", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2


@pytest.mark.anyio
async def test_idempotent_sessions_conditions_and_dual_channel_b(async_client, tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "MONITOR_IMAGES_DIR", str(tmp_path / "mon"))
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "vid"))
    import os
    os.makedirs(settings.MONITOR_IMAGES_DIR, exist_ok=True)
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)

    headers = await _register_and_auth(async_client)

    subj = await async_client.post(
        "/api/v1/subjects",
        json={"age": 22, "gender": "Female", "fitzpatrick_skin_type": 2, "consent_signed": True},
        headers=headers,
    )
    subject_code = subj.json()["subject_code"]

    # 'Other' without detail must fail validation (422)
    other_bad = await async_client.post(
        "/api/v1/measurements/session",
        json={"subject_id": subject_code, "experimental_condition": "Other"},
        headers=headers,
    )
    assert other_bad.status_code == 422

    # Idempotent session 1
    client_key = str(uuid.uuid4())
    sess1 = await async_client.post(
        "/api/v1/measurements/session",
        json={
            "subject_id": subject_code,
            "client_session_id": client_key,
            "experimental_condition": "Immediately After Exercise",
            "activity_duration_min": 5.0,
            "ambient_lighting": "Bright Daylight",
            "device_model": "Pixel 7",
            "device_os": "Android 14",
            "consent_verified": True,
        },
        headers=headers,
    )
    assert sess1.status_code == 200
    d1 = sess1.json()
    assert d1["session_code"] == "SESSION_001"
    assert d1["subject_code"] == subject_code
    assert d1["is_duplicate"] is False

    # Retry with same client_session_id must NOT duplicate
    sess1_dup = await async_client.post(
        "/api/v1/measurements/session",
        json={
            "subject_id": subject_code,
            "client_session_id": client_key,
            "experimental_condition": "Immediately After Exercise",
        },
        headers=headers,
    )
    assert sess1_dup.status_code == 200
    assert sess1_dup.json()["session_id"] == d1["session_id"]
    assert sess1_dup.json()["is_duplicate"] is True

    # Second session for same subject -> SESSION_002
    sess2 = await async_client.post(
        "/api/v1/measurements/session",
        json={
            "subject_id": subject_code,
            "experimental_condition": "After Exercise Recovery",
            "activity_duration_min": 10.0,
        },
        headers=headers,
    )
    assert sess2.status_code == 200
    assert sess2.json()["session_code"] == "SESSION_002"

    session_id = d1["session_id"]

    # Channel B monitor image: corrupt bytes rejected
    corrupt = await async_client.post(
        f"/api/v1/measurements/{session_id}/monitor-image",
        files={"image": ("corrupt.jpg", b"not-a-real-image" * 30, "image/jpeg")},
        headers=headers,
    )
    assert corrupt.status_code == 400

    # Channel B valid monitor image accepted
    jpg_bytes = _make_valid_jpeg_bytes()
    mon_ok = await async_client.post(
        f"/api/v1/measurements/{session_id}/monitor-image",
        files={"image": ("monitor_capture.jpg", jpg_bytes, "image/jpeg")},
        data={"monitor_device_name": "Mindray iPM12"},
        headers=headers,
    )
    assert mon_ok.status_code == 200
    assert mon_ok.json()["format"] == "JPEG"

    # Channel B manual reference entry: inverted BP rejected
    bp_bad = await async_client.post(
        f"/api/v1/measurements/{session_id}/reference-readings",
        json={"hr_bpm": 108.0, "sbp_mmhg": 80.0, "dbp_mmhg": 120.0},
        headers=headers,
    )
    assert bp_bad.status_code == 422

    # Channel B valid manual reference readings accepted
    ref_ok = await async_client.post(
        f"/api/v1/measurements/{session_id}/reference-readings",
        json={
            "hr_bpm": 108.0,
            "rr_brpm": 22.0,
            "spo2_percent": 98.0,
            "sbp_mmhg": 134.0,
            "dbp_mmhg": 84.0,
            "monitor_device_name": "Mindray iPM12",
            "operator_notes": "Recorded immediately after 5-min stair climb.",
        },
        headers=headers,
    )
    assert ref_ok.status_code == 200
    assert ref_ok.json()["is_manual_reference_verified"] is True

    # Summary check
    summary = await async_client.get(f"/api/v1/measurements/{session_id}/summary", headers=headers)
    assert summary.status_code == 200
    s_data = summary.json()
    assert s_data["subject_code"] == "SUBJECT_001"
    assert s_data["session_code"] == "SESSION_001"
    assert s_data["has_monitor_image"] is True
    assert s_data["manual_reference"]["hr_bpm"] == 108.0
    assert s_data["manual_reference"]["sbp_mmhg"] == 134.0

    # Subject detail includes both sessions
    subj_detail = await async_client.get(f"/api/v1/subjects/{subject_code}", headers=headers)
    assert subj_detail.status_code == 200
    assert subj_detail.json()["session_count"] == 2
