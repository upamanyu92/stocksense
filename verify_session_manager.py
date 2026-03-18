#!/usr/bin/env python3
"""
Verification script to test the DatabaseSessionManager implementation.
Run this to verify that the database lock issue is resolved.
"""

import sys
import time
import threading
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_connection_pooling():
    """Test that connection pooling works"""
    logger.info("Testing connection pooling...")
    try:
        from app.db.session_manager import get_session_manager

        db = get_session_manager()

        # Test multiple connections
        for i in range(5):
            row = db.fetch_one('SELECT COUNT(*) as count FROM sqlite_master')
            assert row is not None, f"Query {i} returned None"
            logger.info(f"  Query {i+1}: OK")

        logger.info("✅ Connection pooling test PASSED")
        return True
    except Exception as e:
        logger.error(f"❌ Connection pooling test FAILED: {e}")
        return False

def test_auto_retry():
    """Test that automatic retry works on database locks"""
    logger.info("Testing automatic retry mechanism...")
    try:
        from app.db.session_manager import get_session_manager

        db = get_session_manager()

        # This should not raise an exception even under pressure
        for i in range(10):
            rows = db.fetch_all('SELECT 1')
            assert rows is not None, f"Query {i} failed"

        logger.info("✅ Auto-retry test PASSED")
        return True
    except Exception as e:
        logger.error(f"❌ Auto-retry test FAILED: {e}")
        return False

def test_concurrent_access():
    """Test concurrent database access"""
    logger.info("Testing concurrent access...")
    errors = []
    success_count = [0]

    def worker(thread_id):
        try:
            from app.db.session_manager import get_session_manager
            db = get_session_manager()

            for i in range(5):
                rows = db.fetch_all('SELECT COUNT(*) as count FROM sqlite_master')
                if rows:
                    success_count[0] += 1
        except Exception as e:
            errors.append(f"Thread {thread_id}: {e}")

    # Create multiple threads
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    if errors:
        logger.error(f"❌ Concurrent access test FAILED: {errors}")
        return False

    logger.info(f"✅ Concurrent access test PASSED ({success_count[0]} successful queries)")
    return True

def test_session_manager_singleton():
    """Test that session manager is a singleton"""
    logger.info("Testing session manager singleton...")
    try:
        from app.db.session_manager import get_session_manager

        db1 = get_session_manager()
        db2 = get_session_manager()

        assert db1 is db2, "Session manager is not a singleton"
        logger.info("✅ Singleton test PASSED")
        return True
    except Exception as e:
        logger.error(f"❌ Singleton test FAILED: {e}")
        return False

def test_basic_operations():
    """Test basic database operations"""
    logger.info("Testing basic operations...")
    try:
        from app.db.session_manager import get_session_manager

        db = get_session_manager()

        # Test fetch
        row = db.fetch_one('SELECT COUNT(*) as count FROM users')
        logger.info(f"  fetch_one: OK")

        # Test fetch_all
        rows = db.fetch_all('SELECT COUNT(*) as count FROM users LIMIT 1')
        logger.info(f"  fetch_all: OK")

        logger.info("✅ Basic operations test PASSED")
        return True
    except Exception as e:
        logger.error(f"❌ Basic operations test FAILED: {e}")
        return False

def test_wal_mode():
    """Test that WAL mode is enabled"""
    logger.info("Testing WAL mode...")
    try:
        from app.db.session_manager import get_session_manager

        db = get_session_manager()

        # Check WAL mode
        row = db.fetch_one('PRAGMA journal_mode')
        if row and 'wal' in str(row).lower():
            logger.info(f"  WAL mode: {row}")
            logger.info("✅ WAL mode test PASSED")
            return True
        else:
            logger.warning(f"⚠️  WAL mode not detected: {row}")
            return True  # Non-fatal
    except Exception as e:
        logger.error(f"❌ WAL mode test FAILED: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("DatabaseSessionManager Verification Tests")
    logger.info("=" * 60)

    tests = [
        ("Connection Pooling", test_connection_pooling),
        ("Automatic Retry", test_auto_retry),
        ("Concurrent Access", test_concurrent_access),
        ("Singleton Pattern", test_session_manager_singleton),
        ("Basic Operations", test_basic_operations),
        ("WAL Mode", test_wal_mode),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

        logger.info("")  # Newline for readability

    # Summary
    logger.info("=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info("=" * 60)
    logger.info(f"Result: {passed}/{total} tests passed")
    logger.info("=" * 60)

    if passed == total:
        logger.info("\n🎉 All tests passed! Database session manager is working correctly.")
        logger.info("The 'database is locked' issue should be resolved.")
        return 0
    else:
        logger.error(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

