# Feature engineering functions
# ...moved from features/FeatureFactory.py...

import pandas as pd
import numpy as np
from typing import List, Optional

def calculate_technical_indicators(df: pd.DataFrame,
                                custom_periods: Optional[List[int]] = None) -> pd.DataFrame:
    """Calculate technical indicators with customizable periods"""
    periods = custom_periods or [5, 10, 20, 50]

    # Basic price indicators
    for period in periods:
        df[f'SMA_{period}'] = df['Close'].rolling(window=period).mean()
        df[f'EMA_{period}'] = df['Close'].ewm(span=period, adjust=False).mean()

    # Volatility indicators
    df['ATR'] = calculate_atr(df)
    df['Bollinger_Upper'], df['Bollinger_Lower'] = calculate_bollinger_bands(df)

    # Momentum indicators
    df['RSI'] = calculate_rsi(df)
    df['MACD'], df['MACD_Signal'] = calculate_macd(df)
    df['ROC'] = calculate_roc(df)

    # Volume indicators
    df['OBV'] = calculate_obv(df)
    df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']

    return df

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high = df['High']
    low = df['Low']
    close = df['Close']

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calculate_bollinger_bands(df: pd.DataFrame,
                            period: int = 20,
                            std_dev: float = 2.0) -> tuple:
    """Calculate Bollinger Bands"""
    sma = df['Close'].rolling(window=period).mean()
    std = df['Close'].rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, lower_band

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    relative_strength = gain / loss
    return 100 - (100 / (1 + relative_strength))

def calculate_macd(df: pd.DataFrame,
                  fast_period: int = 12,
                  slow_period: int = 26,
                  signal_period: int = 9) -> tuple:
    """Calculate MACD and Signal line"""
    fast_ema = df['Close'].ewm(span=fast_period, adjust=False).mean()
    slow_ema = df['Close'].ewm(span=slow_period, adjust=False).mean()
    macd = fast_ema - slow_ema
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    return macd, signal

def calculate_roc(df: pd.DataFrame, period: int = 12) -> pd.Series:
    """Calculate Rate of Change"""
    return df['Close'].pct_change(periods=period) * 100

def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """Calculate On-Balance Volume"""
    obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    return obv

def create_features(data: pd.DataFrame,
                   custom_periods: Optional[List[int]] = None,
                   volatility_type: str = 'medium') -> pd.DataFrame:
    """Create technical features for stock price prediction with enhanced customization"""
    try:
        stock_data = data.copy()

        # Handle MultiIndex columns
        if isinstance(stock_data.columns, pd.MultiIndex):
            stock_symbol = stock_data.columns.get_level_values('Ticker').unique()[0]
            stock_data = stock_data.xs(stock_symbol, axis=1, level='Ticker')

        # Validate required columns
        required_columns = ['Close', 'Volume', 'High', 'Low']
        for col in required_columns:
            if col not in stock_data.columns:
                raise ValueError(f"Required column {col} not found in data")
            stock_data[col] = pd.to_numeric(stock_data[col], errors='coerce')

        # Adjust periods based on volatility type
        if volatility_type == 'high':
            custom_periods = custom_periods or [3, 5, 10, 20]
        elif volatility_type == 'low':
            custom_periods = custom_periods or [10, 20, 50, 100]
        else:
            custom_periods = custom_periods or [5, 10, 20, 50]

        # Calculate all technical indicators
        stock_data = calculate_technical_indicators(stock_data, custom_periods)

        # Add market timing features
        stock_data['Day_of_Week'] = stock_data.index.dayofweek
        stock_data['Month'] = stock_data.index.month
        stock_data['Quarter'] = stock_data.index.quarter

        # Calculate returns
        stock_data['Returns'] = stock_data['Close'].pct_change()
        stock_data['Returns_Volatility'] = stock_data['Returns'].rolling(window=20).std()

        # Drop any rows with NaN values
        stock_data = stock_data.dropna()

        return stock_data

    except Exception as e:
        print(f"Error in create_features: {str(e)}")
        print(f"DataFrame columns: {data.columns}")
        print(f"DataFrame head: {data.head()}")
        raise
