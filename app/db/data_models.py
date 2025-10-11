# Database models and dataclasses
# ...moved from dataclass_db/stock_predictions.py...

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class StockQuote:
    company_name: str
    current_value: float
    change: float
    p_change: float
    updated_on: str
    security_id: str
    scrip_code: str
    group_type: str
    face_value: float
    industry: str
    previous_close: float
    previous_open: float
    day_high: float
    day_low: float
    week_52_high: float
    week_52_low: float
    weighted_avg_price: float
    total_traded_value: str
    total_traded_quantity: str
    two_week_avg_quantity: str
    market_cap_full: str
    market_cap_free_float: str
    buy_1_quantity: Optional[str] = None
    buy_1_price: Optional[float] = None
    buy_2_quantity: Optional[str] = None
    buy_2_price: Optional[float] = None
    buy_3_quantity: Optional[str] = None
    buy_3_price: Optional[float] = None
    buy_4_quantity: Optional[str] = None
    buy_4_price: Optional[float] = None
    buy_5_quantity: Optional[str] = None
    buy_5_price: Optional[float] = None
    sell_1_quantity: Optional[str] = None
    sell_1_price: Optional[float] = None
    sell_2_quantity: Optional[str] = None
    sell_2_price: Optional[float] = None
    sell_3_quantity: Optional[str] = None
    sell_3_price: Optional[float] = None
    sell_4_quantity: Optional[str] = None
    sell_4_price: Optional[float] = None
    sell_5_quantity: Optional[str] = None
    sell_5_price: Optional[float] = None
    id: Optional[int] = None

@dataclass
class ModelConfiguration:
    id: Optional[int] = None
    symbol: str = ''
    model_type: str = 'transformer'  # transformer or lstm
    num_heads: int = 4
    ff_dim: int = 64
    dropout_rate: float = 0.2
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    sequence_length: int = 60
    early_stopping_patience: int = 10
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class User:
    id: int
    username: str
    password_hash: str
    email: str
    created_at: str

@dataclass
class UserWatchList:
    id: int
    user_id: int
    security_id: str
    added_at: str
