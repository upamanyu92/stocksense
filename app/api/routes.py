# Placeholder for API routes

from fastapi import APIRouter, HTTPException
from app.api.config_routes import router as config_router
from app.models.training_script import train_transformer_model, train_model
from app.services.configuration_service import ConfigurationService
from typing import Optional
from pydantic import BaseModel

router = APIRouter()

# Include configuration routes
router.include_router(config_router, tags=["configurations"])

class TrainingResponse(BaseModel):
    symbol: str
    model_type: str
    model_path: str
    metrics: dict

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.post("/train/{symbol}", response_model=TrainingResponse)
async def train_stock_model(symbol: str, model_type: str = "transformer"):
    """Train a model for a specific stock symbol using stored configurations"""
    try:
        # Get configuration for the symbol
        config = ConfigurationService.get_configuration(symbol, model_type)

        if model_type == "transformer":
            model, scaler = train_transformer_model(
                symbol,
                time_step=config.sequence_length if config else 60,
                epochs=config.epochs if config else 100,
                batch_size=config.batch_size if config else 32
            )
        else:
            model, scaler = train_model(symbol)

        # The model saving is handled within the training functions
        # Return the training results
        return {
            "symbol": symbol,
            "model_type": model_type,
            "model_path": f"model/saved_models/{symbol}_{model_type}_latest",
            "metrics": {
                "status": "success",
                "configuration_used": config is not None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
