---
name: cloud-gcp-networking
description: Google Cloud networking including VPC, firewall, DNS, CDN, and load balancing
---

# GCP Networking Services

**Scope**: VPC networks, firewall rules, Cloud DNS, Cloud CDN, and load balancing configurations
**Lines**: ~320
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Setting up VPC networks and subnets for GCP resources
- Configuring firewall rules and network security policies
- Implementing Cloud DNS for domain management
- Enabling Cloud CDN for content delivery and caching
- Deploying load balancers for high availability and scaling
- Connecting on-premises networks via VPN or Cloud Interconnect
- Setting up Private Google Access for VM-to-service communication
- Optimizing network performance and reducing egress costs

## Core Concepts

### Concept 1: VPC Networks and Subnets

**VPC modes**:
- **Auto mode**: GCP creates subnets automatically in each region
- **Custom mode**: User defines subnets and IP ranges (recommended for production)
- **Shared VPC**: Share VPC across multiple projects in organization

```bash
# Create custom VPC network
gcloud compute networks create production-vpc \
  --subnet-mode=custom \
  --bgp-routing-mode=regional

# Create subnets in different regions
gcloud compute networks subnets create us-central-subnet \
  --network=production-vpc \
  --region=us-central1 \
  --range=10.0.1.0/24 \
  --enable-private-ip-google-access

gcloud compute networks subnets create europe-subnet \
  --network=production-vpc \
  --region=europe-west1 \
  --range=10.0.2.0/24 \
  --enable-private-ip-google-access

# Create instance in custom subnet
gcloud compute instances create web-server \
  --zone=us-central1-a \
  --subnet=us-central-subnet \
  --no-address  # No external IP (use Private Google Access)
```

### Concept 2: Firewall Rules

**Rule components**:
- **Direction**: Ingress (incoming) or egress (outgoing)
- **Priority**: Lower numbers = higher priority (0-65535)
- **Target**: All instances, tags, or service accounts
- **Source/Destination**: IP ranges, tags, or service accounts

```bash
# Allow SSH from specific IP range
gcloud compute firewall-rules create allow-ssh \
  --network=production-vpc \
  --allow=tcp:22 \
  --source-ranges=203.0.113.0/24 \
  --description="Allow SSH from office"

# Allow HTTP/HTTPS with network tags
gcloud compute firewall-rules create allow-web \
  --network=production-vpc \
  --allow=tcp:80,tcp:443 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=web-server

# Deny egress to specific IP (higher priority = lower number)
gcloud compute firewall-rules create deny-malicious-ip \
  --network=production-vpc \
  --direction=EGRESS \
  --action=DENY \
  --rules=all \
  --destination-ranges=198.51.100.0/24 \
  --priority=100
```

### Concept 3: Cloud Load Balancing

**Load balancer types**:
- **HTTP(S)**: Layer 7, global, content-based routing
- **TCP/SSL Proxy**: Layer 4, global, TCP with SSL termination
- **Network**: Layer 4, regional, pass-through
- **Internal**: Layer 4, regional, internal traffic only

```python
from google.cloud import compute_v1

def create_https_load_balancer(project_id):
    # Create backend service
    backend_client = compute_v1.BackendServicesClient()
    backend_service = compute_v1.BackendService(
        name='web-backend',
        protocol='HTTP',
        port_name='http',
        timeout_sec=30,
        health_checks=[f'projects/{project_id}/global/healthChecks/web-health-check'],
        backends=[
            compute_v1.Backend(
                group=f'projects/{project_id}/zones/us-central1-a/instanceGroups/web-mig'
            )
        ]
    )
    backend_client.insert(project=project_id, backend_service_resource=backend_service)

    # Create URL map (routing rules)
    url_maps_client = compute_v1.UrlMapsClient()
    url_map = compute_v1.UrlMap(
        name='web-url-map',
        default_service=f'projects/{project_id}/global/backendServices/web-backend'
    )
    url_maps_client.insert(project=project_id, url_map_resource=url_map)

    # Create HTTPS proxy
    proxy_client = compute_v1.TargetHttpsProxiesClient()
    https_proxy = compute_v1.TargetHttpsProxy(
        name='web-https-proxy',
        url_map=f'projects/{project_id}/global/urlMaps/web-url-map',
        ssl_certificates=[f'projects/{project_id}/global/sslCertificates/web-cert']
    )
    proxy_client.insert(project=project_id, target_https_proxy_resource=https_proxy)

    # Create forwarding rule (external IP + port)
    forwarding_client = compute_v1.GlobalForwardingRulesClient()
    forwarding_rule = compute_v1.ForwardingRule(
        name='web-forwarding-rule',
        ip_protocol='TCP',
        port_range='443',
        target=f'projects/{project_id}/global/targetHttpsProxies/web-https-proxy'
    )
    forwarding_client.insert(project=project_id, forwarding_rule_resource=forwarding_rule)
```

### Concept 4: Cloud CDN

**CDN features**:
- Cache static content at Google edge locations (200+ POPs)
- Reduce origin load and improve latency
- Cache modes: USE_ORIGIN_HEADERS, CACHE_ALL_STATIC, FORCE_CACHE_ALL

```bash
# Enable Cloud CDN on backend service
gcloud compute backend-services update web-backend \
  --enable-cdn \
  --cache-mode=CACHE_ALL_STATIC \
  --default-ttl=3600 \
  --max-ttl=86400 \
  --client-ttl=3600 \
  --global

# Create signed URL for private content
gcloud compute sign-url https://example.com/private/video.mp4 \
  --key-name=cdn-key \
  --key-file=private-key.pem \
  --expires-in=1h

# Invalidate cache
gcloud compute url-maps invalidate-cdn-cache web-url-map \
  --path="/static/*" \
  --global
```

---

## Patterns

### Pattern 1: Shared VPC for Multi-Project Organization

**When to use**:
- Centralize network administration across projects
- Share common network resources (VPN, firewall rules)

```bash
# ❌ Bad: Each project creates separate VPC (management overhead)
# Project A creates VPC, Project B creates VPC, etc.
# Duplicate firewall rules, multiple VPN tunnels

# ✅ Good: Use Shared VPC
# Enable Shared VPC in host project
gcloud compute shared-vpc enable HOST_PROJECT

# Attach service projects
gcloud compute shared-vpc associated-projects add SERVICE_PROJECT_1 \
  --host-project=HOST_PROJECT

gcloud compute shared-vpc associated-projects add SERVICE_PROJECT_2 \
  --host-project=HOST_PROJECT

# Service projects can now use subnets from host project
gcloud compute instances create app-server \
  --project=SERVICE_PROJECT_1 \
  --zone=us-central1-a \
  --subnet=projects/HOST_PROJECT/regions/us-central1/subnetworks/shared-subnet
```

**Benefits**:
- Centralized network policy enforcement
- Reduced complexity and administration overhead
- Consistent security posture across organization

### Pattern 2: Private Google Access

**Use case**: Access Google services (Cloud Storage, BigQuery) from instances without external IPs

```bash
# Enable Private Google Access on subnet
gcloud compute networks subnets update us-central-subnet \
  --region=us-central1 \
  --enable-private-ip-google-access

# Create instance without external IP
gcloud compute instances create private-instance \
  --zone=us-central1-a \
  --subnet=us-central-subnet \
  --no-address

# Instance can now access Cloud Storage without external IP
# SSH via Cloud Identity-Aware Proxy
gcloud compute ssh private-instance \
  --zone=us-central1-a \
  --tunnel-through-iap
```

### Pattern 3: Cloud Armor Security Policies

**Use case**: Protect applications from DDoS and web attacks

```bash
# Create Cloud Armor security policy
gcloud compute security-policies create web-security-policy \
  --description="Protect web application"

# Block traffic from specific countries
gcloud compute security-policies rules create 1000 \
  --security-policy=web-security-policy \
  --expression="origin.region_code == 'CN' || origin.region_code == 'RU'" \
  --action=deny-403 \
  --description="Block traffic from specific countries"

# Rate limit requests
gcloud compute security-policies rules create 2000 \
  --security-policy=web-security-policy \
  --expression="true" \
  --action=rate-based-ban \
  --rate-limit-threshold-count=100 \
  --rate-limit-threshold-interval-sec=60 \
  --ban-duration-sec=600 \
  --description="Rate limit: 100 req/min"

# Attach to backend service
gcloud compute backend-services update web-backend \
  --security-policy=web-security-policy \
  --global
```

### Pattern 4: Cloud DNS with DNSSEC

**Use case**: Secure DNS resolution with cryptographic signatures

