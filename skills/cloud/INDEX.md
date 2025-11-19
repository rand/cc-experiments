# Cloud Computing Skills

Comprehensive skills for AWS and Google Cloud Platform services, serverless computing, and cloud architecture.

## Category Overview

**Total Skills**: 13
**Focus**: AWS (7 skills), GCP (6 skills), Serverless, Infrastructure, Security
**Use Cases**: Cloud migrations, serverless applications, scalable architectures, multi-cloud deployments

## Skills in This Category

### AWS Skills (7 total)

#### aws/aws-lambda-functions.md
**Description**: AWS Lambda function development, runtime configuration, triggers, and optimization
**Lines**: ~350
**Use When**:
- Building serverless functions triggered by events
- Processing API requests without managing servers
- Implementing event-driven architectures with Lambda
- Optimizing Lambda cold start times and memory usage
- Configuring Lambda layers for shared dependencies
- Setting up triggers from API Gateway, S3, DynamoDB, SQS
- Managing Lambda concurrency and performance

**Key Concepts**: Lambda handlers, runtimes, layers, triggers, cold starts, concurrency, event sources

---

#### aws/aws-api-gateway.md
**Description**: AWS API Gateway REST APIs, HTTP APIs, WebSocket APIs, authorization, and integration patterns
**Lines**: ~300
**Use When**:
- Building REST APIs with Lambda backend
- Creating HTTP APIs for lower latency and cost
- Implementing WebSocket APIs for real-time communication
- Configuring API authorization (IAM, Lambda, Cognito, API keys)
- Setting up CORS for cross-origin requests
- Implementing API throttling and usage plans
- Integrating with Lambda, HTTP endpoints, or AWS services

**Key Concepts**: REST vs HTTP APIs, WebSocket, authorization, CORS, throttling, integrations, Lambda proxy

---

#### aws/aws-databases.md
**Description**: AWS database services - RDS, DynamoDB, ElastiCache, Aurora, migration, backup, and optimization
**Lines**: ~350
**Use When**:
- Deploying managed relational databases with RDS
- Building NoSQL applications with DynamoDB
- Implementing caching with ElastiCache (Redis/Memcached)
- Setting up Aurora Serverless for variable workloads
- Migrating databases to AWS
- Configuring database backups and point-in-time recovery
- Optimizing database performance and read replicas

**Key Concepts**: RDS, DynamoDB, ElastiCache, Aurora Serverless, DMS, backup strategies, performance tuning

---

#### aws/aws-iam-security.md
**Description**: AWS IAM policies, roles, Cognito authentication, Secrets Manager, KMS encryption, and security best practices
**Lines**: ~340
**Use When**:
- Creating IAM policies and roles for AWS services
- Implementing user authentication with Cognito
- Managing secrets with Secrets Manager or Parameter Store
- Configuring encryption with KMS
- Setting up temporary credentials with STS
- Implementing least privilege access control
- Troubleshooting permission errors or access denied issues

**Key Concepts**: IAM policies, roles, Cognito, Secrets Manager, KMS, STS, least privilege, credential management

---

#### aws/aws-storage.md
**Description**: AWS storage services - S3, EBS, EFS, Glacier, lifecycle policies, encryption, and data transfer
**Lines**: ~300
**Use When**:
- Storing objects, files, or backups in S3
- Attaching block storage to EC2 with EBS
- Sharing file systems across instances with EFS
- Archiving data long-term with Glacier
- Configuring S3 lifecycle policies for cost optimization
- Setting up S3 event notifications for processing
- Implementing encryption at rest and in transit

**Key Concepts**: S3 buckets, storage classes, EBS volumes, EFS, Glacier, lifecycle policies, S3 events

---

#### aws/aws-ec2-compute.md
**Description**: AWS EC2 instances, Auto Scaling, Load Balancing, AMIs, and instance lifecycle management
**Lines**: ~350
**Use When**:
- Deploying applications on EC2 instances
- Configuring Auto Scaling for dynamic capacity
- Setting up load balancers (ALB, NLB, CLB)
- Creating and managing AMIs for deployment
- Implementing immutable infrastructure patterns
- Optimizing compute costs with spot instances
- Configuring user data scripts for instance initialization

**Key Concepts**: EC2 instance types, Auto Scaling Groups, Elastic Load Balancing, AMIs, spot instances, user data

