# AWS Setup Guide for Flight Price Prediction MLOps

This guide walks you through setting up the complete AWS infrastructure for the Flight Price Prediction project.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS Cloud                            │
│                                                               │
│  ┌─────────────┐      ┌──────────────┐     ┌─────────────┐ │
│  │   S3 Bucket │      │ RDS PostgreSQL│     │ S3 Bucket   │ │
│  │  DVC Data   │      │  MLflow DB    │     │ MLflow      │ │
│  │  Storage    │      │  Predictions  │     │ Artifacts   │ │
│  └─────────────┘      └──────────────┘     └─────────────┘ │
│         │                     │                    │          │
│         └─────────────────────┼────────────────────┘          │
│                               │                               │
│  ┌──────────────────────────────────────────────────┐        │
│  │              ECS Fargate Cluster                 │        │
│  │                                                   │        │
│  │  ┌────────────────┐      ┌─────────────────┐   │        │
│  │  │  MLflow Server │      │ FastAPI App     │   │        │
│  │  │  (Port 5000)   │◄─────┤ (Port 8000)     │   │        │
│  │  └────────────────┘      └─────────────────┘   │        │
│  │                                                   │        │
│  └──────────────────────────────────────────────────┘        │
│                               │                               │
│  ┌──────────────────────────────────────────────────┐        │
│  │        Application Load Balancer (ALB)           │        │
│  └──────────────────────────────────────────────────┘        │
│                               │                               │
└───────────────────────────────┼───────────────────────────────┘
                                │
                         ┌──────┴──────┐
                         │   Internet  │
                         └─────────────┘
```

## Prerequisites

- AWS Account with admin access
- AWS CLI installed and configured
- Docker installed locally
- Git installed

## Step 1: Create S3 Buckets

### 1.1 Create DVC Data Bucket

```bash
# Set your AWS region
export AWS_REGION=us-east-1

# Create bucket for DVC data
aws s3api create-bucket \
  --bucket flightprice-dvc-data \
  --region $AWS_REGION

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket flightprice-dvc-data \
  --versioning-configuration Status=Enabled

# Add lifecycle policy to manage costs
cat > dvc-lifecycle.json <<EOF
{
  "Rules": [
    {
      "Id": "TransitionOldVersions",
      "Status": "Enabled",
      "NoncurrentVersionTransitions": [
        {
          "NoncurrentDays": 30,
          "StorageClass": "STANDARD_IA"
        }
      ]
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket flightprice-dvc-data \
  --lifecycle-configuration file://dvc-lifecycle.json
```

### 1.2 Create MLflow Artifacts Bucket

```bash
# Create bucket for MLflow artifacts
aws s3api create-bucket \
  --bucket flightprice-mlflow-artifacts \
  --region $AWS_REGION

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket flightprice-mlflow-artifacts \
  --versioning-configuration Status=Enabled
```

## Step 2: Set Up RDS PostgreSQL

### 2.1 Create RDS Instance

```bash
# Create DB subnet group (adjust subnet IDs)
aws rds create-db-subnet-group \
  --db-subnet-group-name flightprice-db-subnet \
  --db-subnet-group-description "Subnet group for FlightPrice DB" \
  --subnet-ids subnet-xxx subnet-yyy

# Create security group
aws ec2 create-security-group \
  --group-name flightprice-db-sg \
  --description "Security group for FlightPrice RDS" \
  --vpc-id vpc-xxx

# Allow PostgreSQL access (adjust CIDR as needed)
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxx \
  --protocol tcp \
  --port 5432 \
  --cidr 10.0.0.0/16

# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier flightprice-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username postgres \
  --master-user-password YOUR_STRONG_PASSWORD \
  --allocated-storage 20 \
  --db-subnet-group-name flightprice-db-subnet \
  --vpc-security-group-ids sg-xxx \
  --backup-retention-period 7 \
  --no-publicly-accessible
```

### 2.2 Create Databases

```bash
# Once RDS is available, connect and create databases
psql -h <rds-endpoint> -U postgres -d postgres

CREATE DATABASE mlflow;
CREATE DATABASE flightprice;

# Create users
CREATE USER mlflow_user WITH PASSWORD 'mlflow_password';
CREATE USER app_user WITH PASSWORD 'app_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE mlflow TO mlflow_user;
GRANT ALL PRIVILEGES ON DATABASE flightprice TO app_user;

\q
```

## Step 3: Create ECR Repositories

```bash
# Create ECR repository for app
aws ecr create-repository \
  --repository-name flightprice-app \
  --region $AWS_REGION

# Create ECR repository for MLflow
aws ecr create-repository \
  --repository-name flightprice-mlflow \
  --region $AWS_REGION

# Get login credentials and authenticate Docker
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.$AWS_REGION.amazonaws.com
```

## Step 4: Set Up ECS Cluster

### 4.1 Create ECS Cluster

```bash
# Create ECS cluster
aws ecs create-cluster \
  --cluster-name flightprice-cluster \
  --region $AWS_REGION
```

### 4.2 Create IAM Roles

```bash
# Create ECS task execution role
cat > ecs-task-execution-role-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://ecs-task-execution-role-trust-policy.json

# Attach policies
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create task role for S3 and Secrets Manager access
cat > ecs-task-role-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::flightprice-*",
        "arn:aws:s3:::flightprice-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:flightprice/*"
    }
  ]
}
EOF

