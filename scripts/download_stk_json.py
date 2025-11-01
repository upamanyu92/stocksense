#!/usr/bin/env python3
"""
Script to manage stock list data in JSON format.
This file is used for autocomplete in the watchlist input.

Note: yfinance doesn't provide a bulk stock list API like BSE did.
This script manages existing stock list files rather than downloading from an API.
For a comprehensive Indian stock list, download from NSE/BSE official websites.
"""
import json
import logging
import yfinance as yf

logging.basicConfig(level=logging.INFO)


def download_and_save_scripcode():
    """
    Load or create stock list and save to stk.json.
    
    Note: yfinance doesn't have a built-in method to list all Indian stocks.
    This is a placeholder that loads from existing file or uses a minimal list.
    
    For production use, consider:
    1. Downloading the official NSE/BSE stock list
    2. Using a third-party data provider
    3. Maintaining your own curated list
    """
    try:
        logging.info("Loading stock data...")
        
        # Try to load existing stk.json
        import os
        existing_file = 'stk.json'
        if os.path.exists(existing_file):
            logging.info(f"Loading existing stock list from {existing_file}")
            with open(existing_file, 'r') as f:
                funds = json.load(f)
            logging.info(f"Loaded {len(funds)} stocks from existing file")
        else:
            # Create a minimal list with common Indian stocks
            # In production, download from NSE/BSE website
            logging.warning("No existing stock list found. Creating minimal list.")
            logging.info("For a complete list, please download from NSE/BSE official sources")
            
            funds = {
                '500325': 'RELIANCE INDUSTRIES LTD.',
                '500112': 'STATE BANK OF INDIA',
                '500510': 'LARSEN & TOUBRO LTD.',
                '500180': 'HDFC BANK LTD',
                '532540': 'TATA CONSULTANCY SERVICES LTD',
                '500209': 'INFOSYS LIMITED',
                '500696': 'HINDUSTAN UNILEVER LTD.',
                '532555': 'NTPC LTD',
                '500520': 'MAHINDRA & MAHINDRA LTD',
                '532174': 'ICICI BANK LTD.',
            }
            logging.info(f"Created minimal list with {len(funds)} stocks")
        
        # Save to stk.json in the app/static directory for frontend access
        output_file = 'app/static/stk.json'
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(funds, f, indent=2)
        
        logging.info(f"Saved stock data to {output_file}")
        logging.info("Total stocks saved: {}".format(len(funds)))
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing stock data: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    success = download_and_save_scripcode()
    if success:
        print("✓ Stock data successfully processed and saved!")
        print("Note: For a comprehensive Indian stock list, download from NSE/BSE official sources")
    else:
        print("✗ Failed to process stock data")
