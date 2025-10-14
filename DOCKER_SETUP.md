# Docker Setup Documentation

## Overview

The StockSense application has been successfully containerized with a refactored and optimized Docker setup.

## What Was Fixed

### 1. **Docker Compose Refactoring**

- ✅ Removed obsolete `version` attribute (deprecated in Docker Compose v2+)
- ✅ Implemented proper bridge networking with `stocknet` network
- ✅ Added container names for easier management
- ✅ Configured health checks for the main service
- ✅ Set up proper service dependencies
- ✅ Added restart policies (`unless-stopped`)

### 2. **Entrypoint Script Fix**

- ✅ Refactored `entrypoint.sh` to properly execute commands passed to containers
- ✅ Added error handling with `set -e`
- ✅ Database initialization runs before service starts
- ✅ Each service now runs its designated command correctly

### 3. **Health Endpoint Implementation**

- ✅ Added `/health` endpoint to Flask app for Docker health checks
- ✅ Returns JSON: `{"service": "stocksense", "status": "healthy"}`
- ✅ Enables Docker to monitor service health automatically

### 4. **HTTPS/SSL Support**

- ✅ Added SSL/HTTPS support for secure connections
- ✅ Automatic generation of self-signed certificates for development
- ✅ Configurable SSL paths for production certificates
- ✅ Environment variable `USE_SSL` to enable/disable HTTPS
- ✅ Updated health checks to use HTTPS

## Services

### 1. `predict_main` (Main Application)

- **Port**: 5005 (mapped to host)
- **Command**: `python3 -m app.main`
- **Health Check**: Configured to check `/health` endpoint every 30s
- **Status**: ✅ Running and healthy

### 2. `model_monitor` (Model Monitoring Scheduler)

- **Command**: `python3 -m scripts.model_monitor_scheduler`
- **Schedule**: Runs at 9:16 AM IST daily (except Sunday)
- **Status**: ✅ Running and waiting for scheduled execution

## Network Configuration

- **Network Name**: `stocknet`
- **Driver**: bridge
- **Isolation**: Services communicate within isolated network

## Quick Commands

### Start Services

```bash
docker-compose up -d
```

### Check Status

```bash
docker-compose ps
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f predict_main
docker-compose logs -f model_monitor
```

### Stop Services

```bash
docker-compose down
```

### Rebuild and Start

```bash
docker-compose up -d --build
```

### Test Health Endpoint

```bash
# HTTPS (default)
curl -k https://localhost:5005/health

# HTTP (if SSL disabled)
curl http://localhost:5005/health
```

## Test Results

### Container Status ✅

```
NAME                 IMAGE                      STATUS
stocksense_main      stocksense-predict_main    Up (healthy)
stocksense_monitor   stocksense-model_monitor   Up
```

### Health Check ✅

```json
{
  "service": "stocksense",
  "status": "healthy"
}
```

### Model Monitor ✅

```
Model monitoring scheduler started. Will run at 9:16 AM IST every day except Sunday
Outside market hours, waiting for next scheduled run
```

## Volume Mounts

- `.:/app` - Application code (live reload support)
- `./app/db:/app/db` - Database persistence
- `./app/templates:/app/templates` - Templates
- `./model/saved_models:/app/model/saved_models` - Model persistence

## Environment Variables

- `FLASK_ENV=development`
- `PYTHONPATH=/app`
- `FLASK_PORT=5005`
- `USE_SSL=true` - Enable/disable HTTPS (default: true)
- `SSL_CERT_PATH=/app/certs/cert.pem` - Path to SSL certificate
- `SSL_KEY_PATH=/app/certs/key.pem` - Path to SSL private key
- `TZ=Asia/Kolkata` (model_monitor)

## SSL/HTTPS Configuration

The application now supports HTTPS for secure connections:

### Development
- Self-signed SSL certificates are automatically generated on first run
- Certificates are stored in `./certs/` directory
- Your browser will show a security warning for self-signed certificates - this is expected and safe to bypass in development

### Production
For production deployments, use certificates from a trusted CA:

1. **Let's Encrypt (Recommended - Free)**:
   ```bash
   # Install certbot
   sudo apt-get install certbot
   
   # Generate certificates
   sudo certbot certonly --standalone -d yourdomain.com
   ```

2. **Update environment variables**:
   ```yaml
   environment:
     - USE_SSL=true
     - SSL_CERT_PATH=/path/to/fullchain.pem
     - SSL_KEY_PATH=/path/to/privkey.pem
   ```

3. **Mount certificate directory in docker-compose.yml**:
   ```yaml
   volumes:
     - /etc/letsencrypt:/etc/letsencrypt:ro
   ```

### Disable SSL
To run without HTTPS (not recommended for production):
```bash
export USE_SSL=false
```

## Next Steps

1. ✅ Using production WSGI server recommended for production (current: Flask dev server with SSL)
2. Add environment-specific configurations (.env files)
3. Implement log aggregation for better monitoring
4. Consider adding database service to docker-compose if needed
5. For production: Replace self-signed certificates with CA-signed certificates (e.g., Let's Encrypt)

## Troubleshooting

### Container won't start

```bash
docker-compose logs <service_name>
```

### Health check failing

```bash
# Check if port 5005 is accessible
curl http://localhost:5005/health

# Inspect container
docker exec -it stocksense_main /bin/bash
```

### Database issues

```bash
# Recreate database
docker-compose down
docker-compose up -d --build
```

---
**Last Updated**: October 14, 2025
**Status**: ✅ All systems operational

