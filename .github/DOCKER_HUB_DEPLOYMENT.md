# Docker Hub Deployment Runner

## Overview

This workflow automatically builds and publishes StockSense Docker images to Docker Hub using GitHub Actions.

## Workflow File

- **Location**: `.github/workflows/docker-publish.yml`
- **Name**: Docker Hub Publish

## Triggers

The workflow runs automatically on:

1. **Push to main branch** - Publishes `latest` and `main` tags
2. **New release/tag** (e.g., `v1.0.0`) - Publishes semantic version tags
3. **Manual dispatch** - Can be triggered manually from GitHub Actions UI

## Features

### Multi-Platform Support
- Builds for both `linux/amd64` (x86_64) and `linux/arm64` (ARM/Apple Silicon)
- Uses QEMU and Docker Buildx for cross-platform builds

### Smart Tagging
- `latest` - Always points to the most recent main branch build
- `main` - Latest build from main branch
- `v1.0.0` - Exact semantic version
- `1.0` - Major.minor version
- `1` - Major version only

### Build Optimization
- Uses GitHub Actions cache to speed up subsequent builds
- Leverages Docker layer caching

## Required Secrets

Configure these in GitHub repository settings (Settings → Secrets and variables → Actions):

1. **DOCKER_USERNAME** - Your Docker Hub username
2. **DOCKER_PASSWORD** - Docker Hub password or access token (recommended)

> **Note**: Use a Docker Hub access token instead of your password for better security.
> Create one at: https://hub.docker.com/settings/security

## Usage

### Pulling Images

```bash
# Pull latest version
docker pull upamanyu92/stocksense:latest

# Pull specific version
docker pull upamanyu92/stocksense:v1.0.0

# Pull by major version
docker pull upamanyu92/stocksense:1
```

### Running the Image

```bash
# Basic run
docker run -p 5005:5005 upamanyu92/stocksense:latest

# With volume mounts for persistence
docker run -p 5005:5005 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/db:/app/app/db \
  upamanyu92/stocksense:latest
```

### Using in Docker Compose

Update your `docker-compose.yml` to use the published image:

```yaml
services:
  predict_main:
    image: upamanyu92/stocksense:latest
    # ... rest of configuration
```

## Creating a Release

To publish a new versioned release:

1. Create and push a tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. Or create a release in GitHub UI:
   - Go to Releases → Draft a new release
   - Choose or create a tag (e.g., `v1.0.0`)
   - Publish the release

The workflow will automatically build and push the image with appropriate tags.

## Monitoring

View workflow runs at:
https://github.com/upamanyu92/stocksense/actions/workflows/docker-publish.yml

## Troubleshooting

### Authentication Failed
- Verify `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets are correctly set
- Ensure Docker Hub access token has write permissions

### Build Failed
- Check the workflow logs in GitHub Actions
- Verify the Dockerfile builds locally: `docker build -t test .`

### Multi-platform Build Issues
- QEMU and Buildx are automatically set up by the workflow
- If issues persist, check Docker Buildx compatibility

## Security Best Practices

1. Use Docker Hub access tokens instead of passwords
2. Rotate access tokens regularly
3. Limit token permissions to push only
4. Review workflow permissions (currently set to read contents, write packages)

---

**Last Updated**: October 14, 2025
