"""
Prediction database service for managing prediction table operations
"""
from typing import Optional, List, Dict, Any
from app.utils.util import get_db_connection
from app.db.data_models import Prediction


class PredictionService:
    """Service for managing predictions table operations"""
    
    @staticmethod
    def create(prediction: Prediction) -> Optional[int]:
        """Create a new prediction"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO predictions 
                (company_name, security_id, current_price, predicted_price, prediction_date, stock_status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                prediction.company_name,
                prediction.security_id,
                prediction.current_price,
                prediction.predicted_price,
                prediction.prediction_date,
                prediction.stock_status or 'active'
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            print(f"Error creating prediction: {e}")
            return None
        finally:
            conn.close()
    
    @staticmethod
    def get_by_id(prediction_id: int) -> Optional[Prediction]:
        """Get prediction by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM predictions WHERE id = ?', (prediction_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Prediction(**dict(row))
        return None
    
    @staticmethod
    def get_by_security_id(security_id: str) -> Optional[Prediction]:
        """Get prediction by security ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM predictions WHERE security_id = ?', (security_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Prediction(**dict(row))
        return None
    
    @staticmethod
    def get_all(limit: int = None, offset: int = 0, order_by: str = 'prediction_date DESC') -> List[Prediction]:
        """Get all predictions with optional pagination"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = f'SELECT * FROM predictions ORDER BY {order_by}'
        if limit:
            query += f' LIMIT {limit} OFFSET {offset}'
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        return [Prediction(**dict(row)) for row in rows]
    
    @staticmethod
    def get_top_predictions(page: int = 1, page_size: int = 2000) -> Dict[str, Any]:
        """Get top predictions ordered by profit percentage"""
        offset = (page - 1) * page_size
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM predictions')
        total = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT company_name, security_id, current_price, predicted_price, 
                   (predicted_price - current_price) AS profit,
                   prediction_date
            FROM predictions
            ORDER BY (predicted_price - current_price) / current_price DESC
            LIMIT ? OFFSET ?
        ''', (page_size, offset))
        rows = cursor.fetchall()
        conn.close()
        
        predictions = []
        for row in rows:
            stock = dict(row)
            stock['profit_percentage'] = ((stock['predicted_price'] - stock['current_price']) / stock['current_price']) * 100
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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM predictions')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    @staticmethod
    def delete(prediction_id: int) -> bool:
        """Delete a prediction"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM predictions WHERE id = ?', (prediction_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting prediction: {e}")
            return False
        finally:
            conn.close()
