/**
 * EPS Phoenix - Browser Integrity & Noise-Filtered Proctoring
 * Section 13 Master Directive Compliant
 */

class BrowserProctoringEngine {
  constructor(attemptId, csrfToken, isStrict = true) {
    this.attemptId = attemptId;
    this.csrfToken = csrfToken;
    this.isStrict = isStrict;
    this.blurStartTime = null;
    this.fullscreenExitStartTime = null;

    if (this.isStrict) {
      this.initFullscreenEnforcement();
      this.initFocusMonitoring();
      this.initClipboardRestrictions();
      this.initKeyRestrictions();
    }
  }

  async sendEvent(eventType, durationSeconds = 0.0, metadata = {}) {
    try {
      await fetch(`/proctoring/api/${this.attemptId}/event/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken,
        },
        body: JSON.stringify({
          event_type: eventType,
          duration_seconds: durationSeconds,
          metadata: metadata,
        }),
      });
    } catch (e) {
      console.warn("Proctoring telemetry dispatch error:", e);
    }
  }

  initFullscreenEnforcement() {
    const handleFullscreenChange = () => {
      const isFullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement);
      const overlay = document.getElementById('fullscreen-warning-overlay');

      if (!isFullscreen) {
        this.fullscreenExitStartTime = Date.now();
        if (overlay) overlay.style.display = 'flex';
      } else {
        if (this.fullscreenExitStartTime) {
          const duration = (Date.now() - this.fullscreenExitStartTime) / 1000.0;
          this.sendEvent('FULLSCREEN_EXIT', duration, { message: 'Fullscreen exited and restored' });
          this.fullscreenExitStartTime = null;
        }
        if (overlay) overlay.style.display = 'none';
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
  }

  initFocusMonitoring() {
    window.addEventListener('blur', () => {
      this.blurStartTime = Date.now();
    });

    window.addEventListener('focus', () => {
      if (this.blurStartTime) {
        const duration = (Date.now() - this.blurStartTime) / 1000.0;
        this.sendEvent('TAB_SWITCH', duration, { message: 'Window focus lost and regained' });
        this.blurStartTime = null;
      }
    });

    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        if (!this.blurStartTime) this.blurStartTime = Date.now();
      } else {
        if (this.blurStartTime) {
          const duration = (Date.now() - this.blurStartTime) / 1000.0;
          this.sendEvent('TAB_SWITCH', duration, { message: 'Tab switched' });
          this.blurStartTime = null;
        }
      }
    });
  }

  initClipboardRestrictions() {
    ['copy', 'cut', 'paste'].forEach(evtName => {
      document.addEventListener(evtName, (e) => {
        // Disallow pasting into answer areas or copying question content
        e.preventDefault();
        const type = (evtName === 'paste') ? 'CLIPBOARD_PASTE' : 'CLIPBOARD_COPY';
        this.sendEvent(type, 0.0, { action: evtName });
      });
    });

    // Disable right click context menu in exam room
    document.addEventListener('contextmenu', (e) => {
      e.preventDefault();
    });
  }

  initKeyRestrictions() {
    document.addEventListener('keydown', (e) => {
      // F12 or Ctrl+Shift+I / Ctrl+Shift+J / Ctrl+U
      if (
        e.key === 'F12' ||
        (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'i' || e.key === 'J' || e.key === 'j')) ||
        (e.ctrlKey && (e.key === 'u' || e.key === 'U'))
      ) {
        e.preventDefault();
        this.sendEvent('DEVTOOLS_ATTEMPT', 0.0, { key: e.key, ctrl: e.ctrlKey, shift: e.shiftKey });
      }
    });
  }
}

window.BrowserProctoringEngine = BrowserProctoringEngine;
