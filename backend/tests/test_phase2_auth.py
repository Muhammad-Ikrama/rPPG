"""
Integration Tests for Phase 2: Multi-Device JWT Authentication, Refresh Rotation,
Replay Protection, Expired Token Detection, and Session Revocation.
"""

from datetime import timedelta
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app as fastapi_app
from app.db.session import Base, get_db
from app.core.security import create_access_token
import app.models  # noqa: F401


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def auth_client(tmp_path):
    db_path = tmp_path / "test_auth.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.anyio
async def test_registration_requires_consent_and_normalizes_email(auth_client: AsyncClient):
    # Consent=False must be rejected
    resp_no_consent = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "Member1@FYP.EDU",
            "password": "StrongPassword123!",
            "full_name": "Member One",
            "consent_accepted": False,
        },
    )
    assert resp_no_consent.status_code == 400

    # Valid registration with normalized email
    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "Member1@FYP.EDU",
            "password": "StrongPassword123!",
            "full_name": "Member One",
            "consent_accepted": True,
            "device_id": "phone-a",
            "device_name": "Pixel 7",
            "platform": "android",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == "member1@fyp.edu"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["device_id"] == "phone-a"


@pytest.mark.anyio
async def test_multi_device_login_refresh_rotation_and_replay_protection(auth_client: AsyncClient):
    # Register on Device A
    reg = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "researcher@fyp.edu",
            "password": "ResearchPassword123!",
            "full_name": "Lead Researcher",
            "consent_accepted": True,
            "device_id": "device-A",
            "device_name": "Galaxy S23",
            "platform": "android",
        },
    )
    assert reg.status_code == 200
    dev_a_tokens = reg.json()

    # Login simultaneously on Device B
    login_b = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": "RESEARCHER@FYP.EDU",
            "password": "ResearchPassword123!",
            "device_id": "device-B",
            "device_name": "OnePlus 12",
            "platform": "android",
        },
    )
    assert login_b.status_code == 200
    dev_b_tokens = login_b.json()
    assert dev_b_tokens["device_id"] == "device-B"
    assert dev_b_tokens["refresh_token"] != dev_a_tokens["refresh_token"]

    # Both devices appear in /auth/devices
    devs = await auth_client.get(
        "/api/v1/auth/devices",
        headers={"Authorization": f"Bearer {dev_b_tokens['access_token']}"},
    )
    assert devs.status_code == 200
    active_ids = {d["device_id"] for d in devs.json() if not d["is_revoked"]}
    assert active_ids == {"device-A", "device-B"}

    # Rotate Device A refresh token
    ref_a = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": dev_a_tokens["refresh_token"], "device_id": "device-A"},
    )
    assert ref_a.status_code == 200
    dev_a_rotated = ref_a.json()
    assert dev_a_rotated["refresh_token"] != dev_a_tokens["refresh_token"]

    # Re-using OLD Device A refresh token triggers replay protection (401)
    # and invalidates Device A without logging out Device B
    replay = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": dev_a_tokens["refresh_token"], "device_id": "device-A"},
    )
    assert replay.status_code == 401

    # Device A's newest token is now also revoked by replay protection
    ref_a_after_replay = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": dev_a_rotated["refresh_token"], "device_id": "device-A"},
    )
    assert ref_a_after_replay.status_code == 401

    # Device B refresh token MUST still work cleanly
    ref_b = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": dev_b_tokens["refresh_token"], "device_id": "device-B"},
    )
    assert ref_b.status_code == 200


@pytest.mark.anyio
async def test_expired_access_token_and_logout(auth_client: AsyncClient):
    reg = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "tester@fyp.edu",
            "password": "TestPassword123!",
            "full_name": "QA Tester",
            "consent_accepted": True,
            "device_id": "dev-1",
        },
    )
    assert reg.status_code == 200
    data = reg.json()
    user_id = data["user"]["id"]

    # Simulate expired access token
    expired_token = create_access_token(user_id, expires_delta=timedelta(seconds=-5))
    me_expired = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert me_expired.status_code == 401
    assert me_expired.headers.get("X-Token-Status") == "EXPIRED"

    # Logout current device
    out = await auth_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {data['access_token']}"},
        json={"refresh_token": data["refresh_token"]},
    )
    assert out.status_code == 200
    assert out.json()["revoked_sessions"] == 1

    # Refresh after logout must fail
    ref_after_logout = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert ref_after_logout.status_code == 401