aws iam create-role \
  --role-name flightpriceTaskRole \
  --assume-role-policy-document file://ecs-task-execution-role-trust-policy.json

aws iam put-role-policy \
  --role-name flightpriceTaskRole \
  --policy-name flightpriceTaskPolicy \
  --policy-document file://ecs-task-role-policy.json
```

## Step 5: Store Secrets in Secrets Manager

```bash
# MLflow database URL
aws secretsmanager create-secret \
  --name flightprice/mlflow-backend-uri \
  --secret-string "postgresql://mlflow_user:mlflow_password@<rds-endpoint>:5432/mlflow"

# MLflow artifact root
aws secretsmanager create-secret \
  --name flightprice/mlflow-artifact-root \
  --secret-string "s3://flightprice-mlflow-artifacts"

# App database URL
aws secretsmanager create-secret \
  --name flightprice/database-url \
  --secret-string "postgresql://app_user:app_password@<rds-endpoint>:5432/flightprice"

# MLflow tracking URI (will be set after MLflow service is deployed)
aws secretsmanager create-secret \
  --name flightprice/mlflow-uri \
  --secret-string "http://mlflow-service.local:5000"
```

## Step 6: Create EFS for Model Storage (Optional)

```bash
# Create EFS file system
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=flightprice-models

# Create mount targets in your subnets
aws efs create-mount-target \
  --file-system-id fs-xxx \
  --subnet-id subnet-xxx \
  --security-groups sg-xxx
```

## Step 7: Build and Push Docker Images

```bash
# Build app image
docker build -f docker/Dockerfile.app -t flightprice-app:latest .

# Tag and push
docker tag flightprice-app:latest \
  <account-id>.dkr.ecr.$AWS_REGION.amazonaws.com/flightprice-app:latest

docker push <account-id>.dkr.ecr.$AWS_REGION.amazonaws.com/flightprice-app:latest

# Build MLflow image
docker build -f docker/Dockerfile.mlflow -t flightprice-mlflow:latest .

# Tag and push
docker tag flightprice-mlflow:latest \
  <account-id>.dkr.ecr.$AWS_REGION.amazonaws.com/flightprice-mlflow:latest

docker push <account-id>.dkr.ecr.$AWS_REGION.amazonaws.com/flightprice-mlflow:latest
```

## Step 8: Deploy ECS Services

### 8.1 Update Task Definitions

Edit `infra/aws/ecs-task-definition-app.json` and `infra/aws/ecs-task-definition-mlflow.json`:
- Replace `ACCOUNT_ID` with your AWS account ID
- Replace `REGION` with your AWS region
- Update `fs-XXXXX` with your EFS file system ID (if using EFS)

### 8.2 Register Task Definitions

```bash
# Register MLflow task
aws ecs register-task-definition \
  --cli-input-json file://infra/aws/ecs-task-definition-mlflow.json

# Register app task
aws ecs register-task-definition \
  --cli-input-json file://infra/aws/ecs-task-definition-app.json
```

### 8.3 Create Services

```bash
# Create MLflow service
aws ecs create-service \
  --cluster flightprice-cluster \
  --service-name flightprice-mlflow-service \
  --task-definition flightprice-mlflow-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=DISABLED}"

# Create app service
aws ecs create-service \
  --cluster flightprice-cluster \
  --service-name flightprice-app-service \
  --task-definition flightprice-app-task \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=DISABLED}"
