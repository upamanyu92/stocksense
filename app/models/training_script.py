import logging
import yfinance as yf
import numpy as np
from keras.models import Sequential
from sklearn.preprocessing import MinMaxScaler
from keras.layers import LSTM, Dense, Dropout, Input
from keras.callbacks import EarlyStopping, ReduceLROnPlateau
from app.models.keras_model import build_transformer_model
from app.services.configuration_service import ConfigurationService
import joblib
import json
from datetime import datetime
from pathlib import Path
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

logger = logging.getLogger(__name__)



def download_stock_data(symbol, start='2010-01-01', end='2024-07-04'):
    """
    Downloads stock data for a given symbol within a specified date range.

    Parameters:
    symbol (str): The stock symbol to download data for.
    start (str): The start date for the data in the format 'YYYY-MM-DD'. Default is '2010-01-01'.
    end (str): The end date for the data in the format 'YYYY-MM-DD'. Default is '2024-07-04'.

    Returns:
    pandas.DataFrame: A DataFrame containing the stock data if available, otherwise None.
    """
    stock = yf.download(symbol, start=start, end=end, progress=False)
    if stock is None or stock.empty:
        return None
    return stock


def preprocess_data(data, time_step=100):
    """
    Generate function comment for preprocess_data function.

    Parameters:
    - data: Input data to be preprocessed.
    - time_step: Number of time steps to look back (default=100).

    Returns:
    - X: Array of input sequences.
    - y: Array of target values.
    - scaler: Scaler object used for preprocessing.
    """
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)
    X, y = [], []
    for i in range(time_step, len(scaled_data)):
        X.append(scaled_data[i - time_step:i])
        y.append(scaled_data[i, 3])  # 'Close' column is the target
    X, y = np.array(X), np.array(y)
    return X, y, scaler


def build_model(input_shape):
    """
    Builds and compiles a LSTM model based on the given input shape.

    Parameters:
        input_shape (tuple): The shape of the input data.

    Returns:
        tensorflow.keras.Model: Compiled LSTM model.
    """
    model = Sequential()
    model.add(Input(shape=input_shape))
    model.add(LSTM(units=50, return_sequences=True))
    model.add(Dropout(0.2))
    model.add(LSTM(units=50, return_sequences=False))
    model.add(Dropout(0.2))
    model.add(Dense(units=1))
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model


