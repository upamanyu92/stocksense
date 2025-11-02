// Dashboard JavaScript for StockSense
// Handles watchlist, search, predictions, and background worker monitoring

// WebSocket connection
let socket = null;
let connectionStatus = 'disconnected';

// Real-time chart
let priceChart = null;
let isPriceTracking = false;

document.addEventListener('DOMContentLoaded', () => {
  // Initialize WebSocket connection
  initWebSocket();
  
  // Initialize charts
  initCharts();
  
  // Initialize dashboard
  checkDiskSpace();
  loadWatchlist();
  loadTopPredictions();
  initStockSearch();
  updateUptime(); // Initial uptime fetch
  
  // Auto-refresh every 30 seconds (fallback for non-WebSocket data)
  setInterval(() => {
    loadTopPredictions();
    checkDiskSpace();
  }, 30000);
  
  // Update uptime every minute
  setInterval(updateUptime, 60000);
});

// Initialize charts
function initCharts() {
  try {
    priceChart = new MultiStockChart('priceChart', {
      maxDataPoints: 30,
      label: 'Stock Prices'
    });
    console.log('Charts initialized successfully');
  } catch (error) {
    console.error('Error initializing charts:', error);
  }
}

// WebSocket initialization and management
function initWebSocket() {
  try {
    // Connect to Socket.IO server
    socket = io({
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5
    });

    // Connection event handlers
    socket.on('connect', () => {
      console.log('WebSocket connected');
      connectionStatus = 'connected';
      updateConnectionStatus();
      
      // Subscribe to real-time updates
      socket.emit('subscribe_predictions');
      socket.emit('subscribe_watchlist');
      socket.emit('subscribe_stock_prices', { symbols: [] });
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      connectionStatus = 'disconnected';
      updateConnectionStatus();
    });

    socket.on('connection_status', (data) => {
      console.log('Connection status:', data);
    });

    socket.on('subscription_confirmed', (data) => {
      console.log('Subscription confirmed:', data.type);
    });

    // Real-time event handlers
    socket.on('prediction_update', handlePredictionUpdate);
    socket.on('watchlist_update', handleWatchlistUpdate);
    socket.on('stock_price_update', handleStockPriceUpdate);
    socket.on('background_worker_status', handleBackgroundWorkerStatus);
    socket.on('system_status', handleSystemStatus);
    socket.on('system_alert', handleSystemAlert);
    socket.on('prediction_progress', handlePredictionProgress);

    socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      connectionStatus = 'error';
      updateConnectionStatus();
    });

  } catch (error) {
    console.error('Error initializing WebSocket:', error);
    // Fallback to polling
    startBackgroundWorkerMonitoring();
  }
}

function updateConnectionStatus() {
  const statusElement = document.getElementById('connectionStatus');
  if (statusElement) {
    if (connectionStatus === 'connected') {
      statusElement.innerHTML = '<i class="fas fa-circle" style="color: var(--success-color);"></i> Live';
      statusElement.title = 'Real-time connection active';
    } else if (connectionStatus === 'disconnected') {
      statusElement.innerHTML = '<i class="fas fa-circle" style="color: var(--warning-color);"></i> Offline';
      statusElement.title = 'Reconnecting...';
    } else {
      statusElement.innerHTML = '<i class="fas fa-circle" style="color: var(--danger-color);"></i> Error';
      statusElement.title = 'Connection error';
    }
  }
}

// Real-time event handlers
function handlePredictionUpdate(data) {
  console.log('Prediction update:', data);
  // Refresh predictions table with new data
  loadTopPredictions();
  
  // Show notification
  showNotification(`New prediction: ${data.company_name}`, 'success');
}

function handleWatchlistUpdate(data) {
  console.log('Watchlist update:', data);
  // Refresh watchlist
  loadWatchlist();
}

function handleStockPriceUpdate(data) {
  console.log('Stock price update:', data);
  // Update specific stock price in the UI
  updateStockPriceInUI(data);
  
  // Update chart if tracking is enabled
  if (isPriceTracking && priceChart) {
    const timeLabel = new Date().toLocaleTimeString();
    const symbol = data.company_name || data.symbol;
    priceChart.addDataPoint(symbol, timeLabel, data.price);
  }
}

function handleBackgroundWorkerStatus(data) {
  console.log('Background worker status:', data);
  updateBackgroundWorkerStatusUI(data);
}

function handleSystemStatus(data) {
  console.log('System status:', data);
  // Update system status displays
  if (data.disk_usage) {
    updateDiskUsageUI(data.disk_usage);
  }
}

function handleSystemAlert(data) {
  console.log('System alert:', data);
  showNotification(data.message, data.level || 'warning');
}

