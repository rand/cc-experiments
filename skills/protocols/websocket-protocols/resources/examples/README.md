# WebSocket Production Examples

This directory contains production-ready WebSocket implementations and configurations.

## Examples Overview

### 1. Python Server (`python/`)
Complete WebSocket server with:
- Authentication (JWT)
- Rate limiting
- Connection management
- Broadcast messaging
- Graceful shutdown

**Usage**:
```bash
cd python
pip install websockets pyjwt
python websocket_server.py --host 0.0.0.0 --port 8765
```

### 2. Node.js Server (`nodejs/`)
Production Node.js WebSocket server with:
- Connection tracking
- Heartbeat monitoring
- Message routing
- Error handling

**Usage**:
```bash
cd nodejs
npm install ws
node server.js
```

### 3. React Client (`react/`)
React hook for WebSocket connections with:
- Automatic reconnection
- Exponential backoff
- Message queue
- Connection state management

**Usage**:
```javascript
import useWebSocket from './useWebSocket';

const { isConnected, sendMessage } = useWebSocket('wss://example.com/ws');
```

### 4. nginx Configuration (`nginx/`)
Production nginx configuration for WebSocket proxying:
- TLS/SSL termination
- Sticky sessions (ip_hash)
- Load balancing
- Connection limits
- Proper timeouts

**Usage**:
```bash
# Test configuration
nginx -t -c nginx/websocket.conf

# Reload
nginx -s reload
```

### 5. HAProxy Configuration (`haproxy/`)
HAProxy load balancer configuration:
- WebSocket ACL routing
- Source-based sticky sessions
- Health checks
- TLS termination

**Usage**:
```bash
haproxy -f haproxy/haproxy.cfg -c  # Test
haproxy -f haproxy/haproxy.cfg      # Run
```

### 6. Redis Pub/Sub Scaling (`redis-scaling/`)
Horizontally scalable WebSocket server using Redis:
- Multi-instance support
- Global broadcasting
- Server-to-server communication

**Usage**:
```bash
# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Start multiple server instances
python redis_pubsub_server.py --port 8765 --server-id ws-1
python redis_pubsub_server.py --port 8766 --server-id ws-2
```

### 7. Docker Compose Cluster (`docker/`)
Complete production cluster:
- 3x WebSocket backend servers
- Redis for pub/sub
- nginx load balancer
- Prometheus monitoring
- Grafana dashboards

**Usage**:
```bash
cd docker
docker-compose up -d

# View logs
docker-compose logs -f

# Scale servers
docker-compose up -d --scale websocket=5
```

**Access**:
- WebSocket: `ws://localhost/ws`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (admin/admin)

### 8. Prometheus Monitoring (`monitoring/`)
WebSocket server with comprehensive metrics:
- Active connections
- Message throughput
- Latency histograms
- Error rates
- Connection duration

**Usage**:
```bash
cd monitoring
pip install prometheus-client websockets
python prometheus_metrics.py
```

**Metrics endpoint**: `http://localhost:9090/metrics`

**Key metrics**:
- `websocket_connections_total` - Active connections
- `websocket_messages_sent_total` - Messages sent
- `websocket_messages_received_total` - Messages received
- `websocket_message_latency_seconds` - Processing latency
- `websocket_errors_total` - Error counts by type

## Testing Examples

### Test Connection
```bash
# Using wscat
wscat -c ws://localhost:8080

# Using websocat
websocat ws://localhost:8080

# Using Python
python -c "
import asyncio
import websockets

async def test():
    async with websockets.connect('ws://localhost:8080') as ws:
        await ws.send('Hello')
        print(await ws.recv())

asyncio.run(test())
"
```

### Load Testing
```bash
# From scripts directory
cd ../scripts
./benchmark_websocket.py --url ws://localhost:8080 --connections 1000 --duration 60
```

## Production Checklist

When deploying to production:

- [ ] Enable TLS/SSL (wss://)
- [ ] Configure sticky sessions on load balancer
- [ ] Set appropriate timeouts (7d recommended)
- [ ] Enable heartbeat/ping (30s interval)
- [ ] Implement authentication
- [ ] Add rate limiting
- [ ] Configure connection limits
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Enable logging
- [ ] Configure health checks
- [ ] Test failover scenarios
- [ ] Document error codes
- [ ] Set up alerting
- [ ] Plan capacity (connections per server)
- [ ] Configure auto-scaling

## Security Considerations

1. **Always use wss:// in production**
2. **Validate Origin header** to prevent CSRF
3. **Implement authentication** (JWT, OAuth, session)
4. **Rate limit** connections and messages
5. **Validate and sanitize** all input
6. **Set message size limits**
7. **Use secure WebSocket libraries** (up-to-date)
8. **Monitor for** anomalies and attacks
9. **Implement connection limits** per IP
10. **Log security events**

## Troubleshooting

### Connection Fails
- Check firewall rules
- Verify server is running
- Test with wscat/websocat
- Check nginx/HAProxy logs
- Verify WebSocket upgrade headers

### Random Disconnections
- Check timeout settings
- Enable ping/pong heartbeat
- Review server logs for errors
- Monitor resource usage (CPU, memory)

### Messages Not Broadcasting
- Verify Redis connection (if using pub/sub)
- Check sticky session configuration
- Review server logs
- Test with single server first

### High Latency
- Check network between client/server
- Monitor server CPU/memory
- Review message size
- Check for blocking operations
- Enable compression if appropriate

## Resources

- **Scripts**: `../scripts/` - Validation, testing, benchmarking tools
- **Reference**: `../REFERENCE.md` - Complete protocol documentation
- **Main Skill**: `../../websocket-protocols.md` - Skill overview

## Support

For issues or questions:
1. Check REFERENCE.md for detailed documentation
2. Review script help: `script.py --help`
3. Test with validation scripts
4. Check server logs
5. Monitor metrics (if Prometheus enabled)