def save_model_artifacts(model, scaler, symbol, model_type='transformer', metrics=None):
    """
    Save the trained model, scaler, and metadata with versioning.

    Parameters:
        model: The trained keras model
        scaler: The fitted MinMaxScaler
        symbol: The stock symbol
        model_type: Type of model ('transformer' or 'lstm')
        metrics: Dictionary containing training metrics
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_path = Path('model/saved_models') / f"{symbol}_{model_type}_{timestamp}"
    base_path.mkdir(parents=True, exist_ok=True)

    # Save the model
    model_path = base_path / "model.h5"
    model.save(str(model_path))

    # Save the scaler
    scaler_path = base_path / "scaler.pkl"
    joblib.dump(scaler, str(scaler_path))

    # Save metadata
    metadata = {
        "symbol": symbol,
        "model_type": model_type,
        "training_date": timestamp,
        "metrics": metrics or {},
        "model_path": str(model_path),
        "scaler_path": str(scaler_path)
    }
    with open(base_path / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    return str(base_path)


def calculate_metrics(y_true, y_pred):
    """Calculate comprehensive model performance metrics"""
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    # Calculate directional accuracy
    direction_true = np.diff(y_true) > 0
    direction_pred = np.diff(y_pred) > 0
    directional_accuracy = np.mean(direction_true == direction_pred)

    return {
        "mse": float(mse),
        "rmse": float(rmse),
        "mae": float(mae),
        "r2_score": float(r2),
        "directional_accuracy": float(directional_accuracy)
    }


def train_transformer_model(symbol, time_step=60, epochs=100, batch_size=32):
    """Train and save a Transformer model with enhanced metrics and validation"""
    # Get configuration if exists
    config = ConfigurationService.get_configuration(symbol, 'transformer')

    # Use configuration values if available
    if config:
        time_step = config.sequence_length
        epochs = config.epochs
        batch_size = config.batch_size

    stock = download_stock_data(symbol)
    if stock is None:
        raise ValueError(f"No data available for {symbol}")

    from app.features.feature_factory import create_features
    stock = create_features(stock)

    # Split data into train and validation sets
    train_size = int(len(stock) * 0.8)
    train_data = stock[:train_size]
    val_data = stock[train_size:]

    # Prepare features
    feature_columns = ['Close', 'SMA_20', 'SMA_50', 'EMA_20', 'EMA_50', 'Volume_Mean', 'RSI', 'MACD']
    train_data = train_data[feature_columns].values
    val_data = val_data[feature_columns].values

    # Preprocess data
    X_train, y_train, scaler = preprocess_data(train_data, time_step)
    X_val, y_val, _ = preprocess_data(val_data, time_step)

    # Build model with configuration
    model = build_transformer_model(
        input_shape=(X_train.shape[1], X_train.shape[2]),
        symbol=symbol
    )

    # Callbacks for better training
    callbacks = [
        EarlyStopping(
            monitor='val_loss',
            patience=config.early_stopping_patience if config else 10,
            restore_best_weights=True
        ),
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=0.0001
        )
    ]

    # Train model
    history = model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(X_val, y_val),
        callbacks=callbacks,
        verbose=2
    )

    # Calculate predictions and metrics
    train_pred = model.predict(X_train)
    val_pred = model.predict(X_val)

    # Calculate metrics
    train_metrics = calculate_metrics(y_train, train_pred)
    val_metrics = calculate_metrics(y_val, val_pred)

    # Prepare comprehensive metrics
    metrics = {
        "training": train_metrics,
        "validation": val_metrics,
        "training_history": {
            "loss": history.history['loss'],
            "val_loss": history.history['val_loss']
        },
        "configuration_used": bool(config),
        "features": feature_columns,
        "data_points": {
            "train": len(y_train),
            "validation": len(y_val)
        }
    }

    # Save model with enhanced metrics
    model_path = save_model_artifacts(model, scaler, symbol, 'transformer', metrics)
    logger.info(f"Model saved to: {model_path}")

    return model, scaler, metrics


def train_model(symbol):
    """
    Train and save an LSTM model for the given symbol.
    """
    stock_data = download_stock_data(symbol)
    if stock_data is None:
        return None

    from app.features.feature_factory import create_features
    stock_data = create_features(stock_data)
    data = stock_data[['Close', 'SMA_20', 'SMA_50', 'EMA_20', 'EMA_50', 'Volume_Mean']].values

    X, y, scaler = preprocess_data(data)
    model = build_model((X.shape[1], X.shape[2]))

    history = model.fit(X, y, epochs=50, batch_size=32, verbose=1)

    # Save model artifacts with training metrics
    metrics = {
        "final_loss": float(history.history['loss'][-1]),
        "epochs_trained": len(history.history['loss']),
        "features": ['Close', 'SMA_20', 'SMA_50', 'EMA_20', 'EMA_50', 'Volume_Mean']
    }

    model_path = save_model_artifacts(model, scaler, symbol, 'lstm', metrics)
    logger.info(f"Model saved to: {model_path}")

    return model, scaler


# Optionally, add a main block for CLI usage
def main():
    """Train models for a stock symbol."""
    symbol = 'AAPL'  # Example symbol
    logger.info(f"Training Transformer model for {symbol}...")
    model, scaler, metrics = train_transformer_model(symbol)
    logger.info(f"Training LSTM model for {symbol}...")
    lstm_model, lstm_scaler = train_model(symbol)
    logger.info("Training complete!")


if __name__ == "__main__":
    main()
