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
- `TZ=Asia/Kolkata` (model_monitor)

## Next Steps

1. Consider using production WSGI server (e.g., Gunicorn) instead of Flask dev server
2. Add environment-specific configurations (.env files)
3. Implement log aggregation for better monitoring
4. Consider adding database service to docker-compose if needed

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