---

#### aws/aws-networking.md
**Description**: AWS networking - VPC, subnets, security groups, NACLs, Route53, CloudFront, Transit Gateway
**Lines**: ~320
**Use When**:
- Creating VPCs and subnet architecture
- Configuring security groups and network ACLs
- Setting up DNS with Route53 routing policies
- Implementing CDN with CloudFront
- Connecting multiple VPCs with Transit Gateway
- Setting up VPN or Direct Connect to on-premises
- Implementing network segmentation and isolation

**Key Concepts**: VPC, subnets, security groups, NACLs, Route53, CloudFront, Transit Gateway, VPN, Direct Connect

---

### GCP Skills (6 total)

#### gcp/gcp-serverless.md
**Description**: Google Cloud serverless services including Cloud Functions, Cloud Run, and App Engine
**Lines**: ~360
**Use When**:
- Building event-driven applications with Cloud Functions
- Deploying stateless containerized services with Cloud Run
- Running web applications and APIs on App Engine
- Choosing between serverless compute options
- Configuring triggers and event routing with Eventarc
- Scheduling tasks with Cloud Scheduler and Cloud Tasks
- Optimizing cold start performance and concurrency

**Key Concepts**: Cloud Functions, Cloud Run, App Engine, Eventarc, Cloud Scheduler, serverless patterns

---

#### gcp/gcp-compute.md
**Description**: Google Cloud compute services including Compute Engine, Cloud Run, and GKE
**Lines**: ~350
**Use When**:
- Deploying virtual machines on Google Cloud Platform
- Running containerized applications with Cloud Run
- Setting up Kubernetes clusters with GKE
- Optimizing compute costs with preemptible VMs or committed use discounts
- Configuring autoscaling for instance groups
- Choosing between serverless and VM-based workloads
- Managing SSH access and OS Login for instances

**Key Concepts**: Compute Engine, instance types, preemptible VMs, GKE basics, autoscaling, managed instance groups

---

#### gcp/gcp-databases.md
**Description**: Google Cloud managed database services including Cloud SQL, Firestore, Bigtable, and Spanner
**Lines**: ~340
**Use When**:
- Deploying relational databases with Cloud SQL (MySQL, PostgreSQL, SQL Server)
- Building applications with Firestore document database
- Designing wide-column NoSQL solutions with Bigtable
- Implementing globally distributed SQL databases with Spanner
- Setting up Redis or Memcached caching with Memorystore
- Migrating databases from on-premises or other clouds to GCP
- Configuring high availability, backups, and read replicas

**Key Concepts**: Cloud SQL, Firestore, Bigtable, Spanner, Memorystore, database migration, HA configuration

---

#### gcp/gcp-storage.md
**Description**: Google Cloud storage services including Cloud Storage, Persistent Disk, and Filestore
**Lines**: ~300
**Use When**:
- Storing objects in Cloud Storage buckets with different storage classes
- Attaching persistent disks to Compute Engine instances
- Setting up shared file storage with Filestore (NFS)
- Implementing object lifecycle management and retention policies
- Transferring large datasets to Google Cloud
- Configuring versioning, encryption, and access controls for storage
- Generating signed URLs for temporary access to private objects

**Key Concepts**: Cloud Storage, storage classes, Persistent Disk, Filestore, lifecycle policies, signed URLs

---

#### gcp/gcp-iam-security.md
**Description**: Google Cloud IAM, service accounts, Secret Manager, and Cloud KMS security practices
**Lines**: ~330
**Use When**:
- Configuring IAM roles and permissions for users and services
- Creating and managing service accounts for workloads
- Implementing authentication with Identity Platform
- Storing secrets and credentials in Secret Manager
- Managing encryption keys with Cloud KMS
- Setting up organization policies and constraints
- Implementing least privilege access control

**Key Concepts**: IAM roles, service accounts, Identity Platform, Secret Manager, Cloud KMS, organization policies

---

#### gcp/gcp-networking.md
**Description**: Google Cloud networking including VPC, firewall, DNS, CDN, and load balancing
**Lines**: ~320
**Use When**:
- Setting up VPC networks and subnets for GCP resources
- Configuring firewall rules and network security policies
- Implementing Cloud DNS for domain management
- Enabling Cloud CDN for content delivery and caching
- Deploying load balancers for high availability and scaling
- Connecting on-premises networks via VPN or Cloud Interconnect
- Optimizing network performance and reducing egress costs

