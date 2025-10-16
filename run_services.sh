#!/bin/zsh

# Start main.py in background, log output
python3 -m app.main > main.log 2>&1 &

# Start model_monitor_scheduler.py in background, log output
python3 -m scripts.model_monitor_scheduler > model_monitor.log 2>&1 &

# Print PIDs
echo "main.py PID: $!"
echo "model_monitor_scheduler.py PID: $!"

# Wait for both processes
wait