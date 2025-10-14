# HTTPS/SSL Setup Guide for StockSense

This guide explains how to enable and configure HTTPS/SSL for secure connections in StockSense.

## Overview

StockSense now supports HTTPS by default to ensure secure communication between your browser and the application. This prevents "connection not secure" warnings and encrypts all data in transit.

## Quick Start (Development)

### 1. Generate Self-Signed Certificates

For development and testing, StockSense can automatically generate self-signed SSL certificates:

```bash
# Option 1: Automatic generation (recommended)
# Certificates are automatically generated when you start the app or Docker containers

# Option 2: Manual generation
python scripts/generate_ssl_cert.py
```

### 2. Start the Application

```bash
# Local development
python -m app.main

# Docker
docker compose up --build
```

### 3. Access the Application

Open your browser and navigate to:
```
https://localhost:5005
```

**Important:** Your browser will show a security warning because the certificate is self-signed. This is expected and safe for development. Click "Advanced" and "Proceed to localhost" (or similar) to access the application.

## Browser Security Warnings

When using self-signed certificates, you'll see warnings like:
- Chrome: "Your connection is not private" (NET::ERR_CERT_AUTHORITY_INVALID)
- Firefox: "Warning: Potential Security Risk Ahead"
- Safari: "This Connection Is Not Private"

**This is normal for self-signed certificates.** The connection is still encrypted, but the certificate isn't verified by a trusted authority.

To bypass these warnings:
1. Click "Advanced" or "Show Details"
2. Click "Proceed to localhost (unsafe)" or "Accept the Risk and Continue"
3. The application will load securely

## Production Deployment

For production, you **must** use certificates from a trusted Certificate Authority (CA). Here are the recommended options:

### Option 1: Let's Encrypt (Free - Recommended)

Let's Encrypt provides free SSL certificates that are trusted by all browsers.

#### Prerequisites
- A domain name pointing to your server
- Port 80 and 443 open in your firewall

#### Steps

1. **Install Certbot:**
   ```bash
   sudo apt-get update
   sudo apt-get install certbot
   ```

2. **Generate Certificates:**
   ```bash
   sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
   ```

3. **Configure StockSense:**
   
   Update your environment variables or docker-compose.yml:
   ```yaml
   environment:
     - USE_SSL=true
     - SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
     - SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
   ```

4. **Mount Certificate Directory in Docker:**
   ```yaml
   volumes:
     - /etc/letsencrypt:/etc/letsencrypt:ro
   ```

5. **Set Up Auto-Renewal:**
   ```bash
   sudo certbot renew --dry-run
   sudo crontab -e
   # Add this line to renew certificates automatically:
   0 3 * * * certbot renew --quiet
   ```

### Option 2: Commercial Certificate Authority

If you need an EV (Extended Validation) certificate or have specific requirements:

1. Purchase a certificate from a CA (DigiCert, Comodo, etc.)
2. Follow their instructions to generate a CSR and obtain certificates
3. Configure StockSense with your certificate paths:
   ```bash
   export SSL_CERT_PATH=/path/to/your/certificate.crt
   export SSL_KEY_PATH=/path/to/your/private.key
   ```

### Option 3: Reverse Proxy (Nginx/Apache)

For larger deployments, use a reverse proxy:

1. **Install Nginx:**
   ```bash
   sudo apt-get install nginx certbot python3-certbot-nginx
   ```

2. **Generate Certificates:**
   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```

3. **Configure Nginx:**
   ```nginx
   server {
       listen 443 ssl;
       server_name yourdomain.com;
       
       ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
       
       location / {
           proxy_pass http://localhost:5005;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

4. **Disable SSL in StockSense:**
   ```bash
   export USE_SSL=false
   ```
   (Nginx will handle SSL termination)

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_SSL` | `true` | Enable/disable HTTPS |
| `SSL_CERT_PATH` | `certs/cert.pem` | Path to SSL certificate file |
| `SSL_KEY_PATH` | `certs/key.pem` | Path to SSL private key file |
| `FLASK_PORT` | `5005` | Port to run the application on |

### Example Configurations

#### Development (Self-Signed)
```bash
export USE_SSL=true
# Certificates will be auto-generated in ./certs/
```

#### Production (Let's Encrypt)
```bash
export USE_SSL=true
export SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
export SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
```

#### Disable SSL (Not Recommended)
```bash
export USE_SSL=false
```

## Docker Setup

The docker-compose.yml is pre-configured for SSL:

```yaml
services:
  predict_main:
    environment:
      - USE_SSL=true
      - SSL_CERT_PATH=/app/certs/cert.pem
      - SSL_KEY_PATH=/app/certs/key.pem
    volumes:
      - ./certs:/app/certs
```

Certificates are automatically generated on first startup via the entrypoint.sh script.

## Troubleshooting

### Issue: "SSL context not available" Error

**Solution:**
1. Check if certificates exist:
   ```bash
   ls -l certs/
   ```

2. If missing, generate them:
   ```bash
   python scripts/generate_ssl_cert.py
   ```

### Issue: "Permission Denied" When Reading Certificates

**Solution:**
```bash
# Make certificates readable
chmod 644 certs/cert.pem
chmod 600 certs/key.pem  # Private key should be readable only by owner
```

### Issue: Browser Still Shows "Not Secure"

**Possible causes:**
1. Using self-signed certificates (expected in development)
2. Certificate expired
3. Certificate domain doesn't match the URL
4. Mixed content (loading HTTP resources on HTTPS page)

**Solution for development:**
- Accept the self-signed certificate warning (this is normal)

**Solution for production:**
- Use Let's Encrypt or a commercial CA
- Ensure certificate is valid and matches your domain
- Check certificate expiration date

### Issue: Cannot Connect to HTTPS Port

**Solution:**
1. Check if port is open:
   ```bash
   sudo netstat -tlnp | grep 5005
   ```

2. Check firewall:
   ```bash
   sudo ufw allow 5005
   ```

3. For Docker, ensure port mapping is correct in docker-compose.yml

## Security Best Practices

1. **Never commit certificates to version control**
   - The .gitignore is configured to exclude certificate files
   - Keep private keys secure and never share them

2. **Use strong certificates in production**
   - Minimum 2048-bit RSA keys
   - Use certificates from trusted CAs
   - Keep certificates up to date

3. **Regular certificate rotation**
   - Let's Encrypt certificates expire every 90 days
   - Set up auto-renewal
   - Test renewal process regularly

4. **Use HTTPS everywhere**
   - Don't mix HTTP and HTTPS
   - Redirect HTTP to HTTPS in production
   - Use HSTS headers for enhanced security

5. **Monitor certificate expiration**
   - Set up alerts for certificate expiration
   - Test certificate validity regularly

## Testing HTTPS

### Test with cURL
```bash
# With self-signed certificate (development)
curl -k https://localhost:5005/health

# With valid certificate (production)
curl https://yourdomain.com/health
```

### Test with Python
```python
import requests

# Development (ignore certificate verification)
response = requests.get('https://localhost:5005/health', verify=False)
print(response.json())

# Production (verify certificate)
response = requests.get('https://yourdomain.com/health')
print(response.json())
```

### Test with Browser
1. Open `https://localhost:5005` (or your domain)
2. Check the padlock icon in the address bar
3. Click the padlock to view certificate details
4. Verify certificate information

## Additional Resources

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Flask SSL/HTTPS Configuration](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/)

## Support

If you encounter issues not covered in this guide:
1. Check the application logs for specific error messages
2. Verify your environment variables are set correctly
3. Ensure certificates have correct permissions
4. Open an issue on GitHub with details about your setup
