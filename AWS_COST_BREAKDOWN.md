# AWS Cost Breakdown - Flight Price Prediction MLOps

Detailed monthly cost analysis for running the Flight Price Prediction system on AWS (us-east-1 region).

## 💰 Baseline Configuration Costs

### 1. **ECS Fargate - Application Container** (~$30-35/month)

**Configuration:**
- Task: 1 vCPU (1024 CPU units), 2 GB memory
- Running: 24/7 (730 hours/month)
- Count: 1-2 tasks for high availability

**Pricing:**
- vCPU: $0.04048 per vCPU per hour
- Memory: $0.004445 per GB per hour

**Calculation (1 task):**
```
CPU cost:    1 vCPU × $0.04048 × 730 hours = $29.55/month
Memory cost: 2 GB × $0.004445 × 730 hours = $6.49/month
Total per task: $36.04/month

For 2 tasks (HA): $72.08/month
```

**Optimization Options:**
- Use Fargate Spot: ~70% cheaper = $10.81/task/month
- Reduce to 0.5 vCPU, 1 GB: ~$18/task/month
- Single task (no HA): $36/month

---

### 2. **ECS Fargate - MLflow Server** (~$15-18/month)

**Configuration:**
- Task: 0.5 vCPU (512 CPU units), 1 GB memory
- Running: 24/7
- Count: 1 task

**Calculation:**
```
CPU cost:    0.5 vCPU × $0.04048 × 730 hours = $14.78/month
Memory cost: 1 GB × $0.004445 × 730 hours = $3.24/month
Total: $18.02/month
```

**Optimization:**
- Use Fargate Spot: $5.41/month
- Run only during business hours (12h/day): $9/month
- Use EC2 t3.small instead: $15/month (similar cost but more control)

---

### 3. **RDS PostgreSQL** (~$15-25/month)

**Configuration:**
- Instance: db.t3.micro (2 vCPU, 1 GB RAM)
- Storage: 20 GB General Purpose SSD (gp3)
- Multi-AZ: No (for dev/staging)
- Backup retention: 7 days

**Pricing:**
```
Instance: db.t3.micro
- On-Demand: $0.017 per hour × 730 hours = $12.41/month

Storage (gp3): 20 GB × $0.115/GB = $2.30/month

Backup storage (automated): ~5 GB × $0.095/GB = $0.48/month

Total: ~$15.19/month
```

**What it stores:**
- MLflow backend (experiments, runs, models metadata)
- Predictions table (API request logging)

**Optimization Options:**
- db.t3.micro Reserved Instance (1-year): $8.03/month (35% savings)
- Reduce backup retention to 1 day: $14.89/month
- Use Aurora Serverless v2: $0 when idle, ~$20-30/month active

**Cost if traffic increases:**
- db.t3.small (2GB RAM): $24.82/month
- db.t3.medium (4GB RAM): $49.64/month

---

### 4. **S3 Storage** (~$3-8/month)

**Three buckets needed:**

#### a) **DVC Data Bucket** (~$2-5/month)
```
Storage: 50-100 GB of processed data
- Standard storage: 100 GB × $0.023/GB = $2.30/month
- Versioning overhead: ~20% = $0.46/month
- Requests (PUT/GET): ~10,000 × $0.000005 = $0.05/month
Total: ~$2.81/month
```

#### b) **MLflow Artifacts Bucket** (~$1-2/month)
```
Storage: 10-20 GB (model files, plots, logs)
- Standard storage: 20 GB × $0.023/GB = $0.46/month
- Requests: ~5,000 × $0.000005 = $0.025/month
Total: ~$0.49/month
```

#### c) **Model Backup Bucket** (Optional, ~$0.50/month)
```
Storage: 5-10 GB (joblib files)
- Standard storage: 10 GB × $0.023/GB = $0.23/month
Total: ~$0.23/month
```

**Combined S3 Total: ~$3.53/month**

