from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime

from app.services.configuration_service import ConfigurationService
from app.db.data_models import ModelConfiguration
from app.models.config_validator import ModelConfigValidator
from app.models.stock_configs import get_stock_config

router = APIRouter()

@router.get("/configurations", response_model=List[ModelConfigValidator])
async def get_configurations():
    configs = ConfigurationService.get_all_configurations()
    return configs

@router.get("/configurations/{symbol}", response_model=ModelConfigValidator)
async def get_configuration(symbol: str, model_type: str = 'transformer'):
    config = ConfigurationService.get_configuration(symbol, model_type)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config

@router.post("/configurations", response_model=ModelConfigValidator)
async def create_configuration(config: ModelConfigValidator):
    try:
        model_config = ModelConfiguration(**config.dict())
        created = ConfigurationService.create_configuration(model_config)
        return created
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/configurations/template/{symbol}")
async def create_configuration_from_template(
    symbol: str,
    volatility_type: str = "medium"
):
    """Create a configuration using predefined templates based on stock characteristics"""
    try:
        template_config = get_stock_config(symbol, volatility_type)
        config = ModelConfigValidator(**template_config)
        model_config = ModelConfiguration(**config.dict())
        created = ConfigurationService.create_configuration(model_config)
        return created
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/configurations/{config_id}", response_model=ModelConfigValidator)
async def update_configuration(config_id: int, config: ModelConfigValidator):
    try:
        model_config = ModelConfiguration(id=config_id, **config.dict())
        updated = ConfigurationService.update_configuration(model_config)
        return updated
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/configurations/{config_id}", status_code=204)
async def delete_configuration(config_id: int):
    if not ConfigurationService.delete_configuration(config_id):
        raise HTTPException(status_code=404, detail="Configuration not found")
