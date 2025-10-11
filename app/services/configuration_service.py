from datetime import datetime
from typing import List, Optional
from app.db.data_models import ModelConfiguration
from app.db.db_executor import (
    get_configuration as db_get_configuration,
    get_all_configurations as db_get_all_configurations,
    create_configuration as db_create_configuration,
    update_configuration as db_update_configuration,
    delete_configuration as db_delete_configuration
)

class ConfigurationService:
    @staticmethod
    def get_configuration(symbol: str, model_type: str = 'transformer') -> Optional[ModelConfiguration]:
        result = db_get_configuration(symbol, model_type)
        if result:
            return ModelConfiguration(**result)
        return None

    @staticmethod
    def get_all_configurations() -> List[ModelConfiguration]:
        results = db_get_all_configurations()
        return [ModelConfiguration(**row) for row in results]

    @staticmethod
    def create_configuration(config: ModelConfiguration) -> ModelConfiguration:
        return db_create_configuration(config)

    @staticmethod
    def update_configuration(config: ModelConfiguration) -> ModelConfiguration:
        return db_update_configuration(config)

    @staticmethod
    def delete_configuration(config_id: int) -> bool:
        return db_delete_configuration(config_id)
