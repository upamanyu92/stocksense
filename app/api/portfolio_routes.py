"""
Portfolio management API routes - handles holdings CRUD, transactions,
XLSX/CSV import, analytics, and AI portfolio analysis.
"""
import logging

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)

portfolio_bp = Blueprint('portfolio', __name__, url_prefix='/api/portfolio')

# Maximum upload size: 10 MB
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


# ------------------------------------------------------------------ #
#  Holdings
# ------------------------------------------------------------------ #

@portfolio_bp.route('/holdings', methods=['GET'])
@login_required
def get_holdings():
    """Get all portfolio holdings for the current user."""
    try:
        holdings = PortfolioService.get_holdings(current_user.id)
        summary = PortfolioService.get_portfolio_summary(current_user.id)
        return jsonify({'success': True, 'holdings': holdings, 'summary': summary})
    except Exception as e:
        logger.error(f"Error fetching holdings: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch holdings'}), 500


@portfolio_bp.route('/holdings', methods=['POST'])
@login_required
def add_holding():
    """Add or update a holding manually."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        symbol = data.get('stock_symbol', '').strip().upper()
        if not symbol:
            return jsonify({'error': 'stock_symbol is required'}), 400

        quantity = float(data.get('quantity', 0))
        avg_buy_price = float(data.get('avg_buy_price', 0))
        if quantity <= 0 or avg_buy_price <= 0:
            return jsonify({'error': 'quantity and avg_buy_price must be positive'}), 400

        holding_id = PortfolioService.upsert_holding(
            user_id=current_user.id,
            stock_symbol=symbol,
            company_name=data.get('company_name', ''),
            quantity=quantity,
            avg_buy_price=avg_buy_price,
            current_value=float(data.get('current_value', 0)),
        )

        return jsonify({'success': True, 'holding_id': holding_id})
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid data: {e}'}), 400
    except Exception as e:
        logger.error(f"Error adding holding: {e}", exc_info=True)
        return jsonify({'error': 'Failed to add holding'}), 500


@portfolio_bp.route('/holdings/<int:holding_id>', methods=['DELETE'])
@login_required
def delete_holding(holding_id):
    """Delete a portfolio holding."""
    try:
        deleted = PortfolioService.delete_holding(current_user.id, holding_id)
        if not deleted:
            return jsonify({'error': 'Holding not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting holding: {e}", exc_info=True)
        return jsonify({'error': 'Failed to delete holding'}), 500


# ------------------------------------------------------------------ #
#  Transactions
# ------------------------------------------------------------------ #

@portfolio_bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    """Get transaction history."""
    try:
        symbol = request.args.get('symbol')
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = int(request.args.get('offset', 0))

        transactions = PortfolioService.get_transactions(
            current_user.id, stock_symbol=symbol, limit=limit, offset=offset,
        )
        return jsonify({'success': True, 'transactions': transactions})
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch transactions'}), 500


@portfolio_bp.route('/transactions', methods=['POST'])
@login_required
def add_transaction():
    """Record a new transaction."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        symbol = data.get('stock_symbol', '').strip().upper()
        if not symbol:
            return jsonify({'error': 'stock_symbol is required'}), 400

        txn_type = data.get('transaction_type', 'BUY').upper()
        if txn_type not in ('BUY', 'SELL', 'DIVIDEND', 'SPLIT', 'BONUS'):
            return jsonify({'error': 'Invalid transaction_type'}), 400

        quantity = float(data.get('quantity', 0))
        price = float(data.get('price', 0))
        if quantity <= 0 or price <= 0:
            return jsonify({'error': 'quantity and price must be positive'}), 400

        txn_date = data.get('transaction_date', '')
        if not txn_date:
            from datetime import datetime
            txn_date = datetime.now().strftime('%Y-%m-%d')

        txn_id = PortfolioService.add_transaction(
            user_id=current_user.id,
            stock_symbol=symbol,
            transaction_type=txn_type,
            quantity=quantity,
            price=price,
            transaction_date=txn_date,
            company_name=data.get('company_name', ''),
            fees=float(data.get('fees', 0)),
            notes=data.get('notes', ''),
        )

        return jsonify({'success': True, 'transaction_id': txn_id})
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid data: {e}'}), 400
    except Exception as e:
        logger.error(f"Error adding transaction: {e}", exc_info=True)
        return jsonify({'error': 'Failed to add transaction'}), 500


@portfolio_bp.route('/transactions/<int:transaction_id>', methods=['DELETE'])
@login_required
def delete_transaction(transaction_id):
    """Delete a transaction."""
    try:
        deleted = PortfolioService.delete_transaction(current_user.id, transaction_id)
        if not deleted:
            return jsonify({'error': 'Transaction not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting transaction: {e}", exc_info=True)
        return jsonify({'error': 'Failed to delete transaction'}), 500


# ------------------------------------------------------------------ #
#  Analytics
# ------------------------------------------------------------------ #

@portfolio_bp.route('/summary', methods=['GET'])
@login_required
def get_summary():
    """Get portfolio summary metrics."""
    try:
        summary = PortfolioService.get_portfolio_summary(current_user.id)
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        logger.error(f"Error fetching summary: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch summary'}), 500


@portfolio_bp.route('/allocation', methods=['GET'])
@login_required
def get_allocation():
    """Get asset allocation breakdown."""
    try:
        allocation = PortfolioService.get_asset_allocation(current_user.id)
        return jsonify({'success': True, 'allocation': allocation})
    except Exception as e:
        logger.error(f"Error fetching allocation: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch allocation'}), 500


@portfolio_bp.route('/gainers-losers', methods=['GET'])
@login_required
def get_gainers_losers():
    """Get top gainers and losers."""
    try:
        limit = min(int(request.args.get('limit', 5)), 20)
        data = PortfolioService.get_top_gainers_losers(current_user.id, limit=limit)
        return jsonify({'success': True, **data})
    except Exception as e:
        logger.error(f"Error fetching gainers/losers: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch gainers/losers'}), 500


# ------------------------------------------------------------------ #
#  Import
# ------------------------------------------------------------------ #

@portfolio_bp.route('/import/xlsx', methods=['POST'])
@login_required
def import_xlsx():
    """Import portfolio from an XLSX file."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400

        filename = file.filename
        if not filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'File must be .xlsx or .xls format'}), 400

        file_bytes = file.read()
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            return jsonify({'error': 'File too large. Maximum size is 10 MB'}), 400

        if len(file_bytes) == 0:
            return jsonify({'error': 'File is empty'}), 400

        result = PortfolioService.import_xlsx(current_user.id, file_bytes, filename)
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Error importing XLSX: {e}", exc_info=True)
        return jsonify({'error': 'Failed to import file'}), 500


@portfolio_bp.route('/import/csv', methods=['POST'])
@login_required
def import_csv():
    """Import portfolio from a CSV file."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400

        filename = file.filename
        if not filename.lower().endswith('.csv'):
            return jsonify({'error': 'File must be .csv format'}), 400

        file_bytes = file.read()
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            return jsonify({'error': 'File too large. Maximum size is 10 MB'}), 400

        if len(file_bytes) == 0:
            return jsonify({'error': 'File is empty'}), 400

        csv_content = file_bytes.decode('utf-8', errors='replace')
        result = PortfolioService.import_csv(current_user.id, csv_content, filename)
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Error importing CSV: {e}", exc_info=True)
        return jsonify({'error': 'Failed to import file'}), 500


@portfolio_bp.route('/import/history', methods=['GET'])
@login_required
def get_import_history():
    """Get import history."""
    try:
        history = PortfolioService.get_import_history(current_user.id)
        return jsonify({'success': True, 'imports': history})
    except Exception as e:
        logger.error(f"Error fetching import history: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch import history'}), 500
