/**
 * StockSense — Admin System Controls
 *
 * Uses the centralized SystemAPI from services/api.js.
 * Provides loading states, error feedback, and toast notifications.
 */

'use strict';

// ---------------------------------------------------------------------------
// Status display helpers
// ---------------------------------------------------------------------------

function setWorkerStatus(running) {
  const el = document.getElementById('workerStatus');
  if (!el) return;
  el.textContent = running ? 'Running' : 'Stopped';
  el.className = running ? 'badge bg-success' : 'badge bg-secondary';
}

function setDigestStatus(enabled) {
  const el = document.getElementById('digestStatus');
  if (!el) return;
  el.textContent = enabled ? 'Enabled' : 'Disabled';
  el.className = enabled ? 'badge bg-success' : 'badge bg-secondary';
}

// ---------------------------------------------------------------------------
// Load current status
// ---------------------------------------------------------------------------

async function loadStatus() {
  const [workerResult, digestResult] = await Promise.all([
    SystemAPI.getBackgroundStatus(),
    SystemAPI.getDigestStatus(),
  ]);

  if (workerResult.success) {
    setWorkerStatus(workerResult.data.running);
  } else {
    showToast(`Worker status error: ${workerResult.error}`, 'error');
  }

  if (digestResult.success) {
    setDigestStatus(digestResult.data.digest_email_enabled);
  } else {
    showToast(`Digest status error: ${digestResult.error}`, 'error');
  }
}

// ---------------------------------------------------------------------------
// Worker controls
// ---------------------------------------------------------------------------

async function handleWorkerAction(action, btn) {
  setButtonLoading(btn, true, action === 'start' ? 'Starting...' : 'Stopping...');
  const fn = action === 'start' ? SystemAPI.startWorker : SystemAPI.stopWorker;
  const { success, error } = await fn();
  setButtonLoading(btn, false);

  if (success) {
    showToast(`Background worker ${action === 'start' ? 'started' : 'stopped'}.`, 'success');
  } else {
    showToast(`Failed to ${action} worker: ${error}`, 'error');
  }
  await loadStatus();
}

// ---------------------------------------------------------------------------
// Digest controls
// ---------------------------------------------------------------------------

async function handleDigestAction(action, btn) {
  setButtonLoading(btn, true, action === 'enable' ? 'Enabling...' : 'Disabling...');
  const fn = action === 'enable' ? SystemAPI.enableDigest : SystemAPI.disableDigest;
  const { success, error } = await fn();
  setButtonLoading(btn, false);

  if (success) {
    showToast(`Digest emails ${action === 'enable' ? 'enabled' : 'disabled'}.`, 'success');
  } else {
    showToast(`Failed to ${action} digest: ${error}`, 'error');
  }
  await loadStatus();
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

window.addEventListener('load', () => {
  loadStatus();

  const startBtn   = document.getElementById('startWorker');
  const stopBtn    = document.getElementById('stopWorker');
  const enableBtn  = document.getElementById('enableDigest');
  const disableBtn = document.getElementById('disableDigest');

  if (startBtn)   startBtn.addEventListener('click',   () => handleWorkerAction('start',   startBtn));
  if (stopBtn)    stopBtn.addEventListener('click',    () => handleWorkerAction('stop',    stopBtn));
  if (enableBtn)  enableBtn.addEventListener('click',  () => handleDigestAction('enable',  enableBtn));
  if (disableBtn) disableBtn.addEventListener('click', () => handleDigestAction('disable', disableBtn));
});

