FINAL AWS DEVOPS PROJECT 
PROJECT OBJECTIVE

Build a highly available web application on AWS using EC2, ALB, ASG, EFS, RDS, S3, IAM, and VPC.
The application must survive EC2 failure and retain database data.

1. IAM ROLE (SECURITY)
What I did

Created an IAM role for EC2 so instances can access S3, EFS, and CloudWatch without access keys.

Policies attached

AmazonS3ReadOnlyAccess

AmazonElasticFileSystemClientReadWriteAccess

CloudWatchAgentServerPolicy


2. VPC & NETWORKING
VPC

CIDR: 10.0.0.0/16

Subnets

Public:

10.0.1.0/24 (AZ-a)

10.0.2.0/24 (AZ-b)

Private:

10.0.3.0/24 (AZ-a)

10.0.4.0/24 (AZ-b)

3. INTERNET GATEWAY & NAT GATEWAY

Created Internet Gateway and attached to VPC.

Created NAT Gateway in a public subnet.

Assigned Elastic IP to NAT Gateway.

4. ROUTE TABLES
Public Route Table

Route:

0.0.0.0/0 → Internet Gateway


Associated with both public subnets.

Private Route Table

Route:

0.0.0.0/0 → NAT Gateway


Associated with both private subnets.

5. S3 BUCKET (STATIC CONTENT)
Commands used
aws s3 mb s3://webapp-static-devopsprojcaws


Enable versioning:

aws s3api put-bucket-versioning \
--bucket webapp-static-devopsprojcaws \
--versioning-configuration Status=Enabled


Create and upload file:

echo "Hello from S3" > index.html
aws s3 cp index.html s3://webapp-static-devopsprojcaws/

6. EC2 (SINGLE INSTANCE – TESTING PHASE)
Instance configuration

AMI: Amazon Linux

VPC: Custom VPC

Subnet: Public subnet

IAM Role: Attached

Security Group: HTTP + SSH

USER DATA SCRIPT (USED)
#!/bin/bash
yum update -y
yum install -y httpd amazon-efs-utils mysql

systemctl start httpd
systemctl enable httpd

aws s3 cp s3://webapp-static-devopsprojcaws/index.html /var/www/html/index.html

7. EBS VOLUME ATTACHMENT
Create EBS

Size: 5 GB

AZ: Same as EC2

Commands used
lsblk
sudo mkfs -t xfs /dev/xvdf
sudo mkdir /data
sudo mount /dev/xvdf /data
df -h

8. EFS (SHARED STORAGE)
On AWS Console

Created EFS in same VPC

Created mount targets in all AZs

Allowed NFS (2049) from EC2 SG

On EC2
sudo yum install -y amazon-efs-utils
sudo mkdir /efs
sudo mount -t efs fs-071589de16f9adaaa:/ /efs
df -h

9. APPLICATION LOAD BALANCER (ALB)

ALB created in public subnets

Listener: HTTP 80

Target group: Instance type

Health check path: /

10. LAUNCH TEMPLATE

Includes:

AMI

Instance type

IAM role

EC2 security group

User data script

11. AUTO SCALING GROUP (ASG)

Launch template attached

Subnets: Private subnets

Min: 1

Desired: 2

Max: 3

Attached to ALB target group

12. RDS MYSQL (PRIVATE SUBNET)
RDS setup

Engine: MySQL

Multi-AZ enabled

Public access: Disabled

DB subnet group: Private subnets

Security group: MySQL 3306 from EC2 SG only

MYSQL CLIENT INSTALL (ON EC2)
sudo dnf search mariadb
sudo dnf install mariadb105 -y
mysql --version


If not available:

sudo dnf install https://dev.mysql.com/get/mysql80-community-release-el9-1.noarch.rpm -y
sudo dnf install mysql-community-client --nogpgcheck -y
mysql --version

CONNECT TO RDS
mysql -h rds-mysql-private.cp2gocew6omt.ap-south-1.rds.amazonaws.com -u admin -p

DATABASE COMMANDS
CREATE DATABASE devopsdb;
SHOW DATABASES;
USE devopsdb;

CREATE TABLE users (
  id INT PRIMARY KEY,
  name VARCHAR(50)
);

SHOW TABLES;
INSERT INTO users VALUES (1,'ec2-one');
SELECT * FROM users;

13. FLASK APPLICATION (TEST HIGH AVAILABILITY)
Install packages
sudo dnf install python3 -y
sudo dnf install python3-pip -y
pip3 install flask pymysql


Verify:

python3 -c "import flask, pymysql; print('OK')"

app.py
from flask import Flask
import pymysql

app = Flask(__name__)

DB_HOST = "rds-mysql-private.cp2gocew6omt.ap-south-1.rds.amazonaws.com"
DB_USER = "admin"
DB_PASSWORD = "password"
DB_NAME = "devopsdb"

@app.route("/")
def home():
    return "Flask + RDS is working"

@app.route("/users")
def users():
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    data = cur.fetchall()
    conn.close()
    return str(data)

app.run(host="0.0.0.0", port=5000)


Run:

python3 app.py

14. HIGH AVAILABILITY TEST
Steps

Access app via ALB DNS

Terminate one EC2 manually

ASG launches new EC2

Database data unchanged

Test command on multiple EC2
USE devopsdb;
SELECT * FROM users;
exit;
