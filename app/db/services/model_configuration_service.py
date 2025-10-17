"""
Model Configuration database service for managing model_configurations table operations
"""
from typing import Optional, List
from datetime import datetime
from app.utils.util import get_db_connection
from app.db.data_models import ModelConfiguration


class ModelConfigurationService:
    """Service for managing model_configurations table operations"""
    
    @staticmethod
    def create(config: ModelConfiguration) -> Optional[int]:
        """Create a new model configuration"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now()
        
        try:
            cursor.execute('''
                INSERT INTO model_configurations (
                    symbol, model_type, num_heads, ff_dim, dropout_rate,
                    learning_rate, batch_size, epochs, sequence_length,
                    early_stopping_patience, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                config.symbol, config.model_type, config.num_heads, config.ff_dim,
                config.dropout_rate, config.learning_rate, config.batch_size,
                config.epochs, config.sequence_length, config.early_stopping_patience,
                now, now
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            print(f"Error creating model configuration: {e}")
            return None
        finally:
            conn.close()
    
    @staticmethod
    def get_by_id(config_id: int) -> Optional[ModelConfiguration]:
        """Get model configuration by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM model_configurations WHERE id = ?', (config_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            data = dict(row)
            # Convert timestamp strings to datetime objects if needed
            if 'created_at' in data and isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if 'updated_at' in data and isinstance(data['updated_at'], str):
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            return ModelConfiguration(**data)
        return None
    
    @staticmethod
    def get_by_symbol_and_type(symbol: str, model_type: str) -> Optional[ModelConfiguration]:
        """Get model configuration by symbol and type"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM model_configurations 
            WHERE symbol = ? AND model_type = ?
        ''', (symbol, model_type))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            data = dict(row)
            if 'created_at' in data and isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if 'updated_at' in data and isinstance(data['updated_at'], str):
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            return ModelConfiguration(**data)
        return None
    
    @staticmethod
    def update(config_id: int, **kwargs) -> bool:
        """Update model configuration fields"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        valid_fields = [
            'num_heads', 'ff_dim', 'dropout_rate', 'learning_rate',
            'batch_size', 'epochs', 'sequence_length', 'early_stopping_patience'
        ]
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not update_fields:
            return False
        
        update_fields['updated_at'] = datetime.now()
        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [config_id]
        
        try:
            cursor.execute(f'UPDATE model_configurations SET {set_clause} WHERE id = ?', values)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error updating model configuration: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def delete(config_id: int) -> bool:
        """Delete a model configuration"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM model_configurations WHERE id = ?', (config_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting model configuration: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def get_all() -> List[ModelConfiguration]:
        """Get all model configurations"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM model_configurations')
        rows = cursor.fetchall()
        conn.close()
        
        configs = []
        for row in rows:
            data = dict(row)
            if 'created_at' in data and isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if 'updated_at' in data and isinstance(data['updated_at'], str):
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            configs.append(ModelConfiguration(**data))
        return configs