**Key Concepts**: VPC networks, firewall rules, Cloud DNS, Cloud CDN, load balancing, VPN, Cloud Interconnect

---

## Common Workflows

### Serverless Web Application (AWS)
**Goal**: Build a serverless full-stack application on AWS

**Sequence**:
1. `aws/aws-lambda-functions.md` - Implement Lambda functions for backend logic
2. `aws/aws-api-gateway.md` - Create REST or HTTP API endpoints
3. `aws/aws-databases.md` - Set up DynamoDB for data storage
4. `aws/aws-iam-security.md` - Configure IAM roles and Cognito auth
5. `aws/aws-storage.md` - Store static assets in S3 with CloudFront

**Example**: Serverless blog platform with authentication

---

### Serverless Web Application (GCP)
**Goal**: Build a serverless full-stack application on GCP

**Sequence**:
1. `gcp/gcp-serverless.md` - Deploy Cloud Functions or Cloud Run services
2. `gcp/gcp-databases.md` - Set up Firestore for data storage
3. `gcp/gcp-iam-security.md` - Configure service accounts and Identity Platform
4. `gcp/gcp-storage.md` - Serve static content from Cloud Storage
5. `gcp/gcp-networking.md` - Set up Cloud CDN and load balancing

**Example**: Real-time collaboration platform

---

### Containerized Microservices (AWS)
**Goal**: Deploy microservices on AWS with containers

**Sequence**:
1. `aws/aws-ec2-compute.md` - Set up ECS or EKS cluster
2. `aws/aws-networking.md` - Configure VPC, subnets, and load balancers
3. `aws/aws-databases.md` - Deploy RDS or Aurora for persistence
4. `aws/aws-iam-security.md` - Implement IAM roles for services
5. `aws/aws-api-gateway.md` - Add API Gateway for external access

**Example**: E-commerce platform with multiple services

---

### Containerized Microservices (GCP)
**Goal**: Deploy microservices on GCP with containers

**Sequence**:
1. `gcp/gcp-compute.md` - Set up GKE cluster or Cloud Run services
2. `gcp/gcp-networking.md` - Configure VPC, firewall, and load balancing
3. `gcp/gcp-databases.md` - Deploy Cloud SQL or Spanner
4. `gcp/gcp-iam-security.md` - Set up service accounts and workload identity
5. `gcp/gcp-storage.md` - Configure persistent storage and backups

**Example**: Multi-tenant SaaS application

---

### Data Pipeline (AWS)
**Goal**: Build a data processing pipeline on AWS

**Sequence**:
1. `aws/aws-lambda-functions.md` - Process data with Lambda functions
2. `aws/aws-storage.md` - Use S3 for data lake storage
3. `aws/aws-databases.md` - Store results in RDS or DynamoDB
4. `aws/aws-iam-security.md` - Secure data access with IAM
5. `aws/aws-api-gateway.md` - Expose data via API

**Example**: Real-time analytics platform

---

### Multi-Cloud Strategy
**Goal**: Design for multi-cloud deployment

**Sequence**:
1. Compare AWS and GCP compute options
2. Evaluate database services for compatibility
3. Design portable IAM and security policies
4. Plan networking and VPN connectivity
5. Implement abstraction layers for cloud-specific services

**Example**: High-availability system with cloud failover

---

## Skill Combinations

### With API Skills (`discover-api`)
- Serverless REST APIs with Lambda or Cloud Functions
- API Gateway integration patterns
- GraphQL resolvers on serverless
- API authentication with cloud identity services

**Common combos**:
- `aws/aws-lambda-functions.md` + `api/rest-api-design.md`
- `gcp/gcp-serverless.md` + `api/graphql-schema-design.md`

---

### With Database Skills (`discover-database`)
- Cloud-managed databases vs self-hosted
- Database migration to cloud
- Replication and backup strategies
- Connection pooling for serverless

**Common combos**:
- `aws/aws-databases.md` + `database/postgres-query-optimization.md`
- `gcp/gcp-databases.md` + `database/mongodb-schema-design.md`

---

