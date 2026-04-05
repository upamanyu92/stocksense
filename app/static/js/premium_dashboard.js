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
      document.body.getAttribute('data-username') || 'Investor';
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
    currentDetailSymbol = symbol;
    var section = document.getElementById('section-stockdetail');
    if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    var nameEl = document.getElementById('detailStockName');
    if (nameEl) nameEl.textContent = symbol;
    // Load all detail panels
    loadCandlestick(symbol, currentChartPeriod, currentChartInterval);
    loadTechnicalIndicators(symbol);
    loadAgentDebate(symbol);
    checkKillCriteria(symbol);
    // Update sidebar active
    document.querySelectorAll('[data-section]').forEach(function (l) { l.classList.remove('active'); });
    var detailLink = document.querySelector('[data-section="section-stockdetail"]');
    if (detailLink) detailLink.classList.add('active');
  }

  // ---------------------------------------------------------------------------
  // Stock detail state
  // ---------------------------------------------------------------------------
  var currentDetailSymbol = null;
  var currentChartPeriod = '3mo';
  var currentChartInterval = '1d';
  var lwChart = null;
  var lwCandleSeries = null;
  var lwLineSeries = null;

  // ---------------------------------------------------------------------------
  // NEW: Candlestick chart (TradingView Lightweight Charts)
  // ---------------------------------------------------------------------------

  function initChartTimeTabs() {
    var tabs = document.querySelectorAll('#chartTimeTabs .chart-tab');
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        tabs.forEach(function (t) { t.classList.remove('active'); });
        tab.classList.add('active');
        currentChartPeriod = tab.getAttribute('data-period');
        currentChartInterval = tab.getAttribute('data-interval');
        if (currentDetailSymbol) {
          loadCandlestick(currentDetailSymbol, currentChartPeriod, currentChartInterval);
        }
      });
    });
  }

  async function loadCandlestick(symbol, period, interval) {
    var container = document.getElementById('candlestickChart');
    if (!container) return;
    period = period || '3mo';
    interval = interval || '1d';

    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:360px;color:#666;"><i class="fas fa-spinner fa-spin" style="font-size:28px;"></i></div>';

    var data = await apiFetch('/api/dashboard/candlestick/' + encodeURIComponent(symbol) + '?period=' + period + '&interval=' + interval);
    if (!data || !data.success || !data.candles || data.candles.length === 0) {
      container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:360px;color:#888;flex-direction:column;gap:10px;"><i class="fas fa-chart-line" style="font-size:36px;"></i><p>No chart data available</p></div>';
      return;
    }

    container.innerHTML = '';
    container.style.height = '380px';

    // Use LightweightCharts if available
    if (typeof LightweightCharts !== 'undefined') {
      if (lwChart) {
        try { lwChart.remove(); } catch (e) {}
        lwChart = null;
      }

      lwChart = LightweightCharts.createChart(container, {
        width: container.clientWidth || 800,
        height: 380,
        layout: {
          background: { color: 'transparent' },
          textColor: '#a0a0b8',
        },
        grid: {
          vertLines: { color: 'rgba(255,255,255,0.04)' },
          horzLines: { color: 'rgba(255,255,255,0.04)' },
        },
        crosshair: {
          mode: LightweightCharts.CrosshairMode.Normal,
          vertLine: { color: 'rgba(0,212,255,0.4)', width: 1, style: 3 },
          horzLine: { color: 'rgba(0,212,255,0.4)', width: 1, style: 3 },
        },
        rightPriceScale: {
          borderColor: 'rgba(255,255,255,0.08)',
        },
        timeScale: {
          borderColor: 'rgba(255,255,255,0.08)',
          timeVisible: true,
        },
      });

      lwCandleSeries = lwChart.addCandlestickSeries({
        upColor: '#00ff87',
        downColor: '#ff4757',
        borderUpColor: '#00ff87',
        borderDownColor: '#ff4757',
        wickUpColor: '#00ff87',
        wickDownColor: '#ff4757',
      });

      var candleData = data.candles.map(function (c) {
        return { time: c.x, open: c.o, high: c.h, low: c.l, close: c.c };
      });
      lwCandleSeries.setData(candleData);

      // SMA-20 overlay
      var smaData = data.sma20.filter(function (s) { return s.y !== null; }).map(function (s) {
        return { time: s.x, value: s.y };
      });
      if (smaData.length > 0) {
        lwLineSeries = lwChart.addLineSeries({
          color: 'rgba(0,212,255,0.7)',
          lineWidth: 1.5,
          title: 'SMA 20',
          priceLineVisible: false,
        });
        lwLineSeries.setData(smaData);
      }

      lwChart.timeScale().fitContent();

      // Responsive resize
      var resizeObs = new ResizeObserver(function () {
        if (lwChart && container) {
          lwChart.resize(container.clientWidth, 380);
        }
      });
      resizeObs.observe(container);
    } else {
      // Fallback: Chart.js line chart
      var canvas = document.createElement('canvas');
      canvas.style.cssText = 'width:100%;height:360px;';
      container.appendChild(canvas);
      var closes = data.candles.map(function (c) { return c.c; });
      var labels = data.candles.map(function (c) { return c.x; });
      var existing = Chart.getChart(canvas);
      if (existing) existing.destroy();
      new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: symbol,
            data: closes,
            borderColor: '#00d4ff',
            borderWidth: 2,
            fill: true,
            backgroundColor: 'rgba(0,212,255,0.06)',
            tension: 0.3,
            pointRadius: 0,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: '#666', maxTicksLimit: 8 }, grid: { color: 'rgba(255,255,255,0.04)' } },
            y: { ticks: { color: '#666' }, grid: { color: 'rgba(255,255,255,0.04)' } }
          }
        }
      });
    }
  }

  // ---------------------------------------------------------------------------
  // NEW: Technical indicators with plain-English translation
  // ---------------------------------------------------------------------------

  async function loadTechnicalIndicators(symbol) {
    var container = document.getElementById('techIndicatorsContainer');
    var badge = document.getElementById('techOverallSignal');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;padding:20px;color:#666;"><i class="fas fa-spinner fa-spin"></i></div>';

    var data = await apiFetch('/api/dashboard/technical-indicators/' + encodeURIComponent(symbol));
    if (!data || !data.success || !data.indicators) {
      container.innerHTML = '<div style="color:#888;text-align:center;padding:16px;">No indicator data available</div>';
      return;
    }

    // Update overall badge
    if (badge) {
      badge.textContent = data.overall_signal || '—';
      badge.className = 'tech-overall-badge';
      if (data.overall_signal === 'Bullish') badge.classList.add('bullish');
      else if (data.overall_signal === 'Bearish') badge.classList.add('bearish');
    }

    var html = '<div class="tech-indicators-grid">';
    data.indicators.forEach(function (ind) {
      var signalClass = ind.signal === 'bullish' ? 'tech-bullish' : ind.signal === 'bearish' ? 'tech-bearish' : 'tech-neutral';
      var signalColor = ind.signal === 'bullish' ? '#00ff87' : ind.signal === 'bearish' ? '#ff4757' : '#ffaa00';
      html += '<div class="tech-indicator-card ' + signalClass + '">' +
        '<div class="tech-ind-header">' +
        '<span class="tech-ind-emoji">' + escapeHtml(ind.emoji) + '</span>' +
        '<span class="tech-ind-name">' + escapeHtml(ind.name) + '</span>' +
        '<span class="tech-ind-value" style="color:' + signalColor + ';">' + ind.value + '</span>' +
        '</div>' +
        '<div class="tech-ind-plain">' + escapeHtml(ind.plain_english) + '</div>' +
        '<div class="tech-ind-why"><i class="fas fa-circle-info" style="color:#3b82f6;font-size:10px;"></i> ' + escapeHtml(ind.why) + '</div>' +
        '</div>';
    });
    html += '</div>';
    container.innerHTML = html;
  }

  // ---------------------------------------------------------------------------
  // NEW: Agent Debate (Bull / Bear / Skeptic)
  // ---------------------------------------------------------------------------

  async function loadAgentDebate(symbol) {
    var container = document.getElementById('agentDebateContainer');
    var gaugeLabel = document.getElementById('gaugeLabel');
    var gaugeConf = document.getElementById('gaugeConf');
    var gaugeFill = document.getElementById('gaugeFill');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center;padding:20px;color:#666;"><i class="fas fa-spinner fa-spin"></i></div>';

    var data = await apiFetch('/api/dashboard/agent-reasoning/' + encodeURIComponent(symbol));
    if (!data || !data.success || !data.debate) {
      container.innerHTML = '<div style="color:#888;text-align:center;padding:16px;">No agent analysis available</div>';
      return;
    }

    var d = data.debate;

    // Update gauge
    if (gaugeLabel) {
      gaugeLabel.textContent = d.verdict || '—';
      gaugeLabel.style.color = d.verdict === 'Bull' ? '#00ff87' : d.verdict === 'Bear' ? '#ff4757' : '#ffaa00';
    }
    if (gaugeConf) {
      gaugeConf.textContent = d.verdict_summary || '';
    }
    if (gaugeFill) {
      var bullAgent = d.agents.find(function (a) { return a.id === 'bull'; });
      var bearAgent = d.agents.find(function (a) { return a.id === 'bear'; });
      var bullConf = bullAgent ? bullAgent.confidence_pct : 50;
      var bearConf = bearAgent ? bearAgent.confidence_pct : 50;
      var netBullish = (bullConf - bearConf + 100) / 200;  // 0-1
      var circumference = 157;
      var offset = circumference - (netBullish * circumference);
      gaugeFill.style.strokeDashoffset = offset;
      gaugeFill.style.stroke = netBullish > 0.6 ? '#00ff87' : netBullish < 0.4 ? '#ff4757' : '#ffaa00';
    }

    // Build debate thread
    var html = '<div class="debate-messages">';
    d.agents.forEach(function (agent) {
      var agentClass = 'debate-' + agent.id;
      var gradeColors = { 'High': '#00ff87', 'Medium': '#ffaa00', 'Low': '#ff4757' };
      var gradeColor = gradeColors[agent.evidence_grade] || '#aaa';

      html += '<div class="debate-message-row ' + agentClass + '">' +
        '<div class="debate-avatar" style="background:' + agent.color + '18;border:1px solid ' + agent.color + '40;">' +
        escapeHtml(agent.avatar) + '</div>' +
        '<div class="debate-bubble" style="border-left:3px solid ' + agent.color + ';">' +
        '<div class="debate-bubble-header">' +
        '<span class="debate-agent-name" style="color:' + agent.color + ';">' + escapeHtml(agent.name) + '</span>' +
        '<span class="debate-stance-badge" style="background:' + agent.color + '18;color:' + agent.color + ';">' + escapeHtml(agent.stance) + '</span>' +
        '<span class="debate-evidence-badge" style="color:' + gradeColor + ';border-color:' + gradeColor + '40;">' +
        '<i class="fas fa-check-circle" style="font-size:9px;"></i> ' + escapeHtml(agent.evidence_grade) + ' Confidence' +
        ' &bull; ' + agent.evidence_sources + ' Sources</span>' +
        '</div>' +
        '<p class="debate-summary">' + escapeHtml(agent.summary) + '</p>' +
        '<ul class="debate-args">';
      agent.arguments.forEach(function (arg) {
        html += '<li>' + escapeHtml(arg) + '</li>';
      });
      html += '</ul>' +
        '<div class="debate-conf-bar">' +
        '<span style="font-size:11px;color:#777;">Conviction</span>' +
        '<div class="debate-conf-track"><div class="debate-conf-fill" style="width:' + agent.confidence_pct + '%;background:' + agent.color + ';"></div></div>' +
        '<span style="font-size:11px;color:' + agent.color + ';">' + agent.confidence_pct + '%</span>' +
        '</div>' +
        '</div></div>';
    });
    html += '</div>';

    // Verdict summary
    html += '<div class="debate-verdict">' +
      '<i class="fas fa-gavel" style="color:#ffd700;"></i>' +
      '<span class="debate-verdict-text">' + escapeHtml(d.verdict_summary) + '</span>' +
      '</div>';

    container.innerHTML = html;
  }

  // ---------------------------------------------------------------------------
  // NEW: Portfolio Risk Meter
  // ---------------------------------------------------------------------------

  async function loadRiskMeter() {
    var data = await apiFetch('/api/dashboard/risk-meter');
    var scoreEl = document.getElementById('riskScore');
    var labelEl = document.getElementById('riskLabel');
    var fillEl = document.getElementById('riskRingFill');
    var msgEl = document.getElementById('riskMessage');
    var breakdownEl = document.getElementById('riskBreakdownList');

    if (!data || !data.success || !data.risk) {
      if (scoreEl) scoreEl.textContent = '—';
      if (labelEl) labelEl.textContent = 'No Data';
      return;
    }

    var r = data.risk;
    var score = r.score || 0;

    // Animate ring
    if (fillEl) {
      var circumference = 502;
      var offset = circumference - (score / 100) * circumference;
      fillEl.style.transition = 'stroke-dashoffset 1s cubic-bezier(0.16,1,0.3,1)';
      fillEl.style.stroke = r.color || '#ffaa00';
      fillEl.style.strokeDashoffset = offset;
    }
    if (scoreEl) scoreEl.textContent = score;
    if (labelEl) {
      labelEl.textContent = r.label || '—';
      labelEl.style.color = r.color || '#ffaa00';
    }
    if (msgEl) {
      msgEl.innerHTML = '<span style="color:' + (r.color || '#aaa') + ';">' +
        escapeHtml(r.icon || '') + ' ' + escapeHtml(r.message || '') + '</span>';
    }

    if (breakdownEl && r.breakdown) {
      var html = '';
      r.breakdown.forEach(function (item) {
        var pct = Math.min(item.score / 40 * 100, 100);
        html += '<div class="risk-breakdown-item">' +
          '<div class="risk-breakdown-header">' +
          '<span class="risk-breakdown-label">' + escapeHtml(item.label) + '</span>' +
          '<span class="risk-breakdown-score">' + Math.round(item.score) + '</span>' +
          '</div>' +
          '<div class="risk-breakdown-bar"><div class="risk-breakdown-fill" style="width:' + pct + '%;background:' + (r.color || '#ffaa00') + ';"></div></div>' +
          '<div class="risk-breakdown-detail">' + escapeHtml(item.detail) + '</div>' +
          '</div>';
      });
      breakdownEl.innerHTML = html;
    }
  }

  // ---------------------------------------------------------------------------
  // NEW: Kill criteria checker
  // ---------------------------------------------------------------------------

  async function checkKillCriteria(symbol) {
    var data = await apiFetch('/api/dashboard/kill-criteria/' + encodeURIComponent(symbol));
    if (!data || !data.success) return;

    if (data.triggered) {
      var banner = document.getElementById('killBanner');
      var titleEl = document.getElementById('killBannerTitle');
      var msgEl = document.getElementById('killBannerMsg');
      if (banner) banner.removeAttribute('hidden');
      if (titleEl) titleEl.textContent = (data.notification && data.notification.title) || ('Kill Criterion: ' + symbol);
      if (msgEl) msgEl.textContent = data.reasons && data.reasons[0] ? data.reasons[0] : 'Threshold breached';
      showToast((data.notification && data.notification.body) || 'Kill criterion triggered for ' + symbol, 'warning');
    }
  }

  async function checkKillCriteriaBatch() {
    var data = await apiFetch('/api/dashboard/kill-criteria-batch');
    if (!data || !data.success) return;
    if (data.triggered && data.triggered.length > 0) {
      var badge = document.getElementById('alertsBadge');
      if (badge) {
        badge.textContent = data.triggered.length;
        badge.removeAttribute('hidden');
      }
      data.triggered.forEach(function (item) {
        if (item.severity === 'critical') {
          showToast('⚠️ ' + item.message, 'error');
        }
      });
    }
  }

  // ---------------------------------------------------------------------------
  // NEW: Alerts feed
  // ---------------------------------------------------------------------------

  async function loadAlertsFeed() {
    var container = document.getElementById('alertsFeedContainer');
    if (!container) return;

    var data = await apiFetch('/api/dashboard/alerts-feed');
    if (!data || !data.success || !data.alerts || data.alerts.length === 0) {
      container.innerHTML = '<div style="text-align:center;color:#888;padding:32px;"><i class="fas fa-bell-slash" style="font-size:28px;margin-bottom:10px;"></i><p>No alerts yet. Set price targets to receive notifications.</p></div>';
      return;
    }

    // Update sidebar badge
    if (data.kill_criteria_count > 0) {
      var badge = document.getElementById('alertsBadge');
      if (badge) {
        badge.textContent = data.kill_criteria_count;
        badge.removeAttribute('hidden');
      }
    }

    var severityIcons = {
      high: { icon: 'fa-triangle-exclamation', color: '#ff4757' },
      medium: { icon: 'fa-circle-exclamation', color: '#ffaa00' },
      low: { icon: 'fa-circle-info', color: '#3b82f6' },
      critical: { icon: 'fa-skull-crossbones', color: '#ff0040' },
    };

    var html = '';
    data.alerts.forEach(function (alert) {
      var cfg = severityIcons[alert.severity] || severityIcons.low;
      var isKill = alert.is_kill_criteria;
      var borderColor = isKill ? '#ff4757' : cfg.color;
      html += '<div class="alert-feed-item severity-' + escapeHtml(alert.severity) + (isKill ? ' kill-item' : '') + '">' +
        '<div class="alert-feed-icon" style="color:' + cfg.color + ';">' +
        '<i class="fas ' + cfg.icon + '"></i></div>' +
        '<div class="alert-feed-body">' +
        '<div class="alert-feed-header">' +
        '<span class="alert-feed-symbol">' + escapeHtml(alert.symbol || '') + '</span>' +
        '<span class="alert-feed-type" style="color:' + cfg.color + ';">' + escapeHtml(alert.type || '') + '</span>' +
        (isKill ? '<span class="kill-badge">⚠️ Kill Criterion</span>' : '') +
        '</div>' +
        '<p class="alert-feed-msg">' + escapeHtml(alert.message || '') + '</p>' +
        '<div class="alert-feed-meta">' +
        (alert.timestamp ? new Date(alert.timestamp).toLocaleString('en-IN') : '') +
        (isKill ? ' &bull; <button class="alert-paper-btn" onclick="window.PremiumDashboard.viewPrediction(\'' + escapeHtml(alert.symbol) + '\')"><i class="fas fa-flask"></i> Simulate Exit</button>' : '') +
        '</div>' +
        '</div></div>';
    });
    container.innerHTML = html;
  }

  // ---------------------------------------------------------------------------
  // NEW: Paper trade modal
  // ---------------------------------------------------------------------------

  function openPaperTrade(symbol) {
    var modal = document.getElementById('paperTradeModal');
    if (!modal) return;
    var symInput = document.getElementById('paperSymbol');
    var resultDiv = document.getElementById('paperTradeResult');
    if (symInput) symInput.value = symbol || currentDetailSymbol || '';
    if (resultDiv) resultDiv.setAttribute('hidden', '');
    modal.removeAttribute('hidden');
    modal.style.display = 'flex';
  }

  function closePaperTrade() {
    var modal = document.getElementById('paperTradeModal');
    if (modal) { modal.style.display = 'none'; modal.setAttribute('hidden', ''); }
  }

  function initPaperTradeModal() {
    var form = document.getElementById('paperTradeForm');
    if (form) {
      form.addEventListener('submit', async function (e) {
        e.preventDefault();
        var symbol = (document.getElementById('paperSymbol')?.value || '').trim();
        var qty = parseInt(document.getElementById('paperQty')?.value || '0', 10);
        var price = parseFloat(document.getElementById('paperPrice')?.value || '0');
        var submitBtn = document.getElementById('paperTradeSubmit');
        if (!symbol) { showToast('Enter a symbol', 'warning'); return; }
        if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Simulating…'; }

        var data = await apiFetch('/api/dashboard/paper-trade', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol: symbol, quantity: qty || null, exit_price: price || null, action: 'sell' }),
        });

        if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<i class="fas fa-calculator"></i> Run Simulation'; }
        var resultDiv = document.getElementById('paperTradeResult');
        if (!resultDiv) return;

        if (data && data.success && data.simulation) {
          var sim = data.simulation;
          var pnlPositive = sim.gross_pnl >= 0;
          var pnlColor = pnlPositive ? '#00ff87' : '#ff4757';
          resultDiv.removeAttribute('hidden');
          resultDiv.innerHTML =
            '<div class="paper-result-inner">' +
            '<div class="paper-result-header">Simulation Result — ' + escapeHtml(sim.company) + '</div>' +
            '<div class="paper-result-grid">' +
            '<div class="paper-stat"><span>Avg Buy</span><strong>' + formatCurrency(sim.avg_buy_price) + '</strong></div>' +
            '<div class="paper-stat"><span>Exit Price</span><strong>' + formatCurrency(sim.exit_price) + '</strong></div>' +
            '<div class="paper-stat"><span>Qty</span><strong>' + sim.quantity + '</strong></div>' +
            '<div class="paper-stat"><span>Gross P&L</span><strong style="color:' + pnlColor + ';">' + (pnlPositive ? '+' : '') + formatCurrency(sim.gross_pnl) + ' (' + (pnlPositive ? '+' : '') + sim.pnl_pct.toFixed(2) + '%)</strong></div>' +
            '<div class="paper-stat"><span>Tax Est.</span><strong style="color:#ffaa00;">-' + formatCurrency(sim.tax_estimate) + '</strong></div>' +
            '<div class="paper-stat"><span>Net Proceeds</span><strong>' + formatCurrency(sim.net_proceeds) + '</strong></div>' +
            '</div>' +
            '<div class="paper-recommendation" style="color:' + pnlColor + ';">' +
            '<i class="fas fa-robot"></i> ' + escapeHtml(sim.recommendation) +
            '</div>' +
            '<div class="paper-disclaimer">' + escapeHtml(sim.disclaimer) + '</div>' +
            '</div>';
        } else {
          resultDiv.removeAttribute('hidden');
          resultDiv.innerHTML = '<div style="color:#ff4757;text-align:center;padding:12px;">Simulation failed. Please try again.</div>';
        }
      });
    }

    var closes = [document.getElementById('paperTradeClose'), document.getElementById('paperTradeClose2')];
    closes.forEach(function (btn) {
      if (btn) btn.addEventListener('click', closePaperTrade);
    });
    var modal = document.getElementById('paperTradeModal');
    if (modal) {
      modal.addEventListener('click', function (e) {
        if (e.target === modal || e.target.classList.contains('modal-backdrop')) closePaperTrade();
      });
    }
  }

  function scrollToDebate() {
    var card = document.getElementById('agentDebateCard');
    if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
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
      '<th style="padding:8px 10px;width:60px;"></th>' +
      '</tr></thead><tbody>';

    data.watchlist.forEach(function (item, i) {
      var change = item.change_percent || item.p_change || 0;
      var positive = change >= 0;
      var color = positive ? '#00ff87' : '#ff4757';
      var sparkId = 'wlSparkline' + i;
      var sym = escapeHtml(item.symbol || item.stock_symbol || '');
      html +=
        '<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">' +
        '<td style="padding:10px;">' +
        '<div style="font-weight:600;">' +
        escapeHtml(item.company_name || item.symbol || item.stock_symbol) +
        '</div>' +
        '<div style="font-size:11px;color:#aaa;">' + sym + '</div></td>' +
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
        '" style="width:60px;height:22px;"></canvas></td>' +
        '<td style="padding:10px;">' +
        '<button class="watchlist-remove-btn" data-remove-sym="' + sym + '" title="Remove">' +
        '<i class="fas fa-times"></i>' +
        '</button></td></tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;

    // Wire up remove buttons via event delegation (avoids inline-onclick XSS)
    container.querySelectorAll('.watchlist-remove-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        removeFromWatchlist(btn.getAttribute('data-remove-sym'));
      });
    });

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
    data.sectors.forEach(function (s, idx) {
      var change = s.avg_change || 0;
      var stockCount = s.stock_count || 0;
      var gainers = s.gainers || 0;
      var losers = s.losers || 0;
      var neutral = Math.max(stockCount - gainers - losers, 0);
      var trendClass = 'flat';
      if (change > 2) trendClass = 'strong-gain';
      else if (change > 0) trendClass = 'gain';
      else if (change < -2) trendClass = 'strong-loss';
      else if (change < 0) trendClass = 'loss';
      var breadthPct =
        stockCount > 0
          ? Math.max(0, Math.min(100, Math.round((gainers / stockCount) * 100)))
          : 0;
      var delay = Math.min(idx * 0.06, 0.6).toFixed(2);
      html +=
        '<article class="heatmap-cell ' +
        trendClass +
        '" style="--enter-delay:' +
        delay +
        's;">' +
        '<div class="heatmap-cell-top">' +
        '<div class="heatmap-cell-label" title="' +
        escapeHtml(s.name) +
        '">' +
        escapeHtml(s.name) +
        '</div>' +
        '<div class="heatmap-cell-value">' +
        formatPercent(change) +
        '</div>' +
        '</div>' +
        '<div class="heatmap-cell-metrics">' +
        '<span><i class="fas fa-layer-group"></i> ' +
        stockCount +
        '</span>' +
        '<span class="is-gain"><i class="fas fa-arrow-up"></i> ' +
        gainers +
        '</span>' +
        '<span class="is-loss"><i class="fas fa-arrow-down"></i> ' +
        losers +
        '</span>' +
        '<span><i class="fas fa-minus"></i> ' +
        neutral +
        '</span>' +
        '</div>' +
        '<div class="heatmap-progress-track" role="presentation">' +
        '<div class="heatmap-progress-fill" style="width:' +
        breadthPct +
        '%"></div>' +
        '</div>' +
        '<div class="heatmap-cell-meta"><span>Breadth</span><strong>' +
        breadthPct +
        '%</strong></div>' +
        '</article>';
    });
    container.innerHTML =
      '<div class="heatmap-grid compact-heatmap" data-count="' +
      data.sectors.length +
      '">' +
      html +
      '</div>';
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
          var symSafe = escapeHtml(symbol);
          var nameSafe = escapeHtml(name);
          html +=
            '<div class="search-result-item" data-symbol="' + symSafe + '" data-name="' + nameSafe + '">' +
            '<div class="search-result-name">' + nameSafe + '</div>' +
            '<div class="search-result-symbol">' + symSafe + '</div>' +
            '<div class="search-result-actions">' +
            '<button class="search-result-btn btn-view" data-action="view" data-symbol="' + symSafe + '">' +
            '<i class="fas fa-chart-line"></i> View Analysis</button>' +
            '<button class="search-result-btn btn-watch" data-action="watch" data-symbol="' + symSafe + '" data-name="' + nameSafe + '">' +
            '<i class="fas fa-star"></i> Watchlist</button>' +
            '</div></div>';
        });
        results.innerHTML = html;
        // Attach click handlers via event delegation
        results.querySelectorAll('[data-action="view"]').forEach(function (btn) {
          btn.addEventListener('click', function (e) {
            e.stopPropagation();
            selectStock(btn.getAttribute('data-symbol'));
          });
        });
        results.querySelectorAll('[data-action="watch"]').forEach(function (btn) {
          btn.addEventListener('click', function (e) {
            e.stopPropagation();
            addToWatchlist(btn.getAttribute('data-symbol'), btn.getAttribute('data-name'));
            results.style.display = 'none';
            var inp = document.getElementById('stockSearchInput');
            if (inp) inp.value = '';
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
    // Show the stock detail section instead of navigating away
    viewPrediction(symbol);
    var detailSection = document.getElementById('section-stockdetail');
    if (detailSection) {
      detailSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  // ---------------------------------------------------------------------------
  // Watchlist add / remove helpers
  // ---------------------------------------------------------------------------

  async function addToWatchlist(symbol, companyName) {
    if (!symbol) { showToast('Symbol is required', 'warning'); return; }
    try {
      var data = await apiFetch('/api/watchlist/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stock_symbol: symbol, company_name: companyName || symbol }),
      });
      if (data && data.success) {
        showToast(symbol + ' added to watchlist', 'success');
        loadWatchlist();
      } else {
        showToast((data && data.error) || 'Could not add to watchlist', 'error');
      }
    } catch (err) {
      showToast('Error adding to watchlist', 'error');
    }
  }

  async function removeFromWatchlist(symbol) {
    if (!symbol) return;
    try {
      var data = await apiFetch('/api/watchlist/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stock_symbol: symbol }),
      });
      if (data && data.success) {
        showToast(symbol + ' removed from watchlist', 'info');
        loadWatchlist();
      } else {
        showToast((data && data.error) || 'Could not remove', 'error');
      }
    } catch (err) {
      showToast('Error removing from watchlist', 'error');
    }
  }

  function toggleWatchlistAdd() {
    var panel = document.getElementById('watchlistAddPanel');
    if (!panel) return;
    var isVisible = panel.classList.contains('visible');
    if (isVisible) {
      panel.classList.remove('visible');
    } else {
      panel.classList.add('visible');
      var inp = document.getElementById('watchlistSearchInput');
      if (inp) inp.focus();
    }
  }

  async function watchlistAddSearch() {
    var input = document.getElementById('watchlistSearchInput');
    var query = input ? input.value.trim() : '';
    if (query.length < 2) { showToast('Enter at least 2 characters', 'warning'); return; }
    var resultsEl = document.getElementById('watchlistSearchResults');
    if (resultsEl) {
      resultsEl.innerHTML = '<div style="padding:10px;color:#aaa;font-size:13px;"><i class="fas fa-spinner fa-spin"></i> Searching…</div>';
      resultsEl.style.display = 'block';
    }
    try {
      var data = await apiFetch('/api/stocks/search?q=' + encodeURIComponent(query) + '&max_results=8');
      if (!data || !data.results || data.results.length === 0) {
        data = await apiFetch('/api/stocks/suggestions?q=' + encodeURIComponent(query) + '&limit=8');
      }
      var items = (data && (data.results || data.suggestions)) || [];
      if (!items.length) {
        if (resultsEl) resultsEl.innerHTML = '<div style="padding:10px;color:#888;font-size:13px;">No results found</div>';
        return;
      }
      var html = '';
      items.forEach(function (item) {
        var sym = escapeHtml(item.symbol || item.security_id || '');
        var name = escapeHtml(item.company_name || item.name || sym);
        html += '<div class="search-result-item" style="display:flex;justify-content:space-between;align-items:center;"' +
          ' data-sym="' + sym + '" data-name="' + name + '">' +
          '<div><div class="search-result-name">' + name + '</div><div class="search-result-symbol">' + sym + '</div></div>' +
          '<button class="search-result-btn btn-watch wl-add-btn" data-sym="' + sym + '" data-name="' + name + '">' +
          '<i class="fas fa-plus"></i> Add</button>' +
          '</div>';
      });
      if (resultsEl) {
        resultsEl.innerHTML = html;
        resultsEl.style.display = 'block';
        // Wire up Add buttons via event delegation to prevent inline-onclick XSS
        resultsEl.querySelectorAll('.wl-add-btn').forEach(function (btn) {
          btn.addEventListener('click', function (e) {
            e.stopPropagation();
            addToWatchlist(btn.getAttribute('data-sym'), btn.getAttribute('data-name'));
            toggleWatchlistAdd();
          });
        });
      }
    } catch (err) {
      if (resultsEl) resultsEl.innerHTML = '<div style="padding:10px;color:#f55;font-size:13px;">Search failed</div>';
    }
  }

  // ---------------------------------------------------------------------------
  // Notification bell panel
  // ---------------------------------------------------------------------------

  async function loadNotifications() {
    try {
      var data = await apiFetch('/api/notifications/?sent=0');
      var body = document.getElementById('notifPanelBody');
      var dot = document.getElementById('notifDot');
      if (!data || !data.notifications || data.notifications.length === 0) {
        if (body) body.innerHTML = '<div class="notification-panel-empty"><i class="fas fa-bell-slash" style="font-size:20px;margin-bottom:8px;display:block;"></i>No new notifications</div>';
        if (dot) dot.style.display = 'none';
        return;
      }
      if (dot) dot.style.display = 'block';
      var html = '';
      data.notifications.slice(0, 10).forEach(function (n) {
        html += '<div class="notification-panel-item">' +
          '<div class="notification-item-title">' + escapeHtml(n.symbol || 'Alert') + '</div>' +
          '<div class="notification-item-msg">' + escapeHtml(n.message || '') + '</div>' +
          '</div>';
      });
      if (body) body.innerHTML = html;
    } catch (err) {
      // Silently fail
    }
  }

  function initNotificationBell() {
    var btn = document.getElementById('notifBellBtn');
    var panel = document.getElementById('notifPanel');
    if (!btn || !panel) return;
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      panel.classList.toggle('open');
      if (panel.classList.contains('open')) {
        loadNotifications();
      }
    });
    document.addEventListener('click', function (e) {
      if (panel.classList.contains('open') && !panel.contains(e.target) && e.target !== btn) {
        panel.classList.remove('open');
      }
    });
  }

  function openAccountSection() {
    var s = document.getElementById('section-settings');
    if (s) {
      s.style.display = 'block';
      s.scrollIntoView({ behavior: 'smooth', block: 'start' });
      loadAccountSection();
    }
    return false;
  }

  // ---------------------------------------------------------------------------
  // Account / Settings section loader
  // ---------------------------------------------------------------------------

  async function loadAccountSection() {
    try {
      var ovData = await apiFetch('/api/dashboard/overview');
      var lvData = await apiFetch('/api/dashboard/user-level');
      if (ovData && ovData.success && ovData.overview) {
        var o = ovData.overview;
        var el = function (id) { return document.getElementById(id); };
        if (el('acctHoldings')) el('acctHoldings').textContent = o.holdings_count || 0;
        if (el('acctWatchlist')) el('acctWatchlist').textContent = o.watchlist_count || 0;
        if (el('acctPredictions')) el('acctPredictions').textContent = o.predictions_count || 0;
        if (el('acctTrades')) el('acctTrades').textContent = o.recent_trades || 0;
      }
      if (lvData && lvData.success && lvData.level) {
        var lv = lvData.level;
        var el2 = function (id) { return document.getElementById(id); };
        if (el2('acctLevel')) el2('acctLevel').textContent = lv.level_name || '—';
        if (el2('acctXp')) el2('acctXp').textContent = (lv.xp_points || 0) + ' XP';
        if (el2('acctStreak')) el2('acctStreak').textContent = (lv.streak_days || 0) + ' days';
      }
    } catch (err) {
      // Silently fail
    }
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
    if (chatOpen) {
      panel.removeAttribute('hidden');
    } else {
      panel.setAttribute('hidden', '');
    }
    var badge = document.getElementById('chatBadge');
    if (badge) badge.setAttribute('hidden', '');
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
      modal.removeAttribute('hidden');
      modal.style.display = 'flex';
      var symbolInput = document.getElementById('tradeStockSymbol');
      if (symbolInput) symbolInput.focus();
    }
  }

  function closeTradeModal() {
    var modal = document.getElementById('tradeModal');
    if (modal) {
      modal.style.display = 'none';
      modal.setAttribute('hidden', '');
    }
    clearTradeForm();
  }

  function clearTradeForm() {
    ['tradeStockSymbol', 'tradeCompanyName', 'tradeQuantity', 'tradePrice'].forEach(
      function (id) {
        var el = document.getElementById(id);
        if (el) el.value = '';
      }
    );
    var typeRadio = document.querySelector('input[name="trade_type"][value="BUY"]');
    if (typeRadio) typeRadio.checked = true;
  }

  async function submitTrade() {
    var symbol = (
      document.getElementById('tradeStockSymbol')?.value || ''
    ).trim();
    var company = (
      document.getElementById('tradeCompanyName')?.value || ''
    ).trim();
    var type = 'BUY';
    var tradeTypeRadios = document.querySelectorAll('input[name="trade_type"]');
    tradeTypeRadios.forEach(function(r) { if (r.checked) type = r.value; });
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
        if (e.target === modal || e.target.classList.contains('modal-backdrop')) closeTradeModal();
      });
    }
    // Open modal via any [data-action="add-trade"] button
    document.querySelectorAll('[data-action="add-trade"]').forEach(function (btn) {
      btn.addEventListener('click', openTradeModal);
    });
    // Close buttons (there may be multiple with class trade-modal-close)
    document.querySelectorAll('.trade-modal-close').forEach(function (btn) {
      btn.addEventListener('click', closeTradeModal);
    });
    var closeBtn = document.getElementById('tradeModalClose');
    if (closeBtn) {
      closeBtn.addEventListener('click', closeTradeModal);
    }
    // Form submission
    var form = document.getElementById('tradeForm');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        submitTrade();
      });
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

        // Special handling for settings section (toggled show/hide)
        if (sectionId === 'section-settings') {
          var settingsSection = document.getElementById('section-settings');
          if (settingsSection) {
            settingsSection.style.display =
              settingsSection.style.display === 'none' ? 'block' : 'none';
            if (settingsSection.style.display === 'block') {
              settingsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
              loadAccountSection();
            }
          }
        } else if (section) {
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
  // Portfolio Management Features
  // ---------------------------------------------------------------------------

  /** Switch portfolio sub-tabs */
  function pfSwitchTab(btn, tabId) {
    var parent = btn.closest('.dashboard-section');
    if (!parent) return;
    parent.querySelectorAll('.av-tab').forEach(function (b) { b.classList.remove('active'); });
    parent.querySelectorAll('.av-tab-content').forEach(function (el) { el.style.display = 'none'; });
    btn.classList.add('active');
    var tab = document.getElementById(tabId);
    if (tab) tab.style.display = 'block';

    // Load data for the tab
    if (tabId === 'pfTransactionsTab') loadTransactions();
    if (tabId === 'pfAllocationTab') loadAllocation();
  }

  /** Load portfolio summary cards */
  async function loadPortfolioSummary() {
    try {
      var data = await apiFetch('/api/portfolio/summary');
      if (!data || !data.success) return;
      var s = data.summary;
      var inv = document.getElementById('pfTotalInvested');
      var cur = document.getElementById('pfCurrentValue');
      var pnl = document.getElementById('pfTotalPnl');
      if (inv) inv.textContent = formatCurrency(s.total_invested);
      if (cur) cur.textContent = formatCurrency(s.total_current_value);
      if (pnl) {
        pnl.textContent = formatCurrency(s.total_pnl) + ' (' + formatPercent(s.pnl_percent) + ')';
        pnl.style.color = s.total_pnl >= 0 ? '#00ff87' : '#ff4757';
      }
    } catch (e) { /* ignore */ }
  }

  /** Load transactions list */
  async function loadTransactions() {
    var container = document.getElementById('transactionsContainer');
    if (!container) return;
    container.innerHTML = '<p style="color:#888;text-align:center;padding:16px;">Loading...</p>';
    try {
      var data = await apiFetch('/api/portfolio/transactions?limit=30');
      if (!data || !data.success || !data.transactions || data.transactions.length === 0) {
        container.innerHTML = '<p style="color:#888;text-align:center;padding:24px;">No transactions yet.</p>';
        return;
      }
      var html = '<table style="width:100%;border-collapse:collapse;font-size:13px;">' +
        '<thead><tr style="color:#aaa;text-align:left;border-bottom:1px solid rgba(255,255,255,0.08);">' +
        '<th style="padding:8px;">Date</th><th style="padding:8px;">Symbol</th>' +
        '<th style="padding:8px;">Type</th><th style="padding:8px;">Qty</th>' +
        '<th style="padding:8px;">Price</th><th style="padding:8px;">Total</th>' +
        '<th style="padding:8px;"></th></tr></thead><tbody>';
      data.transactions.forEach(function (t) {
        var typeColor = t.transaction_type === 'BUY' ? '#00ff87' : '#ff4757';
        html += '<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">' +
          '<td style="padding:8px;">' + escapeHtml(t.transaction_date || '') + '</td>' +
          '<td style="padding:8px;font-weight:600;">' + escapeHtml(t.stock_symbol) + '</td>' +
          '<td style="padding:8px;color:' + typeColor + ';font-weight:600;">' + escapeHtml(t.transaction_type) + '</td>' +
          '<td style="padding:8px;">' + t.quantity + '</td>' +
          '<td style="padding:8px;">' + formatCurrency(t.price) + '</td>' +
          '<td style="padding:8px;">' + formatCurrency(t.total_value) + '</td>' +
          '<td style="padding:8px;"><button onclick="deleteTransaction(' + t.id + ')" style="background:none;border:none;color:#ff4757;cursor:pointer;" title="Delete"><i class="fas fa-trash-can"></i></button></td></tr>';
      });
      html += '</tbody></table>';
      container.innerHTML = html;
    } catch (e) {
      container.innerHTML = '<p style="color:#ff4757;text-align:center;padding:16px;">Failed to load transactions.</p>';
    }
  }

  /** Delete a transaction */
  async function deleteTransaction(id) {
    if (!confirm('Delete this transaction? Holdings will be recalculated.')) return;
    try {
      var resp = await apiFetch('/api/portfolio/transactions/' + id, { method: 'DELETE' });
      if (resp && resp.success) {
        showToast('Transaction deleted', 'success');
        loadTransactions();
        loadPortfolio();
        loadPortfolioSummary();
      } else {
        showToast('Failed to delete transaction', 'error');
      }
    } catch (e) {
      showToast('Error deleting transaction', 'error');
    }
  }

  /** Load asset allocation chart */
  async function loadAllocation() {
    try {
      var data = await apiFetch('/api/portfolio/allocation');
      var listEl = document.getElementById('allocationList');
      var canvas = document.getElementById('allocationChart');
      if (!data || !data.success || !data.allocation || data.allocation.length === 0) {
        if (listEl) listEl.innerHTML = '<p style="color:#888;text-align:center;">No allocation data. Add holdings first.</p>';
        return;
      }

      // Render chart
      if (canvas && window.Chart) {
        var ctx = canvas.getContext('2d');
        if (canvas._chartInstance) canvas._chartInstance.destroy();
        var labels = data.allocation.map(function (a) { return a.stock_symbol; });
        var values = data.allocation.map(function (a) { return a.allocation_percent; });
        var colors = ['#00ff87', '#00d4ff', '#ffd93d', '#ff6b9d', '#a855f7',
                      '#06b6d4', '#f59e0b', '#ef4444', '#8b5cf6', '#10b981'];
        canvas._chartInstance = new Chart(ctx, {
          type: 'doughnut',
          data: { labels: labels, datasets: [{ data: values, backgroundColor: colors.slice(0, values.length) }] },
          options: {
            responsive: true,
            plugins: {
              legend: { position: 'right', labels: { color: '#ccc', font: { size: 11 } } },
            },
          },
        });
      }

      // Render list
      if (listEl) {
        var html = '';
        data.allocation.forEach(function (a) {
          html += '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">' +
            '<span>' + escapeHtml(a.stock_symbol) + '</span>' +
            '<span style="color:#aaa;">' + a.allocation_percent.toFixed(1) + '% · ' + formatCurrency(a.invested_value) + '</span></div>';
        });
        listEl.innerHTML = html;
      }
    } catch (e) { /* ignore */ }
  }

  /** Run AI portfolio analysis */
  async function runPortfolioAnalysis(type) {
    var result = document.getElementById('aiAnalysisResult');
    var meta = document.getElementById('aiAnalysisMeta');
    if (result) result.innerHTML = '<p style="color:#888;text-align:center;"><i class="fas fa-spinner fa-spin"></i> Generating AI analysis...</p>';
    if (meta) meta.style.display = 'none';

    try {
      var data = await apiFetch('/api/settings/portfolio-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: type }),
      });
      if (data && data.success) {
        if (result) result.innerHTML = data.analysis.replace(/\n/g, '<br>');
        if (meta) {
          meta.style.display = 'block';
          var modelEl = document.getElementById('aiModelUsed');
          var timeEl = document.getElementById('aiGeneratedAt');
          if (modelEl) modelEl.textContent = 'Model: ' + (data.model_used || 'unknown');
          if (timeEl) timeEl.textContent = data.cached ? 'Cached' : 'Generated just now';
        }
      } else {
        if (result) result.innerHTML = '<p style="color:#ff4757;">Failed to generate analysis.</p>';
      }
    } catch (e) {
      if (result) result.innerHTML = '<p style="color:#ff4757;">Error generating analysis.</p>';
    }
  }

  // ---------------------------------------------------------------------------
  // Import Modal
  // ---------------------------------------------------------------------------

  function initImportModal() {
    var btn = document.getElementById('importPortfolioBtn');
    var modal = document.getElementById('importModal');
    var closeBtn = document.getElementById('importModalClose');
    var form = document.getElementById('importForm');

    if (btn && modal) {
      btn.addEventListener('click', function () { modal.hidden = false; });
    }
    if (closeBtn && modal) {
      closeBtn.addEventListener('click', function () { modal.hidden = true; });
    }
    if (modal) {
      modal.addEventListener('click', function (e) {
        if (e.target.classList.contains('modal-backdrop')) modal.hidden = true;
      });
    }

    if (form) {
      form.addEventListener('submit', async function (e) {
        e.preventDefault();
        var fileInput = document.getElementById('importFile');
        var statusDiv = document.getElementById('importStatus');
        var submitBtn = document.getElementById('importSubmitBtn');

        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
          if (statusDiv) {
            statusDiv.style.display = 'block';
            statusDiv.style.background = 'rgba(255,71,87,0.15)';
            statusDiv.style.color = '#ff4757';
            statusDiv.textContent = 'Please select a file.';
          }
          return;
        }

        var file = fileInput.files[0];
        var formData = new FormData();
        formData.append('file', file);

        if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Importing...'; }
        if (statusDiv) { statusDiv.style.display = 'block'; statusDiv.style.background = 'rgba(0,212,255,0.1)'; statusDiv.style.color = '#00d4ff'; statusDiv.textContent = 'Processing file...'; }

        try {
          var endpoint = file.name.toLowerCase().endsWith('.csv') ? '/api/portfolio/import/csv' : '/api/portfolio/import/xlsx';
          var resp = await fetch(endpoint, { method: 'POST', body: formData });
          var data = await resp.json();

          if (data.success) {
            statusDiv.style.background = 'rgba(0,255,135,0.1)';
            statusDiv.style.color = '#00ff87';
            statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Import successful! ' +
              data.imported + ' transactions imported' +
              (data.skipped ? ', ' + data.skipped + ' skipped' : '') +
              (data.errors && data.errors.length ? ', ' + data.errors.length + ' errors' : '') +
              ' (Format: ' + escapeHtml(data.broker_format || 'unknown') + ')';
            // Refresh portfolio
            loadPortfolio();
            loadPortfolioSummary();
            showToast('Portfolio imported successfully!', 'success');
          } else {
            statusDiv.style.background = 'rgba(255,71,87,0.15)';
            statusDiv.style.color = '#ff4757';
            statusDiv.textContent = 'Import failed: ' + (data.error || 'Unknown error');
          }
        } catch (err) {
          statusDiv.style.background = 'rgba(255,71,87,0.15)';
          statusDiv.style.color = '#ff4757';
          statusDiv.textContent = 'Error: ' + err.message;
        }

        if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<i class="fas fa-upload"></i> Upload & Import'; }
      });
    }
  }

  // ---------------------------------------------------------------------------
  // SenseAI Section
  // ---------------------------------------------------------------------------

  function initSenseAI() {
    var sendBtn = document.getElementById('senseAiSendBtn');
    var input = document.getElementById('senseAiInput');

    if (sendBtn && input) {
      sendBtn.addEventListener('click', function () { sendSenseAiMessage(); });
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); sendSenseAiMessage(); }
      });
    }

    // Load model status
    loadModelStatus();
  }

  async function loadModelStatus() {
    try {
      var data = await apiFetch('/api/settings/model-status');
      var dot = document.getElementById('modelStatusDot');
      var text = document.getElementById('modelStatusText');
      if (!data || !data.success) {
        if (dot) dot.style.background = '#ff4757';
        if (text) text.textContent = 'Unable to check model status';
        return;
      }
      if (data.active_model && data.active_model !== 'none') {
        if (dot) dot.style.background = '#00ff87';
        if (text) text.textContent = 'AI Model Active: ' + data.active_model +
          (data[data.active_model] && data[data.active_model].model ? ' (' + data[data.active_model].model + ')' : '');
      } else {
        if (dot) dot.style.background = '#ffd93d';
        if (text) text.textContent = 'No AI model available. Using template-based analysis.';
      }
    } catch (e) {
      var dot2 = document.getElementById('modelStatusDot');
      var text2 = document.getElementById('modelStatusText');
      if (dot2) dot2.style.background = '#ff4757';
      if (text2) text2.textContent = 'Error checking model status';
    }
  }

  async function sendSenseAiMessage() {
    var input = document.getElementById('senseAiInput');
    var messages = document.getElementById('senseAiMessages');
    if (!input || !messages) return;
    var msg = input.value.trim();
    if (!msg) return;

    // Add user message
    var userDiv = document.createElement('div');
    userDiv.className = 'chat-message user';
    userDiv.innerHTML = '<p>' + escapeHtml(msg) + '</p>';
    messages.appendChild(userDiv);
    input.value = '';
    messages.scrollTop = messages.scrollHeight;

    // Loading indicator
    var loadingDiv = document.createElement('div');
    loadingDiv.className = 'chat-message agent';
    loadingDiv.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> Thinking...</p>';
    messages.appendChild(loadingDiv);
    messages.scrollTop = messages.scrollHeight;

    try {
      var data = await apiFetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      });

      loadingDiv.remove();

      var agentDiv = document.createElement('div');
      agentDiv.className = 'chat-message agent';
      if (data && data.success) {
        agentDiv.innerHTML = '<p>' + escapeHtml(data.response).replace(/\n/g, '<br>') + '</p>';
      } else {
        agentDiv.innerHTML = '<p style="color:#ff4757;">Sorry, I encountered an error. Please try again.</p>';
      }
      messages.appendChild(agentDiv);
      messages.scrollTop = messages.scrollHeight;
    } catch (e) {
      loadingDiv.remove();
      var errDiv = document.createElement('div');
      errDiv.className = 'chat-message agent';
      errDiv.innerHTML = '<p style="color:#ff4757;">Connection error. Please check your network.</p>';
      messages.appendChild(errDiv);
    }
  }

  function senseAiQuickAction(message) {
    var input = document.getElementById('senseAiInput');
    if (input) {
      input.value = message;
      sendSenseAiMessage();
    }
  }

  // ---------------------------------------------------------------------------
  // Onboarding Flow
  // ---------------------------------------------------------------------------

  var onboardingStepIndex = 0;
  var onboardingSteps = ['welcome', 'model_setup', 'portfolio', 'watchlist'];

  function initOnboarding() {
    apiFetch('/api/settings/onboarding').then(function (data) {
      if (!data || !data.success || data.completed) return;
      // Show onboarding
      var overlay = document.getElementById('onboardingOverlay');
      if (overlay) overlay.hidden = false;
      onboardingStepIndex = data.step_index || 0;
      showOnboardingStep(onboardingStepIndex);
    }).catch(function () { /* skip onboarding on error */ });

    var nextBtn = document.getElementById('onbNextBtn');
    var skipBtn = document.getElementById('onbSkipBtn');
    var skipBtn2 = document.getElementById('onboardingSkipBtn');

    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        onboardingStepIndex++;
        if (onboardingStepIndex >= onboardingSteps.length) {
          completeOnboarding();
        } else {
          showOnboardingStep(onboardingStepIndex);
          apiFetch('/api/settings/onboarding/advance', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
        }
      });
    }

    if (skipBtn) {
      skipBtn.addEventListener('click', function () { completeOnboarding(); });
    }
    if (skipBtn2) {
      skipBtn2.addEventListener('click', function () { completeOnboarding(); });
    }
  }

  function showOnboardingStep(idx) {
    onboardingSteps.forEach(function (step, i) {
      var el = document.getElementById('onb-' + step);
      if (el) el.style.display = i === idx ? 'block' : 'none';
    });

    // Update step dots
    document.querySelectorAll('.onboarding-step-dot').forEach(function (dot, i) {
      dot.classList.toggle('active', i <= idx);
    });

    var nextBtn = document.getElementById('onbNextBtn');
    if (nextBtn) {
      nextBtn.textContent = idx >= onboardingSteps.length - 1 ? 'Finish' : 'Next';
    }

    // Load model status for model_setup step
    if (onboardingSteps[idx] === 'model_setup') {
      apiFetch('/api/settings/model-status').then(function (data) {
        var el = document.getElementById('onbModelStatus');
        if (!el) return;
        if (data && data.success && data.active_model !== 'none') {
          el.innerHTML = '<span style="color:#00ff87;"><i class="fas fa-check-circle"></i> AI model detected: ' + escapeHtml(data.active_model) + '</span>';
        } else {
          el.innerHTML = '<span style="color:#ffd93d;"><i class="fas fa-exclamation-triangle"></i> No AI model found. The app will use template-based analysis. You can set up Ollama later.</span>';
        }
      });
    }
  }

  function completeOnboarding() {
    var overlay = document.getElementById('onboardingOverlay');
    if (overlay) overlay.hidden = true;
    apiFetch('/api/settings/onboarding/skip', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
    showToast('Setup complete! Explore your dashboard.', 'success');
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
    initChartTimeTabs();
    initPaperTradeModal();
    initNotificationBell();
    initImportModal();
    initSenseAI();
    initOnboarding();
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
      loadPortfolioSummary(),
      loadRiskMeter(),
      loadAlertsFeed(),
    ]);

    // Check kill criteria batch after watchlist loads
    checkKillCriteriaBatch();

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
    openPaperTrade: openPaperTrade,
    closePaperTrade: closePaperTrade,
    scrollToDebate: scrollToDebate,
    loadCandlestick: loadCandlestick,
    loadTechnicalIndicators: loadTechnicalIndicators,
    loadAgentDebate: loadAgentDebate,
    checkKillCriteria: checkKillCriteria,
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
      loadPortfolioSummary();
      loadRiskMeter();
      loadAlertsFeed();
      checkKillCriteriaBatch();
    },
    formatCurrency: formatCurrency,
    formatPercent: formatPercent,
    showToast: showToast,
  };

  // Expose watchlist and notification helpers for inline onclick handlers
  window.toggleWatchlistAdd = toggleWatchlistAdd;
  window.watchlistAddSearch = watchlistAddSearch;
  window.addToWatchlist = addToWatchlist;
  window.removeFromWatchlist = removeFromWatchlist;
  window.openAccountSection = openAccountSection;

  // Expose new portfolio/AI features for inline onclick handlers
  window.pfSwitchTab = pfSwitchTab;
  window.runPortfolioAnalysis = runPortfolioAnalysis;
  window.senseAiQuickAction = senseAiQuickAction;
  window.deleteTransaction = deleteTransaction;

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
  } else {
    initDashboard();
  }
})();
