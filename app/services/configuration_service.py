from datetime import datetime
from typing import List, Optional
from app.db.data_models import ModelConfiguration
from app.db.db_executor import execute_query, fetch_one, fetch_all

class ConfigurationService:
    @staticmethod
    def get_configuration(symbol: str, model_type: str = 'transformer') -> Optional[ModelConfiguration]:
        query = """
            SELECT * FROM model_configurations 
            WHERE symbol = ? AND model_type = ?
            ORDER BY updated_at DESC LIMIT 1
        """
        result = fetch_one(query, (symbol, model_type))
        if result:
            return ModelConfiguration(**result)
        return None

    @staticmethod
    def get_all_configurations() -> List[ModelConfiguration]:
        query = "SELECT * FROM model_configurations ORDER BY updated_at DESC"
        results = fetch_all(query)
        return [ModelConfiguration(**row) for row in results]

    @staticmethod
    def create_configuration(config: ModelConfiguration) -> ModelConfiguration:
        now = datetime.now()
        config.created_at = now
        config.updated_at = now

        query = """
            INSERT INTO model_configurations (
                symbol, model_type, num_heads, ff_dim, dropout_rate,
                learning_rate, batch_size, epochs, sequence_length,
                early_stopping_patience, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            config.symbol, config.model_type, config.num_heads,
            config.ff_dim, config.dropout_rate, config.learning_rate,
            config.batch_size, config.epochs, config.sequence_length,
            config.early_stopping_patience, config.created_at,
            config.updated_at
        )

        config.id = execute_query(query, params)
        return config

    @staticmethod
    def update_configuration(config: ModelConfiguration) -> ModelConfiguration:
        config.updated_at = datetime.now()

        query = """
            UPDATE model_configurations SET
                num_heads = ?,
                ff_dim = ?,
                dropout_rate = ?,
                learning_rate = ?,
                batch_size = ?,
                epochs = ?,
                sequence_length = ?,
                early_stopping_patience = ?,
                updated_at = ?
            WHERE id = ?
        """
        params = (
            config.num_heads, config.ff_dim, config.dropout_rate,
            config.learning_rate, config.batch_size, config.epochs,
            config.sequence_length, config.early_stopping_patience,
            config.updated_at, config.id
        )

        execute_query(query, params)
        return config

    @staticmethod
    def delete_configuration(config_id: int) -> bool:
        query = "DELETE FROM model_configurations WHERE id = ?"
        return execute_query(query, (config_id,)) > 0
