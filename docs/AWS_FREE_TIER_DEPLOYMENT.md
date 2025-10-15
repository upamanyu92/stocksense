# AWS Free Tier Deployment Guide for StockSense

> 📌 **Quick Reference**: See [AWS Free Tier Quick Reference](AWS_FREE_TIER_QUICK_REFERENCE.md) for a condensed summary of what's free and how to get started in 5 minutes.

## Overview

This guide explains how to deploy StockSense using AWS Free Tier services, allowing you to run your stock prediction platform in the cloud at minimal to no cost for the first 12 months.

## What's Included in AWS Free Tier?

AWS offers a comprehensive Free Tier with three types of offers:

### 1. 12 Months Free (Starting from account creation)

These services are free for the first 12 months:

#### **EC2 (Elastic Compute Cloud)**
- **750 hours/month** of `t2.micro` (or `t3.micro` in some regions) instances
- 1 vCPU, 1 GB RAM
- **Perfect for**: Running the StockSense Flask application
- **Linux or Windows** supported

#### **RDS (Relational Database Service)**
- **750 hours/month** of `db.t2.micro` (or `db.t3.micro`) instance
- 20 GB of General Purpose (SSD) storage
- 20 GB of backup storage
- **Perfect for**: PostgreSQL/MySQL database for stock data (if migrating from SQLite)

#### **EBS (Elastic Block Storage)**
- **30 GB** of General Purpose (SSD) or Magnetic storage
- 2 million I/Os with EBS Magnetic
- 1 GB of snapshot storage
- **Perfect for**: Storing application data and ML models

#### **S3 (Simple Storage Service)**
- **5 GB** of standard storage
- 20,000 GET requests
- 2,000 PUT requests
- **Perfect for**: Storing model files, backups, and static assets

#### **CloudWatch**
- **10 custom metrics** and **10 alarms**
- 1 million API requests
- 5 GB of log data ingestion and storage
- **Perfect for**: Monitoring application performance

#### **Data Transfer**
- **15 GB** of outbound data transfer per month (aggregated across all AWS services)
- **100 GB** of inbound data transfer per month

### 2. Always Free

These services remain free even after 12 months:

#### **Lambda**
- **1 million free requests per month**
- 400,000 GB-seconds of compute time per month
- **Perfect for**: Scheduled tasks like daily stock data fetching

#### **DynamoDB**
- **25 GB** of storage
- 25 provisioned write capacity units (WCU)
- 25 provisioned read capacity units (RCU)
- **Perfect for**: Caching prediction results or storing metadata

#### **CloudFront (CDN)**
- **50 GB** data transfer out
- 2,000,000 HTTP/HTTPS requests
- **Perfect for**: Serving static dashboard assets

#### **SNS (Simple Notification Service)**
- **1 million publishes**
- 100,000 HTTP/S deliveries
- 1,000 email deliveries
- **Perfect for**: Prediction alerts and notifications

#### **SQS (Simple Queue Service)**
- **1 million requests per month**
- **Perfect for**: Async prediction job queues

### 3. Trials

Short-term free trials for specific services:

#### **SageMaker**
- **250 hours** per month of `ml.t2.medium` or `ml.t3.medium` notebooks (2 months)
- **50 hours** per month of training on `ml.m5.xlarge` (2 months)
- **Perfect for**: ML model training and experimentation

## Recommended AWS Architecture for StockSense

### Minimal Setup (Single EC2 Instance)

**Monthly Cost: $0** (within Free Tier limits)

