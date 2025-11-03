#!/bin/bash
set -e

python3 -m app.main

# Execute the command passed to the container
exec "$@"