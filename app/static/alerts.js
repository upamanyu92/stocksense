/**
 * StockSense — Notifications
 *
 * Uses the centralized NotificationAPI from services/api.js.
 */

'use strict';

async function fetchNotifications() {
  const container = document.getElementById('notifications-list');
  if (!container) return;

  const { success, data, error } = await NotificationAPI.list();

  if (!success) {
    container.innerHTML = `<span class="text-danger"><i class="fas fa-exclamation-circle"></i> Failed to load notifications: ${error}</span>`;
    return;
  }

  const notifications = (data && data.notifications) ? data.notifications : [];

  if (notifications.length === 0) {
    container.innerText = 'No notifications found.';
    return;
  }

  const list = document.createElement('ul');
  list.className = 'list-unstyled';
  notifications.forEach(n => {
    const li = document.createElement('li');
    li.className = 'mb-2';
    li.innerHTML = `<span class="text-muted">${n.created_at || ''}</span> — <strong>${n.symbol || ''}</strong> — ${n.message || ''}`;
    list.appendChild(li);
  });
  container.innerHTML = '';
  container.appendChild(list);
}

window.addEventListener('load', () => {
  fetchNotifications();
  // Poll every 30 seconds
  setInterval(fetchNotifications, 30000);
});

