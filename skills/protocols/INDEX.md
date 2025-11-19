# Protocol Skills

Comprehensive skills for implementing network protocols, message queues, and communication systems.

## Category Overview

**Total Skills**: 8
**Focus**: gRPC, HTTP/2, Kafka, MQTT, RabbitMQ, Protocol Buffers, TCP, WebSockets
**Use Cases**: API communication, message streaming, IoT, real-time applications, microservices

## Skills in This Category

### grpc-implementation.md
**Description**: Implementing gRPC APIs with Protocol Buffers
**Lines**: ~350
**Use When**:
- Implementing gRPC services from scratch
- Designing Protocol Buffer schemas for RPC
- Implementing streaming RPCs (unary, server, client, bidirectional)
- Adding error handling and status codes
- Implementing interceptors and middleware
- Optimizing gRPC performance
- Building microservices with gRPC

**Key Concepts**: gRPC services, Protocol Buffers, streaming, error handling, interceptors, deadlines

---

### http2-multiplexing.md
**Description**: HTTP/2 protocol with multiplexing, server push, header compression
**Lines**: ~360
**Use When**:
- Optimizing website performance with HTTP/2
- Implementing HTTP/2 servers or clients
- Debugging HTTP/2 connection issues
- Understanding multiplexing and stream prioritization
- Implementing server push for resource optimization
- Using HPACK for header compression
- Migrating from HTTP/1.1 to HTTP/2

**Key Concepts**: HTTP/2 binary protocol, multiplexing, server push, HPACK, stream prioritization

---

### kafka-streams.md
**Description**: Apache Kafka stream processing and event streaming platform
**Lines**: ~300
**Use When**:
- Building real-time data pipelines with Kafka
- Implementing event-driven architectures
- Processing streams with Kafka Streams or ksqlDB
- Ensuring exactly-once message delivery
- Using Avro/Protobuf with Schema Registry
- Monitoring consumer lag and cluster health
- Designing topic partitioning strategies

**Key Concepts**: Kafka architecture, producers, consumers, Kafka Streams API, exactly-once semantics, schema registry

---

### mqtt-messaging.md
**Description**: MQTT pub-sub messaging for IoT and real-time applications
**Lines**: ~400
**Use When**:
- Implementing MQTT pub-sub messaging systems
- Building IoT device communication
- Designing lightweight messaging protocols
- Implementing real-time sensor data collection
- Setting up MQTT brokers (Mosquitto, EMQX, HiveMQ)
- Configuring QoS levels and message delivery guarantees
- Managing device connectivity and last will messages

**Key Concepts**: MQTT protocol, pub-sub patterns, QoS levels, broker configuration, IoT integration, retained messages

---

### amqp-rabbitmq.md
**Description**: RabbitMQ and AMQP message broker implementation
**Lines**: ~350
**Use When**:
- Implementing message queuing with RabbitMQ
- Designing exchange and queue topologies
- Building work queue, pub-sub, routing, or RPC patterns
- Implementing message durability and acknowledgments
- Setting up RabbitMQ clustering and high availability
- Optimizing RabbitMQ performance
- Handling dead letter queues and message TTL

**Key Concepts**: AMQP 0-9-1 protocol, RabbitMQ, exchanges, queues, routing patterns, clustering, high availability

---

### protobuf-schemas.md
**Description**: Protocol Buffers schema design, evolution, and code generation
**Lines**: ~350
**Use When**:
- Designing Protocol Buffer schemas from scratch
- Implementing schema evolution strategies
- Managing schema versioning and compatibility
- Generating code for multiple languages
- Integrating with gRPC or Kafka
- Setting up schema registries
- Ensuring backward/forward compatibility

**Key Concepts**: Proto syntax, schema design, field numbering, backward/forward compatibility, code generation, schema registry

---

### tcp-optimization.md
**Description**: TCP performance optimization and tuning
**Lines**: ~370
**Use When**:
- Optimizing network throughput and latency
- Tuning TCP for high-bandwidth or high-latency networks
- Diagnosing TCP performance issues
- Configuring congestion control algorithms
- Optimizing cloud networking (AWS, GCP, Azure)
- Tuning container networking (Docker, Kubernetes)
- Adjusting TCP kernel parameters for performance

**Key Concepts**: TCP tuning, congestion control, kernel parameters, performance monitoring, throughput optimization

---

### websocket-protocols.md
**Description**: WebSocket protocol implementation, scaling, and production deployment
**Lines**: ~650
**Use When**:
- Implementing WebSocket servers from scratch
- Designing real-time bidirectional communication systems
- Scaling WebSocket applications horizontally
- Configuring load balancers for WebSocket traffic (nginx, HAProxy)
- Implementing authentication and authorization for WebSocket connections
- Handling reconnection logic and heartbeats
- Monitoring WebSocket connections in production

**Key Concepts**: WebSocket protocol (RFC 6455), connection management, load balancing, scaling strategies, security

---

## Common Workflows

### gRPC Microservices
**Goal**: Build a gRPC-based microservices architecture

