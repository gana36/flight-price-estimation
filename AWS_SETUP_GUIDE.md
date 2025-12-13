# AWS Deployment Guide

This guide covers deploying the Flight Price Prediction API to AWS ECS Fargate.

## Prerequisites

- AWS Account with configured CLI (`aws configure`)
- Docker installed locally
- Trained model (run `dvc repro` first)

## Quick Deployment

For a simple deployment without RDS or ALB:

### 1. Create ECR Repository

```bash
aws ecr create-repository --repository-name flightprice-app --region us-east-1
```

### 2. Create S3 Bucket

```bash
aws s3 mb s3://flightprice-mlops-<your-account-id> --region us-east-1
```

### 3. Create ECS Cluster

```bash
aws ecs create-cluster --cluster-name flightprice-cluster --region us-east-1
```

### 4. Create IAM Role

```bash
# Create role
aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"ecs-tasks.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}"

# Attach policies
aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
```

### 5. Create Log Groups

```bash
aws logs create-log-group --log-group-name /ecs/flightprice-app --region us-east-1
```

### 6. Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build image (from project root)
docker build -t flightprice-app:latest -f docker/Dockerfile.app .

# Tag and push
docker tag flightprice-app:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/flightprice-app:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/flightprice-app:latest
```

### 7. Register Task Definition

Update `infra/aws/ecs-task-definition-app-simple.json` with your account ID, then:

```bash
aws ecs register-task-definition --cli-input-json file://infra/aws/ecs-task-definition-app-simple.json --region us-east-1
```

### 8. Get Network Configuration

```bash
# Get default VPC
aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text --region us-east-1

# Get a subnet
aws ec2 describe-subnets --filters "Name=vpc-id,Values=<vpc-id>" --query "Subnets[0].SubnetId" --output text --region us-east-1

# Get security group
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=<vpc-id>" "Name=group-name,Values=default" --query "SecurityGroups[0].GroupId" --output text --region us-east-1
```

### 9. Allow Traffic on Port 8000

```bash
aws ec2 authorize-security-group-ingress --group-id <sg-id> --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region us-east-1
```

### 10. Create ECS Service

```bash
aws ecs create-service \
  --cluster flightprice-cluster \
  --service-name flightprice-app-service \
  --task-definition flightprice-app-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<subnet-id>],securityGroups=[<sg-id>],assignPublicIp=ENABLED}" \
  --region us-east-1
```

### 11. Get Public IP

```bash
# Get task ARN
aws ecs list-tasks --cluster flightprice-cluster --service-name flightprice-app-service --query "taskArns[0]" --output text --region us-east-1

# Get network interface
aws ecs describe-tasks --cluster flightprice-cluster --tasks <task-arn> --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text --region us-east-1

# Get public IP
aws ec2 describe-network-interfaces --network-interface-ids <eni-id> --query "NetworkInterfaces[0].Association.PublicIp" --output text --region us-east-1
```

### 12. Test Deployment

```bash
curl http://<public-ip>:8000/health
curl -X POST http://<public-ip>:8000/predict -H "Content-Type: application/json" -d "{\"airline\":\"Vistara\",\"flight\":\"UK-123\",\"source_city\":\"Delhi\",\"departure_time\":\"Morning\",\"stops\":\"zero\",\"arrival_time\":\"Afternoon\",\"destination_city\":\"Mumbai\",\"class\":\"Economy\",\"duration\":2.5,\"days_left\":15}"
```

## Update Deployment

When you make changes:

```bash
# Rebuild and push
docker build -t flightprice-app:latest -f docker/Dockerfile.app .
docker tag flightprice-app:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/flightprice-app:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/flightprice-app:latest

# Force new deployment
aws ecs update-service --cluster flightprice-cluster --service flightprice-app-service --force-new-deployment --region us-east-1
```

## View Logs

```bash
aws logs tail /ecs/flightprice-app --follow --region us-east-1
```

## Clean Up

Delete resources to avoid charges:

```bash
# Stop and delete service
aws ecs update-service --cluster flightprice-cluster --service flightprice-app-service --desired-count 0 --region us-east-1
aws ecs delete-service --cluster flightprice-cluster --service flightprice-app-service --region us-east-1

# Delete cluster
aws ecs delete-cluster --cluster flightprice-cluster --region us-east-1

# Delete ECR repository
aws ecr delete-repository --repository-name flightprice-app --force --region us-east-1

# Delete S3 bucket
aws s3 rb s3://flightprice-mlops-<account-id> --force

# Delete log group
aws logs delete-log-group --log-group-name /ecs/flightprice-app --region us-east-1

# Delete IAM role
aws iam detach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
aws iam detach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam detach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
aws iam delete-role --role-name ecsTaskExecutionRole
```

## Cost Estimate

| Service | Monthly Cost |
|---------|-------------|
| ECS Fargate (0.5 vCPU, 1GB) | ~$15 |
| ECR Storage | ~$1 |
| S3 Storage | ~$1 |
| CloudWatch Logs | ~$1 |
| **Total** | **~$18/month** |

## Production Enhancements

For a production deployment, consider adding:

- **RDS PostgreSQL** - For MLflow backend and prediction logging
- **Application Load Balancer** - For HTTPS and load balancing
- **Auto Scaling** - Scale based on CPU/memory usage
- **CloudWatch Alarms** - Monitor errors and latency
- **VPC Endpoints** - Reduce S3 data transfer costs
- **Secrets Manager** - Store database credentials securely

