/**
 * EPS Examination Proctoring Engine
 * Monitored capabilities: WebRTC Camera, Computer Vision Face Presence & Multiple-Face Detection,
 * Audio Spikes (Decibels), Tab Visibility, Fullscreen Lockdown, Clipboard Interception,
 * and Restricted Keystrokes.
 */

class ProctoringEngine {
    constructor(config) {
        this.attemptId = config.attemptId;
        this.logUrl = config.logUrl;
        this.csrfToken = config.csrfToken;
        this.cameraRequired = config.cameraRequired || 'disabled';
        this.microphoneRequired = config.microphoneRequired || 'disabled';
        this.fullscreenRequired = config.fullscreenRequired || false;
        this.blockTabSwitch = config.blockTabSwitch || false;
        this.blockCopyPaste = config.blockCopyPaste || false;
        this.faceDetectionEnabled = (config.faceDetectionEnabled !== false);
        this.maxWarnings = config.maxWarnings || 3;

        this.warningCount = 0;
        this.videoElement = document.getElementById('proctor-camera-preview');
        this.warningCountBadge = document.getElementById('proctor-warning-count');
        this.faceStatusBadge = document.getElementById('proctor-face-badge');
        this.stream = null;
        this.audioContext = null;

        // Computer Vision Face Monitoring State
        this.faceDetector = null;
        this.faceCheckInterval = null;
        this.consecutiveAbsentTicks = 0;
        this.consecutiveMultiTicks = 0;
        this.lastFaceWarningTime = 0;

        this.init();
    }

    init() {
        if (this.cameraRequired !== 'disabled') {
            this.initCamera();
        }
        if (this.microphoneRequired !== 'disabled') {
            this.initMicrophone();
        }
        if (this.fullscreenRequired) {
            this.initFullscreen();
        }
        if (this.blockTabSwitch) {
            this.initTabVisibility();
        }
        if (this.blockCopyPaste) {
            this.initClipboardBlocking();
        }
        this.initKeyInterceptor();
        this.initNetworkMonitoring();
    }

