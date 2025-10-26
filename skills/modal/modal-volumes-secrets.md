---
name: modal-volumes-secrets
description: Persisting data across function invocations
---



# Modal Volumes and Secrets

**Use this skill when:**
- Persisting data across function invocations
- Storing model weights and large files
- Managing API keys and credentials
- Sharing data between Modal functions
- Implementing caching strategies

## Volumes

### Creating Volumes

Define persistent storage:

```python
import modal

app = modal.App("volume-app")

# Create volume
volume = modal.Volume.from_name("my-data", create_if_missing=True)

@app.function(volumes={"/data": volume})
def write_data():
    with open("/data/file.txt", "w") as f:
        f.write("Hello, World!")

    # Commit changes to persist them
    volume.commit()

    return "Data written"

@app.function(volumes={"/data": volume})
def read_data():
    with open("/data/file.txt", "r") as f:
        content = f.read()

    return content
```

### Volume Patterns

Common volume usage patterns:

```python
# Model storage
model_volume = modal.Volume.from_name("models", create_if_missing=True)

@app.function(volumes={"/models": model_volume})
def download_model():
    import torch
    from transformers import AutoModel

    model = AutoModel.from_pretrained("bert-base-uncased")
    model.save_pretrained("/models/bert")

    model_volume.commit()

@app.function(volumes={"/models": model_volume})
def use_model():
    from transformers import AutoModel

    model = AutoModel.from_pretrained("/models/bert")
    return "Model loaded"

# Cache storage
cache_volume = modal.Volume.from_name("cache", create_if_missing=True)

@app.function(volumes={"/cache": cache_volume})
def cache_data(key: str, value: str):
    with open(f"/cache/{key}", "w") as f:
        f.write(value)

    cache_volume.commit()

@app.function(volumes={"/cache": cache_volume})
def get_cached(key: str):
    try:
        with open(f"/cache/{key}", "r") as f:
            return f.read()
    except FileNotFoundError:
        return None
```

### Large File Handling

Store and retrieve large files:

```python
data_volume = modal.Volume.from_name("datasets", create_if_missing=True)

@app.function(volumes={"/datasets": data_volume}, timeout=3600)
def download_dataset():
    import urllib.request

    url = "https://example.com/large-dataset.zip"
    urllib.request.urlretrieve(url, "/datasets/dataset.zip")

    # Unzip
    import zipfile
    with zipfile.ZipFile("/datasets/dataset.zip", "r") as zip_ref:
        zip_ref.extractall("/datasets/data")

    data_volume.commit()

    return "Dataset downloaded"

@app.function(volumes={"/datasets": data_volume})
def process_dataset():
    import os

    files = os.listdir("/datasets/data")
    print(f"Processing {len(files)} files")

    for file in files:
        process_file(f"/datasets/data/{file}")

    return f"Processed {len(files)} files"
```

## Secrets

### Environment Variables

Store sensitive configuration:

```python
# Create secret in Modal dashboard or CLI:
# modal secret create my-secrets \
#   API_KEY=abc123 \
#   DATABASE_URL=postgresql://...

app = modal.App("secrets-app")

@app.function(secrets=[modal.Secret.from_name("my-secrets")])
def use_api_key():
    import os

    api_key = os.environ["API_KEY"]
    database_url = os.environ["DATABASE_URL"]

    # Use secrets
    return call_api(api_key)
```

### Multiple Secrets

Combine multiple secret sets:

```python
@app.function(secrets=[
    modal.Secret.from_name("api-keys"),
    modal.Secret.from_name("database-creds"),
    modal.Secret.from_name("cloud-storage")
])
def multi_secret_function():
    import os

    # From api-keys
    openai_key = os.environ["OPENAI_API_KEY"]

    # From database-creds
    db_url = os.environ["DATABASE_URL"]

    # From cloud-storage
    s3_key = os.environ["AWS_ACCESS_KEY_ID"]

    return "All secrets loaded"
```

### Secret Best Practices

Secure secret usage:

```python
@app.function(secrets=[modal.Secret.from_name("production-keys")])
def secure_function():
    import os

    # ✅ GOOD - Use directly
    api_key = os.environ["API_KEY"]
    result = api_call(api_key)

    # ❌ BAD - Don't log secrets
    # print(f"Using key: {api_key}")

    # ❌ BAD - Don't return secrets
    # return {"key": api_key}

    # ✅ GOOD - Return only result
    return {"result": result}
```

## Combined Volumes and Secrets

### Authenticated Downloads

Download with authentication:

```python
download_volume = modal.Volume.from_name("downloads", create_if_missing=True)

@app.function(
    volumes={"/downloads": download_volume},
    secrets=[modal.Secret.from_name("api-keys")]
)
def authenticated_download():
    import os
    import requests

    api_key = os.environ["API_KEY"]

    response = requests.get(
        "https://api.example.com/data",
        headers={"Authorization": f"Bearer {api_key}"}
    )

    with open("/downloads/data.json", "w") as f:
        f.write(response.text)

    download_volume.commit()

    return "Downloaded"
```

### Database Backups

Store backups with credentials:

```python
backup_volume = modal.Volume.from_name("backups", create_if_missing=True)

@app.function(
    volumes={"/backups": backup_volume},
    secrets=[modal.Secret.from_name("database-creds")],
    schedule=modal.Cron("0 2 * * *")  # 2 AM daily
)
def backup_database():
    import os
    import subprocess
    from datetime import datetime

    db_url = os.environ["DATABASE_URL"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_file = f"/backups/backup_{timestamp}.sql"

    # Create backup
    subprocess.run([
        "pg_dump",
        db_url,
        "-f", backup_file
    ])

    backup_volume.commit()

    return f"Backup created: {backup_file}"
```

## Volume Management

### Listing Files

Navigate volume contents:

```python
@app.function(volumes={"/data": volume})
def list_files():
    import os

    files = []
    for root, dirs, filenames in os.walk("/data"):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            size = os.path.getsize(filepath)
            files.append({"path": filepath, "size": size})

    return files
```

### Cleanup Old Files

Manage volume storage:

```python
from datetime import datetime, timedelta

@app.function(volumes={"/cache": cache_volume})
def cleanup_old_cache():
    import os
    from datetime import datetime

    cutoff = datetime.now() - timedelta(days=7)
    deleted = []

    for filename in os.listdir("/cache"):
        filepath = os.path.join("/cache", filename)
        mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))

        if mod_time < cutoff:
            os.remove(filepath)
            deleted.append(filename)

    cache_volume.commit()

    return {"deleted_count": len(deleted)}
```

## Anti-Patterns to Avoid

**DON'T forget to commit volumes:**
```python
# ❌ BAD - Changes lost!
@app.function(volumes={"/data": volume})
def bad_write():
    with open("/data/file.txt", "w") as f:
        f.write("data")
    # Missing: volume.commit()

# ✅ GOOD
@app.function(volumes={"/data": volume})
def good_write():
    with open("/data/file.txt", "w") as f:
        f.write("data")
    volume.commit()
```

**DON'T log or return secrets:**
```python
# ❌ BAD
@app.function(secrets=[secret])
def bad():
    api_key = os.environ["API_KEY"]
    print(f"Key: {api_key}")  # Logged!
    return {"key": api_key}   # Exposed!

# ✅ GOOD
@app.function(secrets=[secret])
def good():
    api_key = os.environ["API_KEY"]
    result = use_key(api_key)
    return {"result": result}
```

**DON'T use volumes for temporary data:**
```python
# ❌ BAD - Volume for temp data
@app.function(volumes={"/tmp": volume})
def bad_temp():
    with open("/tmp/temp.txt", "w") as f:
        f.write("temp")
    volume.commit()

# ✅ GOOD - Use /tmp (ephemeral)
@app.function()
def good_temp():
    with open("/tmp/temp.txt", "w") as f:
        f.write("temp")
    # No commit needed, cleaned up automatically
```

## Related Skills

- **modal-functions-basics.md** - Basic Modal patterns
- **modal-gpu-workloads.md** - Storing model weights
- **modal-scheduling.md** - Scheduled backups
- **modal-image-building.md** - Baking data into images
