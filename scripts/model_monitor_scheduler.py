#!/usr/bin/env python3
import time
import logging
import os
from datetime import datetime, date
import pytz
from app.models.model_monitor import ModelPerformanceMonitor

# Timezone
IST = pytz.timezone('Asia/Kolkata')

# Configure basic logging and also add explicit file + stream handlers
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Replace root handlers with file + stream and ensure formatter uses IST
file_handler = logging.FileHandler('model_monitoring.log')
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# Use IST for formatter timestamps
formatter.converter = lambda *args: datetime.now(IST).timetuple()
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)
logging.getLogger().handlers = [file_handler, stream_handler]
logging.getLogger().setLevel(logging.INFO)

TARGET_HOUR = 9
TARGET_MINUTE = 16


def is_sunday():
    """Check if today is Sunday in IST"""
    return datetime.now(IST).weekday() == 6


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
    logging.info(f"Model monitoring scheduler starting. Will run daily at {TARGET_HOUR:02d}:{TARGET_MINUTE:02d} IST except Sunday")

    # Test mode: run once and exit
    if os.environ.get('MODEL_MONITOR_TEST') == '1':
        logging.info('MODEL_MONITOR_TEST=1 set - running one job for test and exiting')
        monitoring_job()
        return

    last_run_date = None

    try:
        while True:
            now_ist = datetime.now(IST)
            today = now_ist.date()
            current_time_str = now_ist.strftime('%Y-%m-%d %H:%M:%S')
            logging.info(f"Scheduler heartbeat. Current IST time: {current_time_str}")

            # Only run once per day at the target time window
            if not is_sunday() and today != last_run_date:
                # Allow a window of 1 minute for the scheduled run
                if (now_ist.hour == TARGET_HOUR and now_ist.minute == TARGET_MINUTE and now_ist.second < 60):
                    logging.info(f"IST time matched {TARGET_HOUR:02d}:{TARGET_MINUTE:02d}, running monitoring job")
                    monitoring_job()
                    last_run_date = today
                else:
                    # log debug-level heartbeat occasionally
                    if now_ist.minute % 30 == 0 and now_ist.second < 5:
                        logging.debug(f"Waiting for scheduled time. Current IST time: {current_time_str}")
            time.sleep(5)  # Check every 5 seconds for more accuracy
    except KeyboardInterrupt:
        logging.info('Model monitoring scheduler stopped by user')


if __name__ == "__main__":
    main()
