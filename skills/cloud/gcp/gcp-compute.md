---
name: cloud-gcp-compute
description: Google Cloud compute services including Compute Engine, Cloud Run, and GKE
---

# GCP Compute Services

**Scope**: Compute Engine VMs, Cloud Run serverless containers, and GKE basics
**Lines**: ~350
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Deploying virtual machines on Google Cloud Platform
- Running containerized applications with Cloud Run
- Setting up Kubernetes clusters with GKE
- Optimizing compute costs with preemptible VMs or committed use discounts
- Configuring autoscaling for instance groups
- Choosing between serverless and VM-based workloads
- Migrating workloads from on-premises to GCP compute
- Managing SSH access and OS Login for instances

## Core Concepts

### Concept 1: Compute Engine Instance Types

**Machine families**:
- **General-purpose** (E2, N2, N2D, N1): Balanced CPU/memory for most workloads
- **Compute-optimized** (C2, C2D): High CPU performance for compute-intensive tasks
- **Memory-optimized** (M2, M1): High memory for in-memory databases and analytics
- **Accelerator-optimized** (A2): GPU workloads for ML and HPC

```bash
# Create a general-purpose VM with sustained use discount benefits
gcloud compute instances create web-server \
  --machine-type=n2-standard-4 \
  --zone=us-central1-a \
  --image-family=debian-11 \
  --image-project=debian-cloud \
  --boot-disk-size=20GB \
  --boot-disk-type=pd-balanced

# Create a preemptible VM for cost savings (up to 80% cheaper)
gcloud compute instances create batch-processor \
  --machine-type=e2-standard-8 \
  --zone=us-central1-a \
  --preemptible \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud
```

### Concept 2: Cloud Run Serverless Containers

**Key features**:
- Fully managed serverless platform for stateless containers
- Automatic scaling from 0 to N instances based on traffic
- Pay only for actual request processing time (100ms granularity)
- Built-in traffic splitting for gradual rollouts

```python
# Deploy a container to Cloud Run using Python client
from google.cloud import run_v2

def deploy_cloud_run_service(project_id, service_name, image_url, region="us-central1"):
    client = run_v2.ServicesClient()

    service = run_v2.Service(
        name=f"projects/{project_id}/locations/{region}/services/{service_name}",
        template=run_v2.RevisionTemplate(
            containers=[run_v2.Container(
                image=image_url,
                resources=run_v2.ResourceRequirements(
                    limits={"cpu": "1", "memory": "512Mi"}
                ),
                ports=[run_v2.ContainerPort(container_port=8080)]
            )],
            scaling=run_v2.RevisionScaling(
                min_instance_count=0,
                max_instance_count=100
            )
        )
    )

    request = run_v2.CreateServiceRequest(
        parent=f"projects/{project_id}/locations/{region}",
        service=service,
        service_id=service_name
    )

    operation = client.create_service(request=request)
    return operation.result()
```

### Concept 3: GKE Cluster Modes

**Autopilot vs Standard**:
- **Autopilot**: Fully managed, GKE manages nodes, optimizes resources, enforces best practices
- **Standard**: User manages node pools, custom machine types, full control over configuration

```bash
# Create an Autopilot cluster (recommended for most use cases)
gcloud container clusters create-auto prod-cluster \
  --region=us-central1 \
  --release-channel=regular

# Create a Standard cluster with custom node pool
gcloud container clusters create custom-cluster \
  --zone=us-central1-a \
  --num-nodes=3 \
  --machine-type=n2-standard-4 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10
```

---

## Patterns

### Pattern 1: Instance Templates and Managed Instance Groups

**When to use**:
- Need to create multiple identical VMs
- Require autoscaling based on load
- Want to distribute instances across zones for high availability

```bash
# ❌ Bad: Creating VMs one at a time manually
gcloud compute instances create vm-1 --machine-type=n2-standard-2 --zone=us-central1-a
gcloud compute instances create vm-2 --machine-type=n2-standard-2 --zone=us-central1-a
# ... error-prone and not scalable

# ✅ Good: Use instance template and managed instance group
# Create instance template
gcloud compute instance-templates create web-template \
  --machine-type=n2-standard-2 \
  --image-family=debian-11 \
  --image-project=debian-cloud \
  --metadata=startup-script='#!/bin/bash
    apt-get update
    apt-get install -y nginx
    systemctl start nginx'

# Create managed instance group with autoscaling
gcloud compute instance-groups managed create web-mig \
  --base-instance-name=web \
  --template=web-template \
  --size=3 \
  --zone=us-central1-a

gcloud compute instance-groups managed set-autoscaling web-mig \
  --zone=us-central1-a \
  --max-num-replicas=10 \
  --min-num-replicas=2 \
  --target-cpu-utilization=0.6
```

**Benefits**:
- Consistent VM configuration across all instances
- Automatic healing replaces unhealthy instances
- Seamless autoscaling based on metrics

### Pattern 2: Cloud Run Traffic Splitting

**Use case**: Gradual rollout of new application versions with instant rollback capability

```bash
# Deploy revision 1
gcloud run deploy api-service \
  --image=gcr.io/project/api:v1 \
  --region=us-central1 \
  --tag=v1

# Deploy revision 2
gcloud run deploy api-service \
  --image=gcr.io/project/api:v2 \
  --region=us-central1 \
  --tag=v2 \
  --no-traffic  # Don't send traffic to new revision yet

# Split traffic: 90% to v1, 10% to v2 (canary deployment)
gcloud run services update-traffic api-service \
  --region=us-central1 \
  --to-revisions=v1=90,v2=10

# After validation, shift all traffic to v2
gcloud run services update-traffic api-service \
  --region=us-central1 \
  --to-latest
```

### Pattern 3: Preemptible VM with Shutdown Script

**Use case**: Run batch jobs on low-cost preemptible VMs with graceful shutdown

```python
from google.cloud import compute_v1

def create_preemptible_instance(project_id, zone, instance_name):
    client = compute_v1.InstancesClient()

    # Shutdown script to save state before preemption
    shutdown_script = """#!/bin/bash
    echo "Instance preempted, saving state..."
    gsutil cp /tmp/job_state.json gs://my-bucket/checkpoints/
    """

    instance = compute_v1.Instance(
        name=instance_name,
        machine_type=f"zones/{zone}/machineTypes/n2-standard-4",
        scheduling=compute_v1.Scheduling(
            preemptible=True,
            automatic_restart=False,
            on_host_maintenance="TERMINATE"
        ),
        disks=[
            compute_v1.AttachedDisk(
                auto_delete=True,
                boot=True,
                initialize_params=compute_v1.AttachedDiskInitializeParams(
                    source_image="projects/debian-cloud/global/images/family/debian-11"
                )
            )
        ],
        metadata=compute_v1.Metadata(
            items=[
                compute_v1.Items(key="shutdown-script", value=shutdown_script)
            ]
        ),
        network_interfaces=[
            compute_v1.NetworkInterface(
                network="global/networks/default",
                access_configs=[
                    compute_v1.AccessConfig(name="External NAT", type_="ONE_TO_ONE_NAT")
                ]
            )
        ]
    )

    operation = client.insert(project=project_id, zone=zone, instance_resource=instance)
    return operation
```

### Pattern 4: Regional Managed Instance Groups

**Use case**: High availability across multiple zones in a region

```bash
# Create regional MIG for automatic zone distribution
gcloud compute instance-groups managed create web-regional-mig \
  --base-instance-name=web \
  --template=web-template \
  --size=6 \
  --region=us-central1 \
  --target-distribution-shape=EVEN

# GCP automatically distributes instances:
# 2 in us-central1-a, 2 in us-central1-b, 2 in us-central1-c
```

### Pattern 5: Cloud Run with Secrets and Environment Variables

**Use case**: Securely inject configuration and secrets into Cloud Run services

```bash
# Create secret in Secret Manager
echo -n "my-database-password" | gcloud secrets create db-password \
  --data-file=- \
  --replication-policy=automatic

# Deploy Cloud Run with secret and environment variable
gcloud run deploy api-service \
  --image=gcr.io/project/api:latest \
  --region=us-central1 \
  --set-env-vars=DATABASE_URL=postgresql://host/db \
  --set-secrets=DB_PASSWORD=db-password:latest
```

### Pattern 6: OS Login for Centralized SSH Access

**Use case**: Manage SSH access using IAM instead of managing individual SSH keys

```bash
# Enable OS Login on a project
gcloud compute project-info add-metadata \
  --metadata enable-oslogin=TRUE

# Grant user SSH access via IAM
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=user:alice@example.com \
  --role=roles/compute.osLogin

# SSH using OS Login (no SSH keys needed)
gcloud compute ssh instance-name --zone=us-central1-a

# For sudo access, grant osAdminLogin role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=user:bob@example.com \
  --role=roles/compute.osAdminLogin
```

### Pattern 7: Committed Use Discounts

**Use case**: Save up to 57% for predictable workloads with 1 or 3 year commitments

```bash
# Purchase committed use contract for compute resources
gcloud compute commitments create web-commitment \
  --region=us-central1 \
  --plan=12-month \
  --resources=vcpu=100,memory=400GB

# View active commitments
gcloud compute commitments list

# Instances automatically benefit from commitment pricing
# when they match committed resource types
```

### Pattern 8: GKE Workload Identity

**Use case**: Allow Kubernetes pods to authenticate as GCP service accounts

```bash
# Create GKE cluster with Workload Identity enabled
gcloud container clusters create prod-cluster \
  --workload-pool=PROJECT_ID.svc.id.goog \
  --zone=us-central1-a

# Create Kubernetes service account
kubectl create serviceaccount app-sa

# Create GCP service account
gcloud iam service-accounts create app-gsa

# Bind Kubernetes SA to GCP SA
gcloud iam service-accounts add-iam-policy-binding app-gsa@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[default/app-sa]"

# Annotate Kubernetes service account
kubectl annotate serviceaccount app-sa \
  iam.gke.io/gcp-service-account=app-gsa@PROJECT_ID.iam.gserviceaccount.com
```

