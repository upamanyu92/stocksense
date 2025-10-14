"""
Data enrichment agent that enhances stock data with multiple sources and advanced features.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
import logging
import yfinance as yf
from datetime import datetime, timedelta

from app.agents.base_agent import BaseAgent
from app.features.feature_factory import create_features


class DataEnrichmentAgent(BaseAgent):
    """Agent responsible for enriching stock data with advanced features"""
    
    def __init__(self, name: str = "DataEnrichmentAgent", confidence_threshold: float = 0.7):
        super().__init__(name, confidence_threshold)
        self.cache = {}
        self.cache_expiry = 3600  # 1 hour cache
    
    def predict(self, symbol: str, data: Any = None) -> Dict[str, Any]:
        """
        This agent doesn't make predictions, but enriches data.
        Returns enriched data and quality metrics.
        """
        enriched_data = self.enrich_data(symbol, data)
        quality_score = self._assess_data_quality(enriched_data)
        
        return {
            'enriched_data': enriched_data,
            'quality_score': quality_score,
            'features_added': list(enriched_data.columns),
            'data_points': len(enriched_data)
        }
    
    def enrich_data(self, symbol: str, data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Enrich stock data with advanced technical and fundamental features.
        
        Args:
            symbol: Stock symbol
            data: Optional existing data
            
        Returns:
            Enriched DataFrame with additional features
        """
        # Load data if not provided
        if data is None:
            data = self._load_stock_data(symbol)
        
        # Create base technical features
        enriched_data = create_features(data, volatility_type='medium')
        
        # Add advanced features
        enriched_data = self._add_advanced_technical_features(enriched_data)
        enriched_data = self._add_market_regime_features(enriched_data)
        enriched_data = self._add_volatility_clustering_features(enriched_data)
        enriched_data = self._add_momentum_features(enriched_data)
        
        self.log_decision(
            "Data enrichment complete",
            {
                'symbol': symbol,
                'original_features': len(data.columns) if hasattr(data, 'columns') else 0,
                'enriched_features': len(enriched_data.columns),
                'data_points': len(enriched_data)
            }
        )
        
        return enriched_data
    
    def _load_stock_data(self, symbol: str) -> pd.DataFrame:
        """Load stock data from yfinance"""
        cache_key = f"{symbol}_data"
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_expiry:
                return cached_data
        
        # Download fresh data
        data = yf.download(symbol, start='2010-01-01', progress=False)
        self.cache[cache_key] = (datetime.now(), data)
        
        return data
    
    def _add_advanced_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add advanced technical analysis features"""
        df = df.copy()
        
        # Price patterns
        df['Higher_High'] = (df['High'] > df['High'].shift(1)).astype(int)
        df['Lower_Low'] = (df['Low'] < df['Low'].shift(1)).astype(int)
        
        # Fibonacci retracement levels
        rolling_max = df['High'].rolling(window=50).max()
        rolling_min = df['Low'].rolling(window=50).min()
        diff = rolling_max - rolling_min
        
        df['Fib_382'] = rolling_max - 0.382 * diff
        df['Fib_500'] = rolling_max - 0.500 * diff
        df['Fib_618'] = rolling_max - 0.618 * diff
        
        # Support and resistance
        df['Support_Level'] = df['Low'].rolling(window=20).min()
        df['Resistance_Level'] = df['High'].rolling(window=20).max()
        df['Distance_to_Support'] = (df['Close'] - df['Support_Level']) / df['Close']
        df['Distance_to_Resistance'] = (df['Resistance_Level'] - df['Close']) / df['Close']
        
        # Price momentum indicators
        df['ROC_5'] = df['Close'].pct_change(periods=5) * 100
        df['ROC_10'] = df['Close'].pct_change(periods=10) * 100
        df['ROC_20'] = df['Close'].pct_change(periods=20) * 100
        
        return df
    
    def _add_market_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify and add market regime features"""
        df = df.copy()
        
        # Trend strength
        df['Trend_Strength'] = abs(df['SMA_20'] - df['SMA_50']) / df['Close']
        
        # Market regime: trending vs ranging
        df['ADX'] = self._calculate_adx(df)
        df['Market_Regime'] = np.where(df['ADX'] > 25, 'trending', 'ranging')
        
        # Bull/bear market indicator
        df['Bull_Market'] = (df['Close'] > df['SMA_50']).astype(int)
        
        return df
    
    def _add_volatility_clustering_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add features related to volatility clustering"""
        df = df.copy()
        
        # Historical volatility at different windows
        df['Volatility_10'] = df['Returns'].rolling(window=10).std()
        df['Volatility_20'] = df['Returns'].rolling(window=20).std()
        df['Volatility_50'] = df['Returns'].rolling(window=50).std()
        
        # Volatility ratio
        df['Volatility_Ratio'] = df['Volatility_10'] / (df['Volatility_50'] + 1e-6)
        
        # GARCH-like features
        df['Squared_Returns'] = df['Returns'] ** 2
        df['Volatility_Persistence'] = df['Squared_Returns'].rolling(window=20).mean()
        
        return df
    
    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add momentum-based features"""
        df = df.copy()
        
        # Multiple timeframe momentum
        for period in [5, 10, 20, 50]:
            df[f'Momentum_{period}'] = df['Close'] - df['Close'].shift(period)
            df[f'Momentum_Pct_{period}'] = df['Close'].pct_change(periods=period)
        
        # Momentum acceleration
        df['Momentum_Acceleration'] = df['Momentum_10'].diff()
        
        # Stochastic oscillator
        low_min = df['Low'].rolling(window=14).min()
        high_max = df['High'].rolling(window=14).max()
        df['Stochastic_K'] = 100 * (df['Close'] - low_min) / (high_max - low_min + 1e-6)
        df['Stochastic_D'] = df['Stochastic_K'].rolling(window=3).mean()
        
        return df
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index"""
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        # Calculate +DM and -DM
        up_move = high.diff()
        down_move = -low.diff()
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Calculate ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Calculate DI+ and DI-
        plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean() / atr
        
        # Calculate ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-6)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    def _assess_data_quality(self, df: pd.DataFrame) -> float:
        """Assess quality of enriched data"""
        quality_factors = []
        
        # Check for missing values
        missing_ratio = df.isnull().sum().sum() / (df.shape[0] * df.shape[1])
        quality_factors.append(1.0 - missing_ratio)
        
        # Check data recency
        if hasattr(df.index, 'max'):
            days_old = (datetime.now() - df.index.max()).days
            recency_score = max(0, 1.0 - (days_old / 30))  # Penalize if older than 30 days
            quality_factors.append(recency_score)
        
        # Check data volume
        volume_score = min(1.0, len(df) / 1000)  # Optimal around 1000+ data points
        quality_factors.append(volume_score)
        
        return np.mean(quality_factors)
    
    def get_confidence(self, prediction: Any, data: Any) -> float:
        """Get confidence based on data quality"""
        if isinstance(prediction, dict):
            return prediction.get('quality_score', 0.0)
        return 0.0
