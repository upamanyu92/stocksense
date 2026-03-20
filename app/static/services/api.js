/**
 * StockSense — Centralized API Service Layer
 *
 * All backend API calls are routed through this module so that:
 *  - endpoint URLs are defined in one place
 *  - error handling is consistent
 *  - loading/disabled state helpers can be shared
 *
 * Response contract (mirrors backend standard):
 *   { success: boolean, data: any, error: string|null }
 */

'use strict';

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Generic fetch wrapper that normalises every response to
 * { success, data, error }.
 *
 * @param {string} url
 * @param {RequestInit} [options]
 * @returns {Promise<{success: boolean, data: any, error: string|null}>}
 */
async function _request(url, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
  };
  const config = { ...defaults, ...options };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  try {
    const response = await fetch(url, config);
    let payload;
    try {
      payload = await response.json();
    } catch (_) {
      payload = {};
    }

    if (!response.ok) {
      const errorMsg =
        payload.error || payload.message || `HTTP ${response.status}: ${response.statusText}`;
      return { success: false, data: null, error: errorMsg };
    }

    // Normalise responses that already carry a success flag
    if (typeof payload.success === 'boolean') {
      return {
        success: payload.success,
        data: payload.data !== undefined ? payload.data : payload,
        error: payload.error || null,
      };
    }

    return { success: true, data: payload, error: null };
  } catch (err) {
    return { success: false, data: null, error: err.message || 'Network error' };
  }
}

// ---------------------------------------------------------------------------
// Stock endpoints
// ---------------------------------------------------------------------------

const StockAPI = {
  /**
   * Autocomplete suggestions.
   * @param {string} query
   * @param {number} [limit=10]
   */
  getSuggestions(query, limit = 10) {
    return _request(`/api/stocks/suggestions?q=${encodeURIComponent(query)}&limit=${limit}`);
  },

  /**
   * Full-text company search.
   * @param {string} name
   */
  searchByName(name) {
    return _request(`/api/stocks/search/${encodeURIComponent(name)}`);
  },

  /**
   * Paginated stock list.
   * @param {object} params
   * @param {number}  params.page
   * @param {number}  params.perPage
   * @param {string}  params.sortBy
   * @param {string}  params.sortOrder
   */
  getList({ page = 1, perPage = 50, sortBy = 'company_name', sortOrder = 'asc' } = {}) {
    const qs = new URLSearchParams({
      page,
      per_page: perPage,
      sort_by: sortBy,
      sort_order: sortOrder,
    });
    return _request(`/api/stocks/list?${qs}`);
  },

  /**
   * Single stock quote by company name.
   * @param {string} name
   */
  getQuoteByName(name) {
    return _request(`/api/stocks/quote-by-name?q=${encodeURIComponent(name)}`);
  },
};

// ---------------------------------------------------------------------------
// Prediction endpoints
// ---------------------------------------------------------------------------

const PredictionAPI = {
  /**
   * Top predictions, paginated.
   * @param {number} [page=1]
   * @param {number} [pageSize=50]
   */
  getTopPredictions(page = 1, pageSize = 50) {
    return _request(`/api/predictions/?page=${page}&page_size=${pageSize}`);
  },

  /**
   * Latest prediction for a single stock.
   * @param {string} securityId
   */
  getForStock(securityId) {
    return _request(`/api/predictions/stock/${encodeURIComponent(securityId)}`);
  },

  /**
   * Trigger a prediction for one stock.
   * @param {string} stockSymbol
   * @param {string} [companyName]
   */
  triggerSingle(stockSymbol, companyName = '') {
    return _request('/api/predictions/trigger_single', {
      method: 'POST',
      body: { stock_symbol: stockSymbol, company_name: companyName },
    });
  },

  /** Trigger predictions for all watchlist stocks. */
  triggerWatchlist() {
    return _request('/api/predictions/trigger_watchlist', { method: 'POST' });
  },

  /** Trigger batch predictions for all stocks. */
  triggerAll() {
    return _request('/api/predictions/trigger', { method: 'POST' });
  },

  /** Prediction status stream URL (Server-Sent Events). */
  statusUrl: '/api/predictions/status',
};

