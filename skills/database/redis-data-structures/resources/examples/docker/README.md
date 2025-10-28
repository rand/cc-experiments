# Redis Docker Examples

This directory contains Docker Compose configurations for various Redis setups.

## Quick Start

### Basic Redis Instance

Start a basic Redis server with persistence:

```bash
docker-compose up redis
```

Connect to it:

```bash
redis-cli -h localhost -p 6379
```

### Redis with Custom Configuration

Start Redis with custom configuration (password, memory limits, etc.):

```bash
docker-compose up redis-configured
```

Connect with password:

```bash
redis-cli -h localhost -p 6380 -a strongpassword
```

### Redis with Replication

Start master and replicas:

```bash
docker-compose up redis-master redis-replica-1 redis-replica-2
```

Check replication status:

```bash
redis-cli -h localhost -p 6381 INFO replication
```

### Redis Sentinel (High Availability)

Start master, replicas, and sentinels:

```bash
docker-compose up redis-master redis-replica-1 redis-replica-2 sentinel-1 sentinel-2 sentinel-3
```

Check sentinel status:

```bash
redis-cli -h localhost -p 26379 SENTINEL masters
redis-cli -h localhost -p 26379 SENTINEL replicas mymaster
```

### Redis Cluster

Start all cluster nodes:

```bash
docker-compose up redis-cluster-1 redis-cluster-2 redis-cluster-3 \
                  redis-cluster-4 redis-cluster-5 redis-cluster-6
```

Create the cluster (run after nodes are up):

```bash
docker exec -it redis-cluster-1 redis-cli --cluster create \
  redis-cluster-1:7000 redis-cluster-2:7001 redis-cluster-3:7002 \
  redis-cluster-4:7003 redis-cluster-5:7004 redis-cluster-6:7005 \
  --cluster-replicas 1 --cluster-yes
```

Connect to cluster:

```bash
redis-cli -c -h localhost -p 7000
```

### Web Management Tools

#### Redis Commander

```bash
docker-compose up redis redis-commander
```

Access at: http://localhost:8081

#### Redis Insight

```bash
docker-compose up redis redis-insight
```

Access at: http://localhost:8001

## Services Overview

| Service | Port | Description |
|---------|------|-------------|
| redis | 6379 | Basic Redis with persistence |
| redis-configured | 6380 | Redis with custom config and password |
| redis-master | 6381 | Replication master |
| redis-replica-1 | 6382 | Replica 1 |
| redis-replica-2 | 6383 | Replica 2 |
| sentinel-1 | 26379 | Sentinel 1 |
| sentinel-2 | 26380 | Sentinel 2 |
| sentinel-3 | 26381 | Sentinel 3 |
| redis-cluster-1 | 7000 | Cluster node 1 |
| redis-cluster-2 | 7001 | Cluster node 2 |
| redis-cluster-3 | 7002 | Cluster node 3 |
| redis-cluster-4 | 7003 | Cluster node 4 |
| redis-cluster-5 | 7004 | Cluster node 5 |
| redis-cluster-6 | 7005 | Cluster node 6 |
| redis-commander | 8081 | Web UI |
| redis-insight | 8001 | Official Redis UI |

## Configuration Files

- `redis.conf`: Custom Redis configuration
- `sentinel.conf`: Sentinel configuration

## Data Persistence

All Redis instances use Docker volumes for data persistence:

```bash
# List volumes
docker volume ls | grep redis

# Inspect volume
docker volume inspect redis_data

# Remove all volumes (WARNING: deletes all data)
docker-compose down -v
```

## Useful Commands

### Monitoring

```bash
# Monitor commands in real-time
redis-cli -h localhost -p 6379 MONITOR

# View stats
redis-cli -h localhost -p 6379 INFO

# View memory usage
redis-cli -h localhost -p 6379 INFO memory

# View clients
redis-cli -h localhost -p 6379 CLIENT LIST
```

### Replication

```bash
# Check replication status (on master)
redis-cli -h localhost -p 6381 INFO replication

# Check replication status (on replica)
redis-cli -h localhost -p 6382 INFO replication

# Manually promote replica to master
redis-cli -h localhost -p 6382 REPLICAOF NO ONE
```

### Sentinel

```bash
# List masters
redis-cli -h localhost -p 26379 SENTINEL masters

# List replicas
redis-cli -h localhost -p 26379 SENTINEL replicas mymaster

# Get master address
redis-cli -h localhost -p 26379 SENTINEL get-master-addr-by-name mymaster

# Manual failover
redis-cli -h localhost -p 26379 SENTINEL failover mymaster
```

### Cluster

```bash
# Check cluster info
redis-cli -c -h localhost -p 7000 CLUSTER INFO

# List cluster nodes
redis-cli -c -h localhost -p 7000 CLUSTER NODES

# Check slots
redis-cli -c -h localhost -p 7000 CLUSTER SLOTS

# Add node to cluster
redis-cli --cluster add-node new-node-ip:port existing-node-ip:port

# Reshard cluster
redis-cli --cluster reshard node-ip:port

# Check cluster health
redis-cli --cluster check node-ip:port
```

## Troubleshooting

### Can't connect to Redis

Check if container is running:

```bash
docker ps | grep redis
```

Check logs:

```bash
docker logs redis
```

### Replication not working

Check master logs:

```bash
docker logs redis-master
```

Check replica logs:

```bash
docker logs redis-replica-1
```

Verify network connectivity:

```bash
docker exec redis-replica-1 ping redis-master
```

### Cluster creation fails

Ensure all nodes are running:

```bash
docker ps | grep redis-cluster
```

Check if nodes can reach each other:

```bash
docker exec redis-cluster-1 redis-cli -h redis-cluster-2 -p 7001 PING
```

### Sentinel not detecting master

Check sentinel logs:

```bash
docker logs sentinel-1
```

Verify sentinel configuration:

```bash
docker exec sentinel-1 cat /usr/local/etc/redis/sentinel.conf
```

## Production Considerations

1. **Security**: Set strong passwords using `requirepass`
2. **Memory**: Configure `maxmemory` and eviction policy
3. **Persistence**: Choose appropriate RDB/AOF settings
4. **Monitoring**: Use Redis Insight or external tools
5. **Backups**: Regular backups of RDB/AOF files
6. **Network**: Use proper firewall rules
7. **Resources**: Allocate sufficient CPU and RAM
8. **High Availability**: Use Sentinel or Cluster for HA

## Cleanup

Stop all services:

```bash
docker-compose down
```

Remove all data (WARNING: deletes everything):

```bash
docker-compose down -v
```

Remove specific volume:

```bash
docker volume rm redis_data
```
