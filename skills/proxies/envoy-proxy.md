---
name: proxies-envoy-proxy
description: Envoy proxy architecture including filters, clusters, listeners, service mesh patterns, observability, and advanced load balancing
---

# Envoy Proxy

**Scope**: Envoy architecture, configuration, filters, clusters, observability
**Lines**: ~390
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building service mesh architectures
- Implementing advanced load balancing
- Setting up distributed tracing
- Configuring L7 (application layer) proxying
- Working with gRPC services
- Implementing circuit breakers and retries
- Building API gateways with Envoy
- Integrating observability (metrics, tracing, logging)

## Core Concepts

### Envoy Architecture

```
Downstream Client → Listener → Filter Chain → Cluster → Upstream Service
                     (Port)     (Transform)   (Pool)     (Backend)
```

**Key Components**:
- **Listeners**: Listen on ports, accept connections
- **Filter Chains**: Process requests/responses
- **Clusters**: Define upstream service pools
- **Routes**: Match requests to clusters
- **Endpoints**: Individual backend instances

### Envoy Threading Model

```
Main Thread → Worker Threads (# of CPUs)
              └─ Each handles connections independently
              └─ No shared state, lock-free architecture
```

**Benefits**:
- High performance
- Predictable latency
- Scales with CPU cores

---

## Patterns

### Pattern 1: Basic HTTP Proxy

**Use Case**: Simple reverse proxy configuration

```yaml
# envoy.yaml
static_resources:
  listeners:
    - name: listener_0
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 10000

      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_http
                codec_type: AUTO

                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: backend
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/"
                          route:
                            cluster: backend_cluster

                http_filters:
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router

  clusters:
    - name: backend_cluster
      connect_timeout: 0.25s
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: backend_cluster
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: backend.local
                      port_value: 8080
```

### Pattern 2: Advanced Load Balancing with Health Checks

**Use Case**: Production-ready cluster configuration

```yaml
clusters:
  - name: backend_cluster
    connect_timeout: 1s
    type: STRICT_DNS

    # Load balancing policy
    lb_policy: LEAST_REQUEST
    least_request_lb_config:
      choice_count: 2

    # Circuit breaker
    circuit_breakers:
      thresholds:
        - priority: DEFAULT
          max_connections: 1024
          max_pending_requests: 1024
          max_requests: 1024
          max_retries: 3

    # Outlier detection (passive health check)
    outlier_detection:
      consecutive_5xx: 5
      interval: 10s
      base_ejection_time: 30s
      max_ejection_percent: 50
      enforcing_consecutive_5xx: 100

    # Active health check
    health_checks:
      - timeout: 1s
        interval: 10s
        unhealthy_threshold: 3
        healthy_threshold: 2
        http_health_check:
          path: "/health"
          expected_statuses:
            - start: 200
              end: 299

    # Connection pool
    max_requests_per_connection: 100

    load_assignment:
      cluster_name: backend_cluster
      endpoints:
        - lb_endpoints:
            - endpoint:
                address:
                  socket_address:
                    address: backend1.local
                    port_value: 8080
            - endpoint:
                address:
                  socket_address:
                    address: backend2.local
                    port_value: 8080
            - endpoint:
                address:
                  socket_address:
                    address: backend3.local
                    port_value: 8080
```

### Pattern 3: Path-Based Routing with Retries

**Use Case**: Route different paths to different services

```yaml
route_config:
  name: local_route
  virtual_hosts:
    - name: services
      domains: ["example.com", "*.example.com"]

      routes:
        # API v1 with retry policy
        - match:
            prefix: "/api/v1/"
          route:
            cluster: api_v1_cluster
            retry_policy:
              retry_on: "5xx,reset,connect-failure,refused-stream"
              num_retries: 3
              per_try_timeout: 2s

        # API v2 with timeout
        - match:
            prefix: "/api/v2/"
          route:
            cluster: api_v2_cluster
            timeout: 5s

        # gRPC service
        - match:
            prefix: "/grpc/"
            grpc: {}
          route:
            cluster: grpc_cluster

        # Static content with caching
        - match:
            prefix: "/static/"
          route:
            cluster: cdn_cluster
          response_headers_to_add:
            - header:
                key: "Cache-Control"
                value: "public, max-age=3600"

        # Default fallback
        - match:
            prefix: "/"
          route:
            cluster: web_cluster
```

---

## Filter Configuration

### HTTP Filters

