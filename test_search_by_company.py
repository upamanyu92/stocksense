#!/usr/bin/env python3
"""
Test script for the new company search functionality.

This script demonstrates how to use:
1. search_companies_by_name() - to search for companies
2. get_quote_by_company_name() - to get quotes using company name
"""

import sys
import logging
from app.utils.yfinance_utils import search_companies_by_name, get_quote_by_company_name

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_search():
    """Test the search_companies_by_name function."""
    print("\n" + "="*60)
    print("TEST 1: Search Companies by Name")
    print("="*60)

    company_names = [
        "Reliance",
        "TCS",
        "HDFC Bank",
        "Infosys",
    ]

    for company in company_names:
        print(f"\nSearching for: {company}")
        print("-" * 40)
        results = search_companies_by_name(company, max_results=5)

        if results:
            for idx, result in enumerate(results, 1):
                print(f"\n  Result {idx}:")
                print(f"    Symbol: {result['symbol']}")
                print(f"    Name: {result['name']}")
                print(f"    Exchange: {result['exchange']}")
                print(f"    Type: {result['type']}")
                if result.get('industry'):
                    print(f"    Industry: {result['industry']}")
                if result.get('sector'):
                    print(f"    Sector: {result['sector']}")
        else:
            print("  No results found.")


def test_get_quote_by_company_name():
    """Test the get_quote_by_company_name function."""
    print("\n" + "="*60)
    print("TEST 2: Get Quote by Company Name")
    print("="*60)

    company_names = [
        "Reliance Industries",
        "TCS",
        "HDFC Bank",
    ]

    for company in company_names:
        print(f"\nFetching quote for: {company}")
        print("-" * 40)

        quote = get_quote_by_company_name(company, max_search_results=3)

        if quote:
            print(f"\n  Company Name: {quote.get('companyName')}")
            print(f"  Security ID: {quote.get('securityID')}")
            print(f"  Current Value: ₹{quote.get('currentValue', 0)}")
            print(f"  Change: {quote.get('change', 0)}")
            print(f"  % Change: {quote.get('pChange', 0)}%")
            print(f"  Day High: ₹{quote.get('dayHigh', 0)}")
            print(f"  Day Low: ₹{quote.get('dayLow', 0)}")
            print(f"  Previous Close: ₹{quote.get('previousClose', 0)}")
            print(f"  52 Week High: ₹{quote.get('52weekHigh', 0)}")
            print(f"  52 Week Low: ₹{quote.get('52weekLow', 0)}")
            print(f"  Industry: {quote.get('industry', 'N/A')}")

            if quote.get('searchMatch'):
                search_match = quote['searchMatch']
                print(f"\n  Search Match Info:")
                print(f"    Original Query: {search_match.get('originalQuery')}")
                print(f"    Matched Symbol: {search_match.get('matchedSymbol')}")
                print(f"    Matched Name: {search_match.get('matchedName')}")
                print(f"    Exchange: {search_match.get('exchange')}")
        else:
            print("  Could not fetch quote.")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Company Search & Quote Lookup Test Suite")
    print("="*60)

    try:
        # Test 1: Search functionality
        test_search()

        # Test 2: Get quote by company name
        test_get_quote_by_company_name()

        print("\n" + "="*60)
        print("All tests completed!")
        print("="*60 + "\n")

    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)

