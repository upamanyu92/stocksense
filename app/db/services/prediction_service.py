"""
Prediction database service for managing prediction table operations
"""
from typing import Optional, List, Dict, Any
from app.db.session_manager import get_session_manager
from app.db.data_models import Prediction


class PredictionService:
    """Service for managing predictions table operations"""
    
    @staticmethod
    def create(prediction: Prediction) -> Optional[int]:
        """Create a new prediction"""
        db = get_session_manager()

        try:
            return db.insert('''
                INSERT OR REPLACE INTO predictions 
                (company_name, security_id, current_price, predicted_price, prediction_date, stock_status, stock_symbol)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                prediction.company_name,
                prediction.security_id,
                prediction.current_price,
                prediction.predicted_price,
                prediction.prediction_date,
                prediction.stock_status or 'active',
                prediction.security_id  # Use security_id as stock_symbol
            ))
        except Exception as e:
            print(f"Error creating prediction: {e}")
            return None

    @staticmethod
    def get_by_id(prediction_id: int) -> Optional[Prediction]:
        """Get prediction by ID"""
        db = get_session_manager()
        row = db.fetch_one('SELECT * FROM predictions WHERE id = ?', (prediction_id,))

        if row:
            return Prediction(**row)
        return None
    
    @staticmethod
    def get_by_security_id(security_id: str) -> Optional[Prediction]:
        """Get prediction by security ID"""
        db = get_session_manager()
        row = db.fetch_one('SELECT * FROM predictions WHERE security_id = ?', (security_id,))

        if row:
            return Prediction(**row)
        return None
    
    @staticmethod
    def get_prediction_by_security_id(security_id: str) -> Optional[Dict[str, Any]]:
        """Get prediction by security ID as dictionary"""
        db = get_session_manager()
        stock = db.fetch_one('''
            SELECT company_name, security_id, current_price, predicted_price,
                   (predicted_price - current_price) AS profit,
                   prediction_date, stock_status
            FROM predictions 
            WHERE security_id = ?
        ''', (security_id,))

        if stock:
            if stock['current_price'] and stock['predicted_price']:
                profit_pct = ((stock['predicted_price'] - stock['current_price']) /
                              stock['current_price']) * 100
                stock['profit_percentage'] = profit_pct
            else:
                stock['profit_percentage'] = 0
            return stock
        return None
    
    @staticmethod
    def get_all(limit: int = None, offset: int = 0, order_by: str = 'prediction_date DESC') -> List[Prediction]:
        """Get all predictions with optional pagination"""
        db = get_session_manager()

        query = f'SELECT * FROM predictions ORDER BY {order_by}'
        if limit:
            query += f' LIMIT {limit} OFFSET {offset}'
        
        rows = db.fetch_all(query)

        return [Prediction(**row) for row in rows]

    @staticmethod
    def get_top_predictions(page: int = 1, page_size: int = 2000) -> Dict[str, Any]:
        """Get top predictions ordered by profit percentage"""
        db = get_session_manager()
        offset = (page - 1) * page_size

        total_row = db.fetch_one('SELECT COUNT(*) as count FROM predictions')
        total = total_row['count'] if total_row else 0

        rows = db.fetch_all('''
            SELECT company_name, security_id, current_price, predicted_price,
                   (predicted_price - current_price) AS profit,
                   prediction_date
            FROM predictions
            ORDER BY (predicted_price - current_price) / current_price DESC
            LIMIT ? OFFSET ?
        ''', (page_size, offset))

        predictions = []
        for stock in rows:
            profit_pct = ((stock['predicted_price'] - stock['current_price']) /
                          stock['current_price']) * 100
            stock['profit_percentage'] = profit_pct
            predictions.append(stock)
        
        return {
            'predictions': predictions,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
    
    @staticmethod
    def count() -> int:
        """Get total count of predictions"""
        db = get_session_manager()
        row = db.fetch_one('SELECT COUNT(*) as count FROM predictions')
        return row['count'] if row else 0

    @staticmethod
    def delete(prediction_id: int) -> bool:
        """Delete a prediction"""
        db = get_session_manager()

        try:
            return db.delete('DELETE FROM predictions WHERE id = ?', (prediction_id,))
        except Exception as e:
            print(f"Error deleting prediction: {e}")
            return False

