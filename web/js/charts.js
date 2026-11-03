/**
 * High-Performance Biomedical Signal Charting Module using HTML5 Canvas.
 * Renders:
 * 1. Filtered rPPG Pulse Waveform with zero-line, grid, and gradient stroke.
 * 2. Welch Power Spectral Density (PSD) with physiological HR band [0.7 - 3.5 Hz].
 */

class BiomedicalCharts {
  /**
   * Renders the reconstructed rPPG cardiac pulse waveform.
   */
  static renderWaveform(canvas, signalData, durationSec = 10.0) {
    if (!canvas || !signalData || signalData.length < 2) return;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Background grid
    ctx.strokeStyle = "rgba(100, 116, 139, 0.15)";
    ctx.lineWidth = 1;
    const gridCols = 8;
    const gridRows = 4;
    for (let c = 1; c < gridCols; c++) {
      const gx = (w / gridCols) * c;
      ctx.beginPath();
      ctx.moveTo(gx, 0);
      ctx.lineTo(gx, h);
      ctx.stroke();
    }
    for (let r = 1; r < gridRows; r++) {
      const gy = (h / gridRows) * r;
      ctx.beginPath();
      ctx.moveTo(0, gy);
      ctx.lineTo(w, gy);
      ctx.stroke();
    }

    // Min and max
    let minVal = Math.min(...signalData);
    let maxVal = Math.max(...signalData);
    const range = maxVal - minVal || 1e-4;
    const padding = 20;

    const getY = (val) => {
      const norm = (val - minVal) / range;
      return h - padding - norm * (h - 2 * padding);
    };

    // Draw baseline
    const zeroY = getY(0);
    ctx.strokeStyle = "rgba(100, 116, 139, 0.35)";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, zeroY);
    ctx.lineTo(w, zeroY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Gradient fill under waveform
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, "rgba(0, 173, 181, 0.35)");
    grad.addColorStop(1, "rgba(0, 173, 181, 0.0)");

    ctx.beginPath();
    const stepX = w / (signalData.length - 1);
    ctx.moveTo(0, getY(signalData[0]));

    for (let i = 1; i < signalData.length; i++) {
      const x = i * stepX;
      const y = getY(signalData[i]);
      ctx.lineTo(x, y);
    }

    // Close path for gradient
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Stroke line
    ctx.beginPath();
    ctx.moveTo(0, getY(signalData[0]));
    for (let i = 1; i < signalData.length; i++) {
      const x = i * stepX;
      const y = getY(signalData[i]);
      ctx.lineTo(x, y);
    }
    ctx.strokeStyle = "#00ADB5";
    ctx.lineWidth = 2.2;
    ctx.stroke();

    // Time label
    ctx.fillStyle = "#94A3B8";
    ctx.font = "11px Outfit, sans-serif";
    ctx.fillText("0.0s", 8, h - 6);
    ctx.fillText(`${durationSec.toFixed(1)}s`, w - 38, h - 6);
  }

  /**
   * Renders the Welch Power Spectral Density (PSD) frequency spectrum.
   */
  static renderPSD(canvas, freqs, psdValues, detectedBPM = null) {
    if (!canvas || !freqs || !psdValues || freqs.length < 2) return;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;

    ctx.clearRect(0, 0, w, h);

    const minF = freqs[0];
    const maxF = freqs[freqs.length - 1];
    const maxP = Math.max(...psdValues) || 1e-6;
    const padding = 20;

    const getX = (f) => ((f - minF) / (maxF - minF)) * (w - 2 * padding) + padding;
    const getY = (p) => h - padding - (p / maxP) * (h - 2 * padding);

    // Physiological cardiac band overlay [0.7 Hz to 3.5 Hz]
    const bandX1 = getX(0.7);
    const bandX2 = getX(3.5);
    ctx.fillStyle = "rgba(0, 173, 181, 0.08)";
    ctx.fillRect(bandX1, 0, Math.max(0, bandX2 - bandX1), h - padding);

    // PSD curve
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, "rgba(59, 130, 246, 0.4)");
    grad.addColorStop(1, "rgba(59, 130, 246, 0.02)");

    ctx.beginPath();
    ctx.moveTo(getX(freqs[0]), h - padding);
    for (let i = 0; i < freqs.length; i++) {
      ctx.lineTo(getX(freqs[i]), getY(psdValues[i]));
    }
    ctx.lineTo(getX(freqs[freqs.length - 1]), h - padding);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    ctx.beginPath();
    for (let i = 0; i < freqs.length; i++) {
      const x = getX(freqs[i]);
      const y = getY(psdValues[i]);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = "#3B82F6";
    ctx.lineWidth = 2.0;
    ctx.stroke();

    // Mark peak frequency if detected
    if (detectedBPM) {
      const peakF = detectedBPM / 60.0;
      const peakX = getX(peakF);
      ctx.strokeStyle = "#10B981";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(peakX, 0);
      ctx.lineTo(peakX, h - padding);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = "#10B981";
      ctx.font = "bold 11px Outfit, sans-serif";
      ctx.fillText(`${detectedBPM.toFixed(0)} BPM`, peakX + 5, 20);
    }

    // Axis labels
    ctx.fillStyle = "#94A3B8";
    ctx.font = "10px Outfit, sans-serif";
    ctx.fillText("0.5 Hz", padding, h - 5);
    ctx.fillText("2.0 Hz", getX(2.0) - 14, h - 5);
    ctx.fillText("3.5 Hz", getX(3.5) - 14, h - 5);
  }
}

window.BiomedicalCharts = BiomedicalCharts;
