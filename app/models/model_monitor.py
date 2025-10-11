from datetime import datetime, timedelta
import numpy as np
from app.services.configuration_service import ConfigurationService
from app.db.db_executor import get_recent_predictions_for_monitor
from app.models.training_script import train_transformer_model
import logging

class ModelPerformanceMonitor:
    ACCURACY_THRESHOLD = 0.75  # 75% accuracy threshold
    MONITORING_WINDOW_DAYS = 7  # Look at last 7 days of predictions

    @staticmethod
    def get_recent_predictions():
        """Fetch recent predictions from the database"""
        cutoff_date = (datetime.now() - timedelta(days=ModelPerformanceMonitor.MONITORING_WINDOW_DAYS))
        return get_recent_predictions_for_monitor(cutoff_date)

    @staticmethod
    def calculate_model_metrics(predictions):
        """Calculate comprehensive model performance metrics by symbol"""
        metrics_by_symbol = {}

        for pred in predictions:
            symbol = pred['symbol']
            if symbol not in metrics_by_symbol:
                metrics_by_symbol[symbol] = {
                    'errors': [],
                    'directional_accuracy': [],
                    'total_predictions': 0
                }

            # Calculate percentage error
            actual = pred['actual_price']
            predicted = pred['predicted_price']
            error = abs(actual - predicted) / actual
            metrics_by_symbol[symbol]['errors'].append(error)

            # Calculate directional accuracy (did we predict the direction correctly?)
            if 'last_actual' in metrics_by_symbol[symbol]:
                actual_direction = actual > metrics_by_symbol[symbol]['last_actual']
                predicted_direction = predicted > metrics_by_symbol[symbol]['last_predicted']
                metrics_by_symbol[symbol]['directional_accuracy'].append(
                    1 if actual_direction == predicted_direction else 0
                )

            metrics_by_symbol[symbol]['last_actual'] = actual
            metrics_by_symbol[symbol]['last_predicted'] = predicted
            metrics_by_symbol[symbol]['total_predictions'] += 1

        # Calculate final metrics for each symbol
        results = {}
        for symbol, data in metrics_by_symbol.items():
            if data['total_predictions'] < 5:  # Skip symbols with too few predictions
                continue

            results[symbol] = {
                'mape': np.mean(data['errors']) * 100,  # Mean Absolute Percentage Error
                'directional_accuracy': np.mean(data['directional_accuracy']) if data['directional_accuracy'] else 0,
                'total_predictions': data['total_predictions']
            }

        return results

    @staticmethod
    def adjust_model_configuration(symbol, metrics):
        """Adjust model configuration based on performance metrics"""
        current_config = ConfigurationService.get_configuration(symbol)
        if not current_config:
            logging.warning(f"No configuration found for {symbol}")
            return None

        mape = metrics['mape']
        dir_accuracy = metrics['directional_accuracy']

        # Adjust configuration based on performance
        if mape > 20 or dir_accuracy < 0.6:  # Poor performance
            # Increase model complexity and training
            new_config = current_config.copy()
            new_config.num_heads = min(16, current_config.num_heads + 2)
            new_config.sequence_length = min(100, current_config.sequence_length + 10)
            new_config.epochs = min(200, current_config.epochs + 50)
            new_config.batch_size = max(16, current_config.batch_size - 8)

        elif mape > 10 or dir_accuracy < 0.7:  # Moderate performance
            # Minor adjustments
            new_config = current_config.copy()
            new_config.num_heads = min(12, current_config.num_heads + 1)
            new_config.sequence_length = min(80, current_config.sequence_length + 5)
            new_config.epochs = min(150, current_config.epochs + 25)

        else:  # Good performance
            # Keep current configuration with small optimization
            new_config = current_config.copy()
            new_config.early_stopping_patience = max(5, current_config.early_stopping_patience - 1)

        # Update configuration in database
        ConfigurationService.update_configuration(new_config)
        return new_config

    @staticmethod
    def monitor_and_retrain():
        """Main monitoring function that checks performance and triggers retraining"""
        logging.info("Starting model performance monitoring...")

        # Get recent predictions
        predictions = ModelPerformanceMonitor.get_recent_predictions()
        if not predictions:
            logging.info("No recent predictions to analyze")
            return

        # Calculate metrics for each symbol
        metrics_by_symbol = ModelPerformanceMonitor.calculate_model_metrics(predictions)

        for symbol, metrics in metrics_by_symbol.items():
            logging.info(f"\nAnalyzing {symbol}:")
            logging.info(f"MAPE: {metrics['mape']:.2f}%")
            logging.info(f"Directional Accuracy: {metrics['directional_accuracy']:.2f}")

            if metrics['mape'] > 10 or metrics['directional_accuracy'] < 0.7:
                logging.info(f"Performance below target for {symbol}, adjusting configuration...")
                new_config = ModelPerformanceMonitor.adjust_model_configuration(symbol, metrics)

                if new_config:
                    logging.info("Retraining model with new configuration...")
                    try:
                        model, scaler, training_metrics = train_transformer_model(symbol)
                        logging.info(f"Retraining complete. New training metrics: {training_metrics}")
                    except Exception as e:
                        logging.error(f"Error retraining model for {symbol}: {str(e)}")
            else:
                logging.info(f"Performance satisfactory for {symbol}, no retraining needed")