// ---------------------------------------------------------------------------
// Watchlist endpoints
// ---------------------------------------------------------------------------

const WatchlistAPI = {
  /** Fetch the current user's watchlist. */
  get() {
    return _request('/api/watchlist/');
  },

  /**
   * Add a stock to the watchlist.
   * @param {string} stockSymbol
   * @param {string} [companyName]
   */
  add(stockSymbol, companyName = '') {
    return _request('/api/watchlist/add', {
      method: 'POST',
      body: { stock_symbol: stockSymbol, company_name: companyName },
    });
  },

  /**
   * Remove a stock from the watchlist.
   * @param {string} stockSymbol
   */
  remove(stockSymbol) {
    return _request('/api/watchlist/remove', {
      method: 'POST',
      body: { stock_symbol: stockSymbol },
    });
  },

  /**
   * Reorder watchlist items.
   * @param {Array<{stock_symbol: string, order: number}>} items
   */
  reorder(items) {
    return _request('/api/watchlist/reorder', {
      method: 'POST',
      body: { items },
    });
  },
};

// ---------------------------------------------------------------------------
// Alert endpoints
// ---------------------------------------------------------------------------

const AlertAPI = {
  /**
   * List alerts, optionally filtered by symbol.
   * @param {string} [symbol]
   */
  list(symbol = '') {
    const qs = symbol ? `?symbol=${encodeURIComponent(symbol)}` : '';
    return _request(`/api/alerts/${qs}`);
  },

  /**
   * Create a new price alert.
   * @param {object} alert
   * @param {string} alert.symbol
   * @param {string} alert.condition_type
   * @param {number} alert.condition_value
   * @param {number} [alert.min_confidence=0]
   */
  create({ symbol, condition_type, condition_value, min_confidence = 0 }) {
    return _request('/api/alerts/', {
      method: 'POST',
      body: { symbol, condition_type, condition_value, min_confidence },
    });
  },

  /** Evaluate all alerts immediately. */
  evaluate() {
    return _request('/api/alerts/evaluate', { method: 'POST' });
  },
};

// ---------------------------------------------------------------------------
// Notification endpoints
// ---------------------------------------------------------------------------

const NotificationAPI = {
  /**
   * List notifications.
   * @param {boolean|null} [sent] – filter by sent status; null = all
   */
  list(sent = null) {
    const qs = sent !== null ? `?sent=${sent ? 1 : 0}` : '';
    return _request(`/api/notifications/${qs}`);
  },

  /**
   * Mark a notification as sent.
   * @param {number} id
   */
  markSent(id) {
    return _request(`/api/notifications/${id}/mark_sent`, { method: 'POST' });
  },
};

// ---------------------------------------------------------------------------
// System / Admin endpoints
// ---------------------------------------------------------------------------

const SystemAPI = {
  /** System status (disk, worker, etc.). */
  getStatus() {
    return _request('/api/system/status');
  },

  /** Application uptime. */
  getUptime() {
    return _request('/api/system/uptime');
  },

  /** Background worker live status. */
  getBackgroundStatus() {
    return _request('/api/system/background-status');
  },

  /** Start the background worker. */
  startWorker() {
    return _request('/api/system/background_worker/start', { method: 'POST' });
  },

  /** Stop the background worker. */
  stopWorker() {
    return _request('/api/system/background_worker/stop', { method: 'POST' });
  },

  /** Cleanup old model files. */
  cleanupModels() {
    return _request('/api/system/cleanup_models', { method: 'POST' });
  },

  /** Digest email status. */
  getDigestStatus() {
    return _request('/api/system/digest/status');
  },

  /** Enable digest emails. */
  enableDigest() {
    return _request('/api/system/digest/enable', { method: 'POST' });
  },

  /** Disable digest emails. */
  disableDigest() {
    return _request('/api/system/digest/disable', { method: 'POST' });
  },
};

