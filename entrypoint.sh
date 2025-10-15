#!/bin/bash
set -e

# Initialize database
python3 -m scripts.create_db

# Generate SSL certificates if they don't exist and SSL is enabled
if [ "${USE_SSL:-true}" = "true" ]; then
    if [ ! -f "/app/certs/cert.pem" ] || [ ! -f "/app/certs/key.pem" ]; then
        echo "Generating SSL certificates for HTTPS..."
        python3 -m scripts.generate_ssl_cert --cert-dir /app/certs
    else
        echo "SSL certificates already exist, skipping generation."
    fi
fi

# Execute the command passed to the container
exec "$@"