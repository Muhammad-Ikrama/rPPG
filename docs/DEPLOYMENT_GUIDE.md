# Deployment Guide: Complete Cross-Platform rPPG Monitoring System

This guide outlines deployment procedures for the Python FastAPI Cloud Backend, PostgreSQL Database, Web Application, Android APK/AAB builds, and iOS build configurations.

---

## 1. Cloud Backend & Database Deployment

### Option A: Docker Compose (Production Environment)
The easiest way to spin up the entire production environment with PostgreSQL 16 and FastAPI is using `docker-compose.yml`:

```bash
# From repository root
docker-compose up -d --build
```
This initializes:
* **PostgreSQL 16**: listening on `localhost:5432` with persistent data volume `postgres_data`.
* **FastAPI Backend & rPPG Processing Engine**: listening on `http://localhost:8000`.
* **Static Web Dashboard**: automatically mounted and accessible at `http://localhost:8000/app/index.html`.

### Option B: Local Development Run (Zero-Docker / Fast Run)
The backend automatically falls back to an asynchronous SQLite database (`rppg_local.db`) if PostgreSQL is not active:

```bash
# 1. Activate virtual environment
cd backend
.venv\Scripts\activate      # Windows
# or source .venv/bin/activate (Linux/macOS)

# 2. Run backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Access the web application at: `http://localhost:8000/app/index.html`  
Access API documentation at: `http://localhost:8000/docs`

---

## 2. Android Mobile Application Deployment

The Flutter mobile application is located under `mobile/`.

### 2.1 Install Dependencies
```bash
cd mobile
flutter pub get
```

### 2.2 Configure Backend Server URL
In `mobile/lib/services/api_service.dart` or via the mobile **Settings Screen**:
* **Android Emulator**: `http://10.0.2.2:8000`
* **Physical Device (Local Wi-Fi)**: `http://<YOUR_PC_LOCAL_IP>:8000`
* **Cloud Production**: `https://your-api-domain.com`

### 2.3 Build Installable Android APK

#### Method 1: 100% Free Cloud Build via GitHub Actions (Recommended - No Local Tools Needed)
The project includes a ready-to-run GitHub Actions workflow in [`.github/workflows/build_apk.yml`](file:///d:/BME/FYP/.github/workflows/build_apk.yml):
1. Push your repository to GitHub (`git push origin master`).
2. Go to your repository on GitHub and click the **Actions** tab.
3. Select **Build Android APK (rPPG Vital Signs)** and click **Run workflow**.
4. Once completed (~3 minutes), download the ready-to-install **`rppg-vital-signs-release-apk`** directly from the **Artifacts** section!

#### Method 2: 1-Click Cloud Build via Google Colab & Google Drive
Open [`notebooks/build_flutter_apk_colab.ipynb`](file:///d:/BME/FYP/notebooks/build_flutter_apk_colab.ipynb) in Google Colab:
1. Connects to a free cloud runtime.
2. Automatically installs the Flutter Linux SDK.
3. Compiles `mobile/build/app/outputs/flutter-apk/app-release.apk`.
4. Saves the APK directly to your Google Drive (`RPPG_FYP/mobile_apk/`) and automatically triggers a browser download.

#### Method 3: Local Windows Build (Requires Flutter SDK installed)
If Flutter is installed on your local machine:
```bash
cd mobile
flutter pub get
flutter build apk --release
```
* Output location: `mobile/build/app/outputs/flutter-apk/app-release.apk`
* Transfer and install on any physical Android smartphone (requires Android 5.0+ / API 21+).

### 2.4 Build Release-Ready Android App Bundle (AAB)
For deployment to the Google Play Store:
```bash
flutter build appbundle --release
```
* Output location: `mobile/build/app/outputs/bundle/release/app-release.aab`
* Fully configured with target SDK 34, ProGuard rules, and front-camera permission declarations.

---

## 3. iOS Mobile Application Deployment

### 3.1 Install CocoaPods
```bash
cd mobile/ios
pod install
```

### 3.2 Build Configuration & Signing
1. Open `mobile/ios/Runner.xcworkspace` in Xcode.
2. Select the **Runner** target -> **Signing & Capabilities**.
3. Select your Apple Developer Team and bundle identifier (`com.bme.fyp.rppgVitalSigns`).
4. Ensure camera permissions (`NSCameraUsageDescription`) are verified in `Info.plist`.

### 3.3 Build iOS Application
```bash
cd mobile
flutter build ios --release --no-codesign
```
Or archive directly in Xcode for TestFlight distribution.

---

## 4. Web Application Deployment

The web client (`web/`) is built using standard responsive HTML5, modern Vanilla CSS, and Canvas APIs. It has zero Node.js build dependencies and can be hosted via:
* **The FastAPI Backend**: Directly served at `/app/index.html` (preconfigured in `app/main.py`).
* **Nginx / Apache / Caddy**: Point web root to `d:\BME\FYP\web`.
* **Cloudflare Pages / Vercel / Firebase Hosting**: Upload the `web/` folder directly.

### Camera Permissions for Browsers
Modern web browsers require **HTTPS** (or `localhost`/`127.0.0.1`) to grant camera access via `navigator.mediaDevices.getUserMedia`. Ensure SSL certificates are active when deploying to public domains.
