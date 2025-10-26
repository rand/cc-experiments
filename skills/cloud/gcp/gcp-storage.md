---
name: cloud-gcp-storage
description: Google Cloud storage services including Cloud Storage, Persistent Disk, and Filestore
---

# GCP Storage Services

**Scope**: Cloud Storage buckets, Persistent Disk, Filestore, and data transfer tools
**Lines**: ~300
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Storing objects in Cloud Storage buckets with different storage classes
- Attaching persistent disks to Compute Engine instances
- Setting up shared file storage with Filestore (NFS)
- Implementing object lifecycle management and retention policies
- Transferring large datasets to Google Cloud
- Configuring versioning, encryption, and access controls for storage
- Optimizing storage costs with appropriate storage classes
- Generating signed URLs for temporary access to private objects

## Core Concepts

### Concept 1: Cloud Storage Classes

**Storage tiers**:
- **Standard**: Hot data, frequent access, no minimum storage duration
- **Nearline**: Accessed <1/month, 30-day minimum, backups, disaster recovery
- **Coldline**: Accessed <1/quarter, 90-day minimum, archival data
- **Archive**: Accessed <1/year, 365-day minimum, long-term compliance

```bash
# Create bucket with Standard storage class
gsutil mb -c STANDARD -l us-central1 gs://my-app-data

# Create bucket with Nearline for backups
gsutil mb -c NEARLINE -l us-central1 gs://my-backups

# Upload file to specific storage class
gsutil -h "x-goog-storage-class:COLDLINE" cp archive.tar.gz gs://my-archives/

# Change storage class of existing object
gsutil rewrite -s ARCHIVE gs://my-backups/old-backup.tar.gz
```

### Concept 2: Persistent Disk Types

**Disk options**:
- **pd-standard** (HDD): Bulk storage, sequential I/O, lowest cost
- **pd-balanced** (SSD): Balanced price/performance, most workloads
- **pd-ssd**: High IOPS, low latency, databases
- **pd-extreme**: Highest performance, customizable IOPS

```python
from google.cloud import compute_v1

def create_instance_with_disk(project_id, zone, instance_name):
    client = compute_v1.InstancesClient()

    # Create instance with balanced persistent disk
    instance = compute_v1.Instance(
        name=instance_name,
        machine_type=f"zones/{zone}/machineTypes/n2-standard-4",
        disks=[
            # Boot disk (pd-balanced, 20GB)
            compute_v1.AttachedDisk(
                auto_delete=True,
                boot=True,
                initialize_params=compute_v1.AttachedDiskInitializeParams(
                    source_image="projects/debian-cloud/global/images/family/debian-11",
                    disk_size_gb=20,
                    disk_type=f"zones/{zone}/diskTypes/pd-balanced"
                )
            ),
            # Data disk (pd-ssd, 500GB)
            compute_v1.AttachedDisk(
                auto_delete=False,  # Preserve disk after instance deletion
                initialize_params=compute_v1.AttachedDiskInitializeParams(
                    disk_size_gb=500,
                    disk_type=f"zones/{zone}/diskTypes/pd-ssd"
                )
            )
        ],
        network_interfaces=[
            compute_v1.NetworkInterface(
                network="global/networks/default"
            )
        ]
    )

    operation = client.insert(project=project_id, zone=zone, instance_resource=instance)
    return operation.result()
```

### Concept 3: Object Lifecycle Management

**Lifecycle actions**:
- **SetStorageClass**: Transition to cheaper storage class after time
- **Delete**: Remove objects after expiration
- Conditions: age, created_before, number_of_newer_versions

```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 30}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 365}
      }
    ]
  }
}
```

```bash
# Apply lifecycle policy to bucket
gsutil lifecycle set lifecycle.json gs://my-bucket
```

---

## Patterns

### Pattern 1: Versioning with Retention Policy

**When to use**:
- Protect against accidental deletion or overwrite
- Meet compliance requirements for data retention

```bash
# ❌ Bad: No versioning, data can be permanently lost
gsutil mb gs://critical-data
# Accidental overwrite loses data permanently

# ✅ Good: Enable versioning with retention policy
gsutil mb gs://critical-data
gsutil versioning set on gs://critical-data

# Set retention policy (data cannot be deleted for 7 years)
gsutil retention set 7y gs://critical-data

# Lock retention policy (irreversible - use carefully!)
gsutil retention lock gs://critical-data
```

**Benefits**:
- Recover from accidental deletion or corruption
- Compliance with regulations (HIPAA, FINRA, etc.)
- Immutable storage for audit logs

### Pattern 2: Regional Persistent Disk for HA

**Use case**: Database high availability across zones in a region

```bash
# Create regional persistent disk (replicated across 2 zones)
gcloud compute disks create db-disk \
  --size=500GB \
  --type=pd-ssd \
  --region=us-central1 \
  --replica-zones=us-central1-a,us-central1-b

# Attach to instance in zone A
gcloud compute instances attach-disk db-primary \
  --disk=db-disk \
  --zone=us-central1-a

# If instance fails, disk can be attached to instance in zone B
gcloud compute instances detach-disk db-primary \
  --disk=db-disk \
  --zone=us-central1-a

gcloud compute instances attach-disk db-secondary \
  --disk=db-disk \
  --zone=us-central1-b
```

