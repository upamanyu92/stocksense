from datetime import datetime, timedelta
import numpy as np
from app.services.configuration_service import ConfigurationService
from app.db.db_executor import execute_query, fetch_all
from app.models.training_script import train_transformer_model
import logging

class ModelPerformanceMonitor:
    ACCURACY_THRESHOLD = 0.75  # 75% accuracy threshold
    MONITORING_WINDOW_DAYS = 7  # Look at last 7 days of predictions

    @staticmethod
    def _get_prediction_columns():
        """Return a set of column names present in the predictions table"""
        try:
            cols = execute_query("PRAGMA table_info('predictions')", fetchall=True)
            if not cols:
                return set()
            return set([row['name'] for row in cols])
        except Exception:
            logging.exception("Failed to get predictions table info")
            return set()

    @staticmethod
    def get_recent_predictions():
        """Fetch recent predictions from the database in a schema-robust way"""
        cols = ModelPerformanceMonitor._get_prediction_columns()
        cutoff = datetime.now() - timedelta(days=ModelPerformanceMonitor.MONITORING_WINDOW_DAYS)
        cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')

        # Build a safe select list depending on available columns
        select_cols = []
        if 'security_id' in cols:
            select_cols.append("security_id AS symbol")
        elif 'company_name' in cols:
            select_cols.append("company_name AS symbol")
        else:
            # fallback to id
            select_cols.append("id AS symbol")

        if 'current_price' in cols:
            select_cols.append('current_price')
        elif 'current_value' in cols:
            select_cols.append('current_value AS current_price')

        if 'predicted_price' in cols:
            select_cols.append('predicted_price')

        if 'actual_price' in cols:
            select_cols.append('actual_price')

        if 'prediction_date' in cols:
            select_cols.append('prediction_date')

        select_clause = ',\n                '.join(select_cols)

        query = f"""
            SELECT
                {select_clause}
            FROM predictions
            WHERE prediction_date >= ?
        """

        try:
            results = fetch_all(query, (cutoff_str,))
            logging.info(f"Fetched {len(results)} predictions from the last {ModelPerformanceMonitor.MONITORING_WINDOW_DAYS} days")
            return results
        except Exception as e:
            logging.error(f"Error fetching recent predictions: {e}", exc_info=True)
            return []

    @staticmethod
    def calculate_model_metrics(predictions):
        """Calculate comprehensive model performance metrics by symbol"""
        metrics_by_symbol = {}

        usable_count = 0
        for pred in predictions:
            # Skip if actual_price not present
            actual = pred.get('actual_price') if isinstance(pred, dict) else None
            if actual is None:
                # Can't compute error without actuals
                continue

            usable_count += 1
            symbol = pred.get('symbol')
            if symbol not in metrics_by_symbol:
                metrics_by_symbol[symbol] = {
                    'errors': [],
                    'directional_accuracy': [],
                    'total_predictions': 0
                }

            # Calculate percentage error
            predicted = pred.get('predicted_price')
            try:
                error = abs(actual - predicted) / actual if actual != 0 else 0
            except Exception:
                logging.exception(f"Invalid numeric values for prediction row: {pred}")
                continue

            metrics_by_symbol[symbol]['errors'].append(error)

            # Directional accuracy requires previous actual/predicted; we handle when present
            if 'last_actual' in metrics_by_symbol[symbol]:
                actual_direction = actual > metrics_by_symbol[symbol]['last_actual']
                predicted_direction = predicted > metrics_by_symbol[symbol]['last_predicted']
                metrics_by_symbol[symbol]['directional_accuracy'].append(
                    1 if actual_direction == predicted_direction else 0
                )

            metrics_by_symbol[symbol]['last_actual'] = actual
            metrics_by_symbol[symbol]['last_predicted'] = predicted
            metrics_by_symbol[symbol]['total_predictions'] += 1

        logging.info(f"Usable predictions with actuals: {usable_count}")

        # Calculate final metrics for each symbol
        results = {}
        for symbol, data in metrics_by_symbol.items():
            if data['total_predictions'] < 5:  # Skip symbols with too few predictions
                continue

            results[symbol] = {
                'mape': float(np.mean(data['errors'])) * 100 if data['errors'] else 0.0,  # Mean Absolute Percentage Error
                'directional_accuracy': float(np.mean(data['directional_accuracy'])) if data['directional_accuracy'] else 0.0,
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

        if not metrics_by_symbol:
            logging.info("No usable predictions with actual values found for monitoring")
            return

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
