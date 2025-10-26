---
name: mtls-implementation
description: Implementing mutual TLS authentication
---



# mTLS Implementation

**Use this skill when:**
- Implementing mutual TLS authentication
- Securing service-to-service communication
- Building zero-trust architectures
- Verifying client and server identities
- Replacing API keys with certificates

## Certificate Generation

### Create CA and Certificates

```bash
# Create Certificate Authority
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 365 -key ca-key.pem -out ca-cert.pem \
  -subj "/CN=My CA"

# Create server certificate
openssl genrsa -out server-key.pem 4096
openssl req -new -key server-key.pem -out server-csr.pem \
  -subj "/CN=server.example.com"
openssl x509 -req -days 365 -in server-csr.pem \
  -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial \
  -out server-cert.pem

# Create client certificate
openssl genrsa -out client-key.pem 4096
openssl req -new -key client-key.pem -out client-csr.pem \
  -subj "/CN=client.example.com"
openssl x509 -req -days 365 -in client-csr.pem \
  -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial \
  -out client-cert.pem
```

## Python Implementation

### mTLS Server (Flask)

```python
from flask import Flask, request
import ssl

app = Flask(__name__)

@app.route('/api/data')
def get_data():
    # Client certificate available in request
    client_cert = request.environ.get('peercert')
    client_cn = dict(x[0] for x in client_cert['subject'])['commonName']

    return {
        "message": "Authenticated!",
        "client": client_cn
    }

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Load server certificate
    context.load_cert_chain('server-cert.pem', 'server-key.pem')

    # Require client certificate
    context.verify_mode = ssl.CERT_REQUIRED

    # Load CA to verify clients
    context.load_verify_locations('ca-cert.pem')

    app.run(host='0.0.0.0', port=8443, ssl_context=context)
```

### mTLS Client (requests)

```python
import requests

response = requests.get(
    'https://server.example.com:8443/api/data',
    cert=('client-cert.pem', 'client-key.pem'),
    verify='ca-cert.pem'
)

print(response.json())
```

## Go Implementation

### mTLS Server

```go
package main

import (
    "crypto/tls"
    "crypto/x509"
    "fmt"
    "io/ioutil"
    "log"
    "net/http"
)

func handler(w http.ResponseWriter, r *http.Request) {
    // Extract client certificate
    if r.TLS != nil && len(r.TLS.PeerCertificates) > 0 {
        clientCert := r.TLS.PeerCertificates[0]
        fmt.Fprintf(w, "Hello %s\n", clientCert.Subject.CommonName)
    } else {
        http.Error(w, "No client certificate", http.StatusUnauthorized)
    }
}

func main() {
    // Load CA cert
    caCert, err := ioutil.ReadFile("ca-cert.pem")
    if err != nil {
        log.Fatal(err)
    }

    caCertPool := x509.NewCertPool()
    caCertPool.AppendCertsFromPEM(caCert)

    // Configure TLS
    tlsConfig := &tls.Config{
        ClientCAs:  caCertPool,
        ClientAuth: tls.RequireAndVerifyClientCert,
    }

    server := &http.Server{
        Addr:      ":8443",
        TLSConfig: tlsConfig,
    }

    http.HandleFunc("/", handler)

    log.Fatal(server.ListenAndServeTLS("server-cert.pem", "server-key.pem"))
}
```

### mTLS Client

```go
package main

import (
    "crypto/tls"
    "crypto/x509"
    "io/ioutil"
    "log"
    "net/http"
)

func main() {
    // Load client cert
    cert, err := tls.LoadX509KeyPair("client-cert.pem", "client-key.pem")
    if err != nil {
        log.Fatal(err)
    }

    // Load CA cert
    caCert, err := ioutil.ReadFile("ca-cert.pem")
    if err != nil {
        log.Fatal(err)
    }

    caCertPool := x509.NewCertPool()
    caCertPool.AppendCertsFromPEM(caCert)

    // Configure TLS
    tlsConfig := &tls.Config{
        Certificates: []tls.Certificate{cert},
        RootCAs:      caCertPool,
    }

    client := &http.Client{
        Transport: &http.Transport{
            TLSClientConfig: tlsConfig,
        },
    }

    resp, err := client.Get("https://server.example.com:8443/")
    if err != nil {
        log.Fatal(err)
    }
    defer resp.Body.Close()

    body, _ := ioutil.ReadAll(resp.Body)
    log.Printf("Response: %s", body)
}
```

## Rust Implementation

### mTLS Server (Actix-web)

```rust
use actix_web::{web, App, HttpRequest, HttpServer};
use openssl::ssl::{SslAcceptor, SslFiletype, SslMethod, SslVerifyMode};

async fn handler(req: HttpRequest) -> String {
    if let Some(cert) = req.peer_cert() {
        format!("Hello from mTLS! Client: {:?}", cert.subject_name())
    } else {
        "No certificate".to_string()
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let mut builder = SslAcceptor::mozilla_intermediate(SslMethod::tls())?;

    builder.set_private_key_file("server-key.pem", SslFiletype::PEM)?;
    builder.set_certificate_chain_file("server-cert.pem")?;
    builder.set_ca_file("ca-cert.pem")?;

    builder.set_verify(SslVerifyMode::PEER | SslVerifyMode::FAIL_IF_NO_PEER_CERT);

    HttpServer::new(|| App::new().route("/", web::get().to(handler)))
        .bind_openssl("0.0.0.0:8443", builder)?
        .run()
        .await
}
```

## Service Mesh Pattern

### Envoy Sidecar

```yaml
# envoy.yaml
static_resources:
  listeners:
  - name: listener_mtls
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8443
    filter_chains:
    - transport_socket:
        name: envoy.transport_sockets.tls
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
          require_client_certificate: true
          common_tls_context:
            tls_certificates:
            - certificate_chain:
                filename: "/etc/certs/server-cert.pem"
              private_key:
                filename: "/etc/certs/server-key.pem"
            validation_context:
              trusted_ca:
                filename: "/etc/certs/ca-cert.pem"
```

## Certificate Rotation

### Automated Rotation

```python
import os
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CertReloader(FileSystemEventHandler):
    def __init__(self, server):
        self.server = server

    def on_modified(self, event):
        if event.src_path.endswith('.pem'):
            print(f"Certificate changed: {event.src_path}")
            self.server.reload_certs()

class MTLSServer:
    def __init__(self):
        self.load_certs()

    def load_certs(self):
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain('server-cert.pem', 'server-key.pem')
        self.context.verify_mode = ssl.CERT_REQUIRED
        self.context.load_verify_locations('ca-cert.pem')

    def reload_certs(self):
        print("Reloading certificates...")
        self.load_certs()

# Watch for cert changes
observer = Observer()
observer.schedule(CertReloader(server), path='/etc/certs', recursive=False)
observer.start()
```

## Anti-Patterns to Avoid

**DON'T skip certificate verification:**
```python
# ❌ BAD
requests.get(url, verify=False)

# ✅ GOOD
requests.get(url, verify='ca-cert.pem')
```

**DON'T use self-signed certs in production without CA:**
```bash
# ❌ BAD - No verification possible
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem

# ✅ GOOD - Use CA
# Create CA first, then sign certs with it
```

## Related Skills

- **tailscale-vpn.md** - Combine Tailscale with mTLS
- **secure-networking.md** - Overall security patterns
