async function loadAlerts() {
  const res = await fetch('/api/alerts/');
  const data = await res.json();
  const container = document.getElementById('alertsList');
  container.innerHTML = '';
  if (!data.alerts || data.alerts.length === 0) {
    container.innerText = 'No alerts found';
    return;
  }
  const table = document.createElement('table');
  table.className = 'table table-dark';
  table.innerHTML = '<thead><tr><th>ID</th><th>Symbol</th><th>Type</th><th>Value</th><th>Min Confidence</th></tr></thead>';
  const tbody = document.createElement('tbody');
  data.alerts.forEach(a => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${a.id}</td><td>${a.symbol}</td><td>${a.condition_type}</td><td>${a.condition_value}</td><td>${a.min_confidence}</td>`;
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  container.appendChild(table);
}

window.addEventListener('load', () => {
  loadAlerts();
  document.getElementById('createAlertForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const symbol = document.getElementById('alertSymbol').value;
    const type = document.getElementById('alertType').value;
    const val = document.getElementById('alertValue').value;
    const minc = document.getElementById('alertMinConfidence').value || 0.0;
    const res = await fetch('/api/alerts/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({symbol: symbol, condition_type: type, condition_value: val, min_confidence: minc})});
    const data = await res.json();
    if (data.status === 'created') {
      alert('Alert created');
      loadAlerts();
    } else {
      alert('Failed to create alert');
    }
  });
});

