#!/bin/bash
#
# Generate TLS Certificates for MQTT
#
# This script generates:
# - CA certificate (ca.crt, ca.key)
# - Server certificate (server.crt, server.key)
# - Client certificate (client.crt, client.key)
#
# Usage:
#   ./generate_certs.sh [hostname]
#   ./generate_certs.sh mqtt.example.com

set -e

HOSTNAME="${1:-mqtt.example.com}"
VALIDITY_DAYS=365

echo "Generating TLS certificates for $HOSTNAME..."
echo

# Create directories
mkdir -p certs
cd certs

# 1. Generate CA certificate
echo "[1/3] Generating CA certificate..."
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
  -subj "/C=US/ST=State/L=City/O=MQTT/CN=MQTT CA"

echo "  ✓ CA certificate: ca.crt, ca.key"
echo

# 2. Generate server certificate
echo "[2/3] Generating server certificate for $HOSTNAME..."
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
  -subj "/C=US/ST=State/L=City/O=MQTT/CN=$HOSTNAME"

# Sign server certificate with CA
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days $VALIDITY_DAYS

rm server.csr

echo "  ✓ Server certificate: server.crt, server.key"
echo

# 3. Generate client certificate
echo "[3/3] Generating client certificate..."
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr \
  -subj "/C=US/ST=State/L=City/O=MQTT/CN=mqtt_client"

# Sign client certificate with CA
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out client.crt -days $VALIDITY_DAYS

rm client.csr

echo "  ✓ Client certificate: client.crt, client.key"
echo

# List generated files
echo "Generated files:"
ls -lh

echo
echo "✓ Certificate generation complete!"
echo
echo "Mosquitto configuration:"
echo "  listener 8883"
echo "  cafile $(pwd)/ca.crt"
echo "  certfile $(pwd)/server.crt"
echo "  keyfile $(pwd)/server.key"
echo "  tls_version tlsv1.2"
echo
echo "Test with mosquitto_pub:"
echo "  mosquitto_pub -h $HOSTNAME -p 8883 -t test/topic -m \"hello\" \\"
echo "    --cafile $(pwd)/ca.crt \\"
echo "    --cert $(pwd)/client.crt \\"
echo "    --key $(pwd)/client.key"
echo
echo "Test with mosquitto_sub:"
echo "  mosquitto_sub -h $HOSTNAME -p 8883 -t test/# -v \\"
echo "    --cafile $(pwd)/ca.crt \\"
echo "    --cert $(pwd)/client.crt \\"
echo "    --key $(pwd)/client.key"
