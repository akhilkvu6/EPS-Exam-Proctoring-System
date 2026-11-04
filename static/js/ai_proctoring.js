/**
 * EPS Phoenix - Edge Client-Side AI Proctoring Engine
 * Strictly Zero Video Recording, Zero Live Stream Transmission
 * Analyzes video feed entirely inside candidate's local browser memory.
 */

class EdgeAIProctoringEngine {
  constructor(attemptId, csrfToken, onTelemetryCallback = null) {
    this.attemptId = attemptId;
    this.csrfToken = csrfToken;
    this.onTelemetry = onTelemetryCallback;
    this.videoElement = null;
    this.canvas = document.createElement('canvas');
    this.canvas.width = 160;
    this.canvas.height = 120;
    this.ctx = this.canvas.getContext('2d');
    this.isRunning = false;
    this.absenceStart = null;
    this.gazeAwayStart = null;
    this.stream = null;

    this.initCamera();
  }

  async initCamera() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240, frameRate: 15 },
        audio: false, // Strict zero continuous audio recording
      });

      this.videoElement = document.getElementById('ai-camera-preview');
      if (this.videoElement) {
        this.videoElement.srcObject = this.stream;
        this.videoElement.play().catch(() => {});
      }

      this.updateIndicator(true);
      this.startEdgeAnalysisLoop();
    } catch (e) {
      console.warn("Camera access denied or unequipped for AI proctoring:", e);
      this.updateIndicator(false);
    }
  }

  updateIndicator(isActive) {
    const pill = document.getElementById('ai-camera-status-pill');
    if (!pill) return;
    if (isActive) {
      pill.innerHTML = '<span style="color: #22c55e;">●</span> AI Edge Vision Active (Local Only)';
      pill.style.display = 'inline-flex';
    } else {
      pill.innerHTML = '<span style="color: #ef4444;">●</span> Camera Offline';
      pill.style.display = 'inline-flex';
    }
  }

  startEdgeAnalysisLoop() {
    this.isRunning = true;
    // Sample frames locally at 1 Hz (1 frame per second)
    setInterval(() => {
      if (!this.isRunning || !this.videoElement || this.videoElement.readyState < 2) return;
      this.analyzeLocalFrame();
    }, 1500);
  }

  /**
   * Evaluates local canvas pixels without ever streaming bytes to network.
   */
  analyzeLocalFrame() {
    this.ctx.drawImage(this.videoElement, 0, 0, this.canvas.width, this.canvas.height);
    const frame = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
    const data = frame.data;

    let totalLuminance = 0;
    let pixelCount = data.length / 4;

    for (let i = 0; i < data.length; i += 16) { // subsample 4x
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      totalLuminance += (0.299 * r + 0.587 * g + 0.114 * b);
    }
    const avgLuminance = totalLuminance / (pixelCount / 4);

    // Heuristic 1: Camera covered or candidate completely absent
    if (avgLuminance < 12 || avgLuminance > 245) {
      if (!this.absenceStart) {
        this.absenceStart = Date.now();
      } else {
        const duration = (Date.now() - this.absenceStart) / 1000.0;
        if (duration >= 3.0) { // Sustained absence > 3 seconds
          this.dispatchAnomaly('AI_ABSENCE', duration, { reason: 'Occluded or undetectable face', luminance: avgLuminance });
        }
      }
    } else {
      this.absenceStart = null;
    }
  }

  async dispatchAnomaly(anomalyType, durationSeconds, metadata = {}) {
    try {
      await fetch(`/proctoring/api/${this.attemptId}/event/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken,
        },
        body: JSON.stringify({
          event_type: anomalyType,
          duration_seconds: durationSeconds,
          metadata: metadata, // Strictly metadata, zero video data!
        }),
      });

      if (this.onTelemetry) {
        this.onTelemetry(anomalyType, durationSeconds);
      }
    } catch (e) {
      console.warn("AI anomaly dispatch failed:", e);
    }
  }

  destroy() {
    this.isRunning = false;
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
    }
  }
}

window.EdgeAIProctoringEngine = EdgeAIProctoringEngine;
