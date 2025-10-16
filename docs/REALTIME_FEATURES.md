# Real-time Features Documentation

## Overview

StockSense now includes comprehensive real-time features to provide live updates and instant feedback for stock predictions, price tracking, and background operations. This document describes the real-time capabilities and how to use them.

## Key Real-time Features

### 1. WebSocket-based Communication

The application uses **Flask-SocketIO** to provide bidirectional, real-time communication between the server and clients.

#### Connection Status
- A live connection indicator is displayed in the dashboard header
- Shows connection state: Connected (green), Disconnected (yellow), Error (red)
- Automatic reconnection with exponential backoff

#### WebSocket Events

**Client-to-Server Events:**
- `connect` - Client connection established
- `disconnect` - Client disconnected
- `subscribe_predictions` - Subscribe to prediction updates
- `subscribe_watchlist` - Subscribe to watchlist changes
- `subscribe_stock_prices` - Subscribe to live price updates
- `unsubscribe_stock_prices` - Unsubscribe from price updates
- `request_system_status` - Request current system status

**Server-to-Client Events:**
- `connection_status` - Connection confirmation
- `subscription_confirmed` - Subscription confirmation
- `prediction_update` - New prediction available
- `prediction_progress` - Prediction processing progress
- `watchlist_update` - Watchlist changed
- `stock_price_update` - Live stock price update
- `background_worker_status` - Background worker status
- `system_status` - System status update
- `system_alert` - System alert (disk space, errors, etc.)

### 2. Real-time Stock Price Streaming

Live stock price updates for watchlist stocks.

#### Features:
- Automatic price updates every 10 seconds
- WebSocket-based push notifications
- Visual chart updates
- No page refresh required

#### Usage:

**Start Price Tracking:**
```javascript
// Via UI: Click "Start Tracking" button in the dashboard
// Automatically tracks all watchlist stocks

// Via API:
POST /api/price_stream/start
{
  "symbols": ["RELIANCE", "TCS", "INFY"]
}
```

**Stop Price Tracking:**
```javascript
POST /api/price_stream/stop
{
  "symbols": ["RELIANCE", "TCS", "INFY"]
}
```

**Get Tracking Status:**
```javascript
GET /api/price_stream/status
```

**Get Single Stock Price:**
```javascript
GET /api/price/<symbol>
```

### 3. Live Prediction Updates

Real-time updates as predictions are generated.

#### Features:
- Instant notification when prediction completes
- Progress tracking for batch predictions
- Live updates to prediction tables
- Confidence scores and decision indicators

#### WebSocket Event Example:
```javascript
socket.on('prediction_update', (data) => {
  // data contains:
  // - company_name
  // - security_id
  // - current_price
  // - predicted_price
  // - profit_percentage
  // - confidence
  // - decision
  // - timestamp
});
```

### 4. Real-time Watchlist Management

Instant synchronization of watchlist changes across all connected clients.

#### Features:
- Immediate UI updates when adding/removing stocks
- Multi-device synchronization
- Auto-start price tracking for new stocks

#### WebSocket Event Example:
```javascript
socket.on('watchlist_update', (data) => {
  // data contains:
  // - action: 'added' or 'removed'
  // - stock_symbol
  // - company_name
  // - user_id
  // - watchlist: updated complete watchlist
});
```

### 5. Background Worker Status

Live updates on background operations (downloads, predictions, etc.).

#### Features:
- Real-time progress tracking
- Current operation display
- Processed/remaining counts
- Activity log with timestamps
- ETA calculations

#### Status Update Example:
```javascript
{
  "type": "prediction",
  "status": "progress",
  "processed": 150,
  "total": 500,
  "stock_name": "Reliance Industries",
  "timestamp": "2025-10-15T18:30:00Z"
}
```

### 6. Real-time Charts

Live updating charts powered by Chart.js.

#### Chart Types:

**Single Stock Chart:**
```javascript
const chart = new RealtimeChart('chartCanvas', {
  label: 'Stock Price',
  maxDataPoints: 20
});

chart.addDataPoint('18:30:00', 2500.50);
```

