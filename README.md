# Highly Available Web Application on AWS

A fault-tolerant, multi-tier web application deployed on AWS using EC2, ALB, Auto Scaling, EFS, RDS (Multi-AZ), S3, and VPC — designed to remain available and retain data integrity through individual instance or AZ-level failures.

## Architecture

```
                          ┌─────────────────────┐
                          │   Users (Internet)   │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  Application Load   │
                          │  Balancer (ALB)     │
                          │  public subnets     │
                          └────┬──────────┬─────┘
                               │          │
              ┌────────────────▼──┐  ┌────▼──────────────┐
              │  EC2 (AZ-a)       │  │  EC2 (AZ-b)        │
              │  Private subnet   │  │  Private subnet    │
              │  Flask + Apache   │  │  Flask + Apache    │
              └────────┬──────────┘  └──────────┬─────────┘
                       │    Auto Scaling Group   │
                       │    (min 1 / max 3)      │
                       └────────┬────────────────┘
                    ┌───────────▼──────────────┐
                    │       Amazon EFS          │
                    │  (shared /efs mount)      │
                    └───────────┬──────────────┘
                    ┌───────────▼──────────────┐
                    │    RDS MySQL (Multi-AZ)   │
                    │    Private subnets only   │
                    └──────────────────────────┘
```

**Region:** ap-south-1 (Mumbai)  
**Availability Zones:** ap-south-1a, ap-south-1b  
**Application:** Python Flask REST API reading/writing to MySQL via RDS

---

## Network Design

### VPC: `10.0.0.0/16`

| Subnet | CIDR | AZ | Type |
|---|---|---|---|
| public-1a | 10.0.1.0/24 | ap-south-1a | Public |
| public-1b | 10.0.2.0/24 | ap-south-1b | Public |
| private-1a | 10.0.3.0/24 | ap-south-1a | Private |
| private-1b | 10.0.4.0/24 | ap-south-1b | Private |

**Routing:**
- Public subnets → Internet Gateway (for ALB and NAT Gateway)
- Private subnets → NAT Gateway (outbound-only internet for EC2 updates/installs; no inbound public exposure)

**Security Groups:**
- `alb-sg`: inbound 80 from 0.0.0.0/0
- `ec2-sg`: inbound 80 from `alb-sg` only; inbound 22 from admin IP only
- `rds-sg`: inbound 3306 from `ec2-sg` only
- `efs-sg`: inbound 2049 (NFS) from `ec2-sg` only

---

## IAM Role (EC2)

A single IAM role is attached to EC2 instances via the Launch Template — no hardcoded credentials anywhere.

| Policy | Purpose |
|---|---|
| `AmazonS3ReadOnlyAccess` | Pull static assets from S3 at boot |
| `AmazonElasticFileSystemClientReadWriteAccess` | Mount EFS shared storage |
| `CloudWatchAgentServerPolicy` | Ship metrics and logs to CloudWatch |

---

## Storage

### S3 — Static Content
Bucket `webapp-static-devopsprojcaws` holds the application's `index.html`. EC2 instances pull this file during bootstrap via User Data, keeping the AMI generic and content-updateable without re-baking images.

Versioning is enabled on the bucket to support rollback.

### EFS — Shared Application Storage
EFS is mounted at `/efs` on all EC2 instances. This ensures that any file written by one instance (e.g. uploaded content, logs) is immediately visible to all other instances behind the ALB — a requirement for stateful shared storage across a horizontally scaled fleet.

Mount targets are created in both private subnets to survive an AZ failure.

### RDS MySQL — Application Database
- Engine: MySQL 8.0
- Multi-AZ: **Enabled** (synchronous standby in ap-south-1b)
- Deployed in private subnets — no public endpoint
- Automated backups: 7-day retention

Multi-AZ ensures that if the primary DB instance or its AZ becomes unavailable, RDS automatically fails over to the standby replica with no manual intervention and minimal downtime (~60–120 seconds).

---

## Application

A minimal Flask API with two endpoints to demonstrate live database connectivity through the load balancer:

```python
# GET / → health check
# GET /users → fetches all rows from RDS MySQL users table
```

Database credentials are injected via environment variables — not hardcoded. The app connects to the RDS endpoint, which automatically resolves to whichever instance (primary or standby) is currently active.

---

## Auto Scaling

| Parameter | Value |
|---|---|
| Minimum instances | 1 |
| Desired capacity | 2 |
| Maximum instances | 3 |
| Health check | ALB (HTTP 200 on `/`) |
| Launch Template | Includes IAM role, User Data, security group |

The ASG spans both private subnets. If an instance fails its ALB health check, ASG terminates and replaces it automatically. If an AZ goes down, ASG launches replacement capacity in the surviving AZ.

---

## Deployment

### Prerequisites
- AWS CLI configured with appropriate permissions
- EC2 key pair for SSH access
- VPC, subnets, and security groups provisioned as described above

### Launch

1. **Create Launch Template** with the User Data script below
2. **Create Target Group** (HTTP, health check on `/`)
3. **Create ALB** in public subnets, add listener on port 80 forwarding to target group
4. **Create ASG** using the Launch Template, attached to the ALB target group

**User Data (EC2 bootstrap):**
```bash
#!/bin/bash
yum update -y
yum install -y httpd amazon-efs-utils python3 python3-pip
pip3 install flask pymysql

systemctl start httpd
systemctl enable httpd

# Pull static content from S3
aws s3 cp s3://webapp-static-devopsprojcaws/index.html /var/www/html/index.html

# Mount EFS shared storage
mkdir /efs
mount -t efs fs-071589de16f9adaaa:/ /efs
```

---

## High Availability Test

To verify the setup survives instance failure:

1. Access the application via the **ALB DNS name** — confirm it returns a response
2. **Manually terminate one EC2 instance** from the console
3. Observe the ASG launch a replacement instance automatically (typically within 3–5 minutes)
4. Confirm the ALB continues routing requests to the surviving instance during replacement
5. After replacement launches, confirm **database data is intact** — the RDS endpoint never changed

```bash
# Verify data persistence after failover
mysql -h <rds-endpoint> -u admin -p devopsdb -e "SELECT * FROM users;"
```

Expected: all rows present, no data loss — confirming that application state lives in RDS, not on the EC2 instances themselves.

---

## Technologies

| Component | Service / Tool |
|---|---|
| Compute | AWS EC2 (Amazon Linux, Auto Scaling) |
| Load balancing | AWS Application Load Balancer |
| Shared storage | Amazon EFS |
| Object storage | Amazon S3 |
| Database | Amazon RDS MySQL (Multi-AZ) |
| Networking | AWS VPC, subnets, IGW, NAT Gateway |
| Security | AWS IAM, Security Groups |
| Application | Python 3, Flask, PyMySQL |
| Observability | Amazon CloudWatch |
