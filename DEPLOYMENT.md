# Deployment Guide

Comprehensive guide for deploying the AI Research Assistant to production.

## Table of Contents

1. [Streamlit Cloud Deployment](#streamlit-cloud-deployment)
2. [AWS Deployment](#aws-deployment)
3. [Docker Deployment](#docker-deployment)
4. [Security Checklist](#security-checklist)
5. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Streamlit Cloud Deployment

### Prerequisites

- GitHub account
- Streamlit Cloud account (free at streamlit.io)
- Anthropic API key

### Steps

#### 1. Prepare Repository

```bash
# Ensure .gitignore is properly configured
cat .gitignore

# Verify .env is NOT tracked
git status

# Add and commit code (WITHOUT .env)
git add .
git commit -m "Initial commit"
git push origin main
```

#### 2. Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Connect your GitHub repository
4. Select:
   - Repository: `your-username/research-assistant`
   - Branch: `main`
   - Main file: `app.py`

#### 3. Configure Secrets

In Streamlit Cloud dashboard, add secrets:

```toml
# .streamlit/secrets.toml format
ANTHROPIC_API_KEY = "your-api-key-here"
MAX_UPLOAD_SIZE_MB = "100"
MAX_DOCUMENTS = "10"
PROCESSING_TIMEOUT_MINUTES = "15"
```

#### 4. Deploy

Click "Deploy" and wait for deployment to complete (2-5 minutes).

#### 5. Test

Visit your deployed URL and test with sample PDFs.

### Streamlit Cloud Benefits

- ✅ Free tier available
- ✅ Automatic HTTPS
- ✅ Easy updates (push to Git)
- ✅ Built-in secrets management
- ✅ No server management

### Streamlit Cloud Limitations

- ⚠️ 1GB RAM limit (free tier)
- ⚠️ Shared resources
- ⚠️ May sleep after inactivity
- ⚠️ Limited concurrent users

---

## AWS Deployment

### Architecture

```
User → CloudFront → ALB → ECS (Streamlit) → Claude API
                            ↓
                         EFS (Storage)
```

### Prerequisites

- AWS Account
- AWS CLI installed and configured
- Docker installed locally

### Option A: ECS Fargate (Recommended)

#### 1. Create Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/uploads data/outputs data/temp logs

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### 2. Build and Push to ECR

```bash
# Create ECR repository
aws ecr create-repository --repository-name research-assistant

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t research-assistant .

# Tag image
docker tag research-assistant:latest \
    YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/research-assistant:latest

# Push to ECR
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/research-assistant:latest
```

#### 3. Create ECS Cluster

```bash
# Create cluster
aws ecs create-cluster --cluster-name research-assistant-cluster
```

#### 4. Create Task Definition

Create `task-definition.json`:

```json
{
  "family": "research-assistant",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "research-assistant",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/research-assistant:latest",
      "portMappings": [
        {
          "containerPort": 8501,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "MAX_UPLOAD_SIZE_MB",
          "value": "100"
        },
        {
          "name": "MAX_DOCUMENTS",
          "value": "10"
        }
      ],
      "secrets": [
        {
          "name": "ANTHROPIC_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:research-assistant/claude-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/research-assistant",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Register task:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### 5. Create Service

```bash
aws ecs create-service \
    --cluster research-assistant-cluster \
    --service-name research-assistant-service \
    --task-definition research-assistant \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

#### 6. Set Up Load Balancer

Create ALB and target group, then update service to use ALB.

#### 7. Configure Secrets Manager

```bash
# Create secret for API key
aws secretsmanager create-secret \
    --name research-assistant/claude-api-key \
    --secret-string "your-api-key-here"
```

### Option B: EC2 Deployment

#### 1. Launch EC2 Instance

- Instance Type: t3.medium or larger
- AMI: Amazon Linux 2 or Ubuntu
- Storage: 30GB+
- Security Group: Allow ports 22, 80, 443, 8501

#### 2. Connect and Setup

```bash
# Connect to instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Update system
sudo yum update -y

# Install Python 3.11
sudo yum install python3.11 -y

# Install Git
sudo yum install git -y

# Clone repository
git clone https://github.com/your-username/research-assistant.git
cd research-assistant

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
nano .env
# Add: ANTHROPIC_API_KEY=your-key-here

# Test application
streamlit run app.py
```

#### 3. Set Up as Systemd Service

Create `/etc/systemd/system/research-assistant.service`:

```ini
[Unit]
Description=AI Research Assistant
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/research-assistant
Environment="PATH=/home/ec2-user/research-assistant/venv/bin"
ExecStart=/home/ec2-user/research-assistant/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable research-assistant
sudo systemctl start research-assistant
sudo systemctl status research-assistant
```

#### 4. Set Up Nginx Reverse Proxy

```bash
sudo yum install nginx -y

# Configure Nginx
sudo nano /etc/nginx/conf.d/research-assistant.conf
```

Add:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

Start Nginx:

```bash
sudo systemctl enable nginx
sudo systemctl start nginx
```

#### 5. Set Up SSL with Let's Encrypt

```bash
sudo yum install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

---

## Docker Deployment

### Docker Compose Setup

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  research-assistant:
    build: .
    ports:
      - "8501:8501"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - MAX_UPLOAD_SIZE_MB=100
      - MAX_DOCUMENTS=10
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Deploy:

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Security Checklist

### Before Deployment

- [ ] API keys in environment variables (not hardcoded)
- [ ] `.env` file in `.gitignore`
- [ ] No sensitive data in Git history
- [ ] Updated all dependencies
- [ ] Configured proper file size limits
- [ ] Set up error logging
- [ ] Tested error handling

### Production Security

- [ ] HTTPS enabled
- [ ] API rate limiting configured
- [ ] File upload validation active
- [ ] Input sanitization enabled
- [ ] Secrets in AWS Secrets Manager / similar
- [ ] Security groups properly configured
- [ ] Regular security updates scheduled
- [ ] Monitoring and alerting set up

### Ongoing Security

- [ ] Rotate API keys quarterly
- [ ] Review logs weekly
- [ ] Update dependencies monthly
- [ ] Security audit quarterly
- [ ] Backup data regularly
- [ ] Test disaster recovery

---

## Monitoring & Maintenance

### CloudWatch Monitoring (AWS)

```bash
# Create CloudWatch log group
aws logs create-log-group --log-group-name /ecs/research-assistant

# Create alarms
aws cloudwatch put-metric-alarm \
    --alarm-name research-assistant-high-cpu \
    --alarm-description "Alert when CPU > 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold
```

### Application Monitoring

Add to `config/settings.py`:

```python
# Monitoring settings
ENABLE_MONITORING = True
ALERT_EMAIL = "admin@yourdomain.com"
```

### Backup Strategy

```bash
# Backup uploaded files
aws s3 sync data/uploads s3://research-assistant-backups/uploads/

# Backup generated reports
aws s3 sync data/outputs s3://research-assistant-backups/outputs/

# Automated daily backup
# Add to crontab:
# 0 2 * * * /path/to/backup.sh
```

### Log Rotation

```bash
# Configure logrotate
sudo nano /etc/logrotate.d/research-assistant
```

Add:

```
/home/ec2-user/research-assistant/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ec2-user ec2-user
}
```

### Update Procedure

```bash
# 1. Backup current version
cp -r research-assistant research-assistant-backup

# 2. Pull updates
cd research-assistant
git pull origin main

# 3. Update dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt

# 4. Restart service
sudo systemctl restart research-assistant

# 5. Verify
curl http://localhost:8501/_stcore/health
```

---

## Cost Estimation

### Streamlit Cloud
- Free: 1 app, limited resources
- Standard: $20/month per app

### AWS ECS Fargate
- ECS Task (2 vCPU, 4GB RAM): ~$60/month
- Load Balancer: ~$20/month
- Data Transfer: Variable
- **Total: ~$80-100/month**

### AWS EC2
- t3.medium instance: ~$30/month
- Storage (30GB): ~$3/month
- Data Transfer: Variable
- **Total: ~$35-50/month**

### API Costs
- Claude API: Variable based on usage
- Estimated: $50-200/month for moderate use

---

## Troubleshooting

### Common Deployment Issues

**Port Already in Use**
```bash
sudo lsof -i :8501
sudo kill -9 <PID>
```

**Permission Errors**
```bash
chmod +x app.py
chown -R ec2-user:ec2-user /path/to/app
```

**Memory Issues**
- Increase instance size
- Reduce MAX_DOCUMENTS
- Enable swap space

**API Timeouts**
- Check security groups
- Verify API key
- Check Anthropic API status

---

## Support

For deployment issues:
1. Check logs: `tail -f logs/app_*.log`
2. Verify environment variables
3. Test locally first
4. Check cloud provider status pages

---

**Deployment Checklist Complete** ✅