```
┌─────────────────────────────────────┐
│   AWS Free Tier Architecture        │
│                                      │
│  ┌────────────────────────────────┐ │
│  │  EC2 t2.micro (750 hrs/month)  │ │
│  │                                 │ │
│  │  - Flask App (Port 5005)       │ │
│  │  - SQLite Database             │ │
│  │  - ML Models (Transformer+LSTM)│ │
│  │  - Nginx (reverse proxy)       │ │
│  └────────────────────────────────┘ │
│              │                       │
│              │                       │
│  ┌────────────────────────────────┐ │
│  │  Elastic IP (1 free)           │ │
│  └────────────────────────────────┘ │
│              │                       │
│              │                       │
│  ┌────────────────────────────────┐ │
│  │  Security Group                │ │
│  │  - Port 22 (SSH)               │ │
│  │  - Port 80 (HTTP)              │ │
│  │  - Port 443 (HTTPS)            │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

**Components:**
- 1x EC2 `t2.micro` instance (Ubuntu 22.04 LTS)
- 30 GB EBS volume for OS and application
- 1x Elastic IP (free when attached to running instance)
- Security Group for firewall rules

**Limitations:**
- Single point of failure
- 1 GB RAM may limit concurrent predictions
- Local SQLite database (consider RDS for production)

### Enhanced Setup (EC2 + RDS + S3)

**Monthly Cost: $0** (within Free Tier limits)

```
┌──────────────────────────────────────────────────────┐
│   Enhanced AWS Free Tier Architecture                │
│                                                        │
│  ┌──────────────────┐       ┌──────────────────┐    │
│  │  EC2 t2.micro    │       │  RDS db.t2.micro │    │
│  │                  │       │                  │    │
│  │  - Flask App     │◄─────►│  PostgreSQL      │    │
│  │  - Nginx         │       │  - Stock Data    │    │
│  │  - ML Models     │       │  - Predictions   │    │
│  └──────────────────┘       └──────────────────┘    │
│          │                                            │
│          │                                            │
│          ▼                                            │
│  ┌──────────────────┐       ┌──────────────────┐    │
│  │  S3 Bucket       │       │  CloudWatch      │    │
│  │                  │       │                  │    │
│  │  - Model Files   │       │  - Logs          │    │
│  │  - Backups       │       │  - Metrics       │    │
│  │  - Static Assets │       │  - Alarms        │    │
│  └──────────────────┘       └──────────────────┘    │
└──────────────────────────────────────────────────────┘
```

**Benefits:**
- Managed database with automated backups
- Scalable storage for models and assets
- Better monitoring and alerting
- Separation of concerns

### Serverless Setup (Lambda + DynamoDB)

**Monthly Cost: $0** (within Free Tier limits)

```
┌──────────────────────────────────────────────────────┐
│   Serverless AWS Free Tier Architecture              │
│                                                        │
│  ┌──────────────────┐       ┌──────────────────┐    │
│  │  API Gateway     │       │  Lambda Functions│    │
│  │                  │──────►│                  │    │
│  │  - REST API      │       │  - Predictions   │    │
│  │  - /predict      │       │  - Data Fetch    │    │
│  │  - /health       │       │  - Monitoring    │    │
│  └──────────────────┘       └──────────────────┘    │
│                                      │                │
│                                      ▼                │
│  ┌──────────────────┐       ┌──────────────────┐    │
│  │  DynamoDB        │       │  S3 Bucket       │    │
│  │                  │       │                  │    │
│  │  - Cache         │       │  - ML Models     │    │
│  │  - Metadata      │       │  - Results       │    │
│  └──────────────────┘       └──────────────────┘    │
│                                                        │
│  ┌──────────────────┐       ┌──────────────────┐    │
│  │  CloudFront      │       │  EventBridge     │    │
│  │                  │       │                  │    │
│  │  - CDN           │       │  - Cron Jobs     │    │
│  │  - Dashboard     │       │  - Schedulers    │    │
│  └──────────────────┘       └──────────────────┘    │
└──────────────────────────────────────────────────────┘
```

**Benefits:**
- No server management
- Automatic scaling
- Pay only for usage (within free tier limits)
- High availability

## Step-by-Step Deployment Guide

### Option 1: Single EC2 Instance Deployment

#### Prerequisites
- AWS account (sign up at aws.amazon.com)
- SSH key pair for EC2 access

#### Step 1: Launch EC2 Instance

1. **Login to AWS Console** → Navigate to EC2

2. **Launch Instance:**
   - Click "Launch Instance"
   - **Name**: `stocksense-app`
   - **AMI**: Ubuntu Server 22.04 LTS (Free tier eligible)
   - **Instance Type**: `t2.micro` (1 vCPU, 1 GB RAM)
   - **Key pair**: Create new or select existing
   - **Network Settings**:
     - Allow SSH (port 22) from your IP
     - Allow HTTP (port 80) from anywhere
     - Allow HTTPS (port 443) from anywhere
   - **Storage**: 30 GB gp2 (Free tier eligible)
   - Click "Launch Instance"

3. **Allocate Elastic IP:**
   - EC2 Dashboard → Elastic IPs → Allocate Elastic IP
   - Associate it with your instance
   - **Important**: Elastic IP is free when attached to a running instance

#### Step 2: Connect and Setup Environment

```bash
# Connect to your instance
ssh -i your-key.pem ubuntu@<your-elastic-ip>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3-pip python3-venv git nginx

# Install Docker (optional, for containerized deployment)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
```

#### Step 3: Deploy StockSense

```bash
# Clone repository
cd /home/ubuntu
git clone https://github.com/upamanyu92/stocksense.git
cd stocksense

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
nano .env  # Edit as needed

# Initialize database
python scripts/create_db.py

