/**
 * StockSense Premium Dashboard
 * Comprehensive dashboard with real-time updates, AI insights, and portfolio management.
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let socket = null;
  let refreshInterval = null;
  let searchDebounceTimer = null;
  let chatOpen = false;
  let sidebarCollapsed = false;
  const REFRESH_MS = 60000;

  // ---------------------------------------------------------------------------
  // Utility helpers
  // ---------------------------------------------------------------------------

  function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') return String(unsafe ?? '');
    return unsafe
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /** Indian ₹ format: ₹12,34,567.89 */
  function formatCurrency(value) {
    if (value == null || isNaN(value)) return '₹0.00';
    var n = Number(value);
    var sign = n < 0 ? '-' : '';
    var abs = Math.abs(n).toFixed(2);
    var parts = abs.split('.');
    var intPart = parts[0];
    var decPart = parts[1];
    // Indian grouping: last 3 digits then groups of 2
    var lastThree = intPart.slice(-3);
    var rest = intPart.slice(0, -3);
    if (rest.length > 0) {
      lastThree = ',' + lastThree;
    }
    var formatted = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + lastThree;
    return sign + '₹' + formatted + '.' + decPart;
  }

  function formatPercent(value) {
    if (value == null || isNaN(value)) return '0.00%';
    var n = Number(value);
    var prefix = n > 0 ? '+' : '';
    return prefix + n.toFixed(2) + '%';
  }

  function debounce(func, delay) {
    var timer;
    return function () {
      var context = this;
      var args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () {
        func.apply(context, args);
      }, delay);
    };
  }

  // ---------------------------------------------------------------------------
  // Toast notifications
  // ---------------------------------------------------------------------------

  function showToast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.style.cssText =
        'position:fixed;top:20px;right:20px;z-index:10000;display:flex;flex-direction:column;gap:10px;';
      document.body.appendChild(container);
    }
    var icons = {
      success: 'fa-check-circle',
      error: 'fa-exclamation-circle',
      warning: 'fa-exclamation-triangle',
      info: 'fa-info-circle',
    };
    var colors = {
      success: '#00ff87',
      error: '#ff4757',
      warning: '#ffaa00',
      info: '#00d4ff',
    };
    var toast = document.createElement('div');
    toast.style.cssText =
      'background:rgba(30,30,50,0.95);border-left:4px solid ' +
      (colors[type] || colors.info) +
      ';color:#e0e0e0;padding:14px 20px;border-radius:8px;min-width:280px;' +
      'box-shadow:0 8px 32px rgba(0,0,0,0.4);display:flex;align-items:center;gap:10px;' +
      'animation:slideInRight 0.3s ease;backdrop-filter:blur(10px);font-size:14px;';
    toast.innerHTML =
      '<i class="fas ' +
      (icons[type] || icons.info) +
      '" style="color:' +
      (colors[type] || colors.info) +
      ';font-size:18px;"></i>' +
      '<span>' +
      escapeHtml(message) +
      '</span>';
    container.appendChild(toast);
    setTimeout(function () {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 300);
    }, 3500);
  }

  // ---------------------------------------------------------------------------
  // Loading skeletons
  // ---------------------------------------------------------------------------

  function showSkeleton(containerId) {
    var el = document.getElementById(containerId);
    if (!el) return;
    el.setAttribute('data-original-content', el.innerHTML);
    var count = parseInt(el.getAttribute('data-skeleton-count'), 10) || 3;
    var html = '';
    for (var i = 0; i < count; i++) {
      html +=
        '<div class="skeleton-item" style="background:linear-gradient(90deg,rgba(255,255,255,0.04) 25%,' +
        'rgba(255,255,255,0.08) 50%,rgba(255,255,255,0.04) 75%);background-size:200% 100%;' +
        'animation:shimmer 1.5s infinite;border-radius:8px;height:48px;margin-bottom:10px;"></div>';
    }
    el.innerHTML = html;
  }

  function hideSkeleton(containerId) {
    var el = document.getElementById(containerId);
    if (!el) return;
    // Remove skeleton items if still present; render functions replace content directly
    var skeletons = el.querySelectorAll('.skeleton-item');
    skeletons.forEach(function (s) {
      if (s.parentNode) s.parentNode.removeChild(s);
    });
  }

  // ---------------------------------------------------------------------------
  // Sparkline helper (Chart.js)
  // ---------------------------------------------------------------------------

  function createSparkline(canvasId, data, color) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    var ctx = canvas.getContext('2d');
    if (!ctx) return null;
    // Destroy previous chart instance if any
    var existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    return new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.map(function (_, i) {
          return '';
        }),
        datasets: [
          {
            data: data,
            borderColor: color || '#00d4ff',
            borderWidth: 1.5,
            fill: true,
            backgroundColor: (color || '#00d4ff') + '15',
            tension: 0.4,
            pointRadius: 0,
            pointHoverRadius: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 500 },
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        scales: {
          x: { display: false },
          y: { display: false },
        },
      },
    });
  }

  // ---------------------------------------------------------------------------
  // Animated counter
  // ---------------------------------------------------------------------------

  function animateCounter(elementId, targetValue, duration, isCurrency) {
    var el = document.getElementById(elementId);
    if (!el) return;
    duration = duration || 1200;
    var start = 0;
    var startTime = null;

    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      // Ease-out quad
      var eased = 1 - (1 - progress) * (1 - progress);
      var current = start + (targetValue - start) * eased;
      if (isCurrency) {
        el.textContent = formatCurrency(current);
      } else {
        el.textContent = Math.round(current).toLocaleString('en-IN');
      }
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    }

    requestAnimationFrame(step);
  }

  // ---------------------------------------------------------------------------
  // Time-based greeting
  // ---------------------------------------------------------------------------

  function setGreeting() {
    var el = document.getElementById('greetingText');
    if (!el) return;
    var hour = new Date().getHours();
    var greeting;
    if (hour < 12) greeting = 'Good morning';
    else if (hour < 17) greeting = 'Good afternoon';
    else greeting = 'Good evening';
    var username =
      el.getAttribute('data-username') || 'Investor';
    el.textContent = greeting + ', ' + username + '!';
  }

  // ---------------------------------------------------------------------------
  // Generic fetch helper
  // ---------------------------------------------------------------------------

  async function apiFetch(url, options) {
    try {
      var resp = await fetch(url, options);
      if (!resp.ok) {
        throw new Error('HTTP ' + resp.status);
      }
      return await resp.json();
    } catch (err) {
      console.error('API error (' + url + '):', err);
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // 1. Portfolio overview
  // ---------------------------------------------------------------------------

  async function loadPortfolioOverview() {
    showSkeleton('overviewContainer');
    var data = await apiFetch('/api/dashboard/overview');
    if (!data || !data.success) {
      renderOverviewEmpty();
      return;
    }
    var o = data.overview;
    animateCounter('portfolioValue', o.total_value || 0, 1200, true);
    animateCounter('totalInvested', o.total_invested || 0, 1200, true);
    animateCounter('holdingsCount', o.holdings_count || 0, 800, false);

    var pnlEl = document.getElementById('totalPnl');
    if (pnlEl) {
      var pnl = o.total_pnl || 0;
      pnlEl.textContent = formatCurrency(pnl);
      pnlEl.className = pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
    }
    var pnlPctEl = document.getElementById('pnlPercent');
    if (pnlPctEl) {
      pnlPctEl.textContent = formatPercent(o.pnl_percent || 0);
      pnlPctEl.className =
        (o.pnl_percent || 0) >= 0 ? 'pnl-positive' : 'pnl-negative';
    }
    var statsEls = {
      watchlistCount: o.watchlist_count,
      predictionsCount: o.predictions_count,
      recentTradesCount: o.recent_trades,
    };
    Object.keys(statsEls).forEach(function (id) {
      var elem = document.getElementById(id);
      if (elem) elem.textContent = statsEls[id] || 0;
    });
    hideSkeleton('overviewContainer');
  }

  function renderOverviewEmpty() {
    var el = document.getElementById('overviewContainer');
    if (!el) return;
    el.innerHTML =
      '<div style="text-align:center;color:#888;padding:20px;">' +
      '<i class="fas fa-chart-line" style="font-size:36px;margin-bottom:10px;"></i>' +
      '<p>No portfolio data yet. Start trading to see your overview.</p></div>';
  }

  // ---------------------------------------------------------------------------
  // 2. Market indices
  // ---------------------------------------------------------------------------

  async function loadMarketIndices() {
    showSkeleton('indicesContainer');
    var data = await apiFetch('/api/dashboard/market-indices');
    var container = document.getElementById('indicesContainer');
    if (!container) return;
    if (!data || !data.success || !data.indices || data.indices.length === 0) {
      container.innerHTML =
        '<div style="color:#888;text-align:center;padding:16px;">Market data unavailable</div>';
      return;
    }
    var html = '';
    data.indices.forEach(function (idx, i) {
      var positive = (idx.p_change || 0) >= 0;
      var color = positive ? '#00ff87' : '#ff4757';
      var arrow = positive ? 'fa-caret-up' : 'fa-caret-down';
      var sparkId = 'indexSparkline' + i;
      html +=
        '<div class="index-card" style="background:rgba(255,255,255,0.03);border-radius:12px;' +
        'padding:14px 16px;min-width:180px;flex:1;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;">' +
        '<span style="font-size:12px;color:#aaa;">' +
        escapeHtml(idx.name) +
        '</span>' +
        '<i class="fas ' +
        arrow +
        '" style="color:' +
        color +
        ';"></i></div>' +
        '<div style="font-size:20px;font-weight:700;margin:6px 0;">' +
        Number(idx.value || 0).toLocaleString('en-IN', {
          maximumFractionDigits: 2,
        }) +
        '</div>' +
        '<div style="display:flex;justify-content:space-between;align-items:center;">' +
        '<span style="color:' +
        color +
        ';font-size:13px;font-weight:600;">' +
        formatPercent(idx.p_change) +
        '</span>' +
        '<canvas id="' +
        sparkId +
        '" style="width:60px;height:24px;"></canvas>' +
        '</div></div>';
    });
    container.innerHTML =
      '<div style="display:flex;gap:12px;flex-wrap:wrap;">' + html + '</div>';

    // Render sparklines with synthetic data based on direction
    data.indices.forEach(function (idx, i) {
      var positive = (idx.p_change || 0) >= 0;
      var base = idx.value || 100;
      var points = [];
      for (var j = 0; j < 12; j++) {
        var trend = positive ? j * 0.3 : -j * 0.3;
        points.push(base + trend + (Math.random() - 0.5) * base * 0.005);
      }
      createSparkline(
        'indexSparkline' + i,
        points,
        positive ? '#00ff87' : '#ff4757'
      );
    });
  }

  // ---------------------------------------------------------------------------
  // 3. AI Predictions panel
  // ---------------------------------------------------------------------------

  async function loadPredictions() {
    showSkeleton('predictionsContainer');
    var data = await apiFetch('/api/dashboard/predictions-summary');
    var container = document.getElementById('predictionsContainer');
    if (!container) return;
    if (
      !data ||
      !data.success ||
      !data.predictions ||
      data.predictions.length === 0
    ) {
      container.innerHTML =
        '<div style="color:#888;text-align:center;padding:24px;">' +
        '<i class="fas fa-robot" style="font-size:32px;margin-bottom:8px;"></i>' +
        '<p>No predictions yet. Add stocks to your watchlist and run AI predictions.</p></div>';
      return;
    }
    var html = '';
    data.predictions.forEach(function (p) {
      var conf = Math.round((p.confidence || 0) * 100);
      var isHigh = conf > 80;
      var movColor =
        p.movement === 'Up'
          ? '#00ff87'
          : p.movement === 'Down'
            ? '#ff4757'
            : '#ffaa00';
      var movIcon =
        p.movement === 'Up'
          ? 'fa-arrow-trend-up'
          : p.movement === 'Down'
            ? 'fa-arrow-trend-down'
            : 'fa-minus';
      var barColor =
        conf > 80 ? '#00ff87' : conf > 50 ? '#ffaa00' : '#ff4757';
      var glowStyle = isHigh
        ? 'box-shadow:0 0 15px rgba(0,255,135,0.25);border:1px solid rgba(0,255,135,0.3);'
        : 'border:1px solid rgba(255,255,255,0.06);';

      html +=
        '<div class="prediction-card" style="background:rgba(255,255,255,0.03);border-radius:12px;' +
        'padding:16px;' +
        glowStyle +
        '">' +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">' +
        '<div><div style="font-weight:700;font-size:15px;">' +
        escapeHtml(p.company_name || p.stock_symbol) +
        '</div>' +
        '<div style="font-size:12px;color:#aaa;">' +
        escapeHtml(p.stock_symbol) +
        '</div></div>' +
        '<span style="display:inline-flex;align-items:center;gap:4px;color:' +
        movColor +
        ';font-weight:600;font-size:13px;">' +
        '<i class="fas ' +
        movIcon +
        '"></i> ' +
        escapeHtml(p.movement) +
        '</span></div>' +
        '<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:8px;">' +
        '<span style="color:#aaa;">Current: ' +
        formatCurrency(p.current_price) +
        '</span>' +
        '<span style="color:' +
        movColor +
        ';">Target: ' +
        formatCurrency(p.predicted_price) +
        '</span></div>' +
        '<div style="margin-bottom:8px;">' +
        '<div style="display:flex;justify-content:space-between;font-size:11px;color:#aaa;margin-bottom:3px;">' +
        '<span>Confidence</span><span>' +
        conf +
        '%</span></div>' +
        '<div style="background:rgba(255,255,255,0.08);border-radius:4px;height:6px;overflow:hidden;">' +
        '<div style="width:' +
        conf +
        '%;height:100%;background:' +
        barColor +
        ';border-radius:4px;transition:width 0.6s ease;"></div></div></div>' +
        '<button onclick="window.PremiumDashboard.viewPrediction(\'' +
        escapeHtml(p.stock_symbol) +
        '\')" ' +
        'style="width:100%;background:rgba(0,212,255,0.1);color:#00d4ff;border:1px solid rgba(0,212,255,0.2);' +
        'border-radius:6px;padding:6px;cursor:pointer;font-size:12px;transition:background 0.2s;" ' +
        'onmouseover="this.style.background=\'rgba(0,212,255,0.2)\'" ' +
        'onmouseout="this.style.background=\'rgba(0,212,255,0.1)\'">' +
        '<i class="fas fa-chart-bar"></i> View Full Analysis</button></div>';
    });
    container.innerHTML =
      '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;">' +
      html +
      '</div>';
  }

  function viewPrediction(symbol) {
    window.location.href = '/stocks?symbol=' + encodeURIComponent(symbol);
  }

  // ---------------------------------------------------------------------------
  // 4. Watchlist
  // ---------------------------------------------------------------------------

  async function loadWatchlist() {
    showSkeleton('watchlistContainer');
    var data = await apiFetch('/api/watchlist/');
    var container = document.getElementById('watchlistContainer');
    if (!container) return;
    if (!data || !data.watchlist || data.watchlist.length === 0) {
      container.innerHTML =
        '<div style="color:#888;text-align:center;padding:24px;">' +
        '<i class="fas fa-eye" style="font-size:28px;margin-bottom:8px;"></i>' +
        '<p>Your watchlist is empty.</p></div>';
      return;
    }
    var html =
      '<table style="width:100%;border-collapse:collapse;font-size:13px;">' +
      '<thead><tr style="color:#aaa;text-align:left;border-bottom:1px solid rgba(255,255,255,0.08);">' +
      '<th style="padding:8px 10px;">Stock</th>' +
      '<th style="padding:8px 10px;">Price</th>' +
      '<th style="padding:8px 10px;">Change</th>' +
      '<th style="padding:8px 10px;width:70px;">Trend</th>' +
      '</tr></thead><tbody>';

    data.watchlist.forEach(function (item, i) {
      var change = item.change_percent || item.p_change || 0;
      var positive = change >= 0;
      var color = positive ? '#00ff87' : '#ff4757';
      var sparkId = 'wlSparkline' + i;
      html +=
        '<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">' +
        '<td style="padding:10px;">' +
        '<div style="font-weight:600;">' +
        escapeHtml(item.company_name || item.symbol || item.stock_symbol) +
        '</div>' +
        '<div style="font-size:11px;color:#aaa;">' +
        escapeHtml(item.symbol || item.stock_symbol) +
        '</div></td>' +
        '<td style="padding:10px;">' +
        formatCurrency(item.current_price || item.last_price || 0) +
        '</td>' +
        '<td style="padding:10px;color:' +
        color +
        ';font-weight:600;">' +
        formatPercent(change) +
        '</td>' +
        '<td style="padding:10px;"><canvas id="' +
        sparkId +
        '" style="width:60px;height:22px;"></canvas></td></tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;

    // Sparklines
    data.watchlist.forEach(function (item, i) {
      var change = item.change_percent || item.p_change || 0;
      var price = item.current_price || item.last_price || 100;
      var pts = [];
      for (var j = 0; j < 10; j++) {
        var dir = change >= 0 ? j * 0.15 : -j * 0.15;
        pts.push(price + dir + (Math.random() - 0.5) * price * 0.003);
      }
      createSparkline(
        'wlSparkline' + i,
        pts,
        change >= 0 ? '#00ff87' : '#ff4757'
      );
    });
  }

  // ---------------------------------------------------------------------------
  // 5. AI Insights feed
  // ---------------------------------------------------------------------------

  async function loadAIInsights() {
    showSkeleton('insightsContainer');
    var data = await apiFetch('/api/dashboard/ai-insights');
    var container = document.getElementById('insightsContainer');
    if (!container) return;
    if (
      !data ||
      !data.success ||
      !data.insights ||
      data.insights.length === 0
    ) {
      container.innerHTML =
        '<div style="color:#888;text-align:center;padding:20px;">' +
        '<i class="fas fa-lightbulb" style="font-size:28px;margin-bottom:8px;"></i>' +
        '<p>No AI insights available yet.</p></div>';
      return;
    }
    var typeConfig = {
      buy_signal: {
        icon: 'fa-arrow-up',
        color: '#00ff87',
        label: 'Buy Signal',
      },
      sell_signal: {
        icon: 'fa-arrow-down',
        color: '#ff4757',
        label: 'Sell Signal',
      },
      trend: {
        icon: 'fa-chart-line',
        color: '#ffaa00',
        label: 'Trend',
      },
    };
    var html = '';
    data.insights.forEach(function (ins) {
      var cfg = typeConfig[ins.insight_type] || typeConfig.trend;
      var confPct = Math.round((ins.confidence || 0) * 100);
      html +=
        '<div style="background:rgba(255,255,255,0.03);border-radius:10px;padding:14px 16px;' +
        'border-left:3px solid ' +
        cfg.color +
        ';display:flex;gap:12px;align-items:flex-start;">' +
        '<div style="width:36px;height:36px;border-radius:50%;display:flex;align-items:center;' +
        'justify-content:center;background:' +
        cfg.color +
        '18;flex-shrink:0;">' +
        '<i class="fas ' +
        cfg.icon +
        '" style="color:' +
        cfg.color +
        ';font-size:14px;"></i></div>' +
        '<div style="flex:1;min-width:0;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +
        '<span style="font-weight:600;font-size:13px;">' +
        escapeHtml(ins.stock_symbol) +
        ' &mdash; ' +
        escapeHtml(cfg.label) +
        '</span>' +
        '<span style="font-size:11px;color:#aaa;">' +
        confPct +
        '% conf</span></div>' +
        '<p style="margin:0;font-size:12px;color:#ccc;line-height:1.4;">' +
        escapeHtml(ins.message) +
        '</p>' +
        '<div style="font-size:11px;color:#666;margin-top:4px;">' +
        escapeHtml(ins.source || '') +
        (ins.created_at
          ? ' &bull; ' + new Date(ins.created_at).toLocaleDateString()
          : '') +
        '</div></div></div>';
    });
    container.innerHTML =
      '<div style="display:flex;flex-direction:column;gap:10px;">' +
      html +
      '</div>';
  }

  // ---------------------------------------------------------------------------
  // 6. Recent activity timeline
  // ---------------------------------------------------------------------------

  async function loadRecentActivity() {
    showSkeleton('activityContainer');
    var data = await apiFetch('/api/dashboard/recent-activity');
    var container = document.getElementById('activityContainer');
    if (!container) return;
    if (!data || !data.success || !data.trades || data.trades.length === 0) {
      container.innerHTML =
        '<div style="color:#888;text-align:center;padding:20px;">' +
        '<i class="fas fa-history" style="font-size:28px;margin-bottom:8px;"></i>' +
        '<p>No recent activity.</p></div>';
      return;
    }
    var html = '<div style="position:relative;padding-left:24px;">';
    // Vertical timeline line
    html +=
      '<div style="position:absolute;left:8px;top:0;bottom:0;width:2px;background:rgba(255,255,255,0.08);"></div>';
    data.trades.forEach(function (t) {
      var isBuy = (t.trade_type || '').toUpperCase() === 'BUY';
      var dotColor = isBuy ? '#00ff87' : '#ff4757';
      var typeLabel = isBuy ? 'BUY' : 'SELL';
      html +=
        '<div style="position:relative;padding-bottom:16px;">' +
        '<div style="position:absolute;left:-20px;top:4px;width:12px;height:12px;' +
        'border-radius:50%;background:' +
        dotColor +
        ';border:2px solid rgba(0,0,0,0.4);"></div>' +
        '<div style="background:rgba(255,255,255,0.03);border-radius:8px;padding:12px 14px;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +
        '<span style="font-weight:600;font-size:13px;">' +
        escapeHtml(t.company_name || t.stock_symbol) +
        '</span>' +
        '<span style="font-size:11px;padding:2px 8px;border-radius:4px;font-weight:600;' +
        'background:' +
        dotColor +
        '20;color:' +
        dotColor +
        ';">' +
        typeLabel +
        '</span></div>' +
        '<div style="font-size:12px;color:#aaa;">' +
        (t.quantity || 0) +
        ' shares @ ' +
        formatCurrency(t.price) +
        ' = ' +
        formatCurrency(t.total_value) +
        '</div>' +
        '<div style="font-size:11px;color:#666;margin-top:4px;">' +
        (t.created_at
          ? new Date(t.created_at).toLocaleString('en-IN')
          : '') +
        '</div></div></div>';
    });
    html += '</div>';
    container.innerHTML = html;
  }

  // ---------------------------------------------------------------------------
  // 7. Sector heatmap
  // ---------------------------------------------------------------------------

  async function loadSectorHeatmap() {
    showSkeleton('sectorContainer');
    var data = await apiFetch('/api/dashboard/sector-heatmap');
    var container = document.getElementById('sectorContainer');
    if (!container) return;
    if (!data || !data.success || !data.sectors || data.sectors.length === 0) {
      container.innerHTML =
        '<div style="color:#888;text-align:center;padding:20px;">No sector data available</div>';
      return;
    }
    var html = '';
    data.sectors.forEach(function (s) {
      var change = s.avg_change || 0;
      var bg;
      if (change > 2) bg = 'rgba(0,255,135,0.25)';
      else if (change > 0) bg = 'rgba(0,255,135,0.12)';
      else if (change > -2) bg = 'rgba(255,71,87,0.12)';
      else bg = 'rgba(255,71,87,0.25)';
      var textColor = change >= 0 ? '#00ff87' : '#ff4757';
      html +=
        '<div style="background:' +
        bg +
        ';border-radius:10px;padding:14px;text-align:center;' +
        'min-width:120px;flex:1 1 120px;">' +
        '<div style="font-weight:600;font-size:13px;margin-bottom:4px;">' +
        escapeHtml(s.name) +
        '</div>' +
        '<div style="font-size:18px;font-weight:700;color:' +
        textColor +
        ';">' +
        formatPercent(change) +
        '</div>' +
        '<div style="font-size:11px;color:#aaa;margin-top:4px;">' +
        (s.stock_count || 0) +
        ' stocks &bull; ' +
        (s.gainers || 0) +
        ' <span style="color:#00ff87;">▲</span> ' +
        (s.losers || 0) +
        ' <span style="color:#ff4757;">▼</span></div></div>';
    });
    container.innerHTML =
      '<div style="display:flex;flex-wrap:wrap;gap:10px;">' + html + '</div>';
  }

  // ---------------------------------------------------------------------------
  // 8. Sentiment gauge
  // ---------------------------------------------------------------------------

  async function loadSentiment() {
    showSkeleton('sentimentContainer');
    var data = await apiFetch('/api/dashboard/sentiment');
    var container = document.getElementById('sentimentContainer');
    if (!container) return;
    if (!data || !data.success || !data.sentiment) {
      container.innerHTML =
        '<div style="color:#888;text-align:center;padding:16px;">Sentiment data unavailable</div>';
      return;
    }
    var s = data.sentiment;
    var label = s.overall || 'Neutral';
    var score = s.score || 0; // -1 to 1
    var gaugeColor =
      label === 'Bullish'
        ? '#00ff87'
        : label === 'Bearish'
          ? '#ff4757'
          : '#ffaa00';
    // Map score (-1..1) to percentage (0..100)
    var pct = Math.round(((score + 1) / 2) * 100);
    var emoji =
      label === 'Bullish' ? '🐂' : label === 'Bearish' ? '🐻' : '😐';

    container.innerHTML =
      '<div style="text-align:center;padding:12px;">' +
      '<div style="font-size:36px;margin-bottom:6px;">' +
      emoji +
      '</div>' +
      '<div style="font-size:20px;font-weight:700;color:' +
      gaugeColor +
      ';margin-bottom:8px;">' +
      escapeHtml(label) +
      '</div>' +
      '<div style="background:rgba(255,255,255,0.08);border-radius:6px;height:10px;overflow:hidden;' +
      'margin:0 auto;max-width:200px;">' +
      '<div style="width:' +
      pct +
      '%;height:100%;background:linear-gradient(90deg,#ff4757,#ffaa00,#00ff87);' +
      'border-radius:6px;transition:width 0.8s ease;"></div></div>' +
      '<div style="display:flex;justify-content:center;gap:20px;margin-top:10px;font-size:12px;">' +
      '<span style="color:#00ff87;">' +
      (s.bullish_count || 0) +
      ' Bullish</span>' +
      '<span style="color:#ffaa00;">' +
      (s.neutral_count || 0) +
      ' Neutral</span>' +
      '<span style="color:#ff4757;">' +
      (s.bearish_count || 0) +
      ' Bearish</span></div>' +
      '<div style="font-size:11px;color:#666;margin-top:6px;">' +
      (s.total_analyzed || 0) +
      ' stocks analyzed</div></div>';
  }

  // ---------------------------------------------------------------------------
  // 9. User level / Gamification
  // ---------------------------------------------------------------------------

  async function loadUserLevel() {
    showSkeleton('levelContainer');
    var data = await apiFetch('/api/dashboard/user-level');
    var container = document.getElementById('levelContainer');
    if (!container) return;
    if (!data || !data.success || !data.level) {
      container.innerHTML =
        '<div style="color:#888;text-align:center;padding:16px;">Level data unavailable</div>';
      return;
    }
    var lv = data.level;
    var tierColors = { 1: '#00d4ff', 2: '#ffaa00', 3: '#ff006e' };
    var tierColor = tierColors[lv.level_tier] || '#00d4ff';
    var tierIcons = { 1: 'fa-seedling', 2: 'fa-fire', 3: 'fa-crown' };
    var tierIcon = tierIcons[lv.level_tier] || 'fa-star';
    var progress = Math.min(lv.xp_progress || 0, 100);

    var badgesHtml = '';
    if (lv.badges && lv.badges.length > 0) {
      lv.badges.forEach(function (b) {
        badgesHtml +=
          '<span style="display:inline-block;background:rgba(255,255,255,0.06);border-radius:6px;' +
          'padding:3px 8px;font-size:11px;margin:2px;" title="' +
          escapeHtml(typeof b === 'string' ? b : b.name || '') +
          '">' +
          escapeHtml(typeof b === 'string' ? b : b.name || '🏅') +
          '</span>';
      });
    }

    container.innerHTML =
      '<div style="text-align:center;padding:12px;">' +
      '<div style="display:inline-flex;align-items:center;justify-content:center;' +
      'width:52px;height:52px;border-radius:50%;background:' +
      tierColor +
      '20;margin-bottom:8px;">' +
      '<i class="fas ' +
      tierIcon +
      '" style="font-size:22px;color:' +
      tierColor +
      ';"></i></div>' +
      '<div style="font-size:18px;font-weight:700;color:' +
      tierColor +
      ';">' +
      escapeHtml(lv.level_name || 'Investor') +
      '</div>' +
      '<div style="font-size:12px;color:#aaa;margin:6px 0;">Tier ' +
      (lv.level_tier || 1) +
      '</div>' +
      '<div style="max-width:220px;margin:8px auto;">' +
      '<div style="display:flex;justify-content:space-between;font-size:11px;color:#aaa;margin-bottom:3px;">' +
      '<span>' +
      (lv.xp_points || 0) +
      ' XP</span><span>' +
      (lv.next_level_xp || 0) +
      ' XP</span></div>' +
      '<div style="background:rgba(255,255,255,0.08);border-radius:4px;height:8px;overflow:hidden;">' +
      '<div style="width:' +
      progress +
      '%;height:100%;background:' +
      tierColor +
      ';border-radius:4px;transition:width 0.8s ease;"></div></div></div>' +
      '<div style="display:flex;justify-content:center;gap:16px;font-size:12px;margin-top:10px;">' +
      '<span><i class="fas fa-bullseye" style="color:#00d4ff;"></i> ' +
      (lv.predictions_made || 0) +
      ' predictions</span>' +
      '<span><i class="fas fa-check" style="color:#00ff87;"></i> ' +
      (lv.successful_predictions || 0) +
      ' correct</span>' +
      '<span><i class="fas fa-fire" style="color:#ffaa00;"></i> ' +
      (lv.streak_days || 0) +
      'd streak</span></div>' +
      (badgesHtml
        ? '<div style="margin-top:10px;">' + badgesHtml + '</div>'
        : '') +
      '</div>';
  }

  // ---------------------------------------------------------------------------
  // 10. Portfolio holdings
  // ---------------------------------------------------------------------------

  async function loadPortfolio() {
    showSkeleton('portfolioContainer');
    var data = await apiFetch('/api/dashboard/portfolio');
    var container = document.getElementById('portfolioContainer');
    if (!container) return;
    if (
      !data ||
      !data.success ||
      !data.holdings ||
      data.holdings.length === 0
    ) {
      container.innerHTML =
        '<div style="color:#888;text-align:center;padding:24px;">' +
        '<i class="fas fa-wallet" style="font-size:28px;margin-bottom:8px;"></i>' +
        '<p>No holdings yet. Record your first trade to build your portfolio.</p></div>';
      return;
    }
    var html =
      '<table style="width:100%;border-collapse:collapse;font-size:13px;">' +
      '<thead><tr style="color:#aaa;text-align:left;border-bottom:1px solid rgba(255,255,255,0.08);">' +
      '<th style="padding:8px 10px;">Stock</th>' +
      '<th style="padding:8px 10px;">Qty</th>' +
      '<th style="padding:8px 10px;">Avg Price</th>' +
      '<th style="padding:8px 10px;">Value</th>' +
      '<th style="padding:8px 10px;">P&L</th></tr></thead><tbody>';
    data.holdings.forEach(function (h) {
      var pnl = h.pnl || 0;
      var pnlColor = pnl >= 0 ? '#00ff87' : '#ff4757';
      html +=
        '<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">' +
        '<td style="padding:10px;">' +
        '<div style="font-weight:600;">' +
        escapeHtml(h.company_name || h.stock_symbol) +
        '</div>' +
        '<div style="font-size:11px;color:#aaa;">' +
        escapeHtml(h.stock_symbol) +
        '</div></td>' +
        '<td style="padding:10px;">' +
        (h.quantity || 0) +
        '</td>' +
        '<td style="padding:10px;">' +
        formatCurrency(h.avg_buy_price) +
        '</td>' +
        '<td style="padding:10px;">' +
        formatCurrency(h.current_value) +
        '</td>' +
        '<td style="padding:10px;color:' +
        pnlColor +
        ';font-weight:600;">' +
        formatCurrency(pnl) +
        '<div style="font-size:11px;">' +
        formatPercent(h.pnl_percent) +
        '</div></td></tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;
  }

  // ---------------------------------------------------------------------------
  // 11. Stock search (header autocomplete)
  // ---------------------------------------------------------------------------

  function initStockSearch() {
    var input = document.getElementById('stockSearchInput');
    var results = document.getElementById('stockSearchResults');
    if (!input || !results) return;

    var debouncedSearch = debounce(async function () {
      var query = input.value.trim();
      if (query.length < 2) {
        results.style.display = 'none';
        return;
      }
      try {
        var data = await apiFetch(
          '/api/stocks/search?q=' + encodeURIComponent(query) + '&max_results=8'
        );
        if (!data || !data.results || data.results.length === 0) {
          // Try suggestions endpoint
          data = await apiFetch(
            '/api/stocks/suggestions?q=' +
              encodeURIComponent(query) +
              '&limit=8'
          );
        }
        var items = (data && (data.results || data.suggestions)) || [];
        if (items.length === 0) {
          results.innerHTML =
            '<div style="padding:12px;color:#888;font-size:13px;">No results found</div>';
          results.style.display = 'block';
          return;
        }
        var html = '';
        items.forEach(function (item) {
          var name = item.company_name || item.name || item.symbol || '';
          var symbol = item.symbol || item.security_id || '';
          html +=
            '<div class="search-result-item" data-symbol="' +
            escapeHtml(symbol) +
            '" style="padding:10px 14px;cursor:pointer;' +
            'border-bottom:1px solid rgba(255,255,255,0.04);transition:background 0.15s;">' +
            '<div style="font-weight:600;font-size:13px;">' +
            escapeHtml(name) +
            '</div>' +
            '<div style="font-size:11px;color:#aaa;">' +
            escapeHtml(symbol) +
            '</div></div>';
        });
        results.innerHTML = html;
        // Attach click handlers via event delegation
        results.querySelectorAll('.search-result-item').forEach(function (el) {
          el.addEventListener('mouseenter', function () {
            el.style.background = 'rgba(0,212,255,0.08)';
          });
          el.addEventListener('mouseleave', function () {
            el.style.background = 'transparent';
          });
          el.addEventListener('click', function () {
            selectStock(el.getAttribute('data-symbol'));
          });
        });
        results.style.display = 'block';
      } catch (err) {
        console.error('Search error:', err);
      }
    }, 300);

    input.addEventListener('input', debouncedSearch);

    // Close dropdown on outside click
    document.addEventListener('click', function (e) {
      if (!input.contains(e.target) && !results.contains(e.target)) {
        results.style.display = 'none';
      }
    });

    // Navigate on Enter
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        results.style.display = 'none';
      }
    });
  }

  function selectStock(symbol) {
    var results = document.getElementById('stockSearchResults');
    if (results) results.style.display = 'none';
    var input = document.getElementById('stockSearchInput');
    if (input) input.value = '';
    window.location.href = '/stocks?symbol=' + encodeURIComponent(symbol);
  }

  // ---------------------------------------------------------------------------
  // 12. Floating AI chat widget
  // ---------------------------------------------------------------------------

  function initChatWidget() {
    var toggle = document.getElementById('chatToggleBtn');
    var panel = document.getElementById('chatPanel');
    if (toggle) {
      toggle.addEventListener('click', function () {
        toggleChat();
      });
    }
    var sendBtn = document.getElementById('chatSendBtn');
    var chatInput = document.getElementById('chatInput');
    if (sendBtn) {
      sendBtn.addEventListener('click', function () {
        sendChatMessage();
      });
    }
    if (chatInput) {
      chatInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendChatMessage();
        }
      });
    }
    loadChatHistory();
  }

  function toggleChat() {
    var panel = document.getElementById('chatPanel');
    if (!panel) return;
    chatOpen = !chatOpen;
    panel.style.display = chatOpen ? 'flex' : 'none';
    var badge = document.getElementById('chatBadge');
    if (badge) badge.style.display = 'none';
    if (chatOpen) {
      var input = document.getElementById('chatInput');
      if (input) input.focus();
      var body = document.getElementById('chatMessages');
      if (body) body.scrollTop = body.scrollHeight;
    }
  }

  async function sendChatMessage() {
    var input = document.getElementById('chatInput');
    if (!input) return;
    var msg = input.value.trim();
    if (!msg) return;
    input.value = '';

    appendChatBubble(msg, 'user');
    appendTypingIndicator();

    try {
      var data = await apiFetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, context: {} }),
      });
      removeTypingIndicator();
      if (data && data.success && data.response) {
        appendChatBubble(data.response, 'agent');
      } else {
        appendChatBubble(
          (data && data.message) || 'Sorry, something went wrong.',
          'agent'
        );
      }
    } catch (err) {
      removeTypingIndicator();
      appendChatBubble('Unable to reach AI assistant.', 'agent');
    }
  }

  function appendChatBubble(text, sender) {
    var body = document.getElementById('chatMessages');
    if (!body) return;
    var bubble = document.createElement('div');
    var isUser = sender === 'user';
    bubble.style.cssText =
      'max-width:85%;padding:10px 14px;border-radius:12px;font-size:13px;line-height:1.4;' +
      'word-wrap:break-word;margin-bottom:8px;' +
      (isUser
        ? 'background:rgba(0,212,255,0.15);color:#e0e0e0;align-self:flex-end;margin-left:auto;'
        : 'background:rgba(255,255,255,0.06);color:#e0e0e0;align-self:flex-start;');
    bubble.innerHTML = formatChatText(text);
    body.appendChild(bubble);
    body.scrollTop = body.scrollHeight;
  }

  function formatChatText(text) {
    var safe = escapeHtml(text);
    // Bold
    safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Newlines
    safe = safe.replace(/\n/g, '<br>');
    return safe;
  }

  function appendTypingIndicator() {
    var body = document.getElementById('chatMessages');
    if (!body) return;
    var el = document.createElement('div');
    el.id = 'typingIndicator';
    el.style.cssText =
      'color:#888;font-size:12px;padding:8px 14px;font-style:italic;';
    el.textContent = 'AI is thinking...';
    body.appendChild(el);
    body.scrollTop = body.scrollHeight;
  }

  function removeTypingIndicator() {
    var el = document.getElementById('typingIndicator');
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  async function loadChatHistory() {
    try {
      var data = await apiFetch('/api/chat/history?limit=15');
      if (!data || !data.history || data.history.length === 0) return;
      data.history.forEach(function (item) {
        if (item.message) appendChatBubble(item.message, 'user');
        if (item.response) appendChatBubble(item.response, 'agent');
      });
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  }

  // ---------------------------------------------------------------------------
  // 13. Trade modal
  // ---------------------------------------------------------------------------

  function openTradeModal() {
    var modal = document.getElementById('tradeModal');
    if (modal) {
      modal.style.display = 'flex';
      var symbolInput = document.getElementById('tradeStockSymbol');
      if (symbolInput) symbolInput.focus();
    }
  }

  function closeTradeModal() {
    var modal = document.getElementById('tradeModal');
    if (modal) modal.style.display = 'none';
    clearTradeForm();
  }

  function clearTradeForm() {
    ['tradeStockSymbol', 'tradeCompanyName', 'tradeQuantity', 'tradePrice'].forEach(
      function (id) {
        var el = document.getElementById(id);
        if (el) el.value = '';
      }
    );
    var typeSelect = document.getElementById('tradeType');
    if (typeSelect) typeSelect.value = 'BUY';
  }

  async function submitTrade() {
    var symbol = (
      document.getElementById('tradeStockSymbol')?.value || ''
    ).trim();
    var company = (
      document.getElementById('tradeCompanyName')?.value || ''
    ).trim();
    var type = document.getElementById('tradeType')?.value || 'BUY';
    var qty = parseInt(document.getElementById('tradeQuantity')?.value, 10);
    var price = parseFloat(document.getElementById('tradePrice')?.value);

    if (!symbol) {
      showToast('Please enter a stock symbol.', 'warning');
      return;
    }
    if (!qty || qty <= 0) {
      showToast('Please enter a valid quantity.', 'warning');
      return;
    }
    if (!price || price <= 0) {
      showToast('Please enter a valid price.', 'warning');
      return;
    }

    var submitBtn = document.getElementById('tradeSubmitBtn');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Recording...';
    }

    try {
      var data = await apiFetch('/api/dashboard/record-trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stock_symbol: symbol,
          company_name: company || symbol,
          trade_type: type,
          quantity: qty,
          price: price,
        }),
      });
      if (data && data.success) {
        showToast('Trade recorded successfully!', 'success');
        closeTradeModal();
        // Refresh relevant sections
        loadPortfolioOverview();
        loadRecentActivity();
        loadPortfolio();
      } else {
        showToast(
          (data && data.message) || 'Failed to record trade.',
          'error'
        );
      }
    } catch (err) {
      showToast('Error recording trade.', 'error');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Record Trade';
      }
    }
  }

  // Close modal on backdrop click
  function initTradeModal() {
    var modal = document.getElementById('tradeModal');
    if (modal) {
      modal.addEventListener('click', function (e) {
        if (e.target === modal) closeTradeModal();
      });
    }
    var closeBtn = document.getElementById('tradeModalClose');
    if (closeBtn) {
      closeBtn.addEventListener('click', closeTradeModal);
    }
    var submitBtn = document.getElementById('tradeSubmitBtn');
    if (submitBtn) {
      submitBtn.addEventListener('click', submitTrade);
    }
  }

  // ---------------------------------------------------------------------------
  // 14. WebSocket integration
  // ---------------------------------------------------------------------------

  function initWebSocket() {
    if (typeof io === 'undefined') {
      console.warn('Socket.IO not loaded; real-time updates disabled.');
      return;
    }
    socket = io({
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 10,
    });

    socket.on('connect', function () {
      console.log('Premium dashboard: WebSocket connected');
      updateConnectionBadge('connected');
      socket.emit('subscribe_predictions');
      socket.emit('subscribe_watchlist');
      socket.emit('subscribe_stock_prices', { symbols: [] });
    });

    socket.on('disconnect', function () {
      console.log('Premium dashboard: WebSocket disconnected');
      updateConnectionBadge('disconnected');
    });

    socket.on('connect_error', function () {
      updateConnectionBadge('error');
    });

    socket.on('prediction_update', function (data) {
      showToast('New prediction available', 'info');
      loadPredictions();
    });

    socket.on('watchlist_update', function (data) {
      loadWatchlist();
    });

    socket.on('stock_price_update', function (data) {
      // Update any matching price elements on the page
      if (data && data.symbol) {
        var priceEls = document.querySelectorAll(
          '[data-price-symbol="' + CSS.escape(data.symbol) + '"]'
        );
        priceEls.forEach(function (el) {
          el.textContent = formatCurrency(data.price || data.ltp);
        });
      }
    });

    socket.on('system_alert', function (data) {
      if (data && data.message) {
        showToast(data.message, data.type || 'info');
      }
    });
  }

  function updateConnectionBadge(status) {
    var badge = document.getElementById('connectionStatus');
    if (!badge) return;
    var cfg = {
      connected: { text: 'Live', color: '#00ff87' },
      disconnected: { text: 'Offline', color: '#ff4757' },
      error: { text: 'Error', color: '#ffaa00' },
    };
    var c = cfg[status] || cfg.disconnected;
    badge.textContent = c.text;
    badge.style.color = c.color;
  }

  // ---------------------------------------------------------------------------
  // 15. Sidebar navigation
  // ---------------------------------------------------------------------------

  function initSidebar() {
    var toggleBtn = document.getElementById('sidebarToggle');
    var sidebar = document.getElementById('sidebar');
    var mainContent = document.getElementById('mainContent');
    if (toggleBtn && sidebar) {
      toggleBtn.addEventListener('click', function () {
        sidebarCollapsed = !sidebarCollapsed;
        sidebar.classList.toggle('collapsed', sidebarCollapsed);
        if (mainContent) {
          mainContent.classList.toggle('sidebar-collapsed', sidebarCollapsed);
        }
      });
    }

    // Section navigation — smooth scroll
    var navLinks = document.querySelectorAll('[data-section]');
    navLinks.forEach(function (link) {
      link.addEventListener('click', function (e) {
        e.preventDefault();
        var sectionId = link.getAttribute('data-section');
        var section = document.getElementById(sectionId);
        if (section) {
          section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        // Active state
        navLinks.forEach(function (l) {
          l.classList.remove('active');
        });
        link.classList.add('active');
      });
    });
  }

  // ---------------------------------------------------------------------------
  // 16. Auto-refresh
  // ---------------------------------------------------------------------------

  function startAutoRefresh() {
    refreshInterval = setInterval(function () {
      loadMarketIndices();
      loadSentiment();
    }, REFRESH_MS);
  }

  function stopAutoRefresh() {
    if (refreshInterval) {
      clearInterval(refreshInterval);
      refreshInterval = null;
    }
  }

  // ---------------------------------------------------------------------------
  // Inject shimmer keyframes (once)
  // ---------------------------------------------------------------------------

  function injectStyles() {
    if (document.getElementById('premiumDashStyles')) return;
    var style = document.createElement('style');
    style.id = 'premiumDashStyles';
    style.textContent =
      '@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}' +
      '@keyframes slideInRight{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}';
    document.head.appendChild(style);
  }

  // ---------------------------------------------------------------------------
  // Master initialization
  // ---------------------------------------------------------------------------

  async function initDashboard() {
    injectStyles();
    setGreeting();
    initStockSearch();
    initSidebar();
    initTradeModal();
    initChatWidget();
    initWebSocket();

    // Load all sections in parallel
    await Promise.allSettled([
      loadPortfolioOverview(),
      loadMarketIndices(),
      loadPredictions(),
      loadWatchlist(),
      loadAIInsights(),
      loadRecentActivity(),
      loadSectorHeatmap(),
      loadSentiment(),
      loadUserLevel(),
      loadPortfolio(),
    ]);

    startAutoRefresh();
  }

  // ---------------------------------------------------------------------------
  // Public API (exposed on window for onclick handlers)
  // ---------------------------------------------------------------------------

  window.PremiumDashboard = {
    init: initDashboard,
    viewPrediction: viewPrediction,
    selectStock: selectStock,
    openTradeModal: openTradeModal,
    closeTradeModal: closeTradeModal,
    toggleChat: toggleChat,
    refresh: function () {
      loadPortfolioOverview();
      loadMarketIndices();
      loadPredictions();
      loadWatchlist();
      loadAIInsights();
      loadRecentActivity();
      loadSectorHeatmap();
      loadSentiment();
      loadUserLevel();
      loadPortfolio();
    },
    formatCurrency: formatCurrency,
    formatPercent: formatPercent,
    showToast: showToast,
  };

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
  } else {
    initDashboard();
  }
})();
