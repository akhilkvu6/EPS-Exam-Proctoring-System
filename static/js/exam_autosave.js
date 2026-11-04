/**
 * EPS Phoenix - Dual-Layer Autosave, Offline Resilience & Recovery Engine
 * Section 12 Master Specification Compliant
 */

class ExamAutosaveEngine {
  constructor(attemptId, csrfToken) {
    this.attemptId = attemptId;
    this.csrfToken = csrfToken;
    this.storageKey = `eps_journal_${attemptId}`;
    this.debounceTimeout = null;
    this.isOnline = navigator.onLine;
    this.pendingQueue = this.loadLocalQueue();

    this.initNetworkListeners();
    this.updateStatusBadge();
  }

  loadLocalQueue() {
    try {
      const data = localStorage.getItem(this.storageKey);
      return data ? JSON.parse(data) : {};
    } catch (e) {
      console.warn("Storage access failed:", e);
      return {};
    }
  }

  persistLocalQueue() {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.pendingQueue));
    } catch (e) {
      console.warn("Local storage write error:", e);
    }
  }

  initNetworkListeners() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.updateStatusBadge();
      this.flushPendingSync();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.updateStatusBadge();
    });
  }

  updateStatusBadge(statusText = null, statusType = null) {
    const badge = document.getElementById('network-status-badge');
    if (!badge) return;

    if (statusText) {
      badge.innerText = statusText;
      badge.style.display = 'inline-block';
      return;
    }

    if (this.isOnline) {
      const pendingCount = Object.keys(this.pendingQueue).length;
      if (pendingCount > 0) {
        badge.innerText = `🔄 Syncing (${pendingCount})...`;
        badge.style.backgroundColor = 'rgba(56, 189, 248, 0.15)';
        badge.style.color = '#38bdf8';
      } else {
        badge.innerText = '🟢 Connected & Saved';
        badge.style.backgroundColor = 'rgba(34, 197, 94, 0.15)';
        badge.style.color = '#22c55e';
      }
    } else {
      badge.innerText = '🔴 Offline (Local Buffer Active)';
      badge.style.backgroundColor = 'rgba(239, 68, 68, 0.15)';
      badge.style.color = '#ef4444';
    }
  }

  /**
   * Records candidate answer instantly into Layer 2 (Local Journal)
   * and triggers debounced Layer 1 (Server Sync).
   */
  queueAnswer(questionId, answerPayload, timeSpent = 0) {
    const entry = {
      question_id: questionId,
      answer: answerPayload,
      time_spent_seconds: timeSpent,
      timestamp: Date.now(),
      synced: false,
    };

    // Layer 2: Instant local journal write
    this.pendingQueue[questionId] = entry;
    this.persistLocalQueue();
    this.updateStatusBadge();

    // Layer 1: Debounced network dispatch (600ms)
    clearTimeout(this.debounceTimeout);
    this.debounceTimeout = setTimeout(() => {
      this.dispatchSingleSave(questionId, answerPayload, timeSpent);
    }, 600);
  }

  async dispatchSingleSave(questionId, answerPayload, timeSpent) {
    if (!this.isOnline) {
      return; // Handled later by offline sync
    }

    try {
      const resp = await fetch(`/exam/api/${this.attemptId}/questions/${questionId}/save/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken,
        },
        body: JSON.stringify({
          answer: answerPayload,
          time_spent_seconds: timeSpent,
        }),
      });

      if (resp.ok) {
        delete this.pendingQueue[questionId];
        this.persistLocalQueue();
        this.updateStatusBadge();
      } else if (resp.status === 403) {
        // Expiration or closed session
        console.warn("Save rejected by server (expired or submitted)");
      }
    } catch (e) {
      console.warn("Network dispatch failed, preserved in local journal:", e);
      this.isOnline = false;
      this.updateStatusBadge();
    }
  }

  /**
   * Batch flushes all pending journal entries to the server upon reconnection.
   */
  async flushPendingSync() {
    const keys = Object.keys(this.pendingQueue);
    if (keys.length === 0) {
      this.updateStatusBadge();
      return;
    }

    const updates = keys.map(k => this.pendingQueue[k]);
    this.updateStatusBadge(`🔄 Syncing ${updates.length} items...`);

    try {
      const resp = await fetch(`/exam/api/${this.attemptId}/sync/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken,
        },
        body: JSON.stringify({ updates: updates }),
      });

      if (resp.ok) {
        this.pendingQueue = {};
        this.persistLocalQueue();
        this.updateStatusBadge('🟢 All items synced');
        setTimeout(() => this.updateStatusBadge(), 2500);
      }
    } catch (e) {
      console.warn("Batch sync failed, retaining buffer:", e);
      this.updateStatusBadge('⚠️ Sync deferred (network retry)');
    }
  }
}

// Global instance handle
window.ExamAutosaveEngine = ExamAutosaveEngine;