# Test the application
python -m app.main
```

#### Step 4: Configure Nginx as Reverse Proxy

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/stocksense
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name <your-elastic-ip>;

    location / {
        proxy_pass http://127.0.0.1:5005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/ubuntu/stocksense/app/static;
    }
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/stocksense /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

#### Step 5: Setup as System Service

```bash
# Create systemd service file
sudo nano /etc/systemd/system/stocksense.service
```

Add the following:

```ini
[Unit]
Description=StockSense Stock Prediction Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/stocksense
Environment="PATH=/home/ubuntu/stocksense/venv/bin"
ExecStart=/home/ubuntu/stocksense/venv/bin/python -m app.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable stocksense
sudo systemctl start stocksense
sudo systemctl status stocksense
```

#### Step 6: Verify Deployment

```bash
# Check application is running
curl http://localhost:5005/health

# Access from browser
# Open http://<your-elastic-ip> in browser
```

### Option 2: Docker Deployment on EC2

Follow Steps 1-2 from Option 1, then:

```bash
# Clone repository
cd /home/ubuntu
git clone https://github.com/upamanyu92/stocksense.git
cd stocksense

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Build and run with Docker Compose
docker-compose up -d --build

# Check status
docker-compose ps
docker-compose logs -f
```

### Option 3: Enhanced Setup with RDS

#### Step 1: Create RDS Instance

1. **Navigate to RDS** in AWS Console

2. **Create Database:**
   - Click "Create database"
   - **Engine**: PostgreSQL
   - **Template**: Free tier
   - **DB instance identifier**: `stocksense-db`
   - **Master username**: `stocksense`
   - **Master password**: (set strong password)
   - **DB instance class**: `db.t2.micro` or `db.t3.micro`
   - **Storage**: 20 GB General Purpose (SSD)
   - **VPC**: Same as EC2 instance
   - **Public access**: No
   - **VPC security group**: Create new
     - Allow PostgreSQL (5432) from EC2 security group
   - Click "Create database"

3. **Update Security Groups:**
   - RDS security group: Allow port 5432 from EC2 security group
   - EC2 security group: Allow outbound to RDS security group on 5432

#### Step 2: Update StockSense Configuration

```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@<your-elastic-ip>

# Update .env file with RDS connection
cd /home/ubuntu/stocksense
nano .env
```

Add database connection:

```bash
DATABASE_URL=postgresql://stocksense:<password>@<rds-endpoint>:5432/stocksense
```

#### Step 3: Migrate Database

```bash
# Install PostgreSQL client
sudo apt install -y postgresql-client

# Test connection
psql -h <rds-endpoint> -U stocksense -d stocksense

# Run migrations (if applicable)
python scripts/migrate_to_postgres.py
```

### Option 4: Serverless with Lambda

#### Step 1: Package Application for Lambda

```bash
# On your local machine
cd stocksense

# Create deployment package
mkdir lambda_package
cp -r app lambda_package/
cp requirements.txt lambda_package/

cd lambda_package
pip install -r requirements.txt -t .

# Create Lambda handler
cat > lambda_handler.py << 'EOF'
import json
from app.agents.prediction_coordinator import PredictionCoordinator

coordinator = PredictionCoordinator()

def predict_handler(event, context):
    """Lambda handler for predictions"""
    symbol = event.get('symbol', 'AAPL')
    
    try:
        result = coordinator.predict(symbol)
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
EOF