function handlePredictionProgress(data) {
  console.log('Prediction progress:', data);
  updatePredictionProgressUI(data);
}

function showNotification(message, type = 'info') {
  // Simple notification system
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    padding: 15px 20px;
    background: ${type === 'success' ? 'var(--success-color)' : type === 'error' ? 'var(--danger-color)' : 'var(--warning-color)'};
    color: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 10000;
    animation: slideIn 0.3s ease-out;
  `;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-out';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

function updateBackgroundWorkerStatusUI(data) {
  const recent = Array.isArray(data.recent_updates) ? data.recent_updates : (data.type ? [data] : []);
  const latest = recent.length > 0 ? recent[recent.length - 1] : data;

  // Extract a display name from possible fields
  const getNameFromUpdate = (u) => {
    if (!u) return '';
    if (typeof u === 'string') return u;
    return u.current_stock || u.stock_name || u.company_name || u.name || u.security_id || '';
  };

  const displayName = getNameFromUpdate(latest);

  // Update current stock display
  const currentStockElem = document.getElementById('currentStock');
  if (currentStockElem) {
    currentStockElem.textContent = displayName ? `Currently processing: ${displayName}` : 'No active stock';
  }

  // Update completed and remaining
  const processed = latest && (latest.processed !== undefined ? latest.processed : (latest.processed_count !== undefined ? latest.processed_count : null));
  const remaining = latest && (latest.remaining !== undefined ? latest.remaining : (latest.remaining_count !== undefined ? latest.remaining_count : null));
  const total = latest && (latest.total !== undefined ? latest.total : (latest.total_count !== undefined ? latest.total_count : null));

  const completedElem = document.getElementById('stocksCompleted');
  const remainingElem = document.getElementById('stocksRemaining');
  if (completedElem) completedElem.textContent = (processed !== null && processed !== undefined) ? `Completed: ${processed}` : '';
  if (remainingElem) remainingElem.textContent = (remaining !== null && remaining !== undefined) ? `Remaining: ${remaining}` : (total && processed ? `Remaining: ${total - processed}` : '');

  // Update recent activity log
  const logElem = document.getElementById('backgroundActivityLog');
  if (logElem && recent.length > 0) {
    // Keep existing items and add new ones
    const existingItems = Array.from(logElem.querySelectorAll('li')).map(li => li.textContent);
    
    recent.forEach(update => {
      const li = document.createElement('li');
      let timestamp = (update && update.timestamp) ? update.timestamp : (new Date()).toISOString();
      let itemText = '';
      
      if (typeof update === 'string') {
        itemText = `[${timestamp}] ${update}`;
      } else {
        const type = update.type ? `${update.type.toUpperCase()} ` : '';
        const statusText = update.status || update.message || '';
        const name = getNameFromUpdate(update);
        const p = (update.processed !== undefined) ? update.processed : (update.processed_count !== undefined ? update.processed_count : '');
        const t = (update.total !== undefined) ? update.total : (update.total_count !== undefined ? update.total_count : '');
        const processedText = p !== '' && t !== '' ? ` (${p}/${t})` : (p !== '' ? ` (${p})` : '');
        itemText = `[${timestamp}] ${type}${statusText}${name ? ' - ' + name : ''}${processedText}`;
      }
      
      // Only add if not duplicate
      if (!existingItems.includes(itemText)) {
        li.textContent = itemText;
        logElem.insertBefore(li, logElem.firstChild);
      }
    });
    
    // Keep only last 10 items
    while (logElem.children.length > 10) {
      logElem.removeChild(logElem.lastChild);
    }
  }

  // Update progress section
  if (typeof updateProgressSection === 'function') {
    updateProgressSection(data);
  }
}

function updatePredictionProgressUI(data) {
  const currentOperation = document.getElementById('currentOperation');
  const systemStatus = document.getElementById('systemStatus');
  
  if (data.status === 'started') {
    systemStatus.textContent = 'Starting Predictions';
    systemStatus.className = 'status-badge status-predicting';
    currentOperation.innerHTML = '<i class="fas fa-brain"></i> ' + data.message;
  } else if (data.status === 'processing') {
    systemStatus.textContent = 'Running Predictions';
    systemStatus.className = 'status-badge status-predicting';
    currentOperation.innerHTML = `<i class="fas fa-brain"></i> ${data.message}`;
  } else if (data.status === 'completed') {
    systemStatus.textContent = 'Predictions Complete';
    systemStatus.className = 'status-badge status-complete';
    currentOperation.innerHTML = '<i class="fas fa-check"></i> ' + data.message;
  } else if (data.status === 'error') {
    systemStatus.textContent = 'Error';
    systemStatus.className = 'status-badge status-downloading';
    currentOperation.innerHTML = '<i class="fas fa-exclamation-triangle"></i> ' + data.message;
  }
}

function updateStockPriceInUI(priceData) {
  // Update stock price in watchlist and predictions tables
  const symbol = priceData.symbol || priceData.security_id;
  const newPrice = priceData.price || priceData.current_price;
  
  // Update in watchlist
  const watchlistRows = document.querySelectorAll('#watchlistTable tr');
  watchlistRows.forEach(row => {
    const cells = row.querySelectorAll('td');
    if (cells.length > 1 && cells[1].textContent === symbol) {
      if (cells[2]) cells[2].textContent = `$${parseFloat(newPrice).toFixed(2)}`;
    }
  });
}

function updateDiskUsageUI(diskData) {
  const diskWarning = document.getElementById('diskWarning');
  const diskWarningText = document.getElementById('diskWarningText');

  if (diskData && diskData.is_low) {
    diskWarning.style.display = 'flex';
    diskWarningText.textContent = `Only ${diskData.percent_free.toFixed(1)}% disk space remaining.`;
  } else {
    diskWarning.style.display = 'none';
  }
}

// Uptime Monitoring
async function updateUptime() {
  try {
    const response = await fetch('/api/system/uptime');
    const data = await response.json();
    
    const uptimeElement = document.getElementById('appUptime');
    if (uptimeElement) {
      uptimeElement.textContent = data.uptime;
    }
  } catch (error) {
    console.error('Error fetching uptime:', error);
  }
}

// Disk Space Monitoring
async function checkDiskSpace() {
  try {
    const response = await fetch('/api/system/status');
    const data = await response.json();

    const diskWarning = document.getElementById('diskWarning');
    const diskWarningText = document.getElementById('diskWarningText');

    if (data.disk_usage && data.disk_usage.is_low) {
      diskWarning.style.display = 'flex';
      diskWarningText.textContent = `Only ${data.disk_usage.percent_free.toFixed(1)}% disk space remaining. Models using ${data.model_stats.total_mb.toFixed(0)}MB.`;
    } else {
      diskWarning.style.display = 'none';
    }
  } catch (error) {
    console.error('Error checking disk space:', error);
  }
}

async function cleanupModels() {
  if (!confirm('This will remove old model versions, keeping only the 2 newest for each stock. Continue?')) {
    return;
  }

  try {
    const response = await fetch('/api/system/cleanup_models', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keep_newest: 2 })
    });
    
    const data = await response.json();
    
    if (data.success) {
      alert(`Cleanup complete!\nDeleted ${data.result.deleted} old models\nFreed ${data.result.space_freed_mb.toFixed(0)}MB of disk space`);
      checkDiskSpace();
    } else {
      alert('Cleanup failed: ' + data.error);
    }
  } catch (error) {
    console.error('Error during cleanup:', error);
    alert('Cleanup failed: ' + error.message);
  }
}

// Background Worker Monitoring (fallback for non-WebSocket)
function startBackgroundWorkerMonitoring() {
  setInterval(updateBackgroundWorkerStatus, 5000); // Poll every 5 seconds
  updateBackgroundWorkerStatus(); // Initial fetch
}

async function updateBackgroundWorkerStatus() {
  // Skip if WebSocket is connected
  if (connectionStatus === 'connected') {
    return;
  }
  
  try {
    const response = await fetch('/api/background-status');
    const data = await response.json();
    updateBackgroundWorkerStatusUI(data);
  } catch (error) {
    console.error('Error fetching background worker status:', error);
  }
}

function updateProgressSection(status) {
  const currentOperation = document.getElementById('currentOperation');
  const operationETA = document.getElementById('operationETA');
  const systemStatus = document.getElementById('systemStatus');
  
  if (!status.running) {
    systemStatus.textContent = 'System Idle';
    systemStatus.className = 'status-badge status-complete';
    currentOperation.textContent = 'No active operations';
    operationETA.textContent = '--:--';
    return;
  }
  
  const recent = status.recent_updates || [];
  if (recent.length > 0) {
    const latest = recent[recent.length - 1];
    
    if (latest.type === 'download') {
      if (latest.status === 'progress') {
        systemStatus.textContent = 'Downloading Stocks';
        systemStatus.className = 'status-badge status-downloading';
        currentOperation.innerHTML = `<i class="fas fa-download"></i> Downloading stocks (${latest.processed}/${latest.total})`;
        operationETA.textContent = `${latest.failed} failed`;
      } else if (latest.status === 'completed') {
        currentOperation.innerHTML = `<i class="fas fa-check"></i> Download complete`;
      }
    } else if (latest.type === 'prediction') {
      if (latest.status === 'progress') {
        systemStatus.textContent = 'Running Predictions';
        systemStatus.className = 'status-badge status-predicting';
        currentOperation.innerHTML = `<i class="fas fa-brain"></i> Predicting: ${latest.stock_name || ''} (${latest.processed}/${latest.total})`;
        const remainingTime = Math.ceil((latest.total - latest.processed) * 0.5); // Estimate 0.5 min per stock
        operationETA.textContent = `~${remainingTime}min remaining`;
      } else if (latest.status === 'completed') {
        systemStatus.textContent = 'System Ready';
        systemStatus.className = 'status-badge status-complete';
        currentOperation.innerHTML = `<i class="fas fa-check"></i> All predictions complete`;
        operationETA.textContent = 'Done';
      }
    }
  }
}

// Watchlist Management
async function loadWatchlist() {
  try {
    const response = await fetch('/api/watchlist/');
    const data = await response.json();
    
    const tbody = document.getElementById('watchlistTable');
    
    if (data.success && data.watchlist && data.watchlist.length > 0) {
      tbody.innerHTML = data.watchlist.map(stock => `
        <tr>
          <td>${stock.company_name || 'N/A'}</td>
          <td>${stock.stock_symbol}</td>
          <td>${stock.current_price ? '$' + stock.current_price.toFixed(2) : 'N/A'}</td>
          <td>${stock.predicted_price ? '$' + stock.predicted_price.toFixed(2) : 'Pending'}</td>
          <td class="${getProfitClass(stock.current_price, stock.predicted_price)}">
            ${getChangePercent(stock.current_price, stock.predicted_price)}
          </td>
          <td>
            <span class="status-badge ${stock.stock_status === 'active' ? 'status-complete' : 'status-downloading'}">
              ${stock.stock_status || 'active'}
            </span>
          </td>
          <td>
            <button class="btn-custom btn-sm" onclick="rerunPrediction('${stock.stock_symbol}')">
              <i class="fas fa-sync-alt"></i>
            </button>
            <button class="btn-danger-custom btn-sm" onclick="removeFromWatchlist('${stock.stock_symbol}')">
              <i class="fas fa-trash"></i>
            </button>
          </td>
        </tr>
      `).join('');
    } else {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; color: var(--text-muted);">
            No stocks in watchlist. Click "Add Stock" to get started.
          </td>
        </tr>
      `;
    }
  } catch (error) {
    console.error('Error loading watchlist:', error);
  }
}

