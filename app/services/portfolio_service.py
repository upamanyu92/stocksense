"""
Portfolio management service - handles holdings CRUD, transaction history,
P&L calculations, asset allocation, XLSX import, and AI analysis.
"""
import io
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.db.session_manager import get_session_manager

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service for portfolio management operations."""

    # ------------------------------------------------------------------ #
    #  Holdings CRUD
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_holdings(user_id: int) -> List[Dict[str, Any]]:
        """Get all portfolio holdings for a user."""
        db = get_session_manager()
        return db.fetch_all(
            '''SELECT id, user_id, stock_symbol, company_name, quantity,
                      avg_buy_price, current_value, invested_value,
                      pnl, pnl_percent, updated_at
               FROM portfolio_holdings
               WHERE user_id = ?
               ORDER BY stock_symbol''',
            (user_id,),
        )

    @staticmethod
    def get_holding(user_id: int, stock_symbol: str) -> Optional[Dict[str, Any]]:
        """Get a single holding."""
        db = get_session_manager()
        return db.fetch_one(
            '''SELECT id, user_id, stock_symbol, company_name, quantity,
                      avg_buy_price, current_value, invested_value,
                      pnl, pnl_percent, updated_at
               FROM portfolio_holdings
               WHERE user_id = ? AND stock_symbol = ?''',
            (user_id, stock_symbol),
        )

    @staticmethod
    def upsert_holding(
        user_id: int,
        stock_symbol: str,
        company_name: str,
        quantity: float,
        avg_buy_price: float,
        current_value: float = 0.0,
    ) -> Optional[int]:
        """Insert or update a holding."""
        db = get_session_manager()
        invested = quantity * avg_buy_price
        total_current = quantity * current_value if current_value else 0.0
        pnl = total_current - invested
        pnl_pct = (pnl / invested * 100) if invested else 0.0

        existing = db.fetch_one(
            'SELECT id FROM portfolio_holdings WHERE user_id = ? AND stock_symbol = ?',
            (user_id, stock_symbol),
        )

        if existing:
            db.update(
                '''UPDATE portfolio_holdings
                   SET company_name = ?, quantity = ?, avg_buy_price = ?,
                       current_value = ?, invested_value = ?,
                       pnl = ?, pnl_percent = ?, updated_at = datetime('now')
                   WHERE id = ?''',
                (company_name, quantity, avg_buy_price,
                 total_current, invested, pnl, round(pnl_pct, 2),
                 existing['id']),
            )
            return existing['id']
        else:
            return db.insert(
                '''INSERT INTO portfolio_holdings
                   (user_id, stock_symbol, company_name, quantity, avg_buy_price,
                    current_value, invested_value, pnl, pnl_percent)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, stock_symbol, company_name, quantity, avg_buy_price,
                 total_current, invested, pnl, round(pnl_pct, 2)),
            )

    @staticmethod
    def delete_holding(user_id: int, holding_id: int) -> bool:
        """Delete a holding."""
        db = get_session_manager()
        return db.delete(
            'DELETE FROM portfolio_holdings WHERE id = ? AND user_id = ?',
            (holding_id, user_id),
        )

    # ------------------------------------------------------------------ #
    #  Transactions
    # ------------------------------------------------------------------ #

    @staticmethod
    def add_transaction(
        user_id: int,
        stock_symbol: str,
        transaction_type: str,
        quantity: float,
        price: float,
        transaction_date: str,
        company_name: str = '',
        fees: float = 0.0,
        notes: str = '',
        source: str = 'manual',
        import_batch_id: str = None,
    ) -> Optional[int]:
        """Record a portfolio transaction and update the holding."""
        db = get_session_manager()
        total_value = quantity * price

        txn_id = db.insert(
            '''INSERT INTO portfolio_transactions
               (user_id, stock_symbol, company_name, transaction_type,
                quantity, price, total_value, fees, notes,
                transaction_date, source, import_batch_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, stock_symbol, company_name, transaction_type,
             quantity, price, total_value, fees, notes,
             transaction_date, source, import_batch_id),
        )

        # Recalculate holding from all transactions
        PortfolioService._recalculate_holding(user_id, stock_symbol, company_name)
        return txn_id

    @staticmethod
    def get_transactions(
        user_id: int,
        stock_symbol: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get transaction history."""
        db = get_session_manager()
        if stock_symbol:
            return db.fetch_all(
                '''SELECT * FROM portfolio_transactions
                   WHERE user_id = ? AND stock_symbol = ?
                   ORDER BY transaction_date DESC LIMIT ? OFFSET ?''',
                (user_id, stock_symbol, limit, offset),
            )
        return db.fetch_all(
            '''SELECT * FROM portfolio_transactions
               WHERE user_id = ?
               ORDER BY transaction_date DESC LIMIT ? OFFSET ?''',
            (user_id, limit, offset),
        )

    @staticmethod
    def delete_transaction(user_id: int, transaction_id: int) -> bool:
        """Delete a transaction and recalculate holding."""
        db = get_session_manager()
        txn = db.fetch_one(
            'SELECT stock_symbol, company_name FROM portfolio_transactions WHERE id = ? AND user_id = ?',
            (transaction_id, user_id),
        )
        if not txn:
            return False

        db.delete(
            'DELETE FROM portfolio_transactions WHERE id = ? AND user_id = ?',
            (transaction_id, user_id),
        )
        PortfolioService._recalculate_holding(user_id, txn['stock_symbol'], txn['company_name'] or '')
        return True

    # ------------------------------------------------------------------ #
    #  Portfolio Summary & Analytics
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_portfolio_summary(user_id: int) -> Dict[str, Any]:
        """Get aggregate portfolio metrics."""
        db = get_session_manager()
        row = db.fetch_one(
            '''SELECT COALESCE(SUM(invested_value), 0) as total_invested,
                      COALESCE(SUM(current_value), 0) as total_current,
                      COALESCE(SUM(pnl), 0) as total_pnl,
                      COUNT(*) as holdings_count
               FROM portfolio_holdings WHERE user_id = ?''',
            (user_id,),
        )
        total_invested = row['total_invested'] if row else 0
        total_current = row['total_current'] if row else 0
        total_pnl = row['total_pnl'] if row else 0
        pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0

        return {
            'total_invested': round(total_invested, 2),
            'total_current_value': round(total_current, 2),
            'total_pnl': round(total_pnl, 2),
            'pnl_percent': round(pnl_pct, 2),
            'holdings_count': row['holdings_count'] if row else 0,
        }

    @staticmethod
    def get_asset_allocation(user_id: int) -> List[Dict[str, Any]]:
        """Calculate asset allocation by stock."""
        db = get_session_manager()
        holdings = db.fetch_all(
            '''SELECT stock_symbol, company_name, invested_value, current_value
               FROM portfolio_holdings
               WHERE user_id = ? AND invested_value > 0
               ORDER BY invested_value DESC''',
            (user_id,),
        )
        total = sum(h['invested_value'] for h in holdings)
        if total == 0:
            return []

        return [
            {
                'stock_symbol': h['stock_symbol'],
                'company_name': h['company_name'],
                'invested_value': round(h['invested_value'], 2),
                'current_value': round(h['current_value'], 2),
                'allocation_percent': round(h['invested_value'] / total * 100, 2),
            }
            for h in holdings
        ]

    @staticmethod
    def get_top_gainers_losers(user_id: int, limit: int = 5) -> Dict[str, List]:
        """Get top gainers and losers in the portfolio."""
        db = get_session_manager()
        gainers = db.fetch_all(
            '''SELECT stock_symbol, company_name, pnl, pnl_percent
               FROM portfolio_holdings
               WHERE user_id = ? AND pnl > 0
               ORDER BY pnl_percent DESC LIMIT ?''',
            (user_id, limit),
        )
        losers = db.fetch_all(
            '''SELECT stock_symbol, company_name, pnl, pnl_percent
               FROM portfolio_holdings
               WHERE user_id = ? AND pnl < 0
               ORDER BY pnl_percent ASC LIMIT ?''',
            (user_id, limit),
        )
        return {'gainers': gainers, 'losers': losers}

    # ------------------------------------------------------------------ #
    #  XLSX / CSV Import
    # ------------------------------------------------------------------ #

    @staticmethod
    def import_xlsx(user_id: int, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Parse and import an XLSX brokerage statement.
        Returns import summary with errors.
        """
        try:
            import openpyxl
        except ImportError:
            return {'success': False, 'error': 'openpyxl is not installed'}

        batch_id = str(uuid.uuid4())
        db = get_session_manager()

        # Create import log
        db.insert(
            '''INSERT INTO portfolio_imports
               (user_id, batch_id, filename, file_type, status)
               VALUES (?, ?, ?, 'xlsx', 'processing')''',
            (user_id, batch_id, filename),
        )

        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
            ws = wb.active
            if ws is None:
                PortfolioService._fail_import(batch_id, 'No active worksheet found')
                return {'success': False, 'error': 'No active worksheet found', 'batch_id': batch_id}

            rows = list(ws.iter_rows(values_only=True))
            if len(rows) < 2:
                PortfolioService._fail_import(batch_id, 'File has no data rows')
                return {'success': False, 'error': 'File has no data rows', 'batch_id': batch_id}

            header = [str(c).strip().lower() if c else '' for c in rows[0]]
            broker_format = PortfolioService._detect_broker_format(header)

            mapping = PortfolioService._get_column_mapping(header, broker_format)
            if not mapping:
                PortfolioService._fail_import(batch_id, f'Could not detect column mapping for format: {broker_format}')
                return {
                    'success': False,
                    'error': f'Unrecognized column layout. Detected format: {broker_format}',
                    'batch_id': batch_id,
                }

            imported = 0
            skipped = 0
            errors = []

            for row_idx, row in enumerate(rows[1:], start=2):
                try:
                    parsed = PortfolioService._parse_row(row, mapping, broker_format)
                    if parsed is None:
                        skipped += 1
                        continue

                    PortfolioService.add_transaction(
                        user_id=user_id,
                        stock_symbol=parsed['symbol'],
                        transaction_type=parsed['type'],
                        quantity=parsed['quantity'],
                        price=parsed['price'],
                        transaction_date=parsed['date'],
                        company_name=parsed.get('company', ''),
                        fees=parsed.get('fees', 0.0),
                        source='xlsx_import',
                        import_batch_id=batch_id,
                    )
                    imported += 1
                except Exception as e:
                    errors.append({'row': row_idx, 'error': str(e)})

            wb.close()

            # Update import log
            db.update(
                '''UPDATE portfolio_imports
                   SET broker_format = ?, total_rows = ?, imported_rows = ?,
                       skipped_rows = ?, error_rows = ?, errors = ?,
                       status = 'completed', completed_at = datetime('now')
                   WHERE batch_id = ?''',
                (broker_format, len(rows) - 1, imported, skipped, len(errors),
                 json.dumps(errors) if errors else None, batch_id),
            )

            return {
                'success': True,
                'batch_id': batch_id,
                'broker_format': broker_format,
                'total_rows': len(rows) - 1,
                'imported': imported,
                'skipped': skipped,
                'errors': errors,
            }

        except Exception as e:
            logger.error(f"XLSX import error: {e}", exc_info=True)
            PortfolioService._fail_import(batch_id, str(e))
            return {'success': False, 'error': str(e), 'batch_id': batch_id}

    @staticmethod
    def import_csv(user_id: int, csv_content: str, filename: str = 'import.csv') -> Dict[str, Any]:
        """Parse and import a CSV brokerage statement."""
        import csv as csv_module

        batch_id = str(uuid.uuid4())
        db = get_session_manager()

        db.insert(
            '''INSERT INTO portfolio_imports
               (user_id, batch_id, filename, file_type, status)
               VALUES (?, ?, ?, 'csv', 'processing')''',
            (user_id, batch_id, filename),
        )

        try:
            reader = csv_module.DictReader(io.StringIO(csv_content))
            header = [h.strip().lower() for h in (reader.fieldnames or [])]
            broker_format = PortfolioService._detect_broker_format(header)
            mapping = PortfolioService._get_column_mapping(header, broker_format)

            if not mapping:
                PortfolioService._fail_import(batch_id, 'Unrecognized CSV layout')
                return {'success': False, 'error': 'Unrecognized CSV layout', 'batch_id': batch_id}

            imported = 0
            skipped = 0
            errors = []
            total_rows = 0

            for row_idx, row in enumerate(reader, start=2):
                total_rows += 1
                try:
                    values = tuple(row.values())
                    parsed = PortfolioService._parse_row(values, mapping, broker_format)
                    if parsed is None:
                        skipped += 1
                        continue

                    PortfolioService.add_transaction(
                        user_id=user_id,
                        stock_symbol=parsed['symbol'],
                        transaction_type=parsed['type'],
                        quantity=parsed['quantity'],
                        price=parsed['price'],
                        transaction_date=parsed['date'],
                        company_name=parsed.get('company', ''),
                        fees=parsed.get('fees', 0.0),
                        source='csv_import',
                        import_batch_id=batch_id,
                    )
                    imported += 1
                except Exception as e:
                    errors.append({'row': row_idx, 'error': str(e)})

            db.update(
                '''UPDATE portfolio_imports
                   SET broker_format = ?, total_rows = ?, imported_rows = ?,
                       skipped_rows = ?, error_rows = ?, errors = ?,
                       status = 'completed', completed_at = datetime('now')
                   WHERE batch_id = ?''',
                (broker_format, total_rows, imported, skipped, len(errors),
                 json.dumps(errors) if errors else None, batch_id),
            )

            return {
                'success': True,
                'batch_id': batch_id,
                'broker_format': broker_format,
                'imported': imported,
                'skipped': skipped,
                'errors': errors,
            }

        except Exception as e:
            logger.error(f"CSV import error: {e}", exc_info=True)
            PortfolioService._fail_import(batch_id, str(e))
            return {'success': False, 'error': str(e), 'batch_id': batch_id}

    @staticmethod
    def get_import_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get import history for a user."""
        db = get_session_manager()
        return db.fetch_all(
            '''SELECT * FROM portfolio_imports
               WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ?''',
            (user_id, limit),
        )

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _recalculate_holding(user_id: int, stock_symbol: str, company_name: str):
        """Recalculate a holding from all transactions."""
        db = get_session_manager()
        txns = db.fetch_all(
            '''SELECT transaction_type, quantity, price
               FROM portfolio_transactions
               WHERE user_id = ? AND stock_symbol = ?
               ORDER BY transaction_date''',
            (user_id, stock_symbol),
        )

        total_qty = 0.0
        total_cost = 0.0

        for t in txns:
            qty = float(t['quantity'])
            price = float(t['price'])
            if t['transaction_type'] in ('BUY', 'BONUS'):
                total_cost += qty * price
                total_qty += qty
            elif t['transaction_type'] == 'SELL':
                if total_qty > 0:
                    avg = total_cost / total_qty
                    total_cost -= qty * avg
                total_qty -= qty
            elif t['transaction_type'] == 'SPLIT':
                if total_qty > 0:
                    total_qty *= qty  # qty is split ratio

        if total_qty <= 0:
            # Remove holding if fully sold
            db.delete(
                'DELETE FROM portfolio_holdings WHERE user_id = ? AND stock_symbol = ?',
                (user_id, stock_symbol),
            )
            return

        avg_buy = total_cost / total_qty if total_qty else 0
        invested = total_qty * avg_buy

        existing = db.fetch_one(
            'SELECT id FROM portfolio_holdings WHERE user_id = ? AND stock_symbol = ?',
            (user_id, stock_symbol),
        )

        if existing:
            db.update(
                '''UPDATE portfolio_holdings
                   SET company_name = ?, quantity = ?, avg_buy_price = ?,
                       invested_value = ?, updated_at = datetime('now')
                   WHERE id = ?''',
                (company_name, total_qty, round(avg_buy, 4), round(invested, 2), existing['id']),
            )
        else:
            db.insert(
                '''INSERT INTO portfolio_holdings
                   (user_id, stock_symbol, company_name, quantity,
                    avg_buy_price, invested_value)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, stock_symbol, company_name,
                 total_qty, round(avg_buy, 4), round(invested, 2)),
            )

    @staticmethod
    def _detect_broker_format(header: List[str]) -> str:
        """Detect broker format from header columns."""
        header_set = set(header)

        # Zerodha / Kite
        if 'instrument' in header_set or 'tradingsymbol' in header_set:
            return 'zerodha'

        # Groww
        if 'scrip name' in header_set or 'folio no' in header_set:
            return 'groww'

        # Angel One / Angel Broking
        if 'scrip code' in header_set and 'company' in header_set:
            return 'angel'

        # ICICI Direct
        if 'stock code' in header_set and 'action' in header_set:
            return 'icici'

        # CAMS / Karvy mutual fund statements
        if 'scheme name' in header_set or 'folio no.' in header_set:
            return 'mutual_fund'

        # Generic format: must have symbol + quantity + price
        symbol_cols = {'symbol', 'ticker', 'stock', 'stock_symbol', 'scrip'}
        qty_cols = {'quantity', 'qty', 'units', 'shares'}
        price_cols = {'price', 'rate', 'avg_price', 'buy_price', 'nav'}

        if header_set & symbol_cols and header_set & qty_cols and header_set & price_cols:
            return 'generic'

        return 'unknown'

    @staticmethod
    def _get_column_mapping(header: List[str], broker_format: str) -> Optional[Dict[str, int]]:
        """Map logical column names to indices based on broker format."""
        def find_col(names):
            for name in names:
                if name in header:
                    return header.index(name)
            return None

        if broker_format == 'zerodha':
            return {
                'symbol': find_col(['tradingsymbol', 'instrument', 'symbol']),
                'type': find_col(['trade_type', 'type', 'transaction type']),
                'quantity': find_col(['quantity', 'qty']),
                'price': find_col(['price', 'avg. price', 'average price']),
                'date': find_col(['trade_date', 'date', 'order execution time']),
                'company': find_col(['company', 'name']),
            }

        if broker_format == 'groww':
            return {
                'symbol': find_col(['symbol', 'scrip name', 'stock symbol']),
                'type': find_col(['type', 'transaction type', 'action']),
                'quantity': find_col(['quantity', 'qty', 'units']),
                'price': find_col(['price', 'rate', 'avg. price']),
                'date': find_col(['date', 'trade date']),
                'company': find_col(['scrip name', 'company', 'name']),
            }

        if broker_format == 'angel':
            return {
                'symbol': find_col(['scrip code', 'symbol', 'scrip']),
                'type': find_col(['action', 'type', 'buy/sell']),
                'quantity': find_col(['quantity', 'qty']),
                'price': find_col(['price', 'rate']),
                'date': find_col(['date', 'trade date']),
                'company': find_col(['company', 'scrip name']),
            }

        if broker_format == 'icici':
            return {
                'symbol': find_col(['stock code', 'symbol']),
                'type': find_col(['action', 'buy/sell']),
                'quantity': find_col(['quantity', 'qty']),
                'price': find_col(['price', 'rate']),
                'date': find_col(['date', 'trade date']),
                'company': find_col(['stock name', 'company']),
            }

        if broker_format == 'mutual_fund':
            return {
                'symbol': find_col(['scheme name', 'fund name', 'scheme']),
                'type': find_col(['transaction type', 'type', 'transaction']),
                'quantity': find_col(['units', 'quantity']),
                'price': find_col(['nav', 'price', 'rate']),
                'date': find_col(['date', 'transaction date', 'trade date']),
                'company': find_col(['scheme name', 'fund name']),
                'fees': find_col(['stamp duty', 'stt', 'charges']),
            }

        if broker_format == 'generic':
            return {
                'symbol': find_col(['symbol', 'ticker', 'stock', 'stock_symbol', 'scrip']),
                'type': find_col(['type', 'transaction_type', 'action', 'trade_type', 'buy/sell']),
                'quantity': find_col(['quantity', 'qty', 'units', 'shares']),
                'price': find_col(['price', 'rate', 'avg_price', 'buy_price', 'nav']),
                'date': find_col(['date', 'transaction_date', 'trade_date']),
                'company': find_col(['company', 'company_name', 'name']),
                'fees': find_col(['fees', 'charges', 'brokerage']),
            }

        return None

    @staticmethod
    def _parse_row(row: tuple, mapping: Dict[str, Optional[int]], broker_format: str) -> Optional[Dict[str, Any]]:
        """Parse a single data row using column mapping."""
        def get_val(key):
            idx = mapping.get(key)
            if idx is None or idx >= len(row):
                return None
            return row[idx]

        symbol = get_val('symbol')
        if not symbol or str(symbol).strip() == '':
            return None

        symbol = str(symbol).strip().upper()
        quantity = get_val('quantity')
        price = get_val('price')

        if quantity is None or price is None:
            return None

        try:
            quantity = abs(float(quantity))
            price = abs(float(price))
        except (ValueError, TypeError):
            return None

        if quantity == 0:
            return None

        # Determine transaction type
        raw_type = get_val('type')
        txn_type = 'BUY'
        if raw_type:
            raw_type_upper = str(raw_type).strip().upper()
            if raw_type_upper in ('SELL', 'S', 'REDEMPTION', 'SWITCH OUT'):
                txn_type = 'SELL'
            elif raw_type_upper in ('DIVIDEND', 'DIV'):
                txn_type = 'DIVIDEND'

        # Parse date
        raw_date = get_val('date')
        txn_date = datetime.now().strftime('%Y-%m-%d')
        if raw_date:
            txn_date = PortfolioService._parse_date(raw_date)

        company = get_val('company') or ''
        fees = 0.0
        raw_fees = get_val('fees')
        if raw_fees:
            try:
                fees = abs(float(raw_fees))
            except (ValueError, TypeError):
                fees = 0.0

        return {
            'symbol': symbol,
            'type': txn_type,
            'quantity': quantity,
            'price': price,
            'date': txn_date,
            'company': str(company).strip(),
            'fees': fees,
        }

    @staticmethod
    def _parse_date(raw_date) -> str:
        """Parse various date formats to YYYY-MM-DD."""
        if isinstance(raw_date, datetime):
            return raw_date.strftime('%Y-%m-%d')

        date_str = str(raw_date).strip()
        formats = [
            '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y',
            '%Y/%m/%d', '%d-%b-%Y', '%d %b %Y', '%d-%B-%Y',
            '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return date_str

    @staticmethod
    def _fail_import(batch_id: str, error: str):
        """Mark an import as failed."""
        db = get_session_manager()
        db.update(
            '''UPDATE portfolio_imports
               SET status = 'failed', errors = ?, completed_at = datetime('now')
               WHERE batch_id = ?''',
            (json.dumps([{'error': error}]), batch_id),
        )


# ------------------------------------------------------------------ #
#  Backward-compatible module-level functions
# ------------------------------------------------------------------ #

def get_portfolio(user_id: int) -> Dict[str, Any]:
    """Get portfolio summary with holdings."""
    summary = PortfolioService.get_portfolio_summary(user_id)
    holdings = PortfolioService.get_holdings(user_id)
    return {
        'user_id': user_id,
        'holdings': holdings,
        'summary': summary,
    }


def import_portfolio_csv(user_id: int, csv_content: str) -> bool:
    """Import portfolio from CSV content."""
    result = PortfolioService.import_csv(user_id, csv_content)
    return result.get('success', False)

