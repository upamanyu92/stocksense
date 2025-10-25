// Stocks List JavaScript for StockSense
// Handles pagination, sorting, and stock list display

// State management
let currentPage = 1;
let perPage = 50;
let totalPages = 1;
let totalCount = 0;
let sortBy = 'company_name';
let sortOrder = 'asc';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  loadStocks();
  setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
  // Pagination controls
  document.getElementById('firstPageBtn').addEventListener('click', () => goToPage(1));
  document.getElementById('prevPageBtn').addEventListener('click', () => goToPage(currentPage - 1));
  document.getElementById('nextPageBtn').addEventListener('click', () => goToPage(currentPage + 1));
  document.getElementById('lastPageBtn').addEventListener('click', () => goToPage(totalPages));

  document.getElementById('pageInput').addEventListener('change', (e) => {
    const page = parseInt(e.target.value);
    if (page >= 1 && page <= totalPages) {
      goToPage(page);
    } else {
      e.target.value = currentPage;
    }
  });

  // Per page select
  document.getElementById('perPageSelect').addEventListener('change', (e) => {
    perPage = parseInt(e.target.value);
    currentPage = 1;
    loadStocks();
  });

  // Sortable columns
  document.querySelectorAll('.sortable').forEach(th => {
    th.addEventListener('click', () => {
      const newSortBy = th.getAttribute('data-sort');
      if (sortBy === newSortBy) {
        sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
      } else {
        sortBy = newSortBy;
        sortOrder = 'asc';
      }
      loadStocks();
    });
  });
}

// Go to specific page
function goToPage(page) {
  if (page >= 1 && page <= totalPages && page !== currentPage) {
    currentPage = page;
    loadStocks();
  }
}

// Load stocks from API
async function loadStocks() {
  showLoading(true);

  try {
    const response = await fetch(
      `/api/stocks/list?page=${currentPage}&per_page=${perPage}&sort_by=${sortBy}&sort_order=${sortOrder}`
    );

    if (!response.ok) {
      throw new Error('Failed to fetch stocks');
    }

    const data = await response.json();

    // Update pagination state
    totalPages = data.pagination.total_pages;
    totalCount = data.pagination.total_count;

    // Render stocks
    renderStocks(data.stocks);

    // Update pagination UI
    updatePaginationUI();

    // Update sort indicators
    updateSortIndicators();

  } catch (error) {
    console.error('Error loading stocks:', error);
    document.getElementById('stocksTableBody').innerHTML = `
      <tr>
        <td colspan="10" style="text-align: center; padding: 40px; color: var(--danger-color);">
          <i class="fas fa-exclamation-triangle" style="font-size: 2rem;"></i>
          <p style="margin-top: 10px;">Error loading stocks. Please try again.</p>
        </td>
      </tr>
    `;
  } finally {
    showLoading(false);
  }
}

// Render stocks table
function renderStocks(stocks) {
  const tbody = document.getElementById('stocksTableBody');

  if (stocks.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10" style="text-align: center; padding: 40px; color: var(--text-muted);">
          <i class="fas fa-inbox" style="font-size: 2rem;"></i>
          <p style="margin-top: 10px;">No stocks found</p>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = stocks.map(stock => {
    const changeClass = stock.change >= 0 ? 'profit-positive' : 'profit-negative';
    const changeIcon = stock.change >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';

    return `
      <tr>
        <td><strong>${stock.company_name || 'N/A'}</strong></td>
        <td>${stock.security_id || 'N/A'}</td>
        <td>₹${stock.current_value ? stock.current_value.toFixed(2) : '0.00'}</td>
        <td class="${changeClass}">
          <i class="fas ${changeIcon}"></i> ${stock.change ? stock.change.toFixed(2) : '0.00'}
        </td>
        <td class="${changeClass}">
          ${stock.p_change ? stock.p_change.toFixed(2) : '0.00'}%
        </td>
        <td>₹${stock.day_high ? stock.day_high.toFixed(2) : '0.00'}</td>
        <td>₹${stock.day_low ? stock.day_low.toFixed(2) : '0.00'}</td>
        <td>₹${stock.previous_close ? stock.previous_close.toFixed(2) : '0.00'}</td>
        <td>${stock.industry || 'N/A'}</td>
        <td>${stock.updated_on ? formatDate(stock.updated_on) : 'N/A'}</td>
      </tr>
    `;
  }).join('');
}

// Update pagination UI
function updatePaginationUI() {
  const firstPageBtn = document.getElementById('firstPageBtn');
  const prevPageBtn = document.getElementById('prevPageBtn');
  const nextPageBtn = document.getElementById('nextPageBtn');
  const lastPageBtn = document.getElementById('lastPageBtn');
  const pageInput = document.getElementById('pageInput');
  const paginationInfo = document.getElementById('paginationInfo');

  // Update buttons state
  firstPageBtn.disabled = currentPage === 1;
  prevPageBtn.disabled = currentPage === 1;
  nextPageBtn.disabled = currentPage === totalPages || totalPages === 0;
  lastPageBtn.disabled = currentPage === totalPages || totalPages === 0;

  // Update page input
  pageInput.value = currentPage;
  pageInput.max = totalPages;

  // Update info text
  const start = totalCount === 0 ? 0 : (currentPage - 1) * perPage + 1;
  const end = Math.min(currentPage * perPage, totalCount);
  paginationInfo.textContent = `Showing ${start} to ${end} of ${totalCount} stocks (Page ${currentPage} of ${totalPages})`;
}

// Update sort indicators
function updateSortIndicators() {
  document.querySelectorAll('.sortable').forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
    if (th.getAttribute('data-sort') === sortBy) {
      th.classList.add(sortOrder === 'asc' ? 'sort-asc' : 'sort-desc');
    }
  });
}

// Show/hide loading overlay
function showLoading(show) {
  const overlay = document.getElementById('loadingOverlay');
  if (show) {
    overlay.classList.add('active');
  } else {
    overlay.classList.remove('active');
  }
}

// Format date
function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  } catch (e) {
    return dateStr;
  }
}