# Create ZIP file
zip -r ../stocksense-lambda.zip .
```

#### Step 2: Create Lambda Function

1. **Navigate to Lambda** in AWS Console

2. **Create Function:**
   - Click "Create function"
   - **Function name**: `stocksense-predict`
   - **Runtime**: Python 3.11
   - **Architecture**: x86_64
   - Click "Create function"

3. **Upload Code:**
   - Upload the `stocksense-lambda.zip` file
   - **Handler**: `lambda_handler.predict_handler`
   - **Timeout**: 60 seconds
   - **Memory**: 512 MB

4. **Configure Environment Variables:**
   - Add necessary environment variables from `.env`

#### Step 3: Create API Gateway

1. **Navigate to API Gateway** in AWS Console

2. **Create API:**
   - Click "Create API"
   - Choose "REST API"
   - **API name**: `stocksense-api`
   - Click "Create API"

3. **Create Resource:**
   - Actions → Create Resource
   - **Resource Name**: `predict`
   - **Resource Path**: `/predict/{symbol}`
   - Click "Create Resource"

4. **Create Method:**
   - Select `/predict/{symbol}` resource
   - Actions → Create Method → GET
   - **Integration type**: Lambda Function
   - **Lambda Function**: `stocksense-predict`
   - Click "Save"

5. **Deploy API:**
   - Actions → Deploy API
   - **Stage name**: `prod`
   - Click "Deploy"

6. **Test:**
   ```bash
   curl https://<api-id>.execute-api.<region>.amazonaws.com/prod/predict/AAPL
   ```

## Cost Optimization Tips

### 1. Monitor Free Tier Usage

- Use **AWS Free Tier Dashboard** to track usage
- Set up **CloudWatch Billing Alarms**:
  ```bash
  aws cloudwatch put-metric-alarm \
    --alarm-name free-tier-limit \
    --alarm-description "Alert when approaching free tier limit" \
    --metric-name EstimatedCharges \
    --namespace AWS/Billing \
    --statistic Maximum \
    --period 21600 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1
  ```

### 2. Optimize EC2 Usage

- **Stop instance when not in use**: EC2 hours are cumulative across all instances
- **Use reserved instances**: After free tier expires, consider reserved instances for 75% savings
- **Right-size your instance**: `t2.micro` is sufficient for development

### 3. Reduce Data Transfer Costs

- **Use CloudFront**: Reduces origin data transfer
- **Compress responses**: Enable gzip in Nginx
- **Cache aggressively**: Use CloudFront or ElastiCache

### 4. Optimize Storage

- **Delete old snapshots**: Keep only necessary backups
- **Use S3 lifecycle policies**: Move old data to Glacier
- **Clean up EBS volumes**: Delete unused volumes

### 5. Lambda Optimization

- **Right-size memory**: More memory = faster execution = lower cost
- **Reuse connections**: Keep database connections warm
- **Use layers**: Share common dependencies across functions

## Security Best Practices

### 1. EC2 Security

```bash
# Update security group to restrict SSH access
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 22 \
  --cidr <your-ip>/32

# Enable automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 2. Use IAM Roles

Instead of access keys, use IAM roles for EC2:

```bash
# Create IAM role with S3 access
aws iam create-role --role-name stocksense-ec2-role \
  --assume-role-policy-document file://trust-policy.json

# Attach policy
aws iam attach-role-policy --role-name stocksense-ec2-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Attach role to instance
aws ec2 associate-iam-instance-profile \
  --instance-id i-xxxxx \
  --iam-instance-profile Name=stocksense-ec2-role
```

### 3. Enable HTTPS

```bash
# Install Certbot for Let's Encrypt SSL
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate (requires domain name)
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
sudo certbot renew --dry-run
```

### 4. Secrets Management

Use AWS Secrets Manager or SSM Parameter Store:

```bash
# Store database password in SSM Parameter Store (first 10,000 parameters free)
aws ssm put-parameter \
  --name /stocksense/db-password \
  --value "your-secure-password" \
  --type SecureString

# Retrieve in application
aws ssm get-parameter \
  --name /stocksense/db-password \
  --with-decryption
```

## Monitoring and Logging

### 1. CloudWatch Setup

```bash
# Install CloudWatch agent on EC2
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Configure agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard

# Start agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
```

### 2. Application Logging

```python
# Update app/main.py to send logs to CloudWatch
import watchtower
import logging

logger = logging.getLogger(__name__)
logger.addHandler(watchtower.CloudWatchLogHandler(
    log_group='/stocksense/application',
    stream_name='predictions'
))
```

### 3. Performance Metrics

```python
# Send custom metrics to CloudWatch
import boto3

cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_data(
    Namespace='StockSense',
    MetricData=[
        {
            'MetricName': 'PredictionLatency',
            'Value': prediction_time,
            'Unit': 'Seconds'
        }
    ]
)
```

## Troubleshooting

### Common Issues

#### 1. EC2 Instance Not Accessible

```bash
# Check instance status
aws ec2 describe-instance-status --instance-ids i-xxxxx

# Verify security group
aws ec2 describe-security-groups --group-ids sg-xxxxx

# Check system log
aws ec2 get-console-output --instance-id i-xxxxx
```

#### 2. High Memory Usage on t2.micro

```bash
# Monitor memory
free -h

# Create swap file (if RAM is insufficient)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

#### 3. Database Connection Issues

```bash
# Test RDS connectivity
telnet <rds-endpoint> 5432

# Check security groups
aws ec2 describe-security-groups --group-ids <rds-sg-id>

