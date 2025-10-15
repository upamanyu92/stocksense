# AWS Free Tier Quick Reference for StockSense

## TL;DR - What Comes Free in AWS Free Tier?

### 12-Month Free Tier (New Accounts)

| Service | Free Tier Limit | StockSense Use Case | Enough for? |
|---------|----------------|---------------------|-------------|
| **EC2** | 750 hrs/month t2.micro (1GB RAM) | Run Flask app + ML models | ✅ Yes (24/7 for 1 instance) |
| **EBS** | 30 GB storage | Store application + models | ✅ Yes |
| **RDS** | 750 hrs/month db.t2.micro + 20 GB | PostgreSQL database | ✅ Yes (24/7 for 1 instance) |
| **S3** | 5 GB + 20K GET + 2K PUT | Model storage, backups | ✅ Yes (small-medium usage) |
| **CloudWatch** | 10 metrics + 10 alarms | Monitoring | ✅ Yes |
| **Data Transfer** | 15 GB outbound/month | API responses | ⚠️ Depends on traffic |

### Always Free (No Expiration)

| Service | Free Tier Limit | StockSense Use Case |
|---------|----------------|---------------------|
| **Lambda** | 1M requests + 400K GB-sec/month | Scheduled predictions, API | ✅ Excellent |
| **DynamoDB** | 25 GB storage | Cache, metadata | ✅ Good |
| **CloudFront** | 50 GB transfer + 2M requests | CDN for dashboard | ✅ Good |
| **SNS** | 1M publishes + 1K emails | Alerts | ✅ Excellent |
| **SQS** | 1M requests | Job queue | ✅ Good |

## Quick Deployment Options

### Option 1: Free for 12 Months
**Single EC2 Instance**
- Cost: **$0/month** (first year)
- Setup: 30 minutes
- Best for: Personal use, development

### Option 2: Always Free
**Serverless (Lambda + DynamoDB)**
- Cost: **$0/month** (ongoing)
- Setup: 60 minutes
- Best for: Intermittent usage, API-only

### Option 3: Hybrid (Best Value)
**EC2 + Lambda + DynamoDB**
- Cost: **$0/month** (first year)
- Setup: 45 minutes
- Best for: Production-ready setup

## Getting Started (5-Minute Setup)

```bash
# 1. Launch EC2 t2.micro (Ubuntu 22.04)
# 2. SSH into instance
ssh -i key.pem ubuntu@<ip-address>

# 3. Quick install
sudo apt update && sudo apt install -y python3-pip git
git clone https://github.com/upamanyu92/stocksense.git
cd stocksense
pip install -r requirements.txt
python -m app.main

# 4. Access at http://<ip-address>:5005
```

## Cost After Free Tier Expires

| Component | Monthly Cost |
|-----------|--------------|
| EC2 t2.micro (Linux) | ~$8.50 |
| EBS 30 GB | ~$3.00 |
| RDS t2.micro | ~$15.00 |
| **Total** | **~$26.50/month** |

**Optimization**: Use Reserved Instances to save 40% → **~$16/month**

## Important Limits to Monitor

⚠️ **EC2**: Don't exceed 750 hours/month (31 days × 24 hours = 744 hours)
⚠️ **Data Transfer**: Watch outbound traffic (15 GB limit)
⚠️ **S3**: Monitor GET/PUT requests (20K/2K limits)

## Free Tier Alerts Setup

```bash
# Install AWS CLI
pip install awscli

# Create billing alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "free-tier-alert" \
  --alarm-description "Alert at $5 threshold" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

## Resources

- 📖 [Full Deployment Guide](AWS_FREE_TIER_DEPLOYMENT.md) - Complete step-by-step instructions
- 🚀 [Quick Start Guide](QUICK_START.md) - Get StockSense running locally
- 🐳 [Docker Setup](../DOCKER_SETUP.md) - Containerized deployment
- 🤖 [Agentic System](AGENTIC_SYSTEM.md) - Advanced features

---

**Need Help?** See the [full AWS deployment guide](AWS_FREE_TIER_DEPLOYMENT.md) for detailed instructions.
