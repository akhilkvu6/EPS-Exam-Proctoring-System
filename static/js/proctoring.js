/**
 * EPS Browser Proctoring Engine
 * Monitored capabilities: WebRTC Camera, Audio Spikes, Tab Visibility,
 * Fullscreen Enforcement, Clipboard Interception, and Restricted Keystrokes.
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
        this.maxWarnings = config.maxWarnings || 3;

        this.warningCount = 0;
        this.videoElement = document.getElementById('proctor-camera-preview');
        this.warningCountBadge = document.getElementById('proctor-warning-count');
        this.stream = null;
        this.audioContext = null;

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
            this.logEvent('camera_interrupted', 'high', 'Camera not supported in this browser');
            return;
        }

        navigator.mediaDevices.getUserMedia({ video: true, audio: (this.microphoneRequired !== 'disabled') })
            .then(stream => {
                this.stream = stream;
                if (this.videoElement) {
                    this.videoElement.srcObject = stream;
                }

                stream.getVideoTracks().forEach(track => {
                    track.onended = () => {
                        this.logEvent('camera_interrupted', 'high', 'Camera stream stopped unexpectedly');
                    };
                });
            })
            .catch(err => {
                this.logEvent('camera_interrupted', 'high', `Camera permission denied: ${err.message}`);
                alert('Camera access is required for this exam. Please allow camera permissions.');
            });
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

                        // Audio spike detection
                        if (average > 65) {
                            const now = Date.now();
                            if (now - lastAudioSpikeTime > 8000) {
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
                this.showWarningAlert('Fullscreen Exited', 'Please stay in fullscreen mode during the exam.');
                setTimeout(enterFullscreen, 1000);
            }
        });
    }

    initTabVisibility() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.logEvent('tab_switch', 'high', 'Student switched tabs or minimized exam window');
                this.showWarningAlert('Tab Switch Detected', 'Do not switch tabs during your exam. This has been recorded.');
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
            this.showWarningAlert('Action Blocked', `${action} is not allowed during the exam.`);
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
            this.logEvent('network_disconnect', 'low', 'Computer went offline');
        });
        window.addEventListener('online', () => {
            this.logEvent('network_restored', 'low', 'Computer reconnected to network');
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