**Optimization:**
- Lifecycle policies to Glacier after 90 days: $0.004/GB (82% savings)
- Intelligent-Tiering: Auto-optimize for $2/month
- Delete old model versions: $1-2/month

**Cost if data grows:**
- 500 GB data: $11.50/month
- 1 TB data: $23/month

---

### 5. **Application Load Balancer (ALB)** (~$16-20/month)

**Pricing:**
```
Base charge: $0.0225 per hour × 730 hours = $16.43/month
LCU charges (varies by traffic):
- Low traffic (<1M requests/month): $0.50-1.00/month
- Medium traffic (5M requests): $2-3/month

Total: ~$17-19/month
```

**What it provides:**
- HTTPS termination
- Health checks
- Auto-scaling
- Multi-AZ distribution

**Optimization:**
- Use Network Load Balancer: $16/month (no LCU charges for low traffic)
- Direct ECS access (no LB): $0/month (not recommended for production)
- CloudFront + ALB: Better caching, similar cost

---

### 6. **Elastic Container Registry (ECR)** (~$1-2/month)

**Pricing:**
```
Storage: 5-10 GB for Docker images
- Standard storage: 10 GB × $0.10/GB = $1.00/month
- Data transfer OUT (to ECS): Free within same region

Total: ~$1.00/month
```

**What's stored:**
- flightprice-app image (~1-2 GB)
- flightprice-mlflow image (~500 MB)
- Multiple versions/tags

**Optimization:**
- Lifecycle policies: Keep last 5 images only: $0.50/month
- Use ECR Public: Free (but less secure)

---

### 7. **Data Transfer** (~$1-5/month)

**Breakdown:**
```
Data IN to AWS: Free
Data between services (same region): Free

Data OUT to Internet:
- First 1 GB: Free
- Next 9.999 TB: $0.09/GB
- Estimated 10-50 GB/month = $0.90-4.50/month

Total: ~$1-5/month
```

**Depends on:**
- API response sizes
- Model download frequency
- Monitoring dashboard access
- External integrations

**Optimization:**
- Use CloudFront CDN: First 1 TB free/month
- Compress responses: Reduce by 60-70%
- Cache predictions: Reduce by 30-40%

---

### 8. **CloudWatch Logs** (~$2-5/month)

**Pricing:**
```
Ingestion: $0.50 per GB
- App logs: ~2-5 GB/month = $1.00-2.50/month
- MLflow logs: ~1-2 GB/month = $0.50-1.00/month

Storage: $0.03 per GB (after 30 days)
- 10 GB stored × $0.03 = $0.30/month

Total: ~$2.80-3.80/month
```

**Retention strategy:**
- 30 days for app logs
- 7 days for debug logs
- Archive to S3 after retention: $0.023/GB (77% savings)

**Optimization:**
- Reduce log level to WARN/ERROR only: $1/month
- Use S3 for long-term storage: $0.50/month
- Compress logs: $1.50/month

---

### 9. **AWS Secrets Manager** (~$0.40-0.80/month)

**Pricing:**
```
Secrets stored: 4-8 secrets
- $0.40 per secret per month
- 4 secrets × $0.40 = $1.60/month

API calls: ~10,000 per month
- First 10,000: Free
- Additional: $0.05 per 10,000

Total: ~$1.60/month
```

**Secrets stored:**
- Database URLs (2)
- MLflow URIs (1)
- AWS credentials (1)
- API keys (1-3)

**Optimization:**
- Use Parameter Store (free tier): $0/month for <10,000 API calls
- Environment variables (less secure): $0/month
- Reduce secrets rotation frequency: $0.80/month

---

### 10. **Additional Services** (Optional, ~$5-15/month)

#### **NAT Gateway** (~$32/month if using private subnets)
```
Hourly charge: $0.045 × 730 hours = $32.85/month
Data processing: $0.045 per GB
Total: ~$35-40/month
```
**Optimization:** Use VPC Endpoints instead: $7/month

