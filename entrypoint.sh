#!/bin/bash
set -e

# Initialize database
python3 -m scripts.create_db
python3 -m app.main

# Execute the command passed to the container
exec "$@"