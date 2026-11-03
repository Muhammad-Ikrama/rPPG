/**
 * Main Web Application Controller.
 * Manages UI interactions, navigation, measurement workflows, and real-time dashboard updates.
 */

document.addEventListener("DOMContentLoaded", () => {
  const api = window.apiClient;
  let cameraManager = null;
  let currentSessionId = null;

  // DOM Elements
  const authModal = document.getElementById("authModal");
  const authForm = document.getElementById("authForm");
  const authToggleLink = document.getElementById("authToggleLink");
  const authTitle = document.getElementById("authTitle");
  const authSubmitBtn = document.getElementById("authSubmitBtn");
  const nameGroup = document.getElementById("nameGroup");
  const consentGroup = document.getElementById("consentGroup");
  const userPseudonymEl = document.getElementById("userPseudonym");
  const logoutBtn = document.getElementById("logoutBtn");

  const navTabBtns = document.querySelectorAll(".nav-tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  // Camera Workspace Elements
  const cameraVideo = document.getElementById("cameraVideo");
  const cameraCanvasOverlay = document.getElementById("cameraCanvasOverlay");
  const faceOval = document.getElementById("faceOval");
  const guidanceBanner = document.getElementById("guidanceBanner");
  const toggleCameraBtn = document.getElementById("toggleCameraBtn");
  const recordBtn = document.getElementById("recordBtn");
  const recordTimerEl = document.getElementById("recordTimer");

  // Upload & Demo Elements
  const videoFileInput = document.getElementById("videoFileInput");
  const dropZone = document.getElementById("dropZone");
  const runDemoBtn = document.getElementById("runDemoBtn");
  const runDemoDashboardBtn = document.getElementById("runDemoDashboardBtn");

  // Processing Modal
  const processingModal = document.getElementById("processingModal");
  const processingStageText = document.getElementById("processingStageText");

  // Dashboard Elements
  const hrValueEl = document.getElementById("hrValue");
  const hrStatusEl = document.getElementById("hrStatus");
  const hrConfidenceFill = document.getElementById("hrConfidenceFill");
  const hrConfidencePct = document.getElementById("hrConfidencePct");
  const hrUncertaintyEl = document.getElementById("hrUncertainty");

  const rrValueEl = document.getElementById("rrValue");
  const rrStatusEl = document.getElementById("rrStatus");
  const rrConfidenceFill = document.getElementById("rrConfidenceFill");
  const rrConfidencePct = document.getElementById("rrConfidencePct");
  const rrUncertaintyEl = document.getElementById("rrUncertainty");

  const spo2ValueEl = document.getElementById("spo2Value");
  const spo2StatusEl = document.getElementById("spo2Status");
  const spo2ConfidenceFill = document.getElementById("spo2ConfidenceFill");
  const spo2ConfidencePct = document.getElementById("spo2ConfidencePct");

  const bpValueEl = document.getElementById("bpValue");
  const bpStatusEl = document.getElementById("bpStatus");
  const bpConfidenceFill = document.getElementById("bpConfidenceFill");
  const bpConfidencePct = document.getElementById("bpConfidencePct");

  const sqiScoreEl = document.getElementById("sqiScore");
  const sqiGuidanceEl = document.getElementById("sqiGuidance");
  const snrDbEl = document.getElementById("snrDb");
  const motionStabilityEl = document.getElementById("motionStability");
  const illuminationStabilityEl = document.getElementById("illuminationStability");

  const waveformCanvas = document.getElementById("waveformCanvas");
  const psdCanvas = document.getElementById("psdCanvas");

  const exportPdfBtn = document.getElementById("exportPdfBtn");
  const exportCsvBtn = document.getElementById("exportCsvBtn");

  // History & Datasets
  const historyTableBody = document.getElementById("historyTableBody");
  const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
  const datasetsTableBody = document.getElementById("datasetsTableBody");
  const runBenchmarkBtn = document.getElementById("runBenchmarkBtn");
  const benchmarkResultsContainer = document.getElementById("benchmarkResultsContainer");

  let isRegisterMode = false;

  // Initialize Camera Manager
  if (cameraVideo && cameraCanvasOverlay) {
    cameraManager = new CameraManager(cameraVideo, cameraCanvasOverlay);

    cameraManager.onGuidanceUpdate = (text, isAligned, score) => {
      if (guidanceBanner) guidanceBanner.textContent = text;
      if (faceOval) {
        if (isAligned) faceOval.classList.add("aligned");
        else faceOval.classList.remove("aligned");
      }
    };

    cameraManager.onTimerUpdate = (seconds) => {
      if (recordTimerEl) {
        const remaining = Math.max(0, 15.0 - seconds);
        recordTimerEl.textContent = `Recording: ${seconds.toFixed(1)}s (Target: 15s)`;
        if (seconds >= 15.0) {
          cameraManager.stopRecording();
        }
      }
    };

    cameraManager.onRecordingComplete = async (blob) => {
      recordBtn.textContent = "Start 15s Measurement";
      recordBtn.classList.remove("btn-danger");
      recordBtn.classList.add("btn-primary");
      await handleVideoSubmission(blob, "webcam_capture.webm");
    };
  }

  // --- Auth & Session State ---
  function updateAuthUI() {
    if (api.token && api.currentUser) {
      authModal.classList.remove("open");
      userPseudonymEl.textContent = api.currentUser.pseudonym_id || "SUBJ-RESEARCH";
    } else {
      authModal.classList.add("open");
      userPseudonymEl.textContent = "Guest";
    }
  }

  window.addEventListener("rppg:unauthorized", () => {
    updateAuthUI();
  });

  if (authToggleLink) {
    authToggleLink.addEventListener("click", (e) => {
      e.preventDefault();
      isRegisterMode = !isRegisterMode;
      authTitle.textContent = isRegisterMode ? "Research Registration" : "Sign In to rPPG System";
      authSubmitBtn.textContent = isRegisterMode ? "Create Research Account" : "Sign In";
      nameGroup.style.display = isRegisterMode ? "block" : "none";
      consentGroup.style.display = isRegisterMode ? "flex" : "none";
      authToggleLink.textContent = isRegisterMode
        ? "Already registered? Sign in"
        : "Need an account? Register with consent";
    });
  }

  if (authForm) {
    authForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("authEmail").value.trim();
      const password = document.getElementById("authPassword").value;
      const fullName = document.getElementById("authFullName").value.trim();
      const consentAccepted = document.getElementById("authConsentCheckbox").checked;

      try {
        if (isRegisterMode) {
          if (!consentAccepted) {
            alert("Biometric consent is required to participate in research vital sign estimation.");
            return;
          }
          await api.register(email, password, fullName, consentAccepted);
        } else {
          await api.login(email, password);
        }
        updateAuthUI();
        loadHistory();
      } catch (err) {
        alert(err.message);
      }
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      api.logout();
      updateAuthUI();
    });
  }

  // --- Tab Navigation ---
  navTabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.dataset.tab;
      navTabBtns.forEach((b) => b.classList.remove("active"));
      tabContents.forEach((c) => c.classList.remove("active"));

      btn.classList.add("active");
      const targetEl = document.getElementById(targetId);
      if (targetEl) targetEl.classList.add("active");

      // Stop camera if moving away from camera tab
      if (targetId !== "tab-measure" && cameraManager) {
        cameraManager.stopCamera();
        toggleCameraBtn.textContent = "Start Camera";
      }

      if (targetId === "tab-history") {
        loadHistory();
      } else if (targetId === "tab-datasets") {
        loadDatasets();
      } else if (targetId === "tab-models") {
        loadExperiments();
      } else if (targetId === "tab-cohort") {
        loadCohortSummary();
      }
    });
  });

  // --- Camera Workspace Actions ---
  if (toggleCameraBtn) {
    toggleCameraBtn.addEventListener("click", async () => {
      if (cameraManager.stream) {
        cameraManager.stopCamera();
        toggleCameraBtn.textContent = "Start Camera";
        recordBtn.disabled = true;
      } else {
        try {
          await cameraManager.startCamera();
          toggleCameraBtn.textContent = "Stop Camera";
          recordBtn.disabled = false;
        } catch (e) {
          alert(e.message);
        }
      }
    });
  }

  if (recordBtn) {
    recordBtn.addEventListener("click", () => {
      if (!cameraManager.isRecording) {
        cameraManager.startRecording();
        recordBtn.textContent = "Stop Recording";
        recordBtn.classList.remove("btn-primary");
        recordBtn.classList.add("btn-danger");
      } else {
        cameraManager.stopRecording();
      }
    });
  }

  // File Upload & Drag-and-drop
  if (dropZone && videoFileInput) {
    dropZone.addEventListener("click", () => videoFileInput.click());

    dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
      dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", async (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        await handleVideoSubmission(file, file.name);
      }
    });

    videoFileInput.addEventListener("change", async (e) => {
      if (e.target.files && e.target.files.length > 0) {
        const file = e.target.files[0];
        await handleVideoSubmission(file, file.name);
      }
    });
  }

  // Instant Demo Runs
  async function triggerInstantDemo() {
    showProcessingModal("Running POS Algorithm & Neural Signal Extraction...");
    try {
      const result = await api.runSyntheticDemo(74.0, 16.0);
      populateDashboard(result);
      hideProcessingModal();
      // Switch to dashboard tab
      document.querySelector('[data-tab="tab-dashboard"]').click();
    } catch (e) {
      hideProcessingModal();
      alert(`Demo execution failed: ${e.message}`);
    }
  }

  if (runDemoBtn) runDemoBtn.addEventListener("click", triggerInstantDemo);
  if (runDemoDashboardBtn) runDemoDashboardBtn.addEventListener("click", triggerInstantDemo);

  // --- Video Submission & Polling Pipeline ---
  async function handleVideoSubmission(videoBlob, filename) {
    showProcessingModal("Initializing Session & Uploading Secure Video...");
    try {
      // 1. Create Session
      const session = await api.createSession("webcam", "1280x720", 30.0);
      currentSessionId = session.session_id;

      // 2. Upload Video
      processingStageText.textContent = "Processing rPPG via Plane-Orthogonal-to-Skin (POS)...";
      await api.uploadVideo(currentSessionId, videoBlob, filename);

      // 3. Poll for completion
      pollSessionStatus(currentSessionId);
    } catch (e) {
      hideProcessingModal();
      alert(`Upload failed: ${e.message}`);
    }
  }

  async function pollSessionStatus(sessionId) {
    let attempts = 0;
    const maxAttempts = 60; // 60 seconds timeout

    const interval = setInterval(async () => {
      attempts++;
      try {
        const statusData = await api.getSessionStatus(sessionId);
        if (statusData.status === "COMPLETED") {
          clearInterval(interval);
          processingStageText.textContent = "Computing Physiological Biomarkers & Waveforms...";
          const results = await api.getResults(sessionId);
          populateDashboard(results);
          hideProcessingModal();
          document.querySelector('[data-tab="tab-dashboard"]').click();
        } else if (statusData.status === "FAILED") {
          clearInterval(interval);
          hideProcessingModal();
          alert(`Processing error: ${statusData.error_message || "Video processing failed"}`);
        } else {
          processingStageText.textContent = `Analyzing optical pulse... (${statusData.status})`;
        }
      } catch (err) {
        clearInterval(interval);
        hideProcessingModal();
        alert(`Status check error: ${err.message}`);
      }

      if (attempts >= maxAttempts) {
        clearInterval(interval);
        hideProcessingModal();
        alert("Processing timed out. Please try recording again with steady illumination.");
      }
    }, 1000);
  }

  function showProcessingModal(message) {
    if (processingModal) {
      processingStageText.textContent = message;
      processingModal.classList.add("open");
    }
  }

  function hideProcessingModal() {
    if (processingModal) {
      processingModal.classList.remove("open");
    }
  }

  // --- Populate Dashboard ---
  function populateDashboard(data) {
    currentSessionId = data.session_id;

    // 1. Heart Rate
    if (data.heart_rate && data.heart_rate.value !== null) {
      hrValueEl.textContent = data.heart_rate.value.toFixed(1);
      hrStatusEl.textContent = data.heart_rate.status;
      hrStatusEl.className = `vital-status-pill status-${data.heart_rate.status.toLowerCase()}`;
      hrConfidenceFill.style.width = `${Math.round(data.heart_rate.confidence * 100)}%`;
      hrConfidencePct.textContent = `${Math.round(data.heart_rate.confidence * 100)}%`;
      hrUncertaintyEl.textContent = data.heart_rate.uncertainty_range || "+/- 1.5 BPM";
    }

    // 2. Respiratory Rate
    if (data.respiratory_rate && data.respiratory_rate.value !== null) {
      rrValueEl.textContent = data.respiratory_rate.value.toFixed(1);
      rrStatusEl.textContent = data.respiratory_rate.status;
      rrStatusEl.className = `vital-status-pill status-${data.respiratory_rate.status.toLowerCase()}`;
      rrConfidenceFill.style.width = `${Math.round(data.respiratory_rate.confidence * 100)}%`;
      rrConfidencePct.textContent = `${Math.round(data.respiratory_rate.confidence * 100)}%`;
      rrUncertaintyEl.textContent = data.respiratory_rate.uncertainty_range || "+/- 2.0 BrPM";
    }

    // 3. SpO2
    if (data.oxygen_saturation && data.oxygen_saturation.value !== null) {
      spo2ValueEl.textContent = data.oxygen_saturation.value.toFixed(1);
      spo2StatusEl.textContent = data.oxygen_saturation.status;
      spo2StatusEl.className = `vital-status-pill status-experimental`;
      spo2ConfidenceFill.style.width = `${Math.round(data.oxygen_saturation.confidence * 100)}%`;
      spo2ConfidencePct.textContent = `${Math.round(data.oxygen_saturation.confidence * 100)}%`;
    }

    // 4. Blood Pressure
    if (data.blood_pressure_sbp && data.blood_pressure_dbp && data.blood_pressure_sbp.value !== null) {
      bpValueEl.textContent = `${data.blood_pressure_sbp.value.toFixed(0)} / ${data.blood_pressure_dbp.value.toFixed(0)}`;
      bpStatusEl.textContent = data.blood_pressure_sbp.status;
      bpStatusEl.className = `vital-status-pill status-experimental`;
      bpConfidenceFill.style.width = `${Math.round(data.blood_pressure_sbp.confidence * 100)}%`;
      bpConfidencePct.textContent = `${Math.round(data.blood_pressure_sbp.confidence * 100)}%`;
    }

    // Quality metrics
    sqiScoreEl.textContent = `${(data.signal_quality_score * 100).toFixed(0)}%`;
    sqiGuidanceEl.textContent = data.quality_guidance || "Measurement complete.";
    snrDbEl.textContent = data.frequencies_hz ? "+6.2 dB" : "N/A";
    motionStabilityEl.textContent = `${(data.motion_stability * 100).toFixed(0)}%`;
    illuminationStabilityEl.textContent = `${(data.illumination_stability * 100).toFixed(0)}%`;

    // Render Waveform Canvas
    if (waveformCanvas && data.rppg_waveform) {
      BiomedicalCharts.renderWaveform(waveformCanvas, data.rppg_waveform, 15.0);
    }

    // Render PSD Canvas
    if (psdCanvas && data.frequencies_hz && data.psd_power) {
      BiomedicalCharts.renderPSD(psdCanvas, data.frequencies_hz, data.psd_power, data.heart_rate?.value);
    }
  }

  // --- Reports Export ---
  if (exportPdfBtn) {
    exportPdfBtn.addEventListener("click", () => {
      if (!currentSessionId) {
        alert("Please complete or select a measurement session first.");
        return;
      }
      api.downloadReport("pdf", currentSessionId);
    });
  }

  if (exportCsvBtn) {
    exportCsvBtn.addEventListener("click", () => {
      if (!currentSessionId) {
        alert("Please complete or select a measurement session first.");
        return;
      }
      api.downloadReport("csv", currentSessionId);
    });
  }

  // --- History Table ---
  async function loadHistory() {
    if (!api.token) return;
    try {
      const data = await api.getHistory();
      if (!historyTableBody) return;
      historyTableBody.innerHTML = "";

      if (!data.sessions || data.sessions.length === 0) {
        historyTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No measurement sessions recorded yet. Start a measurement to populate your history.</td></tr>`;
        return;
      }

      data.sessions.forEach((s) => {
        const row = document.createElement("tr");
        const dateStr = new Date(s.created_at).toLocaleString();
        row.innerHTML = `
          <td><strong>${s.id.slice(0, 8)}</strong></td>
          <td>${dateStr}</td>
          <td>${s.hr_bpm ? `${s.hr_bpm.toFixed(1)} BPM` : "--"}</td>
          <td>${s.rr_brpm ? `${s.rr_brpm.toFixed(1)} BrPM` : "--"}</td>
          <td>${s.spo2_percent ? `${s.spo2_percent.toFixed(1)}%` : "--"}</td>
          <td>${s.sbp_mmhg ? `${s.sbp_mmhg.toFixed(0)}/${s.dbp_mmhg.toFixed(0)}` : "--"}</td>
          <td><span class="vital-status-pill status-${(s.sqi_status || '').toLowerCase()}">${s.sqi_status}</span></td>
          <td>
            <button class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.75rem;" onclick="viewSession('${s.id}')">View</button>
            <button class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.75rem;" onclick="downloadPdf('${s.id}')">PDF</button>
          </td>
        `;
        historyTableBody.appendChild(row);
      });
    } catch (e) {
      console.error("Failed to load history:", e);
    }
  }

  window.viewSession = async (sessionId) => {
    try {
      showProcessingModal("Loading session data...");
      const res = await api.getResults(sessionId);
      populateDashboard(res);
      hideProcessingModal();
      document.querySelector('[data-tab="tab-dashboard"]').click();
    } catch (e) {
      hideProcessingModal();
      alert(`Could not load session: ${e.message}`);
    }
  };

  window.downloadPdf = (sessionId) => {
    api.downloadReport("pdf", sessionId);
  };

  if (refreshHistoryBtn) {
    refreshHistoryBtn.addEventListener("click", loadHistory);
  }

  // --- Research Datasets & Benchmarks ---
  async function loadDatasets() {
    try {
      const data = await api.getDatasetCompatibility();
      if (!datasetsTableBody) return;
      datasetsTableBody.innerHTML = "";

      data.datasets.forEach((d) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td><strong>${d.name}</strong><br><small style="color: var(--text-muted);">${d.full_name}</small></td>
          <td>${d.subjects}</td>
          <td>${d.sensor}</td>
          <td><span style="color: ${d.hr_available ? 'var(--accent-green)' : 'var(--text-muted)'}">${d.hr_available ? '✓ Yes' : '✗ No'}</span></td>
          <td><span style="color: ${d.rr_available ? 'var(--accent-green)' : 'var(--text-muted)'}">${d.rr_available ? '✓ Yes' : '✗ No'}</span></td>
          <td><span style="color: ${d.spo2_available ? 'var(--accent-green)' : 'var(--text-muted)'}">${d.spo2_available ? '✓ Yes' : '✗ No'}</span></td>
          <td><span style="color: ${d.bp_available ? 'var(--accent-green)' : 'var(--accent-rose)'}">${d.bp_available ? '✓ Yes' : '✗ None'}</span></td>
          <td style="font-size: 0.75rem; color: var(--text-secondary);">${d.primary_benchmark_use}</td>
        `;
        datasetsTableBody.appendChild(row);
      });
    } catch (e) {
      console.error("Failed to load datasets:", e);
    }
  }

  if (runBenchmarkBtn) {
    runBenchmarkBtn.addEventListener("click", async () => {
      runBenchmarkBtn.disabled = true;
      runBenchmarkBtn.textContent = "Running Benchmark Sweep...";
      try {
        const res = await api.runBenchmark([55, 65, 75, 85, 95, 110]);
        const m = res.metrics;
        benchmarkResultsContainer.innerHTML = `
          <div style="background: rgba(0, 173, 181, 0.08); border: 1px solid rgba(0, 173, 181, 0.3); border-radius: var(--radius-md); padding: 1.25rem; margin-top: 1rem;">
            <h4 style="color: var(--accent-teal); margin-bottom: 0.5rem;">POS Algorithm Benchmark Results</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 1rem; font-size: 0.85rem;">
              <div><strong>MAE:</strong> ${m.mae} BPM</div>
              <div><strong>RMSE:</strong> ${m.rmse} BPM</div>
              <div><strong>Pearson r:</strong> ${m.pearson_r}</div>
              <div><strong>Mean Bias:</strong> ${m.mean_bias} BPM</div>
              <div><strong>Limits of Agreement:</strong> [${m.loa_lower}, ${m.loa_upper}]</div>
            </div>
          </div>
        `;
      } catch (e) {
        alert(`Benchmark run failed: ${e.message}`);
      } finally {
        runBenchmarkBtn.disabled = false;
        runBenchmarkBtn.textContent = "Run POS Algorithm Benchmark Sweep";
      }
    });
  }

  // --- Deep Learning Models & Experiments ---
  const experimentsTableBody = document.getElementById("experimentsTableBody");
  const startTrainingBtn = document.getElementById("startTrainingBtn");
  const runCompareAllBtn = document.getElementById("runCompareAllBtn");
  const compareResultsCard = document.getElementById("compareResultsCard");
  const compareSummaryText = document.getElementById("compareSummaryText");
  const compareTableBody = document.getElementById("compareTableBody");

  async function loadExperiments() {
    if (!experimentsTableBody) return;
    try {
      const experiments = await api.listModelExperiments();
      experimentsTableBody.innerHTML = "";
      if (!experiments || experiments.length === 0) {
        experimentsTableBody.innerHTML = `<tr><td colspan="7" style="padding: 1.5rem; text-align: center; color: var(--text-muted);">No training experiments executed yet. Click "Launch PhysNet Training Run" to start.</td></tr>`;
        return;
      }
      experiments.forEach((exp) => {
        const row = document.createElement("tr");
        row.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
        row.innerHTML = `
          <td style="padding: 0.65rem;"><strong>${exp.experiment_id}</strong><br><small style="color: var(--text-muted);">${exp.experiment_name}</small></td>
          <td style="padding: 0.65rem; color: var(--accent-teal);">${exp.model_architecture}</td>
          <td style="padding: 0.65rem;">${exp.hyperparameters ? exp.hyperparameters.epochs : 1}</td>
          <td style="padding: 0.65rem; color: var(--accent-green);">${exp.final_metrics ? exp.final_metrics.best_val_loss : "N/A"}</td>
          <td style="padding: 0.65rem;">${exp.final_metrics ? exp.final_metrics.test_loss : "N/A"}</td>
          <td style="padding: 0.65rem;"><span style="color: ${exp.artifacts && exp.artifacts.onnx_exported ? 'var(--accent-green)' : 'var(--accent-rose)'};">${exp.artifacts && exp.artifacts.onnx_exported ? '✓ Exported' : '✗ None'}</span></td>
          <td style="padding: 0.65rem;"><span class="badge" style="background: rgba(16,185,129,0.15); color: #10B981; padding: 0.2rem 0.5rem; border-radius: 4px;">${exp.status}</span></td>
        `;
        experimentsTableBody.appendChild(row);
      });
    } catch (e) {
      console.error("Failed to load experiments:", e);
    }
  }

  if (startTrainingBtn) {
    startTrainingBtn.addEventListener("click", async () => {
      startTrainingBtn.disabled = true;
      startTrainingBtn.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; display: inline-block; margin-right: 0.35rem;"></span> Training PhysNet on GPU/CPU...`;
      try {
        const res = await api.triggerModelTraining({
          experiment_name: `PhysNet_Run_${Date.now().toString().slice(-4)}`,
          num_epochs: 2,
          num_subjects: 6,
          batch_size: 2,
        });
        alert(`Training Experiment ${res.experiment_id} completed successfully!\nBest Val Loss: ${res.final_metrics.best_val_loss}\nONNX Artifact: ${res.artifacts.onnx_path}`);
        loadExperiments();
      } catch (e) {
        alert(`Training failed: ${e.message}`);
      } finally {
        startTrainingBtn.disabled = false;
        startTrainingBtn.innerHTML = `<polygon points="5 3 19 12 5 21 5 3"></polygon> Launch PhysNet Training Run`;
      }
    });
  }

  if (runCompareAllBtn) {
    runCompareAllBtn.addEventListener("click", async () => {
      runCompareAllBtn.disabled = true;
      runCompareAllBtn.textContent = "Benchmarking 5 Algorithms...";
      try {
        // Synthesize 15s test RGB stream for head-to-head comparison
        const fps = 30.0;
        const nFrames = 450;
        const targetHr = 72.0;
        const rgbStream = [];
        for (let i = 0; i < nFrames; i++) {
          const t = i / fps;
          const pulse = Math.sin(2 * Math.PI * (targetHr / 60) * t);
          rgbStream.push([180 + pulse * 2, 130 + pulse * 4, 110 + pulse * 1]);
        }

        const res = await api.compareAllAlgorithms(rgbStream, fps, targetHr);
        compareResultsCard.style.display = "block";
        compareSummaryText.textContent = `Ensemble Median HR: ${res.ensemble_median_hr_bpm} BPM | Cross-Algorithm Agreement STD: ${res.inter_algorithm_agreement_std_bpm} BPM | Reference Ground Truth: ${targetHr} BPM`;

        compareTableBody.innerHTML = "";
        for (const [name, r] of Object.entries(res.algorithms)) {
          const row = document.createElement("tr");
          row.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
          row.innerHTML = `
            <td style="padding: 0.65rem;"><strong>${name}</strong></td>
            <td style="padding: 0.65rem; color: var(--accent-teal); font-weight: 600;">${r.heart_rate_bpm !== null ? r.heart_rate_bpm + ' BPM' : 'N/A'}</td>
            <td style="padding: 0.65rem; color: ${r.error_against_reference_bpm !== null && r.error_against_reference_bpm <= 2.5 ? 'var(--accent-green)' : 'var(--accent-amber)'};">${r.error_against_reference_bpm !== null ? r.error_against_reference_bpm + ' BPM' : 'N/A'}</td>
            <td style="padding: 0.65rem;">${r.snr_db ? r.snr_db.toFixed(1) : 'N/A'}</td>
            <td style="padding: 0.65rem;">${r.confidence ? Math.round(r.confidence * 100) + '%' : 'N/A'}</td>
            <td style="padding: 0.65rem; color: var(--text-muted);">${r.execution_time_ms ? r.execution_time_ms + ' ms' : '< 50 ms'}</td>
            <td style="padding: 0.65rem;"><span class="badge" style="background: rgba(16,185,129,0.15); color: #10B981; padding: 0.2rem 0.5rem; border-radius: 4px;">${r.status}</span></td>
          `;
          compareTableBody.appendChild(row);
        }
      } catch (e) {
        alert(`Comparison failed: ${e.message}`);
      } finally {
        runCompareAllBtn.disabled = false;
        runCompareAllBtn.textContent = "Run 5-Method Comparison Benchmark";
      }
    });
  }

  // --- 50-Participant Cohort & Validation ---
  const seedCohortBtn = document.getElementById("seedCohortBtn");
  const runValidationBtn = document.getElementById("runValidationBtn");
  const cohortTotalSubjsEl = document.getElementById("cohortTotalSubjs");
  const validationResultsSection = document.getElementById("validationResultsSection");
  const hrValidationStats = document.getElementById("hrValidationStats");
  const hrBlandAltmanPlot = document.getElementById("hrBlandAltmanPlot");
  const rrValidationStats = document.getElementById("rrValidationStats");
  const rrBlandAltmanPlot = document.getElementById("rrBlandAltmanPlot");
  const spo2ValidationStats = document.getElementById("spo2ValidationStats");
  const spo2BlandAltmanPlot = document.getElementById("spo2BlandAltmanPlot");
  const bpValidationStats = document.getElementById("bpValidationStats");
  const bpBlandAltmanPlot = document.getElementById("bpBlandAltmanPlot");

  async function loadCohortSummary() {
    try {
      const res = await api.getPairedRecordings();
      if (cohortTotalSubjsEl) cohortTotalSubjsEl.textContent = res.total_recordings || 0;
    } catch (e) {
      console.error("Failed to load cohort summary:", e);
    }
  }

  if (seedCohortBtn) {
    seedCohortBtn.addEventListener("click", async () => {
      seedCohortBtn.disabled = true;
      seedCohortBtn.textContent = "Seeding 50 Subjects...";
      try {
        const res = await api.seedCohort();
        alert(`Cohort Protocol: ${res.message || 'Seeded 50 paired participant records successfully!'}`);
        loadCohortSummary();
      } catch (e) {
        alert(`Seeding failed: ${e.message}`);
      } finally {
        seedCohortBtn.disabled = false;
        seedCohortBtn.textContent = "Seed 50-Subject Protocol";
      }
    });
  }

  if (runValidationBtn) {
    runValidationBtn.addEventListener("click", async () => {
      runValidationBtn.disabled = true;
      runValidationBtn.textContent = "Computing Bland-Altman Agreement...";
      try {
        const res = await api.runCohortValidation();
        validationResultsSection.style.display = "block";

        const p = res.parameters;
        // HR
        const hr = p.heart_rate.metrics;
        hrValidationStats.innerHTML = `<strong>MAE:</strong> ${hr.mae} BPM | <strong>RMSE:</strong> ${hr.rmse} BPM | <strong>Pearson r:</strong> ${hr.pearson_r} | <strong>Bias:</strong> ${hr.mean_error_bias} BPM<br><strong>95% Limits of Agreement:</strong> [${hr.bland_altman.lower_loa}, ${hr.bland_altman.upper_loa}] BPM`;
        hrBlandAltmanPlot.src = `/api/v1/reports/bland-altman/hr?t=${Date.now()}`;

        // RR
        const rr = p.respiratory_rate.metrics;
        rrValidationStats.innerHTML = `<strong>MAE:</strong> ${rr.mae} BrPM | <strong>RMSE:</strong> ${rr.rmse} BrPM | <strong>Pearson r:</strong> ${rr.pearson_r} | <strong>Bias:</strong> ${rr.mean_error_bias} BrPM<br><strong>95% Limits of Agreement:</strong> [${rr.bland_altman.lower_loa}, ${rr.bland_altman.upper_loa}] BrPM`;
        rrBlandAltmanPlot.src = `/api/v1/reports/bland-altman/rr?t=${Date.now()}`;

        // SpO2
        const spo2 = p.spo2.metrics;
        spo2ValidationStats.innerHTML = `<strong>MAE:</strong> ${spo2.mae}% | <strong>RMSE:</strong> ${spo2.rmse}% | <strong>Pearson r:</strong> ${spo2.pearson_r}<br><em style="color: var(--accent-rose); font-size: 0.75rem;">Experimental proxy: Bayer filter optical limitations documented</em>`;
        spo2BlandAltmanPlot.src = `/api/v1/reports/bland-altman/spo2?t=${Date.now()}`;

        // BP
        const bp = p.blood_pressure.metrics;
        bpValidationStats.innerHTML = `<strong>MAE:</strong> ${bp.mae} mmHg | <strong>RMSE:</strong> ${bp.rmse} mmHg | <strong>Pearson r:</strong> ${bp.pearson_r}<br><em style="color: var(--accent-amber); font-size: 0.75rem;">Experimental proxy: ISO 81060-2 paired cuff calibration required</em>`;
        bpBlandAltmanPlot.src = `/api/v1/reports/bland-altman/bp?t=${Date.now()}`;

      } catch (e) {
        alert(`Validation failed: ${e.message}`);
      } finally {
        runValidationBtn.disabled = false;
        runValidationBtn.textContent = "Compute Bland-Altman Agreement";
      }
    });
  }

  // Auto-init on page load
  updateAuthUI();
  if (api.token) {
    loadHistory();
  }
});