function getProfitClass(current, predicted) {
  if (!current || !predicted) return '';
  return predicted > current ? 'profit-positive' : 'profit-negative';
}

function getChangePercent(current, predicted) {
  if (!current || !predicted) return 'N/A';
  const change = ((predicted - current) / current * 100);
  return (change > 0 ? '+' : '') + change.toFixed(2) + '%';
}

async function showAddToWatchlist() {
  // Create modal for adding stock to watchlist with autocomplete
  const modal = document.createElement('div');
  modal.id = 'addWatchlistModal';
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
  `;
  
  modal.innerHTML = `
    <div style="
      background: var(--bg-card);
      border-radius: 15px;
      padding: 30px;
      max-width: 500px;
      width: 90%;
      border: 1px solid rgba(0, 212, 255, 0.3);
      box-shadow: 0 10px 50px rgba(0, 0, 0, 0.5);
    ">
      <h3 style="color: var(--primary-color); margin-bottom: 20px;">
        <i class="fas fa-plus-circle"></i> Add Stock to Watchlist
      </h3>
      
      <div class="search-container" style="position: relative;">
        <input 
          type="text" 
          class="search-input" 
          id="watchlistStockSearch" 
          placeholder="Search for stock by name or symbol..."
          autocomplete="off"
          style="width: 100%; margin-bottom: 10px;"
        >
        <div class="autocomplete-dropdown" id="watchlistAutocomplete" style="position: absolute; top: 100%; left: 0; right: 0; z-index: 1001;"></div>
      </div>
      
      <div id="selectedStockInfo" style="margin-top: 15px; padding: 10px; background: rgba(0, 212, 255, 0.1); border-radius: 8px; display: none;">
        <p style="margin: 0; color: var(--text-light);">
          <strong>Selected:</strong> <span id="selectedStockName"></span>
        </p>
      </div>
      
      <div style="margin-top: 20px; display: flex; gap: 10px; justify-content: flex-end;">
        <button class="btn-danger-custom" onclick="closeAddWatchlistModal()">
          <i class="fas fa-times"></i> Cancel
        </button>
        <button class="btn-custom" id="confirmAddBtn" onclick="confirmAddToWatchlist()" disabled>
          <i class="fas fa-plus"></i> Add to Watchlist
        </button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Initialize autocomplete for modal
  const searchInput = document.getElementById('watchlistStockSearch');
  const dropdown = document.getElementById('watchlistAutocomplete');
  let selectedStock = null;
  
  searchInput.addEventListener('input', async (e) => {
    const query = e.target.value.trim();
    
    if (query.length < 2) {
      dropdown.style.display = 'none';
      return;
    }
    
    try {
      const response = await fetch(`/api/stocks/suggestions?q=${encodeURIComponent(query)}&limit=10`);
      const suggestions = await response.json();
      
      if (suggestions.length > 0) {
        dropdown.innerHTML = suggestions.map(stock => `
          <div class="autocomplete-item" data-symbol="${stock.security_id}" data-name="${stock.company_name}">
            <strong>${stock.company_name}</strong>
            <br><small style="color: var(--text-muted);">${stock.security_id || stock.scrip_code} ${stock.industry ? '- ' + stock.industry : ''}</small>
          </div>
        `).join('');
        
        dropdown.style.display = 'block';
        
        // Add click handlers
        dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
          item.addEventListener('click', () => {
            selectedStock = {
              symbol: item.dataset.symbol,
              name: item.dataset.name
            };
            document.getElementById('selectedStockName').textContent = `${item.dataset.name} (${item.dataset.symbol})`;
            document.getElementById('selectedStockInfo').style.display = 'block';
            document.getElementById('confirmAddBtn').disabled = false;
            searchInput.value = '';
            dropdown.style.display = 'none';
          });
        });
      } else {
        dropdown.innerHTML = '<div class="autocomplete-item" style="text-align: center; color: var(--text-muted);">No stocks found</div>';
        dropdown.style.display = 'block';
      }
    } catch (error) {
      console.error('Error fetching suggestions:', error);
    }
  });
  
  // Store selected stock globally for confirmation
  window.modalSelectedStock = null;
  searchInput.addEventListener('stockSelected', (e) => {
    window.modalSelectedStock = e.detail;
  });
  
  searchInput.focus();
}