# Verify RDS status
aws rds describe-db-instances --db-instance-identifier stocksense-db
```

#### 4. Lambda Timeout Issues

- **Increase timeout**: Lambda → Configuration → General → Timeout (max 15 minutes)
- **Increase memory**: More memory = faster CPU
- **Optimize code**: Use caching, connection pooling
- **Use async processing**: For long-running tasks, use SQS + Lambda

## Backup and Disaster Recovery

### 1. EC2 Snapshots

```bash
# Create snapshot manually
aws ec2 create-snapshot \
  --volume-id vol-xxxxx \
  --description "StockSense backup $(date +%Y-%m-%d)"

# Automate with Lambda (scheduled via EventBridge)
# See: AWS Backup service (free tier: 5 GB storage)
```

### 2. RDS Automated Backups

- **Enabled by default** in RDS Free Tier
- **Retention period**: 7 days (free)
- **Point-in-time recovery** available

### 3. S3 Versioning

```bash
# Enable versioning on S3 bucket
aws s3api put-bucket-versioning \
  --bucket stocksense-models \
  --versioning-configuration Status=Enabled
```

## Scaling Beyond Free Tier

### When to Upgrade

- **EC2**: Exceed 750 hours/month (run 24/7 with buffer)
- **RDS**: Need > 20 GB storage or > 750 hours
- **S3**: Store > 5 GB or exceed request limits
- **Lambda**: Exceed 1M requests/month or 400K GB-seconds
- **Data Transfer**: Exceed 15 GB outbound/month

### Recommended Upgrades

1. **EC2**: `t3.small` (2 GB RAM) - $15/month
2. **RDS**: `db.t3.small` (2 GB RAM) - $25/month
3. **ElastiCache**: `cache.t3.micro` - $12/month (for caching)
4. **Application Load Balancer**: $16/month (for high availability)

### Multi-Region Setup

For production:
- Primary region: us-east-1 (lowest cost)
- Backup region: us-west-2
- Use Route 53 for failover (50 health checks free)

## Cost Estimation

### Free Tier (First 12 Months)

| Service | Free Tier Limit | StockSense Usage | Cost |
|---------|----------------|------------------|------|
| EC2 t2.micro | 750 hrs/month | 720 hrs (24/7) | $0 |
| EBS | 30 GB | 30 GB | $0 |
| RDS t2.micro | 750 hrs/month | 720 hrs (24/7) | $0 |
| S3 | 5 GB + 20K GET + 2K PUT | 2 GB + 10K req | $0 |
| Data Transfer | 15 GB out | 5 GB | $0 |
| CloudWatch | 10 metrics + 10 alarms | 5 metrics + 5 alarms | $0 |
| **Total** | | | **$0/month** |

### After Free Tier Expires

| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| EC2 t2.micro (Linux) | $8.50 | us-east-1 pricing |
| EBS 30 GB | $3.00 | gp2 storage |
| RDS t2.micro (PostgreSQL) | $15.00 | Single-AZ |
| S3 (10 GB) | $0.23 | Standard storage |
| Data Transfer (20 GB) | $1.80 | Outbound |
| **Total** | **~$28.53/month** | Estimated |

### Cost Optimization

With reserved instances (1 year):
- **EC2 + RDS**: Save ~40% = **$18/month**
- **Spot instances**: Save ~70% = **$8.50/month** (with interruptions)

## Additional Resources

### AWS Documentation

- [AWS Free Tier](https://aws.amazon.com/free/)
- [EC2 User Guide](https://docs.aws.amazon.com/ec2/)
- [RDS User Guide](https://docs.aws.amazon.com/rds/)
- [Lambda Developer Guide](https://docs.aws.amazon.com/lambda/)

### StockSense Documentation

- [Docker Setup](../DOCKER_SETUP.md)
- [Quick Start Guide](QUICK_START.md)
- [API Documentation](API.md)
- [Agentic System](AGENTIC_SYSTEM.md)

### Tools

- [AWS Calculator](https://calculator.aws/) - Estimate costs
- [AWS CLI](https://aws.amazon.com/cli/) - Command-line management
- [Terraform](https://www.terraform.io/) - Infrastructure as Code
- [Ansible](https://www.ansible.com/) - Configuration management

## Conclusion

AWS Free Tier provides generous resources to deploy and run StockSense for a full year at no cost. The recommended approach is:

1. **Start with single EC2 instance** (Option 1) for simplicity
2. **Add RDS** when you need better reliability and backups
3. **Consider serverless** (Lambda) for cost optimization after free tier
4. **Monitor usage** closely to avoid unexpected charges
5. **Implement security best practices** from day one

With proper optimization, you can keep costs under $30/month even after the free tier expires, making AWS an excellent choice for hosting StockSense.

---

**Last Updated**: October 15, 2025  
**Tested on**: AWS Free Tier, Ubuntu 22.04 LTS  
**Estimated Setup Time**: 30-60 minutes