### With Container Skills (`discover-containers`)
- Container orchestration on cloud (ECS, EKS, GKE)
- Serverless containers (Lambda, Cloud Run)
- Container registries and security
- Auto-scaling containerized apps

**Common combos**:
- `aws/aws-ec2-compute.md` + `containers/kubernetes-deployment.md`
- `gcp/gcp-compute.md` + `containers/docker-best-practices.md`

---

### With Infrastructure Skills (`discover-infrastructure`)
- Infrastructure as Code (Terraform, CloudFormation)
- Cost optimization strategies
- Multi-region deployments
- Disaster recovery planning

**Common combos**:
- `aws/aws-networking.md` + `infrastructure/terraform-patterns.md`
- `gcp/gcp-iam-security.md` + `infrastructure/infrastructure-security.md`

---

### With CI/CD Skills (`discover-cicd`)
- Deployment pipelines for cloud services
- Serverless deployment automation
- Blue-green and canary deployments
- Infrastructure testing

**Common combos**:
- `aws/aws-lambda-functions.md` + `cicd/github-actions-workflows.md`
- `gcp/gcp-serverless.md` + `cicd/deployment-strategies.md`

---

## Quick Selection Guide

**AWS vs GCP - When to Choose**:

**Choose AWS when**:
- Need widest service selection
- Require specific AWS services (SageMaker, Athena, etc.)
- Enterprise with existing AWS infrastructure
- Need mature third-party integrations
- Want detailed billing and cost management

**Choose GCP when**:
- Need strong Kubernetes integration (GKE)
- Want simpler networking model
- Require BigQuery for analytics
- Prefer cleaner, more consistent APIs
- Need competitive pricing on compute and networking

**Multi-cloud when**:
- Avoiding vendor lock-in is critical
- Need geographic coverage across providers
- Regulatory requirements mandate redundancy
- Leveraging best-of-breed services from each

---

**Serverless vs Compute**:

**Choose Serverless (Lambda/Cloud Functions) when**:
- Variable or unpredictable traffic
- Event-driven architectures
- Want zero server management
- Need automatic scaling
- Cost optimization for low traffic

**Choose Compute (EC2/Compute Engine) when**:
- Predictable, steady workloads
- Need full control over environment
- Running legacy or stateful applications
- Require specific OS or kernel customization
- Cost optimization for high utilization

**Choose Containers (ECS/GKE/Cloud Run) when**:
- Need portability across environments
- Complex microservices architectures
- Want orchestration capabilities
- Balancing control and automation
- Hybrid serverless-compute workloads

---

**Database Selection**:

**Relational (RDS/Cloud SQL)**:
- ACID transactions required
- Complex queries and joins
- Existing SQL applications
- Strong consistency needed

**NoSQL (DynamoDB/Firestore)**:
- Need horizontal scaling
- Flexible schema requirements
- Key-value or document access patterns
- Low-latency at scale

**Global (Aurora/Spanner)**:
- Multi-region active-active
- Global consistency
- High availability requirements
- Massive scale with SQL

---

## Loading Skills

All AWS skills:
```bash
cat skills/cloud/aws/aws-lambda-functions.md
cat skills/cloud/aws/aws-api-gateway.md
cat skills/cloud/aws/aws-databases.md
cat skills/cloud/aws/aws-iam-security.md
cat skills/cloud/aws/aws-storage.md
cat skills/cloud/aws/aws-ec2-compute.md
cat skills/cloud/aws/aws-networking.md
```

All GCP skills:
```bash
cat skills/cloud/gcp/gcp-serverless.md
cat skills/cloud/gcp/gcp-compute.md
cat skills/cloud/gcp/gcp-databases.md
cat skills/cloud/gcp/gcp-storage.md
cat skills/cloud/gcp/gcp-iam-security.md
cat skills/cloud/gcp/gcp-networking.md
```

**Pro tip**: Start with compute options (serverless vs VMs), then add storage, databases, networking, and security in layers.

---

**Related Categories**:
- `discover-api` - API design and implementation
- `discover-database` - Database design and optimization
- `discover-containers` - Docker and Kubernetes
- `discover-infrastructure` - Infrastructure as Code
- `discover-cicd` - Deployment automation
- `discover-observability` - Monitoring and logging
- `discover-networking` - Network protocols and optimization
