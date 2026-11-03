# Cloud API Documentation: rPPG Vital Signs Monitoring System

Base URL: `http://localhost:8000/api/v1` (or deployed cloud domain)  
Interactive OpenAPI Swagger Docs: `http://localhost:8000/docs`  
Interactive ReDoc: `http://localhost:8000/redoc`

---

## 1. Authentication Endpoints

### 1.1 Register Research Participant
* **Method**: `POST`
* **Endpoint**: `/auth/register`
* **Request Body**:
```json
{
  "email": "researcher@university.edu",
  "password": "SecurePassword123!",
  "full_name": "Dr. Alex Taylor",
  "consent_accepted": true
}
```
* **Response (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "c62b5d03-2fc5-48fa-86c0-67a5bf54a055",
    "email": "researcher@university.edu",
    "full_name": "Dr. Alex Taylor",
    "pseudonym_id": "SUBJ-95A22925",
    "consent_accepted": true,
    "is_active": true,
    "created_at": "2026-11-03T08:16:30Z"
  }
}
```

### 1.2 Sign In (JSON)
* **Method**: `POST`
* **Endpoint**: `/auth/login`
* **Request Body**:
```json
{
  "email": "researcher@university.edu",
  "password": "SecurePassword123!"
}
```

---

## 2. Measurement Endpoints

### 2.1 Initialize Session
* **Method**: `POST`
* **Endpoint**: `/measurements/session`
* **Headers**: `Authorization: Bearer <TOKEN>`
* **Request Body**:
```json
{
  "camera_type": "front_camera",
  "resolution": "1280x720",
  "fps": 30.0
}
```
* **Response**:
```json
{
  "session_id": "848a6062-817c-48c0-bc62-0f56a591aa69",
  "status": "QUEUED",
  "created_at": "2026-11-03T08:17:15Z",
  "message": "Measurement session initialized. Ready for video upload."
}
```

### 2.2 Upload Facial Video
* **Method**: `POST`
* **Endpoint**: `/measurements/upload/{session_id}`
* **Headers**: `Authorization: Bearer <TOKEN>`, `Content-Type: multipart/form-data`
* **Body Form Data**: `video: <FILE_BINARY>` (MP4 / WebM / AVI)

### 2.3 Instant Optical Demo Execution
* **Method**: `POST`
* **Endpoint**: `/measurements/synthetic-demo?target_hr=74.0&target_rr=16.0`
* **Headers**: `Authorization: Bearer <TOKEN>`
* **Response**: Returns complete `DashboardVitalSigns` payload immediately.

### 2.4 Get Measurement Results (4-Card Dashboard)
* **Method**: `GET`
* **Endpoint**: `/measurements/results/{session_id}`
* **Headers**: `Authorization: Bearer <TOKEN>`
* **Response**:
```json
{
  "session_id": "848a6062-817c-48c0-bc62-0f56a591aa69",
  "timestamp": "2026-11-03T08:17:15Z",
  "camera_type": "webcam",
  "status": "COMPLETED",
  "heart_rate": {
    "value": 74.5,
    "unit": "BPM",
    "confidence": 0.83,
    "status": "EXCELLENT",
    "uncertainty_range": "+/- 1.5 BPM"
  },
  "respiratory_rate": {
    "value": 14.3,
    "unit": "BrPM",
    "confidence": 0.62,
    "status": "GOOD",
    "uncertainty_range": "+/- 2.0 BrPM"
  },
  "oxygen_saturation": {
    "value": 85.0,
    "unit": "%",
    "confidence": 0.35,
    "status": "EXPERIMENTAL_UNCALIBRATED",
    "is_experimental": true,
    "disclaimer": "Conventional RGB camera - uncalibrated optical proxy."
  },
  "blood_pressure_sbp": {
    "value": 90.0,
    "unit": "mmHg",
    "confidence": 0.25,
    "status": "EXPERIMENTAL_RESEARCH",
    "is_experimental": true,
    "disclaimer": "ISO 81060-2 experimental research objective."
  },
  "blood_pressure_dbp": {
    "value": 61.0,
    "unit": "mmHg",
    "confidence": 0.25,
    "status": "EXPERIMENTAL_RESEARCH",
    "is_experimental": true,
    "disclaimer": "ISO 81060-2 experimental research objective."
  },
  "signal_quality_score": 0.74,
  "signal_quality_status": "GOOD",
  "motion_stability": 0.88,
  "illumination_stability": 0.92,
  "quality_guidance": "Good signal quality.",
  "rppg_waveform": [-0.021, 0.045, 0.089, ...],
  "frequencies_hz": [0.5, 0.53, 0.56, ...],
  "psd_power": [0.012, 0.045, 0.89, ...]
}
```

---

## 3. Real-Time Streaming & Guidance

### 3.1 Analyze Live Frame
* **Method**: `POST`
* **Endpoint**: `/stream/analyze-frame`
* **Request Body**:
```json
{
  "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ..."
}
```
* **Response**:
```json
{
  "face_detected": true,
  "guidance": "Optimal face position! You may start recording.",
  "quality_score": 0.85,
  "motion_magnitude": 1.2,
  "bbox": [140, 80, 240, 280],
  "zones": {
    "forehead": [180, 95, 160, 45],
    "left_cheek": [160, 200, 60, 50],
    "right_cheek": [260, 200, 60, 50]
  }
}
```

---

## 4. Report Download Endpoints

* `GET /reports/pdf/{session_id}`: Downloads publication-grade biomedical PDF report.
* `GET /reports/csv/{session_id}`: Downloads structured raw measurement CSV.