#### **VPC Endpoints** (~$7/month - Recommended)
```
S3 endpoint: $0.01 per GB × 100 GB = $1.00/month
DynamoDB endpoint: Free
Gateway endpoints: Free

Total: ~$1-2/month
```

#### **Route 53** (~$0.50-1/month)
```
Hosted zone: $0.50/month
DNS queries: $0.40 per million queries
Total: ~$1/month
```

#### **Certificate Manager (ACM)**: Free for AWS services

#### **CloudWatch Alarms** (~$0.10-0.50/month)
```
Standard metrics: Free
Custom metrics: $0.30 per metric
5 alarms × $0.10 = $0.50/month
```

---

## 📊 **Total Cost Summary**

### **Minimal Configuration** (Single region, no HA) = **~$75/month**

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| ECS App (1 task) | 1 vCPU, 2GB | $36.00 |
| ECS MLflow (1 task) | 0.5 vCPU, 1GB | $18.00 |
| RDS PostgreSQL | db.t3.micro, 20GB | $15.00 |
| S3 Storage | 3 buckets, ~100GB | $3.50 |
| ALB | Low traffic | $17.00 |
| ECR | 10GB images | $1.00 |
| Data Transfer | ~20GB OUT | $2.00 |
| CloudWatch Logs | 5GB/month | $3.00 |
| Secrets Manager | 4 secrets | $1.60 |
| **TOTAL** | | **~$97.10** |

### **Optimized Configuration** (Cost-conscious) = **~$45/month**

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| ECS App (Spot) | 0.5 vCPU, 1GB, Spot | $10.80 |
| ECS MLflow (Spot) | 0.25 vCPU, 0.5GB, Spot | $5.40 |
| RDS Reserved | db.t3.micro, 1-yr RI | $8.00 |
| S3 + Lifecycle | Intelligent-Tiering | $2.00 |
| NLB instead of ALB | Network Load Balancer | $16.00 |
| ECR Lifecycle | Keep 3 images only | $0.50 |
| VPC Endpoints | No NAT Gateway | $1.00 |
| CloudWatch (reduced) | WARN/ERROR only | $1.00 |
| Parameter Store | Free tier | $0.00 |
| **TOTAL** | | **~$44.70** |

### **High Availability Configuration** = **~$140/month**

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| ECS App (2 tasks) | 1 vCPU, 2GB × 2 AZ | $72.00 |
| ECS MLflow (2 tasks) | 0.5 vCPU, 1GB × 2 AZ | $36.00 |
| RDS Multi-AZ | db.t3.small, Multi-AZ | $50.00 |
| S3 + Replication | Cross-region | $5.00 |
| ALB | Medium traffic | $20.00 |
| ECR | Replication | $2.00 |
| NAT Gateway (2 AZ) | 2 gateways | $65.00 |
| CloudWatch Enhanced | Custom metrics | $5.00 |
| Secrets Manager | 8 secrets | $3.20 |
| **TOTAL** | | **~$258.20** |

---

## 🎯 **Cost by Traffic Level**

### **Low Traffic** (~1,000 predictions/day) = **$45-75/month**
- Single ECS task
- db.t3.micro
- Fargate Spot

### **Medium Traffic** (~10,000 predictions/day) = **$95-140/month**
- 2 ECS tasks
- db.t3.small
- Standard Fargate

### **High Traffic** (~100,000 predictions/day) = **$250-400/month**
- 4+ ECS tasks with auto-scaling
- db.t3.medium or Aurora
- Reserved capacity

---

## 💡 **Cost Optimization Strategies**

### **Immediate Savings** (40-50% reduction)