function closeAddWatchlistModal() {
  const modal = document.getElementById('addWatchlistModal');
  if (modal) {
    modal.remove();
  }
  window.modalSelectedStock = null;
}

async function confirmAddToWatchlist() {
  const selectedStockName = document.getElementById('selectedStockName').textContent;
  if (!selectedStockName) {
    alert('Please select a stock first');
    return;
  }
  
  // Extract symbol from the selected text (format: "Name (SYMBOL)")
  const matches = selectedStockName.match(/\(([^)]+)\)$/);
  if (!matches) {
    alert('Invalid stock selection');
    return;
  }
  
  const symbol = matches[1];
  const name = selectedStockName.replace(/\s*\([^)]+\)$/, '');
  
  try {
    const response = await fetch('/api/watchlist/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stock_symbol: symbol,
        company_name: name
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showNotification('Stock added to watchlist!', 'success');
      loadWatchlist();
      closeAddWatchlistModal();
    } else {
      alert('Failed to add stock: ' + data.error);
    }
  } catch (error) {
    console.error('Error adding to watchlist:', error);
    alert('Failed to add stock: ' + error.message);
  }
}

async function showAddToWatchlistOld() {
  // Old implementation using prompt dialogs - kept for reference
  const symbol = prompt('Enter stock symbol (e.g., RELIANCE, TCS):');
  if (!symbol) return;
  
  const companyName = prompt('Enter company name (optional):');
  
  try {
    const response = await fetch('/api/watchlist/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stock_symbol: symbol.toUpperCase(),
        company_name: companyName || symbol.toUpperCase()
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      alert('Stock added to watchlist!');
      loadWatchlist();
    } else {
      alert('Failed to add stock: ' + data.error);
    }
  } catch (error) {
    console.error('Error adding to watchlist:', error);
    alert('Failed to add stock: ' + error.message);
  }
}



