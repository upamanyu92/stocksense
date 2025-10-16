# Watchlist-Only Prediction Updates

## Overview

This update modifies the background worker to run predictions **only** on stocks that are in user watchlists, rather than processing all stocks from the scripcode. This significantly reduces the computational load and LLM processing requirements.

## Changes Made

### 1. Background Worker Update

**File:** `app/services/background_worker.py`

**Change:** Modified `_run_predictions()` method to query only watchlist stocks

**Before:**
```python
# Get active stocks
cursor.execute('''
    SELECT * FROM stock_quotes 
    WHERE stock_status = 'active'
    ORDER BY company_name
''')
```

**After:**
```python
# Get watchlist stocks from all users
cursor.execute('''
    SELECT DISTINCT sq.* 
    FROM stock_quotes sq
    INNER JOIN user_watchlist uw ON sq.stock_symbol = uw.stock_symbol OR sq.security_id = uw.stock_symbol
    WHERE sq.stock_status = 'active'
    ORDER BY sq.company_name
''')
```

**Impact:**
- Predictions run only on stocks users are actually interested in
- Reduces LLM processing load
- Faster prediction cycles
- More efficient resource utilization

### 2. Scripcode Data Script

**File:** `scripts/download_stk_json.py`

**Purpose:** Downloads and saves BSE scripcode data to `app/static/stk.json`

**Usage:**
```bash
python scripts/download_stk_json.py
```

**What it does:**
- Fetches all stock symbols and company names from BSE
- Saves to JSON file for frontend autocomplete
- Provides easy access to company names for watchlist input

### 3. Frontend Integration

The autocomplete functionality already uses `stk.json` from the static directory:

**File:** `app/static/dashboard.js`

```javascript
async function initStockSearch() {
  // Load stock data
  const response = await fetch('/static/stk.json');
  const data = await response.json();
  
  stocksData = Object.entries(data).map(([security_id, company_name]) => ({
    security_id,
    company_name
  }));
}
```

## Benefits

1. **Reduced LLM Load:** Only processes stocks in watchlists instead of all stocks
2. **Faster Predictions:** Fewer stocks to process means faster completion
3. **Cost Efficiency:** Less API calls to LLM services
4. **Better User Experience:** Users get predictions for stocks they care about
5. **Scalability:** System can handle more users without processing unnecessary stocks

## Usage

### Adding Stocks to Watchlist

Users can add stocks to their watchlist via:
1. Search box with autocomplete (uses `stk.json`)
2. "Add Stock" button in dashboard
3. From search results

### Running Predictions

Predictions will automatically run on watchlist stocks when:
1. Background worker is enabled
2. Scheduled prediction tasks execute
3. Manual prediction triggers

### Updating Scripcode Data

To refresh the stock list from BSE:
```bash
cd /home/runner/work/stocksense/stocksense
python scripts/download_stk_json.py
```

This should be run periodically (e.g., weekly) to keep the stock list up-to-date.

## Technical Details

### Database Query

The new query uses an INNER JOIN to find stocks that exist in both:
- `stock_quotes` table (has market data)
- `user_watchlist` table (stocks users are watching)

This ensures only relevant stocks are processed.

### File Structure

```
stocksense/
├── app/
│   └── static/
│       └── stk.json          # Stock list for autocomplete
├── scripts/
│   └── download_stk_json.py  # Script to update stk.json
└── stk.json                  # Root copy (for reference)
```

## Migration Notes

- **No database changes required**
- **No breaking changes** - existing functionality preserved
- **Backward compatible** - still processes all watchlist stocks
- **Optional feature** - can revert by changing the SQL query back

## Future Enhancements

1. **Per-user scheduling:** Allow users to set prediction frequency
2. **Priority stocks:** Mark certain stocks for more frequent updates
3. **Batch optimization:** Group similar stocks for efficient processing
4. **Cache predictions:** Reuse recent predictions to reduce processing

## Testing

To verify the changes:

1. Add some stocks to a user's watchlist
2. Trigger predictions (manual or background worker)
3. Check logs to confirm only watchlist stocks are processed
4. Verify prediction results are saved correctly

Example log output:
```
INFO: Starting automated predictions on watchlist stocks
INFO: Found 15 unique stocks in watchlists to process
INFO: Processing prediction for RELIANCE
INFO: Processing prediction for TCS
...
INFO: Predictions completed: 15/15 stocks
```

## Conclusion

This update significantly improves the efficiency of the StockSense application by focusing computational resources on stocks that users are actually monitoring, rather than attempting to process the entire universe of stocks.