---

## Quick Reference

### Compute Service Comparison

```
Service         | Use Case                    | Scaling          | Cost Model
----------------|----------------------------|------------------|------------------
Compute Engine  | VMs, custom OS, full ctrl  | Manual/Auto MIG  | Per second
Cloud Run       | Stateless containers       | Auto 0 to N      | Per 100ms request
GKE Autopilot   | Kubernetes, managed nodes  | Auto pod scaling | Per pod resources
GKE Standard    | Kubernetes, custom config  | Manual/Auto      | Per node hour
```

### Key gcloud Commands

```bash
# Compute Engine
gcloud compute instances create NAME --machine-type=TYPE --zone=ZONE
gcloud compute instances list
gcloud compute instances stop/start/delete NAME --zone=ZONE
gcloud compute ssh INSTANCE --zone=ZONE

# Cloud Run
gcloud run deploy SERVICE --image=IMAGE --region=REGION
gcloud run services list
gcloud run services delete SERVICE --region=REGION

# GKE
gcloud container clusters create CLUSTER --zone=ZONE
gcloud container clusters get-credentials CLUSTER --zone=ZONE
gcloud container clusters delete CLUSTER --zone=ZONE
```

### Key Guidelines

```
✅ DO: Use preemptible VMs for fault-tolerant batch workloads (up to 80% savings)
✅ DO: Enable OS Login for centralized SSH access management
✅ DO: Use regional MIGs for high availability across zones
✅ DO: Tag instances with network tags for firewall rules
✅ DO: Use startup scripts for automated instance configuration
✅ DO: Monitor sustained use discounts and consider committed use for stable workloads

❌ DON'T: Use preemptible VMs for stateful services without checkpointing
❌ DON'T: Create instances without considering machine type right-sizing
❌ DON'T: Leave unused instances running (set up alerts)
❌ DON'T: Use Cloud Run for long-running stateful processes
❌ DON'T: Ignore zone selection (affects latency and cost)
```

---

## Anti-Patterns

### Critical Violations

```bash
# ❌ NEVER: Run stateful databases on preemptible VMs without proper HA setup
gcloud compute instances create db-primary \
  --preemptible  # Database will be terminated within 24 hours!

# ✅ CORRECT: Use standard instances with regional persistent disks
gcloud compute instances create db-primary \
  --machine-type=n2-standard-8 \
  --zone=us-central1-a \
  --create-disk=size=500GB,type=pd-ssd,replica-zones=us-central1-b
```

❌ **Preemptible databases**: Preemptible VMs are terminated within 24 hours or on-demand. Running stateful services without checkpointing causes data loss.
✅ **Correct approach**: Use standard instances with regional persistent disks for automatic replication.

### Common Mistakes

```bash
# ❌ Don't: Use oversized machine types "just in case"
gcloud compute instances create web-server \
  --machine-type=n2-standard-32  # 32 vCPUs for a low-traffic web app!

# ✅ Correct: Right-size and use autoscaling
gcloud compute instances create web-server \
  --machine-type=e2-medium  # Start small, monitor, adjust
```

❌ **Over-provisioning**: Using oversized machine types wastes money and doesn't improve performance for most workloads.
✅ **Better**: Start with smaller machine types, monitor metrics, and scale up if needed.

```python
# ❌ Don't: Deploy Cloud Run without concurrency limits
# Default concurrency of 80 may overwhelm downstream services

# ✅ Correct: Set appropriate concurrency based on backend capacity
from google.cloud import run_v2

service = run_v2.Service(
    template=run_v2.RevisionTemplate(
        containers=[run_v2.Container(
            image="gcr.io/project/api:latest"
        )],
        max_instance_request_concurrency=10  # Limit concurrent requests per instance
    )
)
```

❌ **Unbounded concurrency**: Default Cloud Run concurrency can overwhelm databases or external APIs.
✅ **Better**: Set max concurrency based on backend capacity (e.g., database connection pool size).

```bash
# ❌ Don't: Ignore sustained use discounts when evaluating costs
# Manually calculating costs without considering automatic discounts

# ✅ Correct: Use Pricing Calculator and understand automatic discounts
# Sustained use: 20-30% automatic discount for running >25% of month
# Committed use: 57% discount for 3-year commitment
# Preemptible: 80% discount for interruptible workloads
```

❌ **Ignoring discounts**: Not accounting for sustained use discounts leads to inaccurate cost projections.
✅ **Better**: Use GCP Pricing Calculator and factor in automatic discounts for long-running workloads.

---

## Related Skills

- `gcp-storage.md` - Persistent disks and Cloud Storage for VM data persistence
- `gcp-networking.md` - VPC configuration and load balancing for compute instances
- `gcp-iam-security.md` - Service accounts and IAM roles for compute resources
- `gcp-serverless.md` - Cloud Functions and App Engine as compute alternatives
- `gcp-databases.md` - Managed databases that integrate with compute services

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