async function removeFromWatchlist(symbol) {
  if (!confirm(`Remove ${symbol} from watchlist?`)) return;
  
  try {
    const response = await fetch('/api/watchlist/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stock_symbol: symbol })
    });
    
    const data = await response.json();
    
    if (data.success) {
      loadWatchlist();
    } else {
      alert('Failed to remove stock: ' + data.error);
    }
  } catch (error) {
    console.error('Error removing from watchlist:', error);
  }
}

async function rerunPrediction(symbol) {
  // Trigger prediction for a specific stock
  runPrediction(symbol, null);
}

async function runPrediction(symbol, name) {
  try {
    showNotification('Starting prediction...', 'info');
    
    const response = await fetch('/api/predictions/trigger_single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stock_symbol: symbol,
        company_name: name
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showNotification(`Prediction started for ${data.company_name}. Please wait...`, 'success');
      
      // Listen for prediction progress updates via WebSocket
      if (socket) {
        socket.once('prediction_progress', (progress) => {
          if (progress.status === 'completed' && progress.security_id === symbol) {
            showNotification(`Prediction completed for ${progress.company_name}!`, 'success');
            
            // Reload the stock search results or watchlist to show updated prediction
            if (name) {
              // Reload search results
              setTimeout(() => searchStock(symbol, name), 1000);
            } else {
              // Reload watchlist
              setTimeout(() => loadWatchlist(), 1000);
            }
          } else if (progress.status === 'error' && progress.security_id === symbol) {
            showNotification(`Prediction failed: ${progress.message}`, 'error');
          }
        });
      }
    } else {
      showNotification('Failed to start prediction: ' + data.error, 'error');
    }
  } catch (error) {
    console.error('Error running prediction:', error);
    showNotification('Failed to start prediction: ' + error.message, 'error');
  }
}