**Sequence**:
1. `protobuf-schemas.md` - Design Protocol Buffer schemas
2. `grpc-implementation.md` - Implement gRPC services
3. `tcp-optimization.md` - Optimize network performance
4. `http2-multiplexing.md` - Understand underlying HTTP/2 transport

**Example**: Service mesh with gRPC communication

---

### Real-time Event Streaming
**Goal**: Build an event streaming pipeline

**Sequence**:
1. `kafka-streams.md` - Set up Kafka cluster and topics
2. `protobuf-schemas.md` - Define event schemas
3. `kafka-streams.md` - Implement stream processing

**Example**: Real-time analytics on user events

---

### IoT Message Brokering
**Goal**: Implement IoT device communication

**Sequence**:
1. `mqtt-messaging.md` - Set up MQTT broker and topics
2. `amqp-rabbitmq.md` - Route messages to backend services
3. `websocket-protocols.md` - Enable real-time web dashboards

**Example**: Smart home device network

---

### Message Queue Architecture
**Goal**: Build reliable message processing system

**Sequence**:
1. `amqp-rabbitmq.md` - Design RabbitMQ topology
2. `protobuf-schemas.md` - Define message schemas
3. `kafka-streams.md` - Alternative: Kafka for high-throughput scenarios

**Example**: Asynchronous job processing system

---

### Real-time Web Application
**Goal**: Build bidirectional real-time communication

**Sequence**:
1. `websocket-protocols.md` - Implement WebSocket server
2. `http2-multiplexing.md` - Optimize HTTP/2 for initial page load
3. `tcp-optimization.md` - Tune network performance

**Example**: Collaborative editing platform

---

## Skill Combinations

### With API Skills (`discover-api`)
- gRPC as alternative to REST APIs
- Protocol Buffers for API schemas
- WebSockets for real-time API updates
- HTTP/2 for REST API performance

**Common combos**:
- `grpc-implementation.md` + `api/rest-api-design.md`
- `websocket-protocols.md` + `api/api-authentication.md`

---

### With Database Skills (`discover-database`)
- Kafka for change data capture (CDC)
- Message queues for database write buffering
- Real-time data synchronization
- Event sourcing patterns

**Common combos**:
- `kafka-streams.md` + `database/postgres-cdc.md`
- `amqp-rabbitmq.md` + `database/database-transactions.md`

---

### With Infrastructure Skills (`discover-infrastructure`, `discover-cloud`)
- Deploying message brokers at scale
- Container networking optimization
- Cloud-native messaging services
- Service mesh integration

**Common combos**:
- `tcp-optimization.md` + `infrastructure/infrastructure-security.md`
- `kafka-streams.md` + `cloud/aws/aws-msk.md`

---

### With Frontend Skills (`discover-frontend`)
- WebSocket client libraries
- Real-time UI updates
- Server-Sent Events vs WebSockets
- Connection management in browsers

**Common combos**:
- `websocket-protocols.md` + `frontend/react-data-fetching.md`
- `http2-multiplexing.md` + `frontend/nextjs-performance.md`

---

## Quick Selection Guide

**Choose gRPC when**:
- Building microservices with type-safe contracts
- Need high-performance RPC
- Want built-in streaming support
- Working in polyglot environments (code generation for many languages)

**Choose Kafka when**:
- Need high-throughput event streaming
- Building event-driven architectures
- Require durable message logs
- Need exactly-once processing guarantees

**Choose RabbitMQ when**:
- Need flexible routing patterns
- Want mature AMQP implementation
- Require priority queues and message TTL
- Building traditional work queues

**Choose MQTT when**:
- Working with IoT devices
- Need lightweight protocol for constrained networks
- Implementing pub-sub for sensors/actuators
- Require different QoS levels per message

**Choose WebSockets when**:
- Need bidirectional browser communication
- Building real-time web applications
- Want simple persistent connections
- Implementing chat, notifications, or collaborative features

**HTTP/2 vs HTTP/1.1**:
- HTTP/2 for modern applications (multiplexing, server push)
- Requires TLS for browser support
- Better performance for multiple resources
- Backward compatible at application layer

**TCP Optimization priorities**:
- Cloud environments: Tune for latency and bandwidth product
- Containerized apps: Adjust kernel parameters
- High-throughput: Focus on congestion control algorithms
- Low-latency: Minimize buffering and enable TCP_NODELAY

---

## Loading Skills

All skills are available in the `skills/protocols/` directory:

```bash
cat skills/protocols/grpc-implementation.md
cat skills/protocols/http2-multiplexing.md
cat skills/protocols/kafka-streams.md
cat skills/protocols/mqtt-messaging.md
cat skills/protocols/amqp-rabbitmq.md
cat skills/protocols/protobuf-schemas.md
cat skills/protocols/tcp-optimization.md
cat skills/protocols/websocket-protocols.md
```

**Pro tip**: Start with protocol selection based on your use case, then load specific implementation guides. Combine with infrastructure skills for production deployment.

---

**Related Categories**:
- `discover-api` - API design and implementation
- `discover-database` - Data persistence and streaming
- `discover-infrastructure` - Deployment and scaling
- `discover-frontend` - Client-side integration
- `discover-debugging` - Network debugging and monitoring
