/* -----------------------------------------------------------------------
 * admin_system.js – StockSense System Admin UI
 * Handles background-worker controls, daily-digest toggle, and the
 * live External Integrations status panel.
 * ----------------------------------------------------------------------- */

// -------------------------------------------------------------------------
// Background worker + digest helpers
// -------------------------------------------------------------------------
async function loadStatus() {
  try {
    const res = await fetch('/api/system/background-status');
    const data = await res.json();
    document.getElementById('workerStatus').innerText = data.running ? 'Running' : 'Stopped';
  } catch (_) {
    document.getElementById('workerStatus').innerText = 'Unknown';
  }

  try {
    const dres = await fetch('/api/system/digest/status');
    const ddata = await dres.json();
    document.getElementById('digestStatus').innerText = ddata.digest_email_enabled ? 'Enabled' : 'Disabled';
  } catch (_) {
    document.getElementById('digestStatus').innerText = 'Unknown';
  }
}

// -------------------------------------------------------------------------
// Integration status helpers
// -------------------------------------------------------------------------

/**
 * Build a Bootstrap grid card for one integration entry.
 * @param {Object} integration - { name, key, online, detail, checked_at }
 * @returns {HTMLElement}
 */
function buildIntegrationCard(integration) {
  const col = document.createElement('div');
  col.className = 'col-12 col-sm-6 col-lg-4';

  const onlineBadge = integration.online
    ? '<span class="badge bg-success badge-status">● Online</span>'
    : '<span class="badge bg-danger badge-status">● Offline</span>';

  col.innerHTML = `
    <div class="card integration-card h-100 border-${integration.online ? 'success' : 'danger'}" style="border-width:2px;">
      <div class="card-body p-3">
        <div class="d-flex justify-content-between align-items-start mb-1">
          <strong class="me-2">${escapeHtml(integration.name)}</strong>
          ${onlineBadge}
        </div>
        <p class="detail-text mb-0">${escapeHtml(integration.detail || '')}</p>
      </div>
    </div>`;
  return col;
}

/** Minimal HTML-escape to prevent XSS in dynamic content. */
function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/** Fetch integration statuses from the backend and render them. */
async function loadIntegrations() {
  const loadingEl  = document.getElementById('integrationsLoading');
  const errorEl    = document.getElementById('integrationsError');
  const gridEl     = document.getElementById('integrationsGrid');
  const checkedEl  = document.getElementById('integrationsCheckedAt');
  const refreshBtn = document.getElementById('refreshIntegrations');

  // Show spinner, hide previous results
  loadingEl.classList.remove('d-none');
  errorEl.classList.add('d-none');
  gridEl.classList.add('d-none');
  checkedEl.classList.add('d-none');
  if (refreshBtn) refreshBtn.disabled = true;

  try {
    const res = await fetch('/api/system/integrations/status');
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    const data = await res.json();

    // Render cards
    gridEl.innerHTML = '';
    (data.integrations || []).forEach(integration => {
      gridEl.appendChild(buildIntegrationCard(integration));
    });

    // Show checked-at timestamp
    if (data.checked_at) {
      const ts = new Date(data.checked_at);
      checkedEl.textContent = `Last checked: ${ts.toLocaleString()}`;
      checkedEl.classList.remove('d-none');
    }

    loadingEl.classList.add('d-none');
    gridEl.classList.remove('d-none');
  } catch (err) {
    loadingEl.classList.add('d-none');
    errorEl.textContent = `Failed to load integration status: ${err.message}`;
    errorEl.classList.remove('d-none');
  } finally {
    if (refreshBtn) refreshBtn.disabled = false;
  }
}

// -------------------------------------------------------------------------
// Bootstrap event listeners on page load
// -------------------------------------------------------------------------
window.addEventListener('load', () => {
  // Initial status loads
  loadStatus();
  loadIntegrations();

  // Background worker controls
  document.getElementById('startWorker').addEventListener('click', async () => {
    await fetch('/api/system/background_worker/start', { method: 'POST' });
    loadStatus();
  });
  document.getElementById('stopWorker').addEventListener('click', async () => {
    await fetch('/api/system/background_worker/stop', { method: 'POST' });
    loadStatus();
  });

  // Digest email controls
  document.getElementById('enableDigest').addEventListener('click', async () => {
    await fetch('/api/system/digest/enable', { method: 'POST' });
    loadStatus();
  });
  document.getElementById('disableDigest').addEventListener('click', async () => {
    await fetch('/api/system/digest/disable', { method: 'POST' });
    loadStatus();
  });

  // Manual refresh button for integrations panel
  document.getElementById('refreshIntegrations').addEventListener('click', loadIntegrations);

  // Auto-refresh integrations every 60 seconds
  setInterval(loadIntegrations, 60000);
});