```yaml
http_filters:
  # Rate limiting
  - name: envoy.filters.http.ratelimit
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
      domain: api_ratelimit
      failure_mode_deny: true
      rate_limit_service:
        grpc_service:
          envoy_grpc:
            cluster_name: ratelimit_cluster

  # JWT authentication
  - name: envoy.filters.http.jwt_authn
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.jwt_authn.v3.JwtAuthentication
      providers:
        auth0:
          issuer: "https://example.auth0.com/"
          audiences:
            - "api.example.com"
          remote_jwks:
            http_uri:
              uri: "https://example.auth0.com/.well-known/jwks.json"
              cluster: auth0_jwks_cluster
              timeout: 5s
            cache_duration:
              seconds: 300
      rules:
        - match:
            prefix: "/api/"
          requires:
            provider_name: "auth0"

  # CORS
  - name: envoy.filters.http.cors
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.cors.v3.Cors

  # gRPC Web
  - name: envoy.filters.http.grpc_web
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.grpc_web.v3.GrpcWeb

  # Compression
  - name: envoy.filters.http.compressor
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.compressor.v3.Compressor
      response_direction_config:
        common_config:
          enabled:
            default_value: true
          min_content_length: 100
        disable_on_etag_header: true
      compressor_library:
        name: text_optimized
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.compression.gzip.compressor.v3.Gzip
          compression_level: BEST_COMPRESSION

  # Router (must be last)
  - name: envoy.filters.http.router
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
```

---

## Observability Configuration

### Access Logging

```yaml
access_log:
  - name: envoy.access_loggers.file
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.access_loggers.file.v3.FileAccessLog
      path: /var/log/envoy/access.log
      log_format:
        json_format:
          start_time: "%START_TIME%"
          method: "%REQ(:METHOD)%"
          path: "%REQ(X-ENVOY-ORIGINAL-PATH?:PATH)%"
          protocol: "%PROTOCOL%"
          response_code: "%RESPONSE_CODE%"
          duration: "%DURATION%"
          bytes_sent: "%BYTES_SENT%"
          bytes_received: "%BYTES_RECEIVED%"
          upstream_host: "%UPSTREAM_HOST%"
          x_forwarded_for: "%REQ(X-FORWARDED-FOR)%"
          user_agent: "%REQ(USER-AGENT)%"
          request_id: "%REQ(X-REQUEST-ID)%"
```

### Distributed Tracing

```yaml
tracing:
  http:
    name: envoy.tracers.zipkin
    typed_config:
      "@type": type.googleapis.com/envoy.config.trace.v3.ZipkinConfig
      collector_cluster: zipkin_cluster
      collector_endpoint: "/api/v2/spans"
      collector_endpoint_version: HTTP_JSON

# Or Jaeger
tracing:
  http:
    name: envoy.tracers.opencensus
    typed_config:
      "@type": type.googleapis.com/envoy.config.trace.v3.OpenCensusConfig
      trace_config:
        probability: 1.0
      jaeger_exporter_config:
        collector_endpoint: "jaeger-collector:14268"
        service_name: "envoy-proxy"
```

### Metrics (Prometheus)

```yaml
admin:
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 9901

stats_sinks:
  - name: envoy.stat_sinks.prometheus
    typed_config:
      "@type": type.googleapis.com/envoy.extensions.stat_sinks.metrics_service.v3.MetricsServiceConfig
      grpc_service:
        envoy_grpc:
          cluster_name: prometheus_cluster

# Access metrics at http://localhost:9901/stats/prometheus
```

---

## Service Mesh Pattern

### Sidecar Configuration

```yaml
# Envoy as sidecar proxy
node:
  id: service-v1
  cluster: service-cluster

static_resources:
  listeners:
    # Inbound listener (accept traffic to this service)
    - name: inbound_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 15001
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: inbound_http
                route_config:
                  name: inbound_route
                  virtual_hosts:
                    - name: inbound_service
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/"
                          route:
                            cluster: local_service
                http_filters:
                  - name: envoy.filters.http.router

    # Outbound listener (proxy traffic to other services)
    - name: outbound_listener
      address:
        socket_address:
          address: 127.0.0.1
          port_value: 15000
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: outbound_http
                route_config:
                  name: outbound_route
                  virtual_hosts:
                    - name: backend_services
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/api/"
                          route:
                            cluster: api_service
                        - match:
                            prefix: "/data/"
                          route:
                            cluster: data_service

  clusters:
    # Local service
    - name: local_service
      connect_timeout: 0.25s
      type: STATIC
      load_assignment:
        cluster_name: local_service
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: 127.0.0.1
                      port_value: 8080

    # Remote services (service discovery)
    - name: api_service
      connect_timeout: 1s
      type: EDS
      eds_cluster_config:
        eds_config:
          api_config_source:
            api_type: GRPC
            grpc_services:
              - envoy_grpc:
                  cluster_name: xds_cluster

    - name: data_service
      connect_timeout: 1s
      type: EDS
      eds_cluster_config:
        eds_config:
          api_config_source:
            api_type: GRPC
            grpc_services:
              - envoy_grpc:
                  cluster_name: xds_cluster

    # Control plane
    - name: xds_cluster
      connect_timeout: 1s
      type: STRICT_DNS
      http2_protocol_options: {}
      load_assignment:
        cluster_name: xds_cluster
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: control-plane.local
                      port_value: 18000
```