1. **Use Fargate Spot**: $10.80 vs $36 per task (-70%)
2. **Reserved Instances for RDS**: $8 vs $12.41 (-35%)
3. **S3 Lifecycle Policies**: $2 vs $3.50 (-43%)
4. **Parameter Store vs Secrets Manager**: $0 vs $1.60 (-100%)
5. **VPC Endpoints vs NAT Gateway**: $1 vs $32 (-97%)

**Total optimized: ~$45/month vs $97/month**

### **Medium-term Savings**

1. **Savings Plans** (1-year commitment): 20-30% off compute
2. **S3 Intelligent-Tiering**: Automatic cost optimization
3. **CloudWatch Log Archival**: Move to S3 after 7 days
4. **ECS Auto-scaling**: Scale down during low-traffic hours

### **Advanced Optimizations**

1. **Lambda for API** (if low traffic): $0-5/month for <100K requests
2. **Aurora Serverless v2**: Pay only for active time
3. **CloudFront Caching**: Reduce backend calls by 60%
4. **Scheduled Scaling**: Run MLflow only during training

---

## 📈 **Cost Comparison**

### **vs. On-Premise**
```
Server (mid-range):      $2,000-3,000 upfront + $50/month electricity
AWS (1 year):            $1,200 ($100/month × 12)
Break-even:              ~2 years
Advantage:               No maintenance, scaling, HA out-of-box
```

### **vs. Other Clouds**

| Provider | Similar Setup | Monthly Cost |
|----------|---------------|--------------|
| AWS | Baseline | $97 |
| Azure | App Service + Azure SQL | $85-110 |
| GCP | Cloud Run + Cloud SQL | $75-95 |
| DigitalOcean | App Platform + Managed DB | $60-80 |
| Heroku | Dyno + Postgres | $75-100 |

---

## 🔍 **Hidden Costs to Watch**

1. **Data Transfer**: Can spike if downloading large datasets
2. **CloudWatch Logs**: Verbose logging = $$
3. **NAT Gateway**: Expensive for internet access from private subnets
4. **Multi-AZ**: Doubles instance and data transfer costs
5. **Backup Storage**: RDS snapshots accumulate over time
6. **API Gateway**: If added later ($3.50 per million requests)

---

## 🎁 **AWS Free Tier Benefits** (First 12 months)

If you're a new AWS customer:

- **EC2**: 750 hours/month t2.micro/t3.micro (not Fargate)
- **RDS**: 750 hours db.t2.micro + 20GB storage
- **S3**: 5GB standard storage
- **CloudWatch**: 10 custom metrics
- **Lambda**: 1M requests/month (alternative to Fargate)

**Potential savings in Year 1**: $30-50/month

---

## 💰 **Final Recommendations**

### **For Development/Testing**: ~$30-45/month
- Use Fargate Spot
- Single availability zone
- db.t3.micro with 1-year RI
- S3 lifecycle policies
- Parameter Store (free)
- Run MLflow only when needed

### **For Production (Low-Medium Traffic)**: ~$75-95/month
- 1-2 Fargate tasks (on-demand)
- db.t3.micro with backups
- Standard S3 with versioning
- ALB for HTTPS
- CloudWatch monitoring
- Secrets Manager

### **For Production (High Availability)**: ~$140-180/month
- 2+ Fargate tasks across AZs
- db.t3.small Multi-AZ
- S3 cross-region replication
- Enhanced monitoring
- Auto-scaling enabled

---

## 📊 **Cost Monitoring Tools**

1. **AWS Cost Explorer**: Built-in cost analysis
2. **AWS Budgets**: Set alerts at $50, $75, $100
3. **CloudWatch Billing Alarms**: Real-time notifications
4. **Tags**: Tag all resources with "flightprice-prod"
5. **AWS Cost Anomaly Detection**: ML-based cost alerts

---

**Remember**: These are estimates. Actual costs vary based on:
- Traffic volume
- Data size
- Geographic region
- Reserved capacity usage
- Spot instance availability
- Data transfer patterns

**Best practice**: Start with optimized config ($45/month) and scale up based on actual needs.