### Pattern 3: Signed URLs for Temporary Access

**Use case**: Grant time-limited access to private objects without IAM changes

```python
from google.cloud import storage
from datetime import timedelta

def generate_signed_url(bucket_name, blob_name, expiration_minutes=15):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # Generate signed URL valid for 15 minutes
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expiration_minutes),
        method="GET"
    )

    return url

# Example usage
url = generate_signed_url("private-reports", "report-2025-10.pdf")
# Share URL with user - valid for 15 minutes, no authentication needed
```

### Pattern 4: Resumable Uploads for Large Files

**Use case**: Upload large files with automatic retry on network interruption

```python
from google.cloud import storage

def resumable_upload(bucket_name, source_file, destination_blob):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)

    # Enable resumable upload (automatic for files >5MB)
    # If upload fails, it automatically resumes from where it left off
    blob.upload_from_filename(
        source_file,
        timeout=3600  # 1 hour timeout for large files
    )

    print(f"Uploaded {source_file} to gs://{bucket_name}/{destination_blob}")

# Upload 10GB file - automatically handles interruptions
resumable_upload("my-bucket", "/data/large-dataset.tar.gz", "datasets/2025-10.tar.gz")
```

### Pattern 5: Filestore for Shared NFS Storage

**Use case**: Multiple VMs need access to shared file system

```bash
# Create Filestore instance (1TB, BASIC_HDD tier)
gcloud filestore instances create shared-storage \
  --location=us-central1-a \
  --tier=BASIC_HDD \
  --file-share=name=data,capacity=1TB \
  --network=name=default

# Mount on Compute Engine instance
sudo apt-get install nfs-common
sudo mkdir -p /mnt/shared
sudo mount 10.0.0.2:/data /mnt/shared  # Use IP from filestore instance

# Add to /etc/fstab for automatic mounting
echo "10.0.0.2:/data /mnt/shared nfs defaults 0 0" | sudo tee -a /etc/fstab
```

### Pattern 6: Storage Transfer Service

**Use case**: Migrate large datasets from S3, Azure, or on-premises to Cloud Storage

```bash
# Create transfer job from AWS S3 to Cloud Storage
gcloud transfer jobs create s3://source-bucket gs://dest-bucket \
  --source-creds-file=aws-creds.json \
  --description="Migrate production data" \
  --schedule-starts=2025-10-25T00:00:00Z \
  --schedule-repeats-every=24h \
  --delete-from-source-after-transfer  # Optional: clean up source

# Monitor transfer job
gcloud transfer operations list --job-names=projects/PROJECT/transferJobs/JOB
```

### Pattern 7: Customer-Managed Encryption Keys (CMEK)

**Use case**: Control encryption keys for compliance requirements

```bash
# Create Cloud KMS key ring and key
gcloud kms keyrings create my-keyring --location=us-central1
gcloud kms keys create storage-key \
  --keyring=my-keyring \
  --location=us-central1 \
  --purpose=encryption

# Create bucket with CMEK
gsutil mb \
  -p my-project \
  -c STANDARD \
  -l us-central1 \
  -k projects/my-project/locations/us-central1/keyRings/my-keyring/cryptoKeys/storage-key \
  gs://encrypted-bucket

# Upload object with CMEK
gsutil -o "GSUtil:encryption_key=..." cp file.txt gs://encrypted-bucket/
```

### Pattern 8: Disk Snapshots for Backup

**Use case**: Create point-in-time backups of persistent disks

```bash
# Create snapshot of persistent disk
gcloud compute disks snapshot data-disk \
  --snapshot-names=data-disk-2025-10-25 \
  --zone=us-central1-a \
  --storage-location=us-central1

# Create snapshot schedule for automatic backups
gcloud compute resource-policies create snapshot-schedule daily-backup \
  --region=us-central1 \
  --max-retention-days=7 \
  --on-source-disk-delete=keep-auto-snapshots \
  --daily-schedule \
  --start-time=02:00

# Attach schedule to disk
gcloud compute disks add-resource-policies data-disk \
  --resource-policies=daily-backup \
  --zone=us-central1-a

# Restore from snapshot
gcloud compute disks create restored-disk \
  --source-snapshot=data-disk-2025-10-25 \
  --zone=us-central1-a
```

---

## Quick Reference

### Storage Service Comparison

```
Service         | Type      | Use Case                  | Access       | Cost
----------------|-----------|---------------------------|--------------|-------
Cloud Storage   | Object    | Unstructured data, media  | HTTP/gsutil  | $0.020-0.012/GB/mo
Persistent Disk | Block     | VM attached storage       | VM only      | $0.040-0.170/GB/mo
Filestore       | File/NFS  | Shared filesystem         | NFS mount    | $0.20-0.30/GB/mo
```