```bash
# Create managed DNS zone
gcloud dns managed-zones create production-zone \
  --dns-name=example.com. \
  --description="Production DNS zone"

# Enable DNSSEC
gcloud dns managed-zones update production-zone \
  --dnssec-state=on

# Add DNS records
gcloud dns record-sets create www.example.com. \
  --zone=production-zone \
  --type=A \
  --ttl=300 \
  --rrdatas=203.0.113.1

gcloud dns record-sets create api.example.com. \
  --zone=production-zone \
  --type=CNAME \
  --ttl=300 \
  --rrdatas=web-lb.example.com.

# Create private DNS zone for internal resources
gcloud dns managed-zones create internal-zone \
  --dns-name=internal.example.com. \
  --description="Internal DNS" \
  --visibility=private \
  --networks=production-vpc
```

### Pattern 5: Content-Based Routing with URL Maps

**Use case**: Route requests to different backends based on URL path

```bash
# Create backend services for different apps
gcloud compute backend-services create api-backend --global
gcloud compute backend-services create web-backend --global
gcloud compute backend-services create admin-backend --global

# Create URL map with path-based routing
gcloud compute url-maps create multi-service-lb \
  --default-service=web-backend

gcloud compute url-maps add-path-matcher multi-service-lb \
  --path-matcher-name=main \
  --default-service=web-backend \
  --path-rules="/api/*=api-backend,/admin/*=admin-backend"

# Example routing:
# example.com/          -> web-backend
# example.com/api/users -> api-backend
# example.com/admin/    -> admin-backend
```

### Pattern 6: Cloud VPN for Hybrid Connectivity

**Use case**: Securely connect on-premises network to GCP VPC

```bash
# Create VPN gateway
gcloud compute target-vpn-gateways create on-prem-vpn-gateway \
  --network=production-vpc \
  --region=us-central1

# Reserve static IP for VPN gateway
gcloud compute addresses create vpn-gateway-ip \
  --region=us-central1

# Create forwarding rules
gcloud compute forwarding-rules create vpn-rule-esp \
  --region=us-central1 \
  --ip-protocol=ESP \
  --address=vpn-gateway-ip \
  --target-vpn-gateway=on-prem-vpn-gateway

# Create VPN tunnel
gcloud compute vpn-tunnels create on-prem-tunnel \
  --region=us-central1 \
  --peer-address=203.0.113.1 \
  --shared-secret=SHARED_SECRET \
  --ike-version=2 \
  --target-vpn-gateway=on-prem-vpn-gateway \
  --local-traffic-selector=10.0.0.0/16 \
  --remote-traffic-selector=192.168.0.0/16

# Create route to on-prem network
gcloud compute routes create on-prem-route \
  --network=production-vpc \
  --destination-range=192.168.0.0/16 \
  --next-hop-vpn-tunnel=on-prem-tunnel \
  --next-hop-vpn-tunnel-region=us-central1
```

### Pattern 7: Health Checks for Load Balancers

**Use case**: Automatically remove unhealthy instances from load balancer pool

```bash
# Create health check
gcloud compute health-checks create http web-health-check \
  --port=80 \
  --request-path=/health \
  --check-interval=10s \
  --timeout=5s \
  --unhealthy-threshold=3 \
  --healthy-threshold=2

# Attach to backend service
gcloud compute backend-services update web-backend \
  --health-checks=web-health-check \
  --global

# Health check endpoint should return 200 OK when healthy
```

```python
# Flask health check endpoint
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health_check():
    # Check database connectivity, dependencies, etc.
    try:
        db.execute("SELECT 1")
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503
```

### Pattern 8: Network Tags for Firewall Targeting

**Use case**: Apply firewall rules to specific instance groups using tags

```bash
# Create firewall rule targeting web servers
gcloud compute firewall-rules create allow-web-traffic \
  --network=production-vpc \
  --allow=tcp:80,tcp:443 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=web-server

# Create firewall rule for database access (only from app servers)
gcloud compute firewall-rules create allow-db-from-app \
  --network=production-vpc \
  --allow=tcp:5432 \
  --source-tags=app-server \
  --target-tags=database-server

# Create instance with tags
gcloud compute instances create web-1 \
  --zone=us-central1-a \
  --tags=web-server

gcloud compute instances create db-1 \
  --zone=us-central1-a \
  --tags=database-server \
  --no-address  # No external IP for security
```

---

## Quick Reference

### Load Balancer Selection

```
Type            | Layer | Scope   | Use Case
----------------|-------|---------|---------------------------
HTTP(S)         | 7     | Global  | Web apps, content routing
TCP/SSL Proxy   | 4     | Global  | Non-HTTP with SSL
Network         | 4     | Regional| Low latency, pass-through
Internal HTTP(S)| 7     | Regional| Internal microservices
Internal TCP/UDP| 4     | Regional| Internal databases
```