async function rerunPredictionOld(symbol) {
  // Old implementation - kept for reference  
  alert(`Prediction for ${symbol} will be run in the next batch cycle.`);
}


// Stock Search with Autocomplete using stock_quote table
let stocksData = [];
let searchTimeout = null;

async function initStockSearch() {
  const searchInput = document.getElementById('stockSearch');
  const dropdown = document.getElementById('autocompleteDropdown');
  
  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.trim();
    
    if (query.length < 2) {
      dropdown.style.display = 'none';
      return;
    }
    
    // Debounce the search
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => fetchSuggestions(query, dropdown), 300);
  });
  
  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = 'none';
    }
  });
}

async function fetchSuggestions(query, dropdown) {
  try {
    const response = await fetch(`/api/stocks/suggestions?q=${encodeURIComponent(query)}&limit=10`);
    const suggestions = await response.json();
    
    if (suggestions.length > 0) {
      dropdown.innerHTML = suggestions.map(stock => `
        <div class="autocomplete-item" data-symbol="${stock.security_id}" data-name="${stock.company_name}">
          <strong>${stock.company_name}</strong>
          <br><small style="color: var(--text-muted);">${stock.security_id || stock.scrip_code} ${stock.industry ? '- ' + stock.industry : ''}</small>
        </div>
      `).join('');
      
      dropdown.style.display = 'block';
      
      // Add click handlers
      dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
        item.addEventListener('click', () => {
          searchStock(item.dataset.symbol, item.dataset.name);
          document.getElementById('stockSearch').value = '';
          dropdown.style.display = 'none';
        });
      });
    } else {
      dropdown.innerHTML = '<div class="autocomplete-item" style="text-align: center; color: var(--text-muted);">No stocks found</div>';
      dropdown.style.display = 'block';
    }
  } catch (error) {
    console.error('Error fetching suggestions:', error);
    dropdown.style.display = 'none';
  }
}

