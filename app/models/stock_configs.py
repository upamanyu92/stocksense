"""
Stock configuration templates for different market characteristics
"""

# High volatility stocks (e.g., tech stocks, cryptocurrencies)
HIGH_VOLATILITY_CONFIG = {
    "model_type": "transformer",
    "num_heads": 8,
    "ff_dim": 256,
    "dropout_rate": 0.3,
    "learning_rate": 0.0005,
    "batch_size": 64,
    "epochs": 200,
    "sequence_length": 100,
    "early_stopping_patience": 15
}

# Low volatility stocks (e.g., utilities, consumer staples)
LOW_VOLATILITY_CONFIG = {
    "model_type": "transformer",
    "num_heads": 4,
    "ff_dim": 128,
    "dropout_rate": 0.2,
    "learning_rate": 0.001,
    "batch_size": 32,
    "epochs": 100,
    "sequence_length": 60,
    "early_stopping_patience": 10
}

# High-frequency trading config (for stocks with many intraday movements)
HIGH_FREQUENCY_CONFIG = {
    "model_type": "transformer",
    "num_heads": 12,
    "ff_dim": 512,
    "dropout_rate": 0.25,
    "learning_rate": 0.0003,
    "batch_size": 128,
    "epochs": 300,
    "sequence_length": 120,
    "early_stopping_patience": 20
}

# Long-term trend config (for stocks with clear long-term patterns)
LONG_TERM_CONFIG = {
    "model_type": "transformer",
    "num_heads": 6,
    "ff_dim": 192,
    "dropout_rate": 0.15,
    "learning_rate": 0.0008,
    "batch_size": 48,
    "epochs": 150,
    "sequence_length": 200,
    "early_stopping_patience": 25
}

def get_stock_config(symbol: str, volatility_type: str = "medium") -> dict:
    """
    Get recommended configuration based on stock characteristics.

    Args:
        symbol: Stock symbol
        volatility_type: One of "high", "low", "high_frequency", "long_term"

    Returns:
        dict: Configuration parameters for the stock
    """
    configs = {
        "high": HIGH_VOLATILITY_CONFIG,
        "low": LOW_VOLATILITY_CONFIG,
        "high_frequency": HIGH_FREQUENCY_CONFIG,
        "long_term": LONG_TERM_CONFIG
    }

    config = configs.get(volatility_type, LOW_VOLATILITY_CONFIG).copy()
    config["symbol"] = symbol
    return config
