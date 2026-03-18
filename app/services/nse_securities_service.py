"""
NSE Securities Management - handles loading and managing NSE stocks in database
"""
import logging
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NSESecuritiesService:
    """Service for managing NSE securities in the database"""

    @staticmethod
    def load_nse_securities_from_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Load NSE securities from a JSON file (stk.json).

        Args:
            file_path: Path to stk.json file

        Returns:
            List of securities data
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"Securities file not found: {file_path}")
                return []

            with open(file_path, 'r') as f:
                securities_data = json.load(f)

            logger.info(f"Loaded {len(securities_data)} securities from {file_path}")
            return securities_data

        except Exception as e:
            logger.error(f"Error loading NSE securities file: {e}")
            return []

    @staticmethod
    def add_securities_to_db(securities: Dict[str, str], db_connection) -> Dict[str, Any]:
        """
        Add NSE securities to database.

        Args:
            securities: Dictionary of {code: company_name}
            db_connection: Database connection

        Returns:
            Dictionary with results (added, skipped, errors)
        """
        try:
            cursor = db_connection.cursor()
            added = 0
            skipped = 0
            errors = 0

            for code, company_name in securities.items():
                try:
                    # Check if already exists
                    cursor.execute(
                        'SELECT id FROM stock_quotes WHERE scrip_code = ?',
                        (code,)
                    )

                    if cursor.fetchone():
                        skipped += 1
                        continue

                    # Insert new security
                    cursor.execute('''
                        INSERT INTO stock_quotes 
                        (scrip_code, company_name, security_id, updated_on)
                        VALUES (?, ?, ?, ?)
                    ''', (code, company_name, code, datetime.now().isoformat()))

                    added += 1

                    if added % 100 == 0:
                        db_connection.commit()
                        logger.info(f"Added {added} securities so far...")

                except Exception as e:
                    logger.error(f"Error adding security {code}: {e}")
                    errors += 1
                    continue

            db_connection.commit()

            return {
                'added': added,
                'skipped': skipped,
                'errors': errors,
                'total': len(securities),
                'success': True
            }

        except Exception as e:
            logger.error(f"Error in add_securities_to_db: {e}")
            return {
                'added': 0,
                'skipped': 0,
                'errors': len(securities),
                'total': len(securities),
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_available_securities(db_connection, limit: int = None) -> List[Dict[str, str]]:
        """
        Get list of available NSE securities from database.

        Args:
            db_connection: Database connection
            limit: Maximum number to return (None for all)

        Returns:
            List of securities
        """
        try:
            cursor = db_connection.cursor()

            query = 'SELECT scrip_code, company_name, security_id FROM stock_quotes'
            if limit:
                query += f' LIMIT {limit}'

            cursor.execute(query)
            rows = cursor.fetchall()

            securities = [
                {
                    'scrip_code': row[0],
                    'company_name': row[1],
                    'security_id': row[2]
                }
                for row in rows
            ]

            return securities

        except Exception as e:
            logger.error(f"Error getting available securities: {e}")
            return []

    @staticmethod
    def search_securities(db_connection, query: str) -> List[Dict[str, str]]:
        """
        Search for securities by company name or code.

        Args:
            db_connection: Database connection
            query: Search query

        Returns:
            List of matching securities
        """
        try:
            cursor = db_connection.cursor()
            search_pattern = f"%{query}%"

            cursor.execute('''
                SELECT scrip_code, company_name, security_id 
                FROM stock_quotes 
                WHERE UPPER(company_name) LIKE UPPER(?) 
                   OR UPPER(scrip_code) LIKE UPPER(?)
                LIMIT 10
            ''', (search_pattern, search_pattern))

            rows = cursor.fetchall()

            securities = [
                {
                    'scrip_code': row[0],
                    'company_name': row[1],
                    'security_id': row[2]
                }
                for row in rows
            ]

            return securities

        except Exception as e:
            logger.error(f"Error searching securities: {e}")
            return []

    @staticmethod
    def get_security_count(db_connection) -> int:
        """Get total count of securities in database"""
        try:
            cursor = db_connection.cursor()
            cursor.execute('SELECT COUNT(*) FROM stock_quotes')
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            logger.error(f"Error getting security count: {e}")
            return 0