async function searchStock(symbol, name) {
  const searchResults = document.getElementById('searchResults');
  searchResults.innerHTML = '<div style="text-align: center; padding: 20px;"><div class="spinner"></div> Loading...</div>';
  
  try {
    // Get stock quote
    const quoteResponse = await fetch(`/api/stocks/search/${encodeURIComponent(name)}`);
    const quotes = await quoteResponse.json();
    
    // Get prediction if available
    let prediction = null;
    try {
      const predResponse = await fetch(`/api/predictions/stock/${encodeURIComponent(symbol)}`);
      const predData = await predResponse.json();
      if (predData.success) {
        prediction = predData.prediction;
      }
    } catch (e) {
      console.log('No prediction available yet');
    }
    
    if (quotes && quotes.length > 0) {
      const quote = quotes[0];
      
      searchResults.innerHTML = `
        <div class="card" style="background: rgba(0, 212, 255, 0.05); margin-top: 15px;">
          <div class="card-header">
            <h4>${quote.company_name || name} (${quote.security_id || symbol})</h4>
            <div>
              <button class="btn-custom btn-sm" onclick="addToWatchlistFromSearch('${quote.security_id || symbol}', '${quote.company_name || name}')">
                <i class="fas fa-star"></i> Add to Watchlist
              </button>
            </div>
          </div>
          <table class="custom-table">
            <tr>
              <th>Current Price</th>
              <td>₹${quote.current_value || quote.current_price || 'N/A'}</td>
              <th>Day High</th>
              <td>₹${quote.day_high || 'N/A'}</td>
            </tr>
            <tr>
              <th>Day Low</th>
              <td>₹${quote.day_low || 'N/A'}</td>
              <th>Change</th>
              <td class="${(quote.change || 0) < 0 ? 'profit-negative' : 'profit-positive'}">
                ${quote.change || 'N/A'} (${quote.p_change || 'N/A'}%)
              </td>
            </tr>
            <tr>
              <th>Industry</th>
              <td colspan="3">${quote.industry || 'N/A'}</td>
            </tr>
          </table>
          
          <div style="margin-top: 20px; border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 15px;">
            <h5 style="color: var(--primary-color); margin-bottom: 15px;">
              <i class="fas fa-brain"></i> Prediction Engineering
            </h5>
            
            <div id="predictionStatus-${quote.security_id || symbol}">
              ${prediction ? `
                <table class="custom-table">
                  <tr>
                    <th>Predicted Price</th>
                    <td class="profit-positive">₹${prediction.predicted_price ? prediction.predicted_price.toFixed(2) : 'N/A'}</td>
                    <th>Potential Profit</th>
                    <td class="${(prediction.profit_percentage || 0) > 0 ? 'profit-positive' : 'profit-negative'}">
                      ${prediction.profit_percentage ? prediction.profit_percentage.toFixed(2) : '0.00'}%
                    </td>
                  </tr>
                  <tr>
                    <th>Prediction Date</th>
                    <td colspan="3">${prediction.prediction_date || 'N/A'}</td>
                  </tr>
                </table>
                <div style="margin-top: 10px;">
                  <button class="btn-custom" onclick="runPrediction('${quote.security_id || symbol}', '${quote.company_name || name}')">
                    <i class="fas fa-sync-alt"></i> Update Prediction
                  </button>
                </div>
              ` : `
                <p style="color: var(--text-muted); margin-bottom: 10px;">No prediction available yet. Run prediction to analyze this stock.</p>
                <button class="btn-custom" onclick="runPrediction('${quote.security_id || symbol}', '${quote.company_name || name}')">
                  <i class="fas fa-brain"></i> Run Prediction
                </button>
              `}
            </div>
          </div>
        </div>
      `;
    } else {
      searchResults.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">No results found</div>';
    }
  } catch (error) {
    console.error('Error searching stock:', error);
    searchResults.innerHTML = '<div style="text-align: center; color: var(--danger-color); padding: 20px;">Error loading stock data</div>';
  }
}

async function addToWatchlistFromSearch(symbol, name) {
  try {
    const response = await fetch('/api/watchlist/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stock_symbol: symbol,
        company_name: name
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      alert('Stock added to watchlist!');
      loadWatchlist();
    } else {
      alert('Failed to add stock: ' + data.error);
    }
  } catch (error) {
    console.error('Error adding to watchlist:', error);
  }
}

// Top Predictions with Pagination
let currentPredictionPage = 1;
const predictionPageSize = 20;