**Multi-Stock Comparison Chart:**
```javascript
const multiChart = new MultiStockChart('multiChartCanvas', {
  maxDataPoints: 30
});

multiChart.addStock('RELIANCE', 'Reliance Industries');
multiChart.addStock('TCS', 'Tata Consultancy Services');
multiChart.addDataPoint('RELIANCE', '18:30:00', 2500.50);
multiChart.addDataPoint('TCS', '18:30:00', 3450.25);
```

### 7. System Notifications

Toast-style notifications for important events.

#### Notification Types:
- **Success** (green) - Operations completed successfully
- **Warning** (yellow) - Non-critical alerts
- **Error** (red) - Critical errors
- **Info** (blue) - Informational messages

#### Features:
- Auto-dismiss after 3 seconds
- Slide-in/slide-out animations
- Stackable notifications
- Click to dismiss

## Architecture

### Backend Components

1. **WebSocket Manager** (`app/utils/websocket_manager.py`)
   - Centralized WebSocket event emissions
   - Manages all real-time communications

2. **Price Streamer** (`app/services/price_streamer.py`)
   - Manages live stock price updates
   - Configurable update intervals
   - Thread-safe symbol management

3. **Background Worker** (`app/services/background_worker.py`)
   - Emits progress updates during operations
   - Queue-based status tracking

4. **Prediction Service** (`app/services/prediction_service.py`)
   - Real-time prediction event emissions
   - Progress tracking for batch operations

### Frontend Components

1. **WebSocket Client** (`app/static/dashboard.js`)
   - Socket.IO client connection
   - Event handlers for all real-time events
   - Automatic reconnection logic

2. **Charts** (`app/static/charts.js`)
   - RealtimeChart - Single line chart
   - MultiStockChart - Multi-line comparison
   - Auto-updating with new data

3. **Dashboard UI** (`app/templates/dashboard.html`)
   - Live connection status indicator
   - Real-time data displays
   - Interactive controls

## Configuration

### WebSocket Settings

In `app/main.py`:
```python
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",  # Configure for production
    async_mode='threading'
)
```

### Price Streaming Settings

In `app/services/price_streamer.py`:
```python
self.update_interval = 10  # Update every 10 seconds
self.max_retries = 3       # Max retries on failure
```

### Chart Settings

In `app/static/dashboard.js`:
```javascript
const chart = new RealtimeChart('canvas', {
  maxDataPoints: 30,  // Keep last 30 data points
  label: 'Stock Price'
});
```

## Best Practices

1. **Connection Management**
   - Always check connection status before emitting events
   - Handle reconnection gracefully
   - Implement fallback polling for critical data

2. **Performance**
   - Limit chart data points (20-50 recommended)
   - Throttle frequent updates
   - Use event batching for bulk operations

3. **Error Handling**
   - Always include try-catch blocks
   - Log errors appropriately
   - Show user-friendly error messages

4. **Security**
   - Use authentication for WebSocket connections
   - Validate all incoming data
   - Configure CORS properly for production

## Troubleshooting

### WebSocket Not Connecting
1. Check if Socket.IO client library is loaded
2. Verify server is running with socketio.run()
3. Check CORS configuration
4. Look for connection errors in browser console

### Price Updates Not Showing
1. Verify stocks are in watchlist
2. Check if price streaming is started
3. Ensure BSE API is accessible
4. Check server logs for errors

### Charts Not Updating
1. Verify Chart.js library is loaded
2. Check if canvas element exists
3. Ensure chart is initialized before adding data
4. Look for JavaScript errors in console

## API Reference

See the main API documentation and inline code comments for detailed API references.

## Future Enhancements

Potential improvements for real-time features:

1. **Advanced Notifications**
   - Email/SMS alerts for price targets
   - Customizable alert conditions
   - Alert history and management

2. **Enhanced Charts**
   - Candlestick charts
   - Technical indicators overlay
   - Zoom and pan functionality

3. **Collaborative Features**
   - Shared watchlists
   - Real-time collaboration
   - Group predictions

4. **Performance Optimization**
   - Redis for message queuing
   - Load balancing for WebSocket connections
   - Horizontal scaling support

## Support

For issues or questions about real-time features:
1. Check the documentation
2. Review server logs for errors
3. Test with browser developer tools
4. Submit an issue on GitHub
