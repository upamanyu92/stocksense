async function loadStatus() {
  const res = await fetch('/api/system/background-status');
  const data = await res.json();
  document.getElementById('workerStatus').innerText = data.running ? 'Running' : 'Stopped';
  const dres = await fetch('/api/system/digest/status');
  const ddata = await dres.json();
  document.getElementById('digestStatus').innerText = ddata.digest_email_enabled ? 'Enabled' : 'Disabled';
}
window.addEventListener('load', () => {
  loadStatus();
  document.getElementById('startWorker').addEventListener('click', async () => {
    await fetch('/api/system/background_worker/start', {method:'POST'});
    loadStatus();
  });
  document.getElementById('stopWorker').addEventListener('click', async () => {
    await fetch('/api/system/background_worker/stop', {method:'POST'});
    loadStatus();
  });
  document.getElementById('enableDigest').addEventListener('click', async () => {
    await fetch('/api/system/digest/enable', {method:'POST'});
    loadStatus();
  });
  document.getElementById('disableDigest').addEventListener('click', async () => {
    await fetch('/api/system/digest/disable', {method:'POST'});
    loadStatus();
  });
});

