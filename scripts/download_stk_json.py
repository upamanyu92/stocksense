#!/usr/bin/env python3
"""
Script to download and save BSE scripcode data to a JSON file.
This file will be used for autocomplete in the watchlist input.
"""
import json
import logging
from bsedata.bse import BSE

logging.basicConfig(level=logging.INFO)


def download_and_save_scripcode():
    """Download scripcode from BSE and save to stk.json"""
    try:
        logging.info("Downloading scripcode data from BSE...")
        b = BSE()
        b.updateScripCodes()
        funds = b.getScripCodes()
        
        logging.info(f"Downloaded {len(funds)} stocks")
        
        # Save to stk.json in the app/static directory for frontend access
        output_file = 'app/static/stk.json'
        with open(output_file, 'w') as f:
            json.dump(funds, f, indent=2)
        
        logging.info(f"Saved scripcode data to {output_file}")
        logging.info("Total stocks saved: {}".format(len(funds)))
        
        return True
        
    except Exception as e:
        logging.error(f"Error downloading scripcode: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    success = download_and_save_scripcode()
    if success:
        print("✓ Scripcode data successfully downloaded and saved!")
    else:
        print("✗ Failed to download scripcode data")
