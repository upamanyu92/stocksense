from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class ModelConfigValidator(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)")
    model_type: str = Field(
        default="transformer",
        description="Model type (transformer or lstm)"
    )
    num_heads: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Number of attention heads"
    )
    ff_dim: int = Field(
        default=64,
        ge=32,
        le=512,
        description="Feed-forward dimension"
    )
    dropout_rate: float = Field(
        default=0.2,
        ge=0.0,
        le=0.5,
        description="Dropout rate"
    )
    learning_rate: float = Field(
        default=0.001,
        ge=0.0001,
        le=0.01,
        description="Learning rate"
    )
    batch_size: int = Field(
        default=32,
        ge=8,
        le=256,
        description="Training batch size"
    )
    epochs: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Number of training epochs"
    )
    sequence_length: int = Field(
        default=60,
        ge=20,
        le=200,
        description="Sequence length for time series"
    )
    early_stopping_patience: int = Field(
        default=10,
        ge=5,
        le=50,
        description="Early stopping patience"
    )

    @validator('model_type')
    def validate_model_type(cls, v):
        if v not in ['transformer', 'lstm']:
            raise ValueError('model_type must be either "transformer" or "lstm"')
        return v

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "model_type": "transformer",
                "num_heads": 8,
                "ff_dim": 128,
                "dropout_rate": 0.2,
                "learning_rate": 0.001,
                "batch_size": 32,
                "epochs": 100,
                "sequence_length": 60,
                "early_stopping_patience": 10
            }
        }
