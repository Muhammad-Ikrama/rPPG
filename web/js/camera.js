/**
 * Browser Camera Video Acquisition, Face Guidance, and Recording Module.
 * Camera-independent design supporting laptop webcams, mobile front-facing cameras, and USB cameras.
 */

class CameraManager {
  constructor(videoElement, canvasOverlayElement) {
    this.video = videoElement;
    this.canvas = canvasOverlayElement;
    this.stream = null;
    this.mediaRecorder = null;
    this.recordedChunks = [];
    this.isRecording = false;
    this.recordingStartTime = null;
    this.timerInterval = null;
    this.guidanceInterval = null;

    this.onGuidanceUpdate = null; // Callback (guidanceText, isAligned, qualityScore)
    this.onTimerUpdate = null;    // Callback (secondsElapsed)
    this.onRecordingComplete = null; // Callback (blob)
  }

  async startCamera(facingMode = "user") {
    try {
      if (this.stream) {
        this.stopCamera();
      }

      const constraints = {
        video: {
          facingMode: facingMode,
          width: { ideal: 1280, min: 640 },
          height: { ideal: 720, min: 480 },
          frameRate: { ideal: 30, min: 15 },
        },
        audio: false,
      };

      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.video.srcObject = this.stream;
      await this.video.play();

      this.startFaceGuidanceLoop();
      return true;
    } catch (err) {
      console.error("Camera access failed:", err);
      let errorMsg = "Could not access camera. Please verify camera permissions.";
      if (err.name === "NotAllowedError") errorMsg = "Camera permission denied. Please allow camera access in browser settings.";
      if (err.name === "NotFoundError") errorMsg = "No camera hardware detected on this device.";
      throw new Error(errorMsg);
    }
  }

  stopCamera() {
    this.stopFaceGuidanceLoop();
    if (this.isRecording) {
      this.stopRecording();
    }
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    if (this.video) {
      this.video.srcObject = null;
    }
  }

  startFaceGuidanceLoop() {
    this.stopFaceGuidanceLoop();
    // Sample a frame every 800ms for lightweight, responsive server-side ROI analysis
    this.guidanceInterval = setInterval(() => {
      this.captureAndAnalyzeFrame();
    }, 800);
  }

  stopFaceGuidanceLoop() {
    if (this.guidanceInterval) {
      clearInterval(this.guidanceInterval);
      this.guidanceInterval = null;
    }
  }

  async captureAndAnalyzeFrame() {
    if (!this.video || this.video.readyState < 2 || !window.apiClient) return;

    // Draw video frame to an offscreen canvas
    const offscreen = document.createElement("canvas");
    offscreen.width = 320; // scale down for rapid network transmission
    offscreen.height = 240;
    const ctx = offscreen.getContext("2d");
    ctx.drawImage(this.video, 0, 0, offscreen.width, offscreen.height);

    const base64 = offscreen.toDataURL("image/jpeg", 0.65);

    try {
      const res = await window.apiClient.analyzeFrame(base64);
      if (res && this.canvas) {
        this.renderOverlay(res);
        if (this.onGuidanceUpdate) {
          const isAligned = res.face_detected && res.quality_score >= 0.70;
          this.onGuidanceUpdate(res.guidance, isAligned, res.quality_score);
        }
      }
    } catch (e) {
      // Ignore background transient network hiccups
    }
  }

  renderOverlay(analysisResult) {
    if (!this.canvas || !this.video) return;
    const ctx = this.canvas.getContext("2d");
    const w = this.canvas.width = this.video.videoWidth || 640;
    const h = this.canvas.height = this.video.videoHeight || 480;

    ctx.clearRect(0, 0, w, h);

    if (!analysisResult.face_detected || !analysisResult.bbox) return;

    // Scale from offscreen 320x240 to video dimensions
    const scaleX = w / (analysisResult.frame_width || 320);
    const scaleY = h / (analysisResult.frame_height || 240);

    const [bx, by, bw, bh] = analysisResult.bbox;
    const x = bx * scaleX;
    const y = by * scaleY;
    const width = bw * scaleX;
    const height = bh * scaleY;

    // Draw face bounding box
    ctx.strokeStyle = analysisResult.quality_score > 0.65 ? "#10B981" : "#00ADB5";
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, width, height);

    // Draw ROIs: Forehead, Left Cheek, Right Cheek
    if (analysisResult.zones) {
      ctx.fillStyle = "rgba(0, 173, 181, 0.2)";
      ctx.strokeStyle = "rgba(0, 173, 181, 0.8)";
      ctx.lineWidth = 1.5;

      for (const [zoneName, zBox] of Object.entries(analysisResult.zones)) {
        if (zBox && zBox.length === 4) {
          const [zx, zy, zw, zh] = zBox;
          const rx = zx * scaleX;
          const ry = zy * scaleY;
          const rw = zw * scaleX;
          const rh = zh * scaleY;
          ctx.fillRect(rx, ry, rw, rh);
          ctx.strokeRect(rx, ry, rw, rh);
        }
      }
    }
  }

  startRecording() {
    if (!this.stream) throw new Error("Camera not active");
    this.recordedChunks = [];

    // Choose supported MIME type
    const mimeTypes = [
      "video/webm;codecs=vp8",
      "video/webm;codecs=vp9",
      "video/webm",
      "video/mp4",
    ];
    let selectedMime = mimeTypes.find((m) => MediaRecorder.isTypeSupported(m)) || "";

    const options = selectedMime ? { mimeType: selectedMime } : {};
    this.mediaRecorder = new MediaRecorder(this.stream, options);

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        this.recordedChunks.push(event.data);
      }
    };

    this.mediaRecorder.onstop = () => {
      const blob = new Blob(this.recordedChunks, { type: selectedMime || "video/webm" });
      if (this.onRecordingComplete) {
        this.onRecordingComplete(blob);
      }
    };

    this.mediaRecorder.start(250); // Record chunks every 250ms
    this.isRecording = true;
    this.recordingStartTime = Date.now();

    this.timerInterval = setInterval(() => {
      const elapsed = (Date.now() - this.recordingStartTime) / 1000.0;
      if (this.onTimerUpdate) this.onTimerUpdate(elapsed);
    }, 100);
  }

  stopRecording() {
    if (!this.isRecording) return;
    this.isRecording = false;
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
    }
  }
}

window.CameraManager = CameraManager;