async function loadTopPredictions(page = 1) {
  try {
    const response = await fetch(`/get_predictions?page=${page}&page_size=${predictionPageSize}`);
    const data = await response.json();
    console.log('Fetched Predictions:', data);

    const predictions = Array.isArray(data.predictions) ? data.predictions : [];
    const tbody = document.getElementById('topPredictionsTable');

    if (predictions.length > 0) {
      tbody.innerHTML = predictions.map(stock => `
        <tr>
          <td>${stock.company_name}</td>
          <td>₹${stock.current_price.toFixed(2)}</td>
          <td>₹${stock.predicted_price.toFixed(2)}</td>
          <td class="${stock.profit_percentage > 0 ? 'profit-positive' : 'profit-negative'}">
            ${stock.profit_percentage > 0 ? '+' : ''}${stock.profit_percentage.toFixed(2)}%
          </td>
          <td>${new Date(stock.prediction_date).toLocaleDateString()}</td>
        </tr>
      `).join('');
      console.log('Predictions table updated.');

      // Render pagination controls
      renderPredictionPagination(data.page || page, data.total_pages || 1);
    } else {
      console.warn('No predictions available.');
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--text-muted);">
            No predictions available yet
          </td>
        </tr>
      `;
      // Clear pagination if no data
      const paginationDiv = document.getElementById('predictions-pagination');
      if (paginationDiv) paginationDiv.innerHTML = '';
    }

    currentPredictionPage = page;
  } catch (error) {
    console.error('Error loading predictions:', error);
  }
}

function renderPredictionPagination(currentPage, totalPages) {
  const paginationDiv = document.getElementById('predictions-pagination');
  if (!paginationDiv) return;

  if (totalPages <= 1) {
    paginationDiv.innerHTML = '';
    return;
  }

  let html = '<div class="pagination-controls" style="margin-top: 15px; text-align: center;">';

  // Previous button
  if (currentPage > 1) {
    html += `<button class="btn-custom btn-sm" onclick="loadTopPredictions(${currentPage - 1})" style="margin: 0 5px;">
      <i class="fas fa-chevron-left"></i> Previous
    </button>`;
  } else {
    html += `<button class="btn-custom btn-sm" disabled style="margin: 0 5px; opacity: 0.5;">
      <i class="fas fa-chevron-left"></i> Previous
    </button>`;
  }

  // Page info
  html += `<span style="margin: 0 15px; color: var(--text-color);">
    Page ${currentPage} of ${totalPages}
  </span>`;

  // Next button
  if (currentPage < totalPages) {
    html += `<button class="btn-custom btn-sm" onclick="loadTopPredictions(${currentPage + 1})" style="margin: 0 5px;">
      Next <i class="fas fa-chevron-right"></i>
    </button>`;
  } else {
    html += `<button class="btn-custom btn-sm" disabled style="margin: 0 5px; opacity: 0.5;">
      Next <i class="fas fa-chevron-right"></i>
    </button>`;
  }

  html += '</div>';
  paginationDiv.innerHTML = html;
}

// Real-time Price Tracking Functions
async function startPriceTracking() {
  try {
    // Get watchlist stocks
    const response = await fetch('/api/watchlist/');
    const data = await response.json();
    
    if (data.success && data.watchlist && data.watchlist.length > 0) {
      // Get symbols to track
      const symbols = data.watchlist.map(s => s.stock_symbol);
      
      // Add stocks to chart
      data.watchlist.forEach(stock => {
        if (priceChart) {
          priceChart.addStock(stock.company_name, stock.company_name);
        }
      });
      
      // Subscribe to price updates via WebSocket
      if (socket && socket.connected) {
        socket.emit('subscribe_stock_prices', { symbols: symbols });
      }
      
      // Also start via API
      const streamResponse = await fetch('/api/price_stream/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: symbols })
      });
      
      const streamData = await streamResponse.json();
      
      if (streamData.success) {
        isPriceTracking = true;
        showNotification(`Started tracking ${symbols.length} stocks`, 'success');
      } else {
        showNotification('Failed to start price tracking', 'error');
      }
    } else {
      showNotification('No stocks in watchlist to track', 'warning');
    }
  } catch (error) {
    console.error('Error starting price tracking:', error);
    showNotification('Error starting price tracking', 'error');
  }
}

async function stopPriceTracking() {
  try {
    // Get watchlist stocks
    const response = await fetch('/api/watchlist/');
    const data = await response.json();
    
    if (data.success && data.watchlist && data.watchlist.length > 0) {
      const symbols = data.watchlist.map(s => s.stock_symbol);
      
      // Unsubscribe via WebSocket
      if (socket && socket.connected) {
        socket.emit('unsubscribe_stock_prices', { symbols: symbols });
      }
      
      // Stop via API
      const streamResponse = await fetch('/api/price_stream/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: symbols })
      });
      
      const streamData = await streamResponse.json();
      
      if (streamData.success) {
        isPriceTracking = false;
        if (priceChart) {
          priceChart.clearChart();
        }
        showNotification('Stopped price tracking', 'info');
      }
    }
  } catch (error) {
    console.error('Error stopping price tracking:', error);
    showNotification('Error stopping price tracking', 'error');
  }
}

// Background Worker Control Functions (Admin only)
async function startBackgroundWorker() {
  if (!confirm('Start the background worker? This will automatically download stocks and run predictions.')) {
    return;
  }
  
  try {
    const response = await fetch('/api/system/background_worker/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    const data = await response.json();
    
    if (data.success) {
      showNotification('Background worker started successfully', 'success');
      updateBackgroundWorkerUI(true);
    } else {
      alert('Failed to start worker: ' + data.error);
    }
  } catch (error) {
    console.error('Error starting background worker:', error);
    alert('Failed to start worker: ' + error.message);
  }
}

async function stopBackgroundWorker() {
  if (!confirm('Stop the background worker? Automated tasks will not run.')) {
    return;
  }
  
  try {
    const response = await fetch('/api/system/background_worker/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    const data = await response.json();
    
    if (data.success) {
      showNotification('Background worker stopped successfully', 'success');
      updateBackgroundWorkerUI(false);
    } else {
      alert('Failed to stop worker: ' + data.error);
    }
  } catch (error) {
    console.error('Error stopping background worker:', error);
    alert('Failed to stop worker: ' + error.message);
  }
}

function updateBackgroundWorkerUI(isRunning) {
  const systemStatus = document.getElementById('systemStatus');
  if (systemStatus && !isRunning) {
    systemStatus.textContent = 'Background Worker Disabled';
    systemStatus.className = 'status-badge status-downloading';
  }
}
