// Dashboard JavaScript for StockSense
// Handles watchlist, search, predictions, and background worker monitoring

document.addEventListener('DOMContentLoaded', () => {
  // Initialize dashboard
  checkDiskSpace();
  loadWatchlist();
  loadTopPredictions();
  startBackgroundWorkerMonitoring();
  initStockSearch();
  updateUptime(); // Initial uptime fetch
  
  // Auto-refresh every 30 seconds
  setInterval(() => {
    loadWatchlist();
    loadTopPredictions();
    checkDiskSpace();
  }, 30000);
  
  // Update uptime every minute
  setInterval(updateUptime, 60000);
});

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

// Background Worker Monitoring
function startBackgroundWorkerMonitoring() {
  setInterval(updateBackgroundWorkerStatus, 5000); // Poll every 5 seconds
  updateBackgroundWorkerStatus(); // Initial fetch
}

async function updateBackgroundWorkerStatus() {
  try {
    const response = await fetch('/api/background-status');
    const data = await response.json();

    // Ensure we have a consistent recent updates array
    const recent = Array.isArray(data.recent_updates) ? data.recent_updates : [];
    const latest = recent.length > 0 ? recent[recent.length - 1] : null;

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

    // Update completed and remaining (support different field names)
    const processed = latest && (latest.processed !== undefined ? latest.processed : (latest.processed_count !== undefined ? latest.processed_count : null));
    const remaining = latest && (latest.remaining !== undefined ? latest.remaining : (latest.remaining_count !== undefined ? latest.remaining_count : null));
    const total = latest && (latest.total !== undefined ? latest.total : (latest.total_count !== undefined ? latest.total_count : null));

    const completedElem = document.getElementById('stocksCompleted');
    const remainingElem = document.getElementById('stocksRemaining');
    if (completedElem) completedElem.textContent = (processed !== null && processed !== undefined) ? `Completed: ${processed}` : '';
    if (remainingElem) remainingElem.textContent = (remaining !== null && remaining !== undefined) ? `Remaining: ${remaining}` : (total && processed ? `Remaining: ${total - processed}` : '');

    // Update recent activity log with richer formatting
    const logElem = document.getElementById('backgroundActivityLog');
    if (logElem) {
      logElem.innerHTML = '';
      const items = recent.slice(-10).reverse(); // show newest first
      items.forEach(update => {
        const li = document.createElement('li');
        let timestamp = (update && update.timestamp) ? update.timestamp : (new Date()).toISOString();
        if (typeof update === 'string') {
          li.textContent = `[${timestamp}] ${update}`;
        } else {
          const type = update.type ? `${update.type.toUpperCase()} ` : '';
          const statusText = update.status || update.message || '';
          const name = getNameFromUpdate(update);
          const p = (update.processed !== undefined) ? update.processed : (update.processed_count !== undefined ? update.processed_count : '');
          const t = (update.total !== undefined) ? update.total : (update.total_count !== undefined ? update.total_count : '');
          const processedText = p !== '' && t !== '' ? ` (${p}/${t})` : (p !== '' ? ` (${p})` : '');
          li.textContent = `[${timestamp}] ${type}${statusText}${name ? ' - ' + name : ''}${processedText}`;
        }
        logElem.appendChild(li);
      });
    }

    // Let the progress section update badge and main operation as well
    if (typeof updateProgressSection === 'function') {
      updateProgressSection(data);
    }

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
  // This would trigger a prediction for a specific stock
  alert(`Prediction for ${symbol} will be run in the next batch cycle.`);
}

// Stock Search with Autocomplete
let stocksData = [];

async function initStockSearch() {
  // Load stock data
  try {
    const response = await fetch('/static/stk.json');
    const data = await response.json();
    
    if (!Array.isArray(data)) {
      stocksData = Object.entries(data).map(([security_id, company_name]) => ({
        security_id,
        company_name
      }));
    } else {
      stocksData = data;
    }
  } catch (error) {
    console.error('Error loading stocks data:', error);
  }
  
  const searchInput = document.getElementById('stockSearch');
  const dropdown = document.getElementById('autocompleteDropdown');
  
  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.trim().toLowerCase();
    
    if (query.length < 2) {
      dropdown.style.display = 'none';
      return;
    }
    
    const matches = stocksData.filter(stock =>
      stock.company_name.toLowerCase().includes(query) ||
      (stock.security_id && stock.security_id.toLowerCase().includes(query))
    ).slice(0, 10);
    
    if (matches.length > 0) {
      dropdown.innerHTML = matches.map(stock => `
        <div class="autocomplete-item" data-symbol="${stock.security_id}" data-name="${stock.company_name}">
          <strong>${stock.security_id}</strong> - ${stock.company_name}
        </div>
      `).join('');
      
      dropdown.style.display = 'block';
      
      // Add click handlers
      dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
        item.addEventListener('click', () => {
          searchStock(item.dataset.symbol, item.dataset.name);
          searchInput.value = '';
          dropdown.style.display = 'none';
        });
      });
    } else {
      dropdown.style.display = 'none';
    }
  });
  
  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = 'none';
    }
  });
}

async function searchStock(symbol, name) {
  const searchResults = document.getElementById('searchResults');
  searchResults.innerHTML = '<div style="text-align: center; padding: 20px;"><div class="spinner"></div> Loading...</div>';
  
  try {
    // Get stock quote
    const quoteResponse = await fetch(`/search_quote/${encodeURIComponent(name)}`);
    const quotes = await quoteResponse.json();
    
    // Get prediction if available
    const predResponse = await fetch('/get_predictions');
    const predictions = await predResponse.json();
    
    const prediction = predictions.find(p => p.security_id === symbol);
    
    if (quotes && quotes.length > 0) {
      const quote = quotes[0];
      
      searchResults.innerHTML = `
        <div class="card" style="background: rgba(0, 212, 255, 0.05); margin-top: 15px;">
          <div class="card-header">
            <h4>${quote.company_name} (${quote.security_id || symbol})</h4>
          </div>
          <table class="custom-table">
            <tr>
              <th>Current Price</th>
              <td>₹${quote.current_value || quote.current_price}</td>
              <th>Day High</th>
              <td>₹${quote.day_high || 'N/A'}</td>
            </tr>
            <tr>
              <th>Day Low</th>
              <td>₹${quote.day_low || 'N/A'}</td>
              <th>Change</th>
              <td class="${quote.change < 0 ? 'profit-negative' : 'profit-positive'}">
                ${quote.change || 'N/A'} (${quote.p_change || 'N/A'}%)
              </td>
            </tr>
            ${prediction ? `
              <tr>
                <th>Predicted Price</th>
                <td class="profit-positive">₹${prediction.predicted_price.toFixed(2)}</td>
                <th>Potential Profit</th>
                <td class="${prediction.profit_percentage > 0 ? 'profit-positive' : 'profit-negative'}">
                  ${prediction.profit_percentage.toFixed(2)}%
                </td>
              </tr>
            ` : '<tr><td colspan="4" style="text-align: center;">No prediction available yet</td></tr>'}
          </table>
          <div style="margin-top: 15px;">
            <button class="btn-custom" onclick="addToWatchlistFromSearch('${symbol}', '${quote.company_name}')">
              <i class="fas fa-star"></i> Add to Watchlist
            </button>
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