// ---------------------------------------------------------------------------
// Price streaming endpoints
// ---------------------------------------------------------------------------

const PriceStreamAPI = {
  /**
   * Start streaming prices for a list of symbols.
   * @param {string[]} symbols
   */
  start(symbols) {
    return _request('/api/price_stream/start', {
      method: 'POST',
      body: { symbols },
    });
  },

  /** Stop the price stream. */
  stop() {
    return _request('/api/price_stream/stop', { method: 'POST' });
  },

  /** Current stream status. */
  getStatus() {
    return _request('/api/price_stream/status');
  },
};

// ---------------------------------------------------------------------------
// Chat / LLM endpoints
// ---------------------------------------------------------------------------

const ChatAPI = {
  /**
   * Send a chat message.
   * @param {string} message
   * @param {string} [conversationId]
   */
  sendMessage(message, conversationId = '') {
    return _request('/api/chat/message', {
      method: 'POST',
      body: { message, conversation_id: conversationId },
    });
  },

  /** Get chat history. */
  getHistory() {
    return _request('/api/chat/history');
  },

  /** Clear chat history. */
  clearHistory() {
    return _request('/api/chat/clear-history', { method: 'DELETE' });
  },
};

// ---------------------------------------------------------------------------
// Toast notification utility
// ---------------------------------------------------------------------------

/**
 * Display a toast notification.
 *
 * Relies on the `#toast-container` element already present in the page
 * (dashboard.html injects one). Falls back to console if absent.
 *
 * @param {string} message
 * @param {'success'|'error'|'warning'|'info'} [type='info']
 * @param {number} [duration=3500] – milliseconds
 */
function showToast(message, type = 'info', duration = 3500) {
  // Map type to colour tokens used across the app
  const colorMap = {
    success: '#00ff87',
    error: '#ff4757',
    warning: '#ffd32a',
    info: '#00d4ff',
  };
  const color = colorMap[type] || colorMap.info;

  // If the page has its own showNotification helper, use it
  if (typeof window.showNotification === 'function') {
    window.showNotification(message, type);
    return;
  }

  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    Object.assign(container.style, {
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      zIndex: '9999',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
    });
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  Object.assign(toast.style, {
    background: 'rgba(15,15,30,0.97)',
    border: `1px solid ${color}`,
    borderLeft: `4px solid ${color}`,
    color: '#e0e0e0',
    padding: '12px 20px',
    borderRadius: '8px',
    maxWidth: '360px',
    fontSize: '14px',
    boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
    animation: 'fadeInUp 0.3s ease',
    transition: 'opacity 0.4s ease',
  });
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => container.removeChild(toast), 400);
  }, duration);
}

/**
 * Set a button into a loading/disabled state.
 * @param {HTMLElement} btn
 * @param {boolean} loading
 * @param {string} [loadingText='Loading...']
 */
function setButtonLoading(btn, loading, loadingText = 'Loading...') {
  if (!btn) return;
  if (loading) {
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = `<span style="opacity:0.7">${loadingText}</span>`;
    btn.disabled = true;
  } else {
    if (btn.dataset.originalText) {
      btn.innerHTML = btn.dataset.originalText;
    }
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Public exports (also available as globals for non-module scripts)
// ---------------------------------------------------------------------------

window.StockAPI = StockAPI;
window.PredictionAPI = PredictionAPI;
window.WatchlistAPI = WatchlistAPI;
window.AlertAPI = AlertAPI;
window.NotificationAPI = NotificationAPI;
window.SystemAPI = SystemAPI;
window.PriceStreamAPI = PriceStreamAPI;
window.ChatAPI = ChatAPI;
window.showToast = showToast;
window.setButtonLoading = setButtonLoading;
