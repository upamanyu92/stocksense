/**
 * StockSense — Alerts Management
 *
 * Uses the centralized AlertAPI from services/api.js.
 * Provides loading states, error feedback, and toast notifications.
 */

'use strict';

// ---------------------------------------------------------------------------
// Load and render alerts
// ---------------------------------------------------------------------------

async function loadAlerts() {
  const container = document.getElementById('alertsList');
  if (!container) return;

  container.innerHTML = '<span class="text-muted"><i class="fas fa-spinner fa-spin"></i> Loading alerts...</span>';

  const { success, data, error } = await AlertAPI.list();

  if (!success) {
    container.innerHTML = `<div class="text-danger"><i class="fas fa-exclamation-circle"></i> Failed to load alerts: ${error}</div>`;
    return;
  }

  const alerts = (data && data.alerts) ? data.alerts : [];

  if (alerts.length === 0) {
    container.innerHTML = '<p class="text-muted">No alerts configured yet.</p>';
    return;
  }

  const table = document.createElement('table');
  table.className = 'table table-dark table-striped table-hover';
  table.innerHTML = `
    <thead>
      <tr>
        <th>ID</th>
        <th>Symbol</th>
        <th>Condition</th>
        <th>Value</th>
        <th>Min Confidence</th>
      </tr>
    </thead>
  `;

  const tbody = document.createElement('tbody');
  alerts.forEach(a => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${a.id}</td>
      <td><strong>${a.symbol}</strong></td>
      <td>${a.condition_type}</td>
      <td>${a.condition_value}</td>
      <td>${a.min_confidence}</td>
    `;
    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  container.innerHTML = '';
  container.appendChild(table);
}

// ---------------------------------------------------------------------------
// Form submission — create alert
// ---------------------------------------------------------------------------

async function handleCreateAlert(e) {
  e.preventDefault();

  const symbol    = document.getElementById('alertSymbol').value.trim();
  const type      = document.getElementById('alertType').value;
  const val       = parseFloat(document.getElementById('alertValue').value);
  const minc      = parseFloat(document.getElementById('alertMinConfidence').value || '0');
  const submitBtn = e.target.querySelector('[type="submit"]');

  if (!symbol || !type || isNaN(val)) {
    showToast('Please fill in all required fields.', 'warning');
    return;
  }

  setButtonLoading(submitBtn, true, 'Creating...');

  const { success, data, error } = await AlertAPI.create({
    symbol,
    condition_type: type,
    condition_value: val,
    min_confidence: isNaN(minc) ? 0 : minc,
  });

  setButtonLoading(submitBtn, false);

  if (success) {
    showToast('Alert created successfully.', 'success');
    e.target.reset();
    loadAlerts();
  } else {
    showToast(`Failed to create alert: ${error}`, 'error');
  }
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

window.addEventListener('load', () => {
  loadAlerts();

  const form = document.getElementById('createAlertForm');
  if (form) {
    form.addEventListener('submit', handleCreateAlert);
  }
});

