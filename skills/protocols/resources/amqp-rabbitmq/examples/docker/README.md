# RabbitMQ Cluster with HA and Monitoring

Production-ready RabbitMQ cluster setup with high availability, load balancing, and monitoring.

## Architecture

- **3-node RabbitMQ cluster**: Provides high availability
- **HAProxy**: Load balances AMQP and Management connections
- **Prometheus**: Collects metrics from RabbitMQ nodes
- **Grafana**: Visualizes metrics with dashboards

## Quick Start

```bash
# Start cluster
docker-compose up -d

# Check cluster status
docker exec rabbitmq1 rabbitmqctl cluster_status

# View logs
docker-compose logs -f rabbitmq1

# Access services
# - RabbitMQ Management: http://localhost:15672 (admin/admin)
# - HAProxy Stats: http://localhost:8080
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)

# Connect via load balancer
# amqp://admin:admin@localhost:5673
```

## Testing HA

```bash
# Publish messages
docker exec rabbitmq1 rabbitmqadmin publish exchange=amq.default routing_key=test payload="Test message"

# Stop node 1
docker stop rabbitmq1

# Messages still accessible via nodes 2 and 3

# Restart node 1
docker start rabbitmq1

# Node automatically rejoins cluster
```

## Monitoring

### Prometheus Metrics

Access Prometheus at http://localhost:9090

Key metrics:
- `rabbitmq_queue_messages` - Queue depth
- `rabbitmq_connections` - Active connections
- `rabbitmq_process_resident_memory_bytes` - Memory usage

### Grafana Dashboards

Access Grafana at http://localhost:3000 (admin/admin)

Import RabbitMQ dashboard:
1. Go to Dashboards → Import
2. Enter dashboard ID: 10991
3. Select Prometheus datasource

## Configuration

### Queue Policies

Create quorum queue policy:
```bash
docker exec rabbitmq1 rabbitmqctl set_policy ha-all "^ha\\." \
  '{"ha-mode":"all","ha-sync-mode":"automatic"}' --apply-to queues
```

### Resource Limits

Adjust in `rabbitmq.conf`:
- `vm_memory_high_watermark.relative` - Memory threshold
- `disk_free_limit.absolute` - Disk threshold

## Cleanup

```bash
# Stop and remove all containers
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v
```

## Production Considerations

1. **Security**:
   - Change default credentials
   - Enable TLS for AMQP and Management
   - Use firewall rules

2. **Resources**:
   - Allocate at least 2GB RAM per node
   - Use SSD storage
   - Monitor disk I/O

3. **Networking**:
   - Use private network in production
   - Configure proper DNS
   - Tune TCP settings

4. **Backup**:
   - Backup queue definitions
   - Backup user permissions
   - Backup policies

5. **Monitoring**:
   - Set alerts for queue depth
   - Monitor memory/disk usage
   - Track connection count