```

## Step 9: Set Up Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name flightprice-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx \
  --scheme internet-facing \
  --type application

# Create target group
aws elbv2 create-target-group \
  --name flightprice-app-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxx \
  --target-type ip \
  --health-check-path /health

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn <alb-arn> \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=<tg-arn>

# Update ECS service to use ALB
aws ecs update-service \
  --cluster flightprice-cluster \
  --service flightprice-app-service \
  --load-balancers targetGroupArn=<tg-arn>,containerName=flightprice-app,containerPort=8000
```

## Step 10: Configure DVC Remote

```bash
# Configure DVC to use S3
dvc remote modify s3remote url s3://flightprice-dvc-data/dvc-cache
dvc remote modify s3remote region $AWS_REGION

# Optionally set credentials (or use IAM role)
dvc remote modify s3remote access_key_id $AWS_ACCESS_KEY_ID
dvc remote modify s3remote secret_access_key $AWS_SECRET_ACCESS_KEY

# Push data to S3
dvc push
```

## Step 11: Set Up CloudWatch Logging

```bash
# Create log groups
aws logs create-log-group \
  --log-group-name /ecs/flightprice-app

aws logs create-log-group \
  --log-group-name /ecs/flightprice-mlflow

# Set retention policy (30 days)
aws logs put-retention-policy \
  --log-group-name /ecs/flightprice-app \
  --retention-in-days 30

aws logs put-retention-policy \
  --log-group-name /ecs/flightprice-mlflow \
  --retention-in-days 30
```

## Step 12: Configure GitHub Secrets for CI/CD

Add the following secrets to your GitHub repository:

```
AWS_ACCOUNT_ID=your-account-id
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
MLFLOW_TRACKING_URI=http://<mlflow-alb-dns>:5000
```

## Cost Estimation

Approximate monthly costs (us-east-1):

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| RDS PostgreSQL | db.t3.micro, 20GB | $15-20 |
| S3 Storage | ~100GB | $2-3 |
| ECR | Docker images | $1 |
| ECS Fargate | 2 tasks (1024 CPU, 2048 MB) | $30-40 |
| ALB | Standard | $20 |
| Data Transfer | Varies | $5-10 |
| **Total** | | **~$75-95/month** |

## Monitoring and Maintenance

### View Logs
```bash
# App logs
aws logs tail /ecs/flightprice-app --follow

# MLflow logs
aws logs tail /ecs/flightprice-mlflow --follow
```

### Scale Services
```bash
# Scale app service
aws ecs update-service \
  --cluster flightprice-cluster \
  --service flightprice-app-service \
  --desired-count 4
```

### Update Services
```bash
# Force new deployment
aws ecs update-service \
  --cluster flightprice-cluster \
  --service flightprice-app-service \
  --force-new-deployment
```

## Troubleshooting

### Service fails to start
- Check CloudWatch logs
- Verify security groups allow traffic
- Ensure secrets are accessible
- Check IAM role permissions

### Can't access RDS
- Verify security group rules
- Check subnet routing
- Ensure RDS is in same VPC as ECS tasks

### High costs
- Enable S3 lifecycle policies
- Use Fargate Spot for non-production
- Set up CloudWatch alarms for cost monitoring
- Consider Reserved Capacity for RDS

## Clean Up

To avoid ongoing charges, delete resources in reverse order:

```bash
# Delete ECS services
aws ecs delete-service --cluster flightprice-cluster --service flightprice-app-service --force
aws ecs delete-service --cluster flightprice-cluster --service flightprice-mlflow-service --force

# Delete ALB
aws elbv2 delete-load-balancer --load-balancer-arn <alb-arn>
aws elbv2 delete-target-group --target-group-arn <tg-arn>

# Delete ECS cluster
aws ecs delete-cluster --cluster flightprice-cluster

# Delete RDS
aws rds delete-db-instance --db-instance-identifier flightprice-db --skip-final-snapshot

# Empty and delete S3 buckets
aws s3 rm s3://flightprice-dvc-data --recursive
aws s3 rb s3://flightprice-dvc-data
aws s3 rm s3://flightprice-mlflow-artifacts --recursive
aws s3 rb s3://flightprice-mlflow-artifacts

# Delete ECR repositories
aws ecr delete-repository --repository-name flightprice-app --force
aws ecr delete-repository --repository-name flightprice-mlflow --force
```

## Next Steps

1. Set up CloudWatch alarms for monitoring
2. Configure auto-scaling policies
3. Implement blue/green deployments
4. Set up VPC endpoints for S3 (cost optimization)
5. Enable AWS X-Ray for distributed tracing
6. Configure WAF for API security

## Support

For issues and questions, refer to the main README.md or create an issue in the repository.
