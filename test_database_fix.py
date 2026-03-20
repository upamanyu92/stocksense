#!/usr/bin/env python3
"""Quick test to verify database schema and insertion works"""
import os
import sys

# Add project to path
sys.path.insert(0, '/Users/commandcenter/pycharmprojects/stocksense')

# Test 1: Schema initialization
print("="*80)
print("TEST 1: Database Schema Initialization")
print("="*80)

from scripts.init_db_schema import SchemaManager

try:
    # Remove old database
    db_path = '/Users/commandcenter/pycharmprojects/stocksense/app/db/stock_predictions.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print("✓ Removed old database")

    # Initialize schema
    schema_manager = SchemaManager(verbose=True)
    schema_manager.init_schema()
    print("\n✓ Schema initialization successful!\n")
except Exception as e:
    print(f"\n✗ Schema initialization failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Database insertion
print("="*80)
print("TEST 2: Database Insertion")
print("="*80)

try:
    from app.services.background_worker import BackgroundWorker
    from app.utils.util import get_db_connection

    worker = BackgroundWorker()

    # Create a test quote
    test_quote = {
        'companyName': 'Test Company Limited',
        'securityID': 'TEST',
        'scripCode': 'TEST.BO',
        'currentValue': 100.5,
        'change': 5.0,
        'pChange': 5.24,
        'dayHigh': 105.0,
        'dayLow': 95.0,
        'previousClose': 95.5,
        'previousOpen': 95.0,
        '52weekHigh': 150.0,
        '52weekLow': 80.0,
        'faceValue': 10.0,
        'group': 'EQUITY',
        'industry': 'Test Industry',
        'marketCapFreeFloat': '1000 Cr',
        'marketCapFull': '1000 Cr',
        'totalTradedQuantity': 100000,
        'totalTradedValue': '10 Cr',
        'updatedOn': '19 Mar 26',
        'weightedAvgPrice': 100.5,
        'buy': {},
        'sell': {}
    }

    print(f"\nInserting test quote: {test_quote['companyName']}")
    worker._store_stock_quote(test_quote)
    print("✓ Successfully inserted quote into database")

    # Verify insertion
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT company_name, current_value, group_name, stock_status FROM stock_quotes WHERE security_id = ?', ('TEST',))
    row = cursor.fetchone()
    conn.close()

    if row:
        print(f"✓ Verified in database:")
        print(f"  - Company: {row[0]}")
        print(f"  - Price: ₹{row[1]}")
        print(f"  - Group: {row[2]}")
        print(f"  - Status: {row[3]}")
    else:
        print("✗ Could not verify in database")
        sys.exit(1)

except Exception as e:
    print(f"\n✗ Insertion test failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("✓ ALL TESTS PASSED!")
print("="*80)
print("\nThe database schema is now properly configured and ready to use.")
print("The background worker can successfully store stock quotes.")