---

## Python Envoy Control Plane

```python
import grpc
from concurrent import futures
from envoy.service.discovery.v3 import discovery_pb2_grpc
from envoy.config.endpoint.v3 import endpoint_pb2
from envoy.config.cluster.v3 import cluster_pb2

class EnvoyControlPlane(discovery_pb2_grpc.AggregatedDiscoveryServiceServicer):
    def __init__(self):
        self.version_info = "1"
        self.endpoints = {}

    def StreamAggregatedResources(self, request_iterator, context):
        """Handle xDS requests from Envoy"""
        for request in request_iterator:
            if request.type_url == "type.googleapis.com/envoy.config.endpoint.v3.ClusterLoadAssignment":
                response = self.build_endpoint_response(request)
                yield response

    def build_endpoint_response(self, request):
        """Build EDS response with endpoints"""
        resources = []

        for cluster_name in request.resource_names:
            if cluster_name in self.endpoints:
                cla = endpoint_pb2.ClusterLoadAssignment(
                    cluster_name=cluster_name,
                    endpoints=[
                        endpoint_pb2.LocalityLbEndpoints(
                            lb_endpoints=[
                                endpoint_pb2.LbEndpoint(
                                    endpoint=endpoint_pb2.Endpoint(
                                        address=endpoint_pb2.Address(
                                            socket_address=endpoint_pb2.SocketAddress(
                                                address=ep["address"],
                                                port_value=ep["port"]
                                            )
                                        )
                                    )
                                )
                                for ep in self.endpoints[cluster_name]
                            ]
                        )
                    ]
                )
                resources.append(cla)

        response = discovery_pb2.DiscoveryResponse(
            version_info=self.version_info,
            resources=[r.SerializeToString() for r in resources],
            type_url="type.googleapis.com/envoy.config.endpoint.v3.ClusterLoadAssignment"
        )
        return response

    def register_endpoints(self, cluster: str, endpoints: list):
        """Register endpoints for a cluster"""
        self.endpoints[cluster] = endpoints
        self.version_info = str(int(self.version_info) + 1)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    control_plane = EnvoyControlPlane()

    # Register some endpoints
    control_plane.register_endpoints("api_service", [
        {"address": "10.0.1.10", "port": 8080},
        {"address": "10.0.1.11", "port": 8080}
    ])

    discovery_pb2_grpc.add_AggregatedDiscoveryServiceServicer_to_server(
        control_plane, server
    )

    server.add_insecure_port('[::]:18000')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
```

---

## Best Practices

### 1. Use Connection Pooling

```yaml
clusters:
  - name: backend_cluster
    # ... other config
    http2_protocol_options:
      max_concurrent_streams: 100
    max_requests_per_connection: 100
```

### 2. Configure Timeouts

```yaml
route:
  cluster: backend_cluster
  timeout: 15s
  idle_timeout: 60s
  retry_policy:
    retry_on: "5xx"
    num_retries: 3
    per_try_timeout: 5s
```

### 3. Enable Observability

```yaml
# Always enable tracing, metrics, and logging
tracing:
  http:
    name: envoy.tracers.zipkin

stats_sinks:
  - name: envoy.stat_sinks.prometheus

access_log:
  - name: envoy.access_loggers.file
```

---

## Troubleshooting

### Issue 1: High Latency

**Debug Steps**:
```bash
# Check Envoy admin interface
curl http://localhost:9901/stats | grep upstream

# Check cluster health
curl http://localhost:9901/clusters

# Enable debug logging
curl -X POST http://localhost:9901/logging?level=debug
```

**Common Solutions**:
- Increase connection pool size
- Tune timeout values
- Check upstream health
- Enable connection reuse

### Issue 2: Circuit Breaker Triggered

**Symptoms**: `upstream_rq_pending_overflow` counter increasing

**Solution**:
```yaml
circuit_breakers:
  thresholds:
    - priority: DEFAULT
      max_connections: 2048  # Increase
      max_pending_requests: 2048  # Increase
```

---

## Related Skills

- `proxies-reverse-proxy` - Reverse proxy patterns
- `proxies-nginx-configuration` - Nginx configuration
- `distributed-systems-service-mesh` - Service mesh architecture
- `observability-distributed-tracing` - Distributed tracing
- `protocols-grpc` - gRPC protocol

---

**Last Updated**: 2025-10-27
