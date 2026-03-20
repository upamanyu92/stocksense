async function fetchNotifications() {
  try {
    const res = await fetch('/api/notifications/');
    const data = await res.json();
    const container = document.getElementById('notifications-list');
    if (!data.notifications || data.notifications.length === 0) {
      container.innerText = 'No notifications found';
      return;
    }
    const list = document.createElement('ul');
    data.notifications.forEach(n => {
      const li = document.createElement('li');
      li.innerText = `${n.created_at || ''} - ${n.symbol || ''} - ${n.message || ''}`;
      list.appendChild(li);
    });
    container.innerHTML = '';
    container.appendChild(list);
  } catch (e) {
    console.error('Failed to fetch notifications', e);
    document.getElementById('notifications-list').innerText = 'Failed to load notifications';
  }
}

window.addEventListener('load', () => {
  fetchNotifications();
  // Poll every 30s
  setInterval(fetchNotifications, 30000);
});

