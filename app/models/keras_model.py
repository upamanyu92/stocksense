import logging
import json
import joblib
from pathlib import Path
import time
from datetime import datetime

import numpy as np
import yfinance as yf
from keras.callbacks import EarlyStopping
from keras.models import Sequential, Model, load_model
from keras.layers import Dense, LSTM, Dropout, Bidirectional, Input, LayerNormalization, MultiHeadAttention, GlobalAveragePooling1D
from sklearn.preprocessing import MinMaxScaler

from app.features.feature_factory import create_features
from app.services.configuration_service import ConfigurationService
from app.db.data_models import ModelConfiguration

# Define consistent feature columns
FEATURE_COLUMNS = ['Close', 'SMA_20', 'SMA_50', 'EMA_20', 'EMA_50', 'Volume_Mean', 'RSI', 'MACD']


def get_model_config(symbol: str, model_type: str = 'transformer') -> ModelConfiguration:
    """Get model configuration from DB or return default"""
    config = ConfigurationService.get_configuration(symbol, model_type)
    if not config:
        config = ModelConfiguration(symbol=symbol, model_type=model_type)
    return config


def build_transformer_model(input_shape, symbol: str):
    """Build transformer model using configuration from DB"""
    config = get_model_config(symbol, 'transformer')

    inputs = Input(shape=input_shape)
    x = MultiHeadAttention(num_heads=config.num_heads, key_dim=input_shape[-1])(inputs, inputs)
    x = Dropout(config.dropout_rate)(x)
    x = LayerNormalization(epsilon=1e-6)(x)
    x = Dense(config.ff_dim, activation='relu')(x)
    x = Dropout(config.dropout_rate)(x)
    x = LayerNormalization(epsilon=1e-6)(x)
    x = GlobalAveragePooling1D()(x)
    outputs = Dense(1)(x)
    model = Model(inputs, outputs)
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model


def load_latest_model(symbol, model_type='transformer'):
    """
    Load the most recent model for a given symbol and type.

    Parameters:
        symbol (str): Stock symbol
        model_type (str): Type of model ('transformer' or 'lstm')

    Returns:
        tuple: (model, scaler, metadata) or (None, None, None) if no model found
    """
    try:
        base_dir = Path('model/saved_models')
        # List all matching model directories
        matching_dirs = list(base_dir.glob(f"{symbol}_{model_type}_*"))

        if not matching_dirs:
            return None, None, None

        # Get the most recent directory
        latest_dir = max(matching_dirs, key=lambda x: x.name.split('_')[-1])

        # Load metadata
        with open(latest_dir / "metadata.json", "r") as f:
            metadata = json.load(f)

        # Load model and scaler
        model = load_model(latest_dir / "model.h5")
        scaler = joblib.load(latest_dir / "scaler.pkl")

        return model, scaler, metadata
    except Exception as e:
        logging.error(f"Error loading model for {symbol}: {str(e)}")
        return None, None, None

def predict_max_profit(symbol, use_transformer=True, timeout=30):
    """Make prediction with cancellation support"""
    try:
        model_type = 'transformer' if use_transformer else 'lstm'
        model, scaler, metadata = load_latest_model(symbol, model_type)

        if model is None:  # No saved model found, train new one
            # Download stock data individually to avoid multi-index issues
            stock = yf.download(symbol, start='2010-01-01', auto_adjust=True, progress=False)
            if stock.empty:
                raise ValueError(f"No data downloaded for {symbol}")

            logging.info(f"Downloaded data shape for {symbol}: {stock.shape}")
            stock = create_features(stock)
            logging.info(f"Features created for {symbol}, shape: {stock.shape}")

            # Verify we have all required features
            if not all(col in stock.columns for col in FEATURE_COLUMNS):
                missing_features = [col for col in FEATURE_COLUMNS if col not in stock.columns]
                raise ValueError(f"Missing features after feature creation for {symbol}: {missing_features}")

            data = stock[FEATURE_COLUMNS].values

            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = scaler.fit_transform(data)

            x_train, y_train = [], []
            for i in range(60, len(scaled_data)):
                x_train.append(scaled_data[i-60:i])
                y_train.append(scaled_data[i, 0])
            x_train, y_train = np.array(x_train), np.array(y_train)

            if use_transformer:
                model = build_transformer_model(input_shape=(x_train.shape[1], x_train.shape[2]), symbol=symbol)
            else:
                model = Sequential()
                model.add(Bidirectional(LSTM(units=50, return_sequences=True, input_shape=(x_train.shape[1], x_train.shape[2]))))
                model.add(Dropout(0.2))
                model.add(LSTM(units=50))
                model.add(Dropout(0.2))
                model.add(Dense(1))
                model.compile(optimizer='adam', loss='mean_squared_error')

            early_stopping = EarlyStopping(monitor='loss', patience=10, restore_best_weights=True)
            model.fit(x_train, y_train, epochs=100, batch_size=32, verbose=2, callbacks=[early_stopping])

            # Save the model, scaler, and metadata
            save_dir = Path('model/saved_models') / f"{symbol}_{model_type}_{int(time.time())}"
            save_dir.mkdir(parents=True, exist_ok=True)

            model.save(save_dir / "model.h5")
            joblib.dump(scaler, save_dir / "scaler.pkl")

            metadata = {
                "features": FEATURE_COLUMNS,
                "training_date": datetime.now().isoformat(),
                "symbol": symbol,
                "model_type": model_type
            }
            with open(save_dir / "metadata.json", "w") as f:
                json.dump(metadata, f)

        # Get latest data for prediction
        stock = yf.download(symbol, start='2010-01-01')
        stock = create_features(stock)

        # Use consistent features for prediction
        last_60_days = stock[FEATURE_COLUMNS][-60:].values
        last_60_days_scaled = scaler.transform(last_60_days)
        x_test = np.array([last_60_days_scaled])


        predicted_price = model.predict(x_test)
        predicted_price = scaler.inverse_transform(np.concatenate((predicted_price, np.zeros((1, last_60_days.shape[1] - 1))), axis=1))[:,0]

        return predicted_price[0]
    except Exception as e:
        logging.error(f"Error predicting for {symbol}: {str(e)}")
        raise e