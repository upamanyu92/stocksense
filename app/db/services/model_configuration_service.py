"""
Model Configuration database service for managing model_configurations table operations
"""
from typing import Optional, List
from datetime import datetime
from app.db.session_manager import get_session_manager
from app.db.data_models import ModelConfiguration


class ModelConfigurationService:
    """Service for managing model_configurations table operations"""
    
    @staticmethod
    def create(config: ModelConfiguration) -> Optional[int]:
        """Create a new model configuration"""
        db = get_session_manager()

        now = datetime.now()
        
        try:
            return db.insert('''
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
        except Exception as e:
            print(f"Error creating model configuration: {e}")
            return None

    @staticmethod
    def get_by_id(config_id: int) -> Optional[ModelConfiguration]:
        """Get model configuration by ID"""
        db = get_session_manager()
        row = db.fetch_one('SELECT * FROM model_configurations WHERE id = ?', (config_id,))

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
        db = get_session_manager()
        row = db.fetch_one('''
            SELECT * FROM model_configurations 
            WHERE symbol = ? AND model_type = ?
        ''', (symbol, model_type))

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
        db = get_session_manager()

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
            return db.update(f'UPDATE model_configurations SET {set_clause} WHERE id = ?', tuple(values))
        except Exception as e:
            print(f"Error updating model configuration: {e}")
            return False

    @staticmethod
    def delete(config_id: int) -> bool:
        """Delete a model configuration"""
        db = get_session_manager()

        try:
            return db.delete('DELETE FROM model_configurations WHERE id = ?', (config_id,))
        except Exception as e:
            print(f"Error deleting model configuration: {e}")
            return False

    @staticmethod
    def get_all() -> List[ModelConfiguration]:
        """Get all model configurations"""
        db = get_session_manager()
        rows = db.fetch_all('SELECT * FROM model_configurations')

        configs = []
        for row in rows:
            data = dict(row)
            if 'created_at' in data and isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if 'updated_at' in data and isinstance(data['updated_at'], str):
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            configs.append(ModelConfiguration(**data))
        return configs


