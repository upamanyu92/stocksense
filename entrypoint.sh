#!/bin/bash
python3 -m scripts.create_db
exec "$@"