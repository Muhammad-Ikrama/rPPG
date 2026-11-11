# Changelog

All notable changes, audits, repairs, and validation updates for the **rPPG Non-Contact Vital Sign Monitoring System** are documented in this file.

## [1.1.0-alpha] - Phase 1 & Phase 2 Foundation (In Progress)
### Audited (Phase 1)
- Completed full repository code audit across `backend/`, `mobile/`, `web/`, `notebooks/`, and `storage/`.
- Identified MediaPipe 1.2.0 breaking API change (`mp.solutions` removed, causing `FaceROIExtractor.use_mediapipe` to silently stay `False` and fall back to OpenCV Haar).
- Identified relative SQLite/storage path drift between root `rppg_local.db` and `backend/rppg_local.db`.
- Identified synthetic prediction noise in `backend/app/api/cohort.py::run_cohort_validation`.
- Identified offline mock/placeholder `RPPGEngine` and hardcoded accounts in `mobile/lib/services/local_storage_service.dart` (to be replaced with real backend API integration + genuine local offline upload queue).

### Added & Changed (Phase 2)
- Anchored all backend SQLite and storage directories canonically to `PROJECT_ROOT` in `backend/app/core/config.py`.
- Added non-destructive SQLite schema migration helper `_sync_sqlite_migrate` in `backend/app/db/session.py`.
- Added ORM models for `RefreshToken` (multi-device rotation + revocation), `Subject` (`SUBJECT_XXX`), and extended `MeasurementSession` and `VitalSignEstimate` schemas for Dual Reading (Camera + Patient Monitor), Experimental Condition Form (10 conditions), and Google Drive/Sheets tracking.
- Implemented multi-device JWT authentication (`/auth/register`, `/auth/login`, `/auth/refresh` with replay protection, `/auth/logout`, `/auth/logout-all`, `/auth/devices`, explicit `X-Token-Status: EXPIRED` handling).
- Added `.gitignore` protections for `secrets/` and `.env` files.
- Added integration test suite `backend/tests/test_phase2_auth.py`.