    initCamera() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.logEvent('camera_interrupted', 'high', 'Camera not supported in this browser environment');
            return;
        }

        navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 } },
            audio: (this.microphoneRequired !== 'disabled')
        })
        .then(stream => {
            this.stream = stream;
            if (this.videoElement) {
                this.videoElement.srcObject = stream;
                this.videoElement.play().catch(() => {});
            }

            stream.getVideoTracks().forEach(track => {
                track.onended = () => {
                    this.logEvent('camera_interrupted', 'high', 'Camera stream stopped or disconnected');
                    if (this.faceStatusBadge) {
                        this.faceStatusBadge.textContent = 'Camera Dropped';
                        this.faceStatusBadge.className = 'badge badge-rejected';
                    }
                };
            });

            if (this.faceDetectionEnabled) {
                this.initFaceDetection();
            }
        })
        .catch(err => {
            this.logEvent('camera_interrupted', 'high', `Camera permission denied: ${err.message}`);
            alert('Camera access is mandatory for this proctored examination. Please grant permissions and reload.');
        });
    }

    /**
     * Computer Vision Face Presence & Multiple-Face Detection Engine.
     * Evaluates webcam video frames periodically (every 2.5 seconds).
     * Uses native Chromium FaceDetector if supported, falling back to offscreen
     * canvas chrominance and spatial skin-tone clustering analysis.
     */
    initFaceDetection() {
        if ('FaceDetector' in window) {
            try {
                this.faceDetector = new window.FaceDetector({ fastMode: true, maxDetectedFaces: 5 });
            } catch (e) {
                this.faceDetector = null;
            }
        }

        const offscreenCanvas = document.createElement('canvas');
        offscreenCanvas.width = 160;
        offscreenCanvas.height = 120;
        const offscreenCtx = offscreenCanvas.getContext('2d', { willReadFrequently: true });

        this.faceCheckInterval = setInterval(async () => {
            if (!this.videoElement || this.videoElement.paused || this.videoElement.ended || !this.videoElement.videoWidth) {
                return;
            }

            let detectedFaces = 1;

            if (this.faceDetector) {
                try {
                    const faces = await this.faceDetector.detect(this.videoElement);
                    detectedFaces = faces.length;
                } catch (e) {
                    detectedFaces = this.analyzeCanvasFrame(offscreenCtx, offscreenCanvas);
                }
            } else {
                detectedFaces = this.analyzeCanvasFrame(offscreenCtx, offscreenCanvas);
            }

            this.processFaceResult(detectedFaces);
        }, 2500);
    }

    analyzeCanvasFrame(ctx, canvas) {
        try {
            ctx.drawImage(this.videoElement, 0, 0, canvas.width, canvas.height);
            const frame = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const data = frame.data;
            const totalPixels = canvas.width * canvas.height;

            let totalLuminance = 0;
            let skinPixels = 0;
            let leftSkin = 0;
            let centerSkin = 0;
            let rightSkin = 0;

            for (let i = 0; i < data.length; i += 4) {
                const r = data[i];
                const g = data[i + 1];
                const b = data[i + 2];

                const y = 0.299 * r + 0.587 * g + 0.114 * b;
                totalLuminance += y;

                const cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b;
                const cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b;

                // Typical human skin chrominance cluster in YCbCr
                if (cb >= 77 && cb <= 127 && cr >= 133 && cr <= 173) {
                    skinPixels++;
                    const pixelIdx = i / 4;
                    const x = pixelIdx % canvas.width;
                    if (x < 55) {
                        leftSkin++;
                    } else if (x > 105) {
                        rightSkin++;
                    } else {
                        centerSkin++;
                    }
                }
            }

            const avgLuminance = totalLuminance / totalPixels;
            const skinRatio = skinPixels / totalPixels;

            // Camera is covered, blacked out, or washed out
            if (avgLuminance < 12 || avgLuminance > 248 || skinRatio < 0.025) {
                return 0; // Face missing / not visible
            }

            // Both edges have substantial skin clusters while center is low -> multiple individuals
            if (leftSkin > 350 && rightSkin > 350 && centerSkin < (leftSkin + rightSkin) * 0.35) {
                return 2; // Multiple faces
            }

            return 1; // Single centered examinee verified
        } catch (e) {
            return 1; // Graceful fallback
        }
    }

    processFaceResult(detectedFaces) {
        const now = Date.now();

        if (detectedFaces === 0) {
            this.consecutiveAbsentTicks++;
            this.consecutiveMultiTicks = 0;

            if (this.faceStatusBadge) {
                this.faceStatusBadge.textContent = 'Face Missing';
                this.faceStatusBadge.className = 'badge badge-rejected';
            }

            // Log incident after 2 consecutive checks (~5 seconds of absence)
            if (this.consecutiveAbsentTicks >= 2 && (now - this.lastFaceWarningTime > 12000)) {
                this.lastFaceWarningTime = now;
                this.logEvent('face_not_detected', 'high', 'Candidate face not detected in camera frame');
                this.showWarningAlert('Face Missing', 'Please face the camera directly. Your face is not visible in the frame.');
            }
        } else if (detectedFaces > 1) {
            this.consecutiveMultiTicks++;
            this.consecutiveAbsentTicks = 0;

            if (this.faceStatusBadge) {
                this.faceStatusBadge.textContent = 'Multiple Faces';
                this.faceStatusBadge.className = 'badge badge-rejected';
            }

            // Log incident after 2 consecutive checks
            if (this.consecutiveMultiTicks >= 2 && (now - this.lastFaceWarningTime > 12000)) {
                this.lastFaceWarningTime = now;
                this.logEvent('multiple_faces', 'high', `Multiple faces (${detectedFaces}) detected in camera frame`);
                this.showWarningAlert('Multiple Faces Detected', 'Multiple individuals were detected in your camera frame. Only one candidate is allowed.');
            }
        } else {
            // Normal 1 face verified
            this.consecutiveAbsentTicks = 0;
            this.consecutiveMultiTicks = 0;

            if (this.faceStatusBadge) {
                this.faceStatusBadge.textContent = 'Face Verified';
                this.faceStatusBadge.className = 'badge badge-approved';
            }
        }
    }

    initMicrophone() {
        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;

            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    this.audioContext = new AudioCtx();
                    const analyser = this.audioContext.createAnalyser();
                    const microphone = this.audioContext.createMediaStreamSource(stream);
                    const javascriptNode = this.audioContext.createScriptProcessor(2048, 1, 1);

                    analyser.smoothingTimeConstant = 0.8;
                    analyser.fftSize = 1024;

                    microphone.connect(analyser);
                    analyser.connect(javascriptNode);
                    javascriptNode.connect(this.audioContext.destination);

                    let lastAudioSpikeTime = 0;
                    javascriptNode.onaudioprocess = () => {
                        const array = new Uint8Array(analyser.frequencyBinCount);
                        analyser.getByteFrequencyData(array);
                        let values = 0;
                        for (let i = 0; i < array.length; i++) {
                            values += array[i];
                        }
                        const average = values / array.length;

                        // Visual VU meter indicator
                        const vuBar = document.getElementById('audio-vu-level');
                        if (vuBar) {
                            const pct = Math.min(100, Math.round((average / 100) * 100));
                            vuBar.style.width = `${pct}%`;
                        }

                        // Audio spike threshold
                        if (average > 65) {
                            const now = Date.now();
                            if (now - lastAudioSpikeTime > 10000) {
                                lastAudioSpikeTime = now;
                                this.logEvent('audio_spike', 'low', `High ambient noise detected: level ${Math.round(average)}`);
                            }
                        }
                    };
                })
                .catch(() => {});
        } catch (e) {}
    }

    initFullscreen() {
        const enterFullscreen = () => {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(() => {});
            }
        };

        document.addEventListener('click', enterFullscreen, { once: true });

        document.addEventListener('fullscreenchange', () => {
            if (!document.fullscreenElement) {
                this.logEvent('fullscreen_exit', 'medium', 'Student left fullscreen mode');
                this.showWarningAlert('Fullscreen Exited', 'Please stay in fullscreen mode during the examination.');
                setTimeout(enterFullscreen, 1000);
            }
        });
    }

    initTabVisibility() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.logEvent('tab_switch', 'high', 'Student switched tabs or minimized exam window');
                this.showWarningAlert('Tab Switch Detected', 'Do not switch tabs during your exam. This violation has been recorded.');
            }
        });

        window.addEventListener('blur', () => {
            this.logEvent('window_blur', 'medium', 'Window focus lost');
        });
    }

    initClipboardBlocking() {
        const block = (e, action) => {
            e.preventDefault();
            this.logEvent('copy_paste_attempt', 'medium', `Attempted ${action}`);
            this.showWarningAlert('Action Blocked', `${action} is strictly prohibited during the exam.`);
        };

        document.addEventListener('copy', e => block(e, 'Copy'));
        document.addEventListener('paste', e => block(e, 'Paste'));
        document.addEventListener('cut', e => block(e, 'Cut'));
        document.addEventListener('contextmenu', e => {
            e.preventDefault();
        });
    }

    initKeyInterceptor() {
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && ['c', 'v', 'x', 'a', 'p'].includes(e.key.toLowerCase())) {
                e.preventDefault();
                this.logEvent('copy_paste_attempt', 'low', `Shortcut Ctrl+${e.key.toUpperCase()} pressed`);
            }
            if (e.key === 'F12' || e.key === 'PrintScreen') {
                e.preventDefault();
                this.logEvent('key_violation', 'medium', `Restricted key pressed: ${e.key}`);
            }
        });
    }

    initNetworkMonitoring() {
        window.addEventListener('offline', () => {
            this.logEvent('network_disconnect', 'low', 'Candidate computer went offline');
        });
        window.addEventListener('online', () => {
            this.logEvent('network_restored', 'low', 'Candidate computer reconnected to network');
        });
    }

    logEvent(eventType, severity, details) {
        fetch(this.logUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify({
                event_type: eventType,
                severity: severity,
                details: details
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.warning_count !== undefined) {
                this.warningCount = data.warning_count;
                if (this.warningCountBadge) {
                    this.warningCountBadge.textContent = this.warningCount;
                    if (this.warningCount >= this.maxWarnings) {
                        this.warningCountBadge.style.backgroundColor = 'var(--danger)';
                        this.warningCountBadge.style.color = '#FFFFFF';
                    }
                }
            }
        })
        .catch(() => {});
    }

    showWarningAlert(title, message) {
        const modal = document.getElementById('proctor-alert-modal');
        const titleEl = document.getElementById('proctor-alert-title');
        const msgEl = document.getElementById('proctor-alert-msg');

        if (modal && titleEl && msgEl) {
            titleEl.textContent = title;
            msgEl.textContent = message;
            modal.style.display = 'flex';
        }
    }
}
