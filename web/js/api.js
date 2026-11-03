/**
 * rPPG Cloud API Client Module.
 * Integrates with FastAPI backend endpoints under /api/v1/.
 */

class RPPGApiClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl || window.location.origin;
    this.apiPrefix = `${this.baseUrl}/api/v1`;
    this.token = localStorage.getItem("rppg_auth_token") || null;
    this.currentUser = JSON.parse(localStorage.getItem("rppg_user_profile") || "null");
  }

  setToken(token, user = null) {
    this.token = token;
    this.currentUser = user;
    if (token) {
      localStorage.setItem("rppg_auth_token", token);
      if (user) localStorage.setItem("rppg_user_profile", JSON.stringify(user));
    } else {
      localStorage.removeItem("rppg_auth_token");
      localStorage.removeItem("rppg_user_profile");
    }
  }

  getHeaders(isMultipart = false) {
    const headers = {};
    if (!isMultipart) {
      headers["Content-Type"] = "application/json";
    }
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const isMultipart = options.body instanceof FormData;
    const headers = { ...this.getHeaders(isMultipart), ...(options.headers || {}) };
    const url = `${this.apiPrefix}${endpoint}`;

    try {
      const resp = await fetch(url, { ...options, headers });
      if (resp.status === 401) {
        this.setToken(null);
        window.dispatchEvent(new CustomEvent("rppg:unauthorized"));
        throw new Error("Authentication session expired. Please sign in again.");
      }
      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.detail || `Request failed with status ${resp.status}`);
      }
      return await resp.json();
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  }

  // --- Auth Endpoints ---
  async register(email, password, fullName, consentAccepted) {
    const data = await this.request("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        full_name: fullName,
        consent_accepted: consentAccepted,
      }),
    });
    this.setToken(data.access_token, data.user);
    return data;
  }

  async login(email, password) {
    const data = await this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token, data.user);
    return data;
  }

  logout() {
    this.setToken(null);
  }

  async getMe() {
    return await this.request("/auth/me");
  }

  // --- Measurement Endpoints ---
  async createSession(cameraType = "webcam", resolution = "1280x720", fps = 30.0) {
    return await this.request("/measurements/session", {
      method: "POST",
      body: JSON.stringify({ camera_type: cameraType, resolution, fps }),
    });
  }

  async uploadVideo(sessionId, videoBlob, filename = "capture.webm") {
    const formData = new FormData();
    formData.append("video", videoBlob, filename);
    return await this.request(`/measurements/upload/${sessionId}`, {
      method: "POST",
      body: formData,
    });
  }

  async runSyntheticDemo(targetHr = 72.0, targetRr = 16.0) {
    return await this.request(`/measurements/synthetic-demo?target_hr=${targetHr}&target_rr=${targetRr}`, {
      method: "POST",
    });
  }

  async getSessionStatus(sessionId) {
    return await this.request(`/measurements/status/${sessionId}`);
  }

  async getResults(sessionId) {
    return await this.request(`/measurements/results/${sessionId}`);
  }

  async getHistory() {
    return await this.request("/measurements/history");
  }

  async deleteSession(sessionId) {
    return await this.request(`/measurements/${sessionId}`, { method: "DELETE" });
  }

  // --- Real-time Streaming & Positioning ---
  async analyzeFrame(base64Image) {
    return await this.request("/stream/analyze-frame", {
      method: "POST",
      body: JSON.stringify({ image_base64: base64Image }),
    });
  }

  // --- Reports ---
  getPdfReportUrl(sessionId) {
    return `${this.apiPrefix}/reports/pdf/${sessionId}?token=${this.token || ""}`;
  }

  getCsvReportUrl(sessionId) {
    return `${this.apiPrefix}/reports/csv/${sessionId}?token=${this.token || ""}`;
  }

  async downloadReport(type, sessionId) {
    const url = `${this.apiPrefix}/reports/${type}/${sessionId}`;
    const resp = await fetch(url, { headers: this.getHeaders() });
    if (!resp.ok) throw new Error(`Report generation failed`);
    const blob = await resp.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = `rppg_report_${sessionId.slice(0, 8)}.${type}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(blobUrl);
  }

  // --- Datasets & Benchmarks ---
  async getDatasetCompatibility() {
    return await this.request("/datasets/compatibility");
  }

  async runBenchmark(bpmValues = [55, 68, 75, 88, 102, 120]) {
    return await this.request("/datasets/benchmark-run", {
      method: "POST",
      body: JSON.stringify({ test_bpm_values: bpmValues, snr_db: 10.0, duration_sec: 15.0 }),
    });
  }
}

window.apiClient = new RPPGApiClient();
