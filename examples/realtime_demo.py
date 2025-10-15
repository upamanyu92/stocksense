#!/usr/bin/env python3
"""
Demo script showing how to use StockSense real-time features programmatically.

This script demonstrates:
1. Connecting to WebSocket
2. Subscribing to events
3. Handling real-time updates
4. Starting price streaming
"""

import socketio
import time
import requests

# Create a Socket.IO client
sio = socketio.Client()

# Configuration
SERVER_URL = 'http://localhost:5005'
USERNAME = 'admin'
PASSWORD = 'admin123'

# Store session for authenticated requests
session = requests.Session()


def login():
    """Login to get session cookie"""
    print("Logging in...")
    response = session.post(
        f"{SERVER_URL}/api/auth/login",
        json={'username': USERNAME, 'password': PASSWORD}
    )
    if response.status_code == 200:
        print("✓ Logged in successfully")
        return True
    else:
        print(f"✗ Login failed: {response.text}")
        return False


# Event handlers
@sio.on('connect')
def on_connect():
    print("✓ Connected to StockSense WebSocket")
    
    # Subscribe to various events
    print("Subscribing to events...")
    sio.emit('subscribe_predictions')
    sio.emit('subscribe_watchlist')
    sio.emit('subscribe_stock_prices', {'symbols': []})
    sio.emit('request_system_status')


@sio.on('disconnect')
def on_disconnect():
    print("✗ Disconnected from StockSense")


@sio.on('connection_status')
def on_connection_status(data):
    print(f"Connection status: {data}")


@sio.on('subscription_confirmed')
def on_subscription_confirmed(data):
    print(f"✓ Subscription confirmed: {data['type']}")


@sio.on('prediction_update')
def on_prediction_update(data):
    """Handle new prediction"""
    print("\n" + "="*60)
    print("NEW PREDICTION UPDATE")
    print("="*60)
    print(f"Stock: {data['company_name']} ({data['security_id']})")
    print(f"Current Price: ₹{data['current_price']:.2f}")
    print(f"Predicted Price: ₹{data['predicted_price']:.2f}")
    print(f"Profit Potential: {data['profit_percentage']:.2f}%")
    print(f"Confidence: {data.get('confidence', 0):.2f}")
    print(f"Decision: {data.get('decision', 'N/A')}")
    print("="*60 + "\n")


@sio.on('stock_price_update')
def on_price_update(data):
    """Handle live price update"""
    print(f"Price Update: {data['company_name']} - ₹{data['price']:.2f} ({data['pChange']:.2f}%)")


@sio.on('watchlist_update')
def on_watchlist_update(data):
    """Handle watchlist change"""
    print(f"\nWatchlist {data['action']}: {data['company_name']} ({data['stock_symbol']})")


@sio.on('background_worker_status')
def on_worker_status(data):
    """Handle background worker status"""
    if data.get('type') == 'prediction' and data.get('status') == 'progress':
        processed = data.get('processed', 0)
        total = data.get('total', 0)
        stock = data.get('stock_name', 'Unknown')
        print(f"Prediction Progress: {processed}/{total} - {stock}")


@sio.on('prediction_progress')
def on_prediction_progress(data):
    """Handle prediction progress"""
    status = data.get('status', '')
    message = data.get('message', '')
    print(f"[{status.upper()}] {message}")


@sio.on('system_alert')
def on_system_alert(data):
    """Handle system alert"""
    print(f"\n⚠️  ALERT: {data['message']}")


@sio.on('system_status')
def on_system_status(data):
    """Handle system status update"""
    print("\nSystem Status:")
    if 'disk_usage' in data:
        disk = data['disk_usage']
        print(f"  Disk: {disk.get('percent_free', 0):.1f}% free")
    if 'background_worker' in data:
        worker = data['background_worker']
        print(f"  Worker: {'Running' if worker.get('running') else 'Idle'}")


def start_price_streaming(symbols):
    """Start price streaming for given symbols"""
    print(f"\nStarting price streaming for: {symbols}")
    response = session.post(
        f"{SERVER_URL}/api/price_stream/start",
        json={'symbols': symbols}
    )
    if response.status_code == 200:
        print("✓ Price streaming started")
    else:
        print(f"✗ Failed to start streaming: {response.text}")


def add_to_watchlist(symbol, name):
    """Add a stock to watchlist"""
    print(f"\nAdding {name} to watchlist...")
    response = session.post(
        f"{SERVER_URL}/api/watchlist/add",
        json={'stock_symbol': symbol, 'company_name': name}
    )
    if response.status_code == 200:
        print(f"✓ Added {name} to watchlist")
    else:
        print(f"✗ Failed to add: {response.text}")


def trigger_predictions():
    """Trigger batch predictions"""
    print("\nTriggering batch predictions...")
    response = session.post(f"{SERVER_URL}/trigger_prediction")
    if response.status_code == 200:
        print("✓ Predictions triggered")
    else:
        print(f"✗ Failed to trigger predictions: {response.text}")


def main():
    """Main demo function"""
    print("="*60)
    print("StockSense Real-time Features Demo")
    print("="*60)
    print()
    
    # Login first
    if not login():
        print("Cannot proceed without login. Exiting.")
        return
    
    # Connect to WebSocket
    print("\nConnecting to WebSocket...")
    try:
        sio.connect(SERVER_URL)
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return
    
    # Wait a moment for subscriptions
    time.sleep(2)
    
    # Demo: Add stock to watchlist
    add_to_watchlist('RELIANCE', 'Reliance Industries')
    time.sleep(1)
    
    # Demo: Start price streaming
    start_price_streaming(['RELIANCE', 'TCS', 'INFY'])
    
    # Demo: Trigger predictions (optional - comment out if too slow)
    # trigger_predictions()
    
    # Keep the connection alive and listen for events
    print("\n" + "="*60)
    print("Listening for real-time events...")
    print("Press Ctrl+C to exit")
    print("="*60 + "\n")
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        sio.disconnect()
        print("✓ Disconnected")


if __name__ == '__main__':
    main()
