# Gemini AI Integration - Verification Checklist

## Pre-Installation Checklist

- [ ] Python 3.8+ installed (`python3 --version`)
- [ ] pip updated (`pip install --upgrade pip`)
- [ ] Internet connection available
- [ ] GitHub account (for API key)
- [ ] No existing installations conflicts

---

## Installation Checklist

### Step 1: Get API Key
- [ ] Visit https://aistudio.google.com/app/apikey
- [ ] Click "Get API Key"
- [ ] Copy API key to clipboard
- [ ] Keep it safe (don't share!)

### Step 2: Configure Environment
- [ ] Run: `cp .env.example .env`
- [ ] Edit `.env` with your editor
- [ ] Replace `GEMINI_API_KEY=your_google...` with actual key
- [ ] Save and close file
- [ ] Verify: `grep GEMINI_API_KEY .env` (should show your key)

### Step 3: Install Dependencies
- [ ] Run: `pip install -r requirements.txt`
- [ ] Wait for installation to complete
- [ ] No errors during installation

### Step 4: Verify Installation
```bash
# Run these commands
python3 -c "import google.generativeai; print('✓ google-generativeai installed')"
python3 -c "import dotenv; print('✓ python-dotenv installed')"
python3 -c "import flask; print('✓ Flask installed')"
python3 -c "import yfinance; print('✓ yfinance installed')"
```
- [ ] All four commands print success messages
- [ ] No import errors

---

## Application Start Checklist

### Starting the App
```bash
python -m app.main
```

Look for these messages:
- [ ] `Initializing database schema...`
- [ ] `Database schema initialization completed`
- [ ] `Initializing Google Gemini AI API...`
- [ ] `Gemini AI initialized successfully`
- [ ] `Starting StockSense application on port 5005`

### Browser Access
- [ ] Open http://localhost:5005 in browser
- [ ] Login page loads successfully
- [ ] No 404 or connection errors
- [ ] CSS/JS loads correctly

---

## Functional Testing Checklist

### Test 1: Basic Prediction
```bash
python3 << EOF
from app.models.gemini_model import predict_with_details

result = predict_with_details('INFY.BO')
print(f"Prediction: {result['predicted_price']}")
print(f"Confidence: {result['confidence']}")
print(f"Decision: {result['decision']}")
EOF
```
- [ ] No errors printed
- [ ] predicted_price is a number > 0
- [ ] confidence is between 0.0 and 1.0
- [ ] decision is one of: accept, caution, reject

### Test 2: Check Database
```bash
sqlite3 app/db/stock_predictions.db "SELECT COUNT(*) FROM predictions;"
```
- [ ] Command returns a number
- [ ] Number is >= 0

### Test 3: View Recent Predictions
```bash
sqlite3 app/db/stock_predictions.db << EOF
.headers on
.mode column
SELECT company_name, predicted_price, confidence, decision 
FROM predictions 
ORDER BY prediction_date DESC 
LIMIT 3;
EOF
```
- [ ] No SQL errors
- [ ] Predictions displayed (if any exist)
- [ ] Column headers visible

### Test 4: Check Logs
```bash
tail -20 logs/stocksense.log
```
- [ ] Log file exists
- [ ] No error messages (warnings are OK)
- [ ] Contains Gemini initialization messages

---

## Dashboard Testing Checklist

### Login
- [ ] Can login with your credentials
- [ ] Dashboard loads after login
- [ ] All main sections visible

### Stock Management
- [ ] Can add stock to watchlist
- [ ] Stock appears in list
- [ ] Can view stock details
- [ ] Price updates visible

### Predictions
- [ ] Can trigger prediction from UI
- [ ] Prediction result appears
- [ ] Confidence score displayed
- [ ] Decision (accept/caution/reject) shown
- [ ] Reasoning visible (if expanded)

### Background Worker
- [ ] Can navigate to Admin → Background Worker
- [ ] Can enable/disable worker
- [ ] Worker status updates appear
- [ ] Real-time progress visible

### WebSocket Updates
- [ ] Predictions show up in real-time
- [ ] No WebSocket errors in browser console
- [ ] Multiple concurrent updates work

---

## Performance Testing Checklist

### Single Prediction Time
```bash
time python3 << EOF
from app.models.gemini_model import predict_with_details
result = predict_with_details('INFY.BO')
EOF
```
- [ ] Completed in 7-15 seconds (normal)
- [ ] Not taking > 30 seconds (connection issue?)

### Multiple Predictions
```bash
for stock in INFY RELIANCE TCS; do
  echo "Testing $stock.BO"
  python3 << EOF
from app.models.gemini_model import predict_with_details
result = predict_with_details('${stock}.BO')
EOF
done
```
- [ ] All completed successfully
- [ ] No rate limit errors

### Concurrent Predictions
- [ ] Background worker can run multiple predictions
- [ ] No conflicts in database
- [ ] All results stored correctly

---

## Configuration Testing Checklist

### Test Different Temperatures
Edit `.env` and test:

```bash
# Test 1: Conservative (0.3)
GEMINI_TEMPERATURE=0.3
# Run a prediction

# Test 2: Moderate (0.7)
GEMINI_TEMPERATURE=0.7
# Run a prediction

# Test 3: Creative (1.2)
GEMINI_TEMPERATURE=1.2
# Run a prediction
```
- [ ] Conservative gives consistent results
- [ ] Moderate gives balanced results
- [ ] Creative gives diverse results

### Test Token Limits
```bash
# Test with different token limits
GEMINI_MAX_OUTPUT_TOKENS=256   # Fast but brief
GEMINI_MAX_OUTPUT_TOKENS=1024  # Balanced
GEMINI_MAX_OUTPUT_TOKENS=2048  # Detailed but slow
```
- [ ] Smaller tokens = faster responses
- [ ] Larger tokens = more detailed reasoning
- [ ] No truncation errors

### Test Retry Logic
```bash
# Disable internet temporarily and run prediction
# Re-enable internet
# Prediction should succeed after retry
```
- [ ] Retry mechanism works
- [ ] Error handling is graceful

---

## Error Recovery Testing Checklist

### Test 1: Wrong API Key
- [ ] Edit .env with wrong key
- [ ] Try to run prediction
- [ ] Get clear error message
- [ ] Fix key and retry
- [ ] Works after fix

### Test 2: Network Disconnection
- [ ] Disable internet
- [ ] Try to run prediction
- [ ] Should retry and fail gracefully
- [ ] Enable internet
- [ ] Next prediction works

### Test 3: Missing .env File
- [ ] Rename .env to .env.bak
- [ ] Start app
- [ ] Should warn about missing API key
- [ ] Rename back
- [ ] Restart and works

### Test 4: Database Issues
- [ ] Temporarily move app/db/stock_predictions.db
- [ ] Start app
- [ ] Should create new database
- [ ] Move original back
- [ ] Old data intact

---

## Security Testing Checklist

### API Key Safety
- [ ] .env file is in .gitignore
- [ ] .env not committed to git
- [ ] API key not in any code files
- [ ] API key not in logs (verify: `grep GEMINI_API_KEY logs/stocksense.log` = no matches)

### Database Security
- [ ] Database file has correct permissions
- [ ] SQL injection prevention works (Django ORM handles this)
- [ ] No sensitive data in logs

### API Communication
- [ ] All API calls use HTTPS
- [ ] No API key in URLs
- [ ] No credentials in request headers (handled by library)

---

## Data Integrity Checklist

### Stock Quotes
```bash
sqlite3 app/db/stock_predictions.db << EOF
SELECT COUNT(*) FROM stock_quotes;
EOF
```
- [ ] Returns a count
- [ ] Count makes sense (> 0)

### Predictions
```bash
sqlite3 app/db/stock_predictions.db << EOF
SELECT COUNT(*) FROM predictions;
EOF
```
- [ ] Returns a count
- [ ] Count increasing as predictions run

### Data Consistency
```bash
sqlite3 app/db/stock_predictions.db << EOF
SELECT security_id, COUNT(*) FROM predictions 
GROUP BY security_id;
EOF
```
- [ ] No NULL security_ids
- [ ] No duplicate prediction entries
- [ ] Counts are reasonable

---

## Integration Testing Checklist

### With Background Worker
- [ ] Enable background worker
- [ ] Set watchlist with 3-5 stocks
- [ ] Worker starts downloading
- [ ] Worker runs predictions
- [ ] All predictions saved to database
- [ ] Dashboard updates in real-time

### With WebSocket
- [ ] Open dashboard in 2 browser tabs
- [ ] Trigger prediction in tab 1
- [ ] Tab 2 updates in real-time
- [ ] No missing updates

### With REST API
```bash
# Test prediction API
curl -X POST http://localhost:5005/api/predict \
  -H "Content-Type: application/json" \
  -d '{"symbol": "INFY"}'
```
- [ ] Returns valid JSON
- [ ] Contains predicted_price
- [ ] Contains confidence
- [ ] Contains decision

---

## Cleanup Checklist

### Remove Old Files (Optional)
- [ ] Backup old Keras models: `tar czf keras_models_backup.tar.gz model/saved_models/`
- [ ] Delete old models: `rm -rf model/saved_models/*`
- [ ] Verify space saved: `du -sh model/`

### Cleanup Dependencies (Optional)
```bash
# Remove unneeded packages (if not used elsewhere)
pip uninstall tensorflow keras joblib -y
```
- [ ] No errors during uninstall
- [ ] Application still works

---

## Final Verification Checklist

- [ ] All 4 dependency imports work
- [ ] Prediction returns valid results
- [ ] Database saves predictions
- [ ] Dashboard displays predictions
- [ ] Background worker runs successfully
- [ ] WebSocket updates work
- [ ] No errors in logs
- [ ] .env properly configured
- [ ] API key not exposed
- [ ] Confident that Gemini AI is working

---

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| `GEMINI_API_KEY not set` | Edit .env and add your key |
| `No module named google.generativeai` | Run `pip install -r requirements.txt` |
| `Failed to parse JSON` | Check internet, increase MAX_OUTPUT_TOKENS |
| `All retries exhausted` | Check API key validity, wait and retry |
| Slow predictions (> 30s) | Normal is 7-10s, might be network issue |
| Predictions missing | Check database, verify app is running |
| Dashboard not loading | Check Flask logs: `tail logs/stocksense.log` |

---

## Support Resources

1. **Documentation**
   - IMPLEMENTATION_SUMMARY.md - Overview
   - GEMINI_INTEGRATION.md - Technical details
   - QUICK_START.md - Quick setup
   - MIGRATION_GUIDE.md - From Keras

2. **Debugging**
   - Check logs: `tail -f logs/stocksense.log`
   - Test prediction: See "Test 1: Basic Prediction" above
   - Verify config: `cat .env | grep GEMINI`

3. **Google Resources**
   - API Status: https://status.cloud.google.com
   - Documentation: https://ai.google.dev
   - Pricing: https://ai.google.dev/pricing

---

## Completion

When all checkboxes above are checked, your Gemini AI integration is complete and verified! 🎉

**Next Steps:**
1. Add your stocks to the watchlist
2. Enable background worker for automated predictions
3. Monitor prediction accuracy in dashboard
4. Fine-tune configuration as needed
5. Share feedback and report any issues

