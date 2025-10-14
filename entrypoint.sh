#!/bin/bash
set -e

# Initialize database
python3 -m scripts.create_db

# Execute the command passed to the container
exec "$@"