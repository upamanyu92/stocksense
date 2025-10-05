#!/usr/bin/env python3
import schedule
import time
import logging
from datetime import datetime
import pytz
from app.models.model_monitor import ModelPerformanceMonitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('model_monitoring.log'),
        logging.StreamHandler()
    ]
)

def is_sunday():
    """Check if today is Sunday in IST"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).weekday() == 6

def monitoring_job():
    try:
        # Skip if it's Sunday
        if is_sunday():
            logging.info("Skipping monitoring job as it's Sunday")
            return

        logging.info("Starting scheduled model monitoring job")
        monitor = ModelPerformanceMonitor()
        monitor.monitor_and_retrain()
        logging.info("Completed model monitoring job")
    except Exception as e:
        logging.error(f"Error in monitoring job: {str(e)}", exc_info=True)

def main():
    # Schedule the monitoring job to run at 9:16 AM IST (3:46 AM UTC)
    schedule.every().day.at("03:46").do(monitoring_job)

    logging.info("Model monitoring scheduler started. Will run at 9:16 AM IST every day except Sunday")

    # Run immediately if it's not Sunday and within market hours
    if not is_sunday():
        ist_now = datetime.now(pytz.timezone('Asia/Kolkata'))
        if 9 <= ist_now.hour < 16:  # Only run immediately during market hours (9 AM to 4 PM IST)
            monitoring_job()
        else:
            logging.info("Outside market hours, waiting for next scheduled run")

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute instead of every hour

if __name__ == "__main__":
    main()
