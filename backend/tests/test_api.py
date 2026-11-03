"""
End-to-End FastAPI Backend and Integration Tests.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import init_db


@pytest.mark.anyio
async def test_health_endpoint():
    """Verify healthcheck endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "POS" in data["engine"]


@pytest.mark.anyio
async def test_dataset_compatibility_endpoint():
    """Verify dataset compatibility matrix returns required benchmark metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/datasets/compatibility")
    assert response.status_code == 200
    data = response.json()
    assert "datasets" in data
    dataset_names = [d["name"] for d in data["datasets"]]
    assert "UBFC-rPPG" in dataset_names
    assert "PURE" in dataset_names
    assert "COHFACE" in dataset_names


@pytest.mark.anyio
async def test_auth_and_synthetic_demo_pipeline():
    """
    Complete end-to-end user workflow test:
    1. Register user with biometric consent.
    2. Obtain JWT token.
    3. Generate synthetic demo session (POS + 4 vitals).
    4. Retrieve full dashboard measurements.
    5. Download CSV report.
    """
    await init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register
        user_email = "biomedical_tester@fyp.edu"
        reg_payload = {
            "email": user_email,
            "password": "SecurePassword123!",
            "full_name": "Biomedical Engineering Researcher",
            "consent_accepted": True,
        }
        reg_resp = await ac.post("/api/v1/auth/register", json=reg_payload)
        if reg_resp.status_code == 400:
            # If already exists from prior test run, log in
            login_resp = await ac.post("/api/v1/auth/login", json={"email": user_email, "password": "SecurePassword123!"})
            assert login_resp.status_code == 200
            token = login_resp.json()["access_token"]
        else:
            assert reg_resp.status_code == 200
            token = reg_resp.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # 2. Synthetic demo session (runs POS, HR, RR, SpO2, BP, SQI)
        demo_resp = await ac.post(
            "/api/v1/measurements/synthetic-demo?target_hr=74.0&target_rr=15.0",
            headers=headers,
        )
        assert demo_resp.status_code == 200
        dashboard_data = demo_resp.json()
        session_id = dashboard_data["session_id"]

        # Validate 4 measurement cards
        hr = dashboard_data["heart_rate"]
        rr = dashboard_data["respiratory_rate"]
        spo2 = dashboard_data["oxygen_saturation"]
        sbp = dashboard_data["blood_pressure_sbp"]
        dbp = dashboard_data["blood_pressure_dbp"]

        assert hr["value"] is not None
        assert abs(hr["value"] - 74.0) < 3.0  # High accuracy POS
        assert hr["unit"] == "BPM"

        assert rr["value"] is not None
        assert abs(rr["value"] - 15.0) < 3.5
        assert rr["unit"] == "BrPM"

        assert spo2["value"] is not None
        assert spo2["is_experimental"] is True

        assert sbp["value"] is not None
        assert dbp["value"] is not None
        assert sbp["is_experimental"] is True

        # Signal quality
        assert dashboard_data["signal_quality_score"] > 0.4

        # Waveforms present
        assert len(dashboard_data["rppg_waveform"]) > 20

        # 3. CSV report generation
        csv_resp = await ac.get(f"/api/v1/reports/csv/{session_id}", headers=headers)
        assert csv_resp.status_code == 200
        assert "rPPG VITAL SIGNS MONITORING SYSTEM" in csv_resp.text

        # 4. History retrieval
        hist_resp = await ac.get("/api/v1/measurements/history", headers=headers)
        assert hist_resp.status_code == 200
        assert hist_resp.json()["total_count"] >= 1