### Firewall Rule Priority

```
Priority | Use Case
---------|----------------------------------
0-99     | Critical deny rules
100-999  | Standard security rules
1000+    | Application-specific rules
65535    | Default allow rules
```

### Key gcloud Commands

```bash
# VPC
gcloud compute networks create VPC --subnet-mode=custom
gcloud compute networks subnets create SUBNET --network=VPC --range=CIDR

# Firewall
gcloud compute firewall-rules create RULE --network=VPC --allow=PROTOCOL:PORT
gcloud compute firewall-rules list --network=VPC

# Load Balancing
gcloud compute backend-services create NAME --global
gcloud compute url-maps create NAME --default-service=BACKEND
gcloud compute forwarding-rules create NAME --global --target-http-proxy=PROXY

# DNS
gcloud dns managed-zones create ZONE --dns-name=DOMAIN
gcloud dns record-sets create NAME --zone=ZONE --type=TYPE --rrdatas=DATA
```

### Key Guidelines

```
✅ DO: Use custom VPC mode for production environments
✅ DO: Enable Private Google Access to reduce egress costs
✅ DO: Tag instances for granular firewall rule targeting
✅ DO: Use Cloud CDN for static content delivery
✅ DO: Implement health checks for all load-balanced services
✅ DO: Enable DNSSEC for public DNS zones

❌ DON'T: Use auto-mode VPC for production (inflexible IP ranges)
❌ DON'T: Create overly permissive firewall rules (0.0.0.0/0 on all ports)
❌ DON'T: Forget to enable Private Google Access (increases egress costs)
❌ DON'T: Use Network load balancer when HTTP(S) features needed
❌ DON'T: Skip Cloud Armor for internet-facing applications
```

---

## Anti-Patterns

### Critical Violations

```bash
# ❌ NEVER: Create overly permissive firewall rules
gcloud compute firewall-rules create allow-all \
  --network=production-vpc \
  --allow=all \
  --source-ranges=0.0.0.0/0
# Exposes all services to internet!

# ✅ CORRECT: Create specific rules with least privilege
gcloud compute firewall-rules create allow-web \
  --network=production-vpc \
  --allow=tcp:80,tcp:443 \
  --source-ranges=0.0.0.0/0 \
  --target-tags=web-server

gcloud compute firewall-rules create allow-ssh-from-office \
  --network=production-vpc \
  --allow=tcp:22 \
  --source-ranges=203.0.113.0/24 \
  --target-tags=ssh-access
```

❌ **Overly permissive rules**: Allowing all protocols from all sources exposes services to attacks.
✅ **Correct approach**: Create specific rules for each service with source restrictions and target tags.

### Common Mistakes

```bash
# ❌ Don't: Use auto-mode VPC in production
gcloud compute networks create production-vpc --subnet-mode=auto
# Cannot control IP ranges, subnet created in every region

# ✅ Correct: Use custom-mode VPC for control
gcloud compute networks create production-vpc --subnet-mode=custom
gcloud compute networks subnets create us-subnet \
  --network=production-vpc \
  --region=us-central1 \
  --range=10.0.1.0/24
```

❌ **Auto-mode VPC in production**: Cannot control IP ranges, wastes IP space, inflexible.
✅ **Better**: Use custom-mode VPC to define only needed subnets with appropriate CIDR ranges.

```bash
# ❌ Don't: Forget to enable Private Google Access
# Instances without external IPs cannot access Cloud Storage
gcloud compute instances create app-server \
  --zone=us-central1-a \
  --subnet=us-central-subnet \
  --no-address
# gsutil commands fail!

# ✅ Correct: Enable Private Google Access on subnet
gcloud compute networks subnets update us-central-subnet \
  --region=us-central1 \
  --enable-private-ip-google-access
```

❌ **Missing Private Google Access**: Instances without external IPs cannot reach Google services, increasing egress costs.
✅ **Better**: Enable Private Google Access on subnets to allow access to Google APIs without external IPs.

---

## Related Skills

- `gcp-compute.md` - Creating instances in VPC subnets with network tags
- `gcp-iam-security.md` - Service accounts for network access control
- `gcp-databases.md` - Private IP configuration for Cloud SQL instances
- `gcp-serverless.md` - VPC connector for Cloud Run and Cloud Functions

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