### Storage Class Pricing (Standard region)

```
Class     | Storage $/GB/mo | Retrieval $/GB | Minimum Duration
----------|-----------------|----------------|------------------
Standard  | $0.020          | Free           | None
Nearline  | $0.010          | $0.01          | 30 days
Coldline  | $0.004          | $0.02          | 90 days
Archive   | $0.0012         | $0.05          | 365 days
```

### Key gsutil Commands

```bash
# Bucket operations
gsutil mb -c STANDARD -l LOCATION gs://BUCKET
gsutil ls gs://BUCKET
gsutil du -s gs://BUCKET  # Check size
gsutil rm -r gs://BUCKET

# Object operations
gsutil cp LOCAL gs://BUCKET/
gsutil cp gs://BUCKET/file .
gsutil mv gs://BUCKET/old gs://BUCKET/new
gsutil rm gs://BUCKET/file

# Parallel uploads (faster for many files)
gsutil -m cp -r /local/dir gs://BUCKET/

# Set metadata
gsutil setmeta -h "Cache-Control:public,max-age=3600" gs://BUCKET/file
```

### Key Guidelines

```
✅ DO: Use lifecycle policies to transition to cheaper storage classes
✅ DO: Enable versioning for critical data
✅ DO: Use regional persistent disks for database high availability
✅ DO: Implement retention policies for compliance requirements
✅ DO: Use signed URLs instead of making objects public
✅ DO: Choose appropriate storage class based on access frequency

❌ DON'T: Store frequently accessed data in Archive class (expensive retrieval)
❌ DON'T: Use Filestore for object storage (use Cloud Storage instead)
❌ DON'T: Attach persistent disks to multiple VMs in read-write mode (data corruption)
❌ DON'T: Delete snapshots needed for disaster recovery
❌ DON'T: Use pd-extreme unless you've confirmed IOPS requirements
```

---

## Anti-Patterns

### Critical Violations

```bash
# ❌ NEVER: Lock retention policy without careful consideration
gsutil retention lock gs://bucket  # IRREVERSIBLE - cannot be unlocked!

# ✅ CORRECT: Test retention policy first, then lock only if required by compliance
gsutil retention set 7y gs://bucket
# Verify policy works as expected for several months
# Only lock if legally required:
# gsutil retention lock gs://bucket
```

❌ **Premature retention lock**: Locking a retention policy is permanent. You cannot delete the bucket or objects until retention period expires, even if you delete the project.
✅ **Correct approach**: Test retention policies thoroughly before locking. Only lock if required by compliance regulations.

### Common Mistakes

```python
# ❌ Don't: Use Archive class for frequently accessed data
bucket = storage_client.bucket("user-uploads")
blob = bucket.blob("profile.jpg")
blob.upload_from_filename("profile.jpg")
blob.update_storage_class("ARCHIVE")  # $0.05/GB retrieval cost!

# ✅ Correct: Use Standard class for hot data, lifecycle policy for cold data
blob.upload_from_filename("profile.jpg")
# Let lifecycle policy transition to cheaper class after 90 days
```

❌ **Wrong storage class**: Using Archive class for frequently accessed data results in high retrieval costs that exceed storage savings.
✅ **Better**: Use Standard for hot data, Nearline for warm, Coldline/Archive for cold. Use lifecycle policies to automate transitions.

```bash
# ❌ Don't: Attach persistent disk to multiple instances in read-write mode
gcloud compute instances attach-disk vm-1 --disk=shared-disk --mode=rw
gcloud compute instances attach-disk vm-2 --disk=shared-disk --mode=rw
# Results in data corruption!

# ✅ Correct: Use Filestore for shared read-write access
gcloud filestore instances create shared-storage \
  --location=us-central1-a \
  --tier=BASIC_HDD \
  --file-share=name=data,capacity=1TB \
  --network=name=default
```

❌ **Multi-attach read-write**: Attaching a persistent disk to multiple VMs in read-write mode causes data corruption.
✅ **Better**: Use Filestore (NFS) for shared file access, or attach disk in read-only mode to additional VMs.

```bash
# ❌ Don't: Delete original snapshots when using incremental snapshots
gcloud compute snapshots delete snapshot-1  # Breaks snapshot chain!

# ✅ Correct: Keep base snapshot or understand incremental chain
# Snapshots are incremental - deleting old snapshots is safe
# GCP automatically maintains snapshot chain integrity
gcloud compute snapshots delete snapshot-1  # Actually safe - GCP handles dependencies
```

❌ **Snapshot chain confusion**: GCP snapshots are incremental but deleting old snapshots is safe because GCP automatically consolidates data.
✅ **Better**: Understand that GCP manages snapshot dependencies. Use snapshot schedules with retention policies to automate cleanup.

---

## Related Skills

- `gcp-compute.md` - Attaching persistent disks to Compute Engine instances
- `gcp-iam-security.md` - Bucket IAM policies and service account access
- `gcp-databases.md` - Persistent disk configuration for database workloads
- `gcp-networking.md` - Private Google Access for storage without public IPs

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
