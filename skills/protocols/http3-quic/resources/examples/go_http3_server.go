// Go HTTP/3 Server using quic-go
// Production-ready HTTP/3 server implementation
//
// Install dependencies:
//   go get github.com/quic-go/quic-go/http3
//
// Generate TLS certificates:
//   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
//
// Run:
//   go run go_http3_server.go
//
// Test:
//   curl --http3 https://localhost:4433
//   curl --http3 https://localhost:4433/api/data
//   curl --http3 https://localhost:4433/stream

package main

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/quic-go/quic-go"
	"github.com/quic-go/quic-go/http3"
)

// Server represents HTTP/3 server
type Server struct {
	addr      string
	certFile  string
	keyFile   string
	tlsConfig *tls.Config
	metrics   *Metrics
}

// Metrics tracks server statistics
type Metrics struct {
	mu               sync.RWMutex
	totalRequests    int64
	activeConnections int64
	bytesReceived    int64
	bytesSent        int64
}

func (m *Metrics) IncrementRequests() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.totalRequests++
}

func (m *Metrics) IncrementConnection() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.activeConnections++
}

func (m *Metrics) DecrementConnection() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.activeConnections--
}

func (m *Metrics) AddBytes(received, sent int64) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.bytesReceived += received
	m.bytesSent += sent
}

func (m *Metrics) Get() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	return map[string]interface{}{
		"total_requests":     m.totalRequests,
		"active_connections": m.activeConnections,
		"bytes_received":     m.bytesReceived,
		"bytes_sent":         m.bytesSent,
	}
}

// NewServer creates a new HTTP/3 server
func NewServer(addr, certFile, keyFile string) (*Server, error) {
	cert, err := tls.LoadX509KeyPair(certFile, keyFile)
	if err != nil {
		return nil, fmt.Errorf("failed to load certificates: %w", err)
	}

	tlsConfig := &tls.Config{
		Certificates: []tls.Certificate{cert},
		NextProtos:   []string{"h3"},
		MinVersion:   tls.VersionTLS13, // QUIC requires TLS 1.3
	}

	return &Server{
		addr:      addr,
		certFile:  certFile,
		keyFile:   keyFile,
		tlsConfig: tlsConfig,
		metrics:   &Metrics{},
	}, nil
}

// Start starts the HTTP/3 server
func (s *Server) Start() error {
	mux := http.NewServeMux()

	// Register handlers
	mux.HandleFunc("/", s.handleHome)
	mux.HandleFunc("/api/data", s.handleAPI)
	mux.HandleFunc("/stream", s.handleStream)
	mux.HandleFunc("/metrics", s.handleMetrics)
	mux.HandleFunc("/health", s.handleHealth)

	// Wrap with middleware
	handler := s.loggingMiddleware(s.metricsMiddleware(mux))

	// Configure QUIC
	quicConfig := &quic.Config{
		MaxIdleTimeout:                 5 * time.Minute,
		MaxIncomingStreams:             100,
		MaxIncomingUniStreams:          10,
		InitialStreamReceiveWindow:     1024 * 1024,     // 1 MB
		MaxStreamReceiveWindow:         6 * 1024 * 1024, // 6 MB
		InitialConnectionReceiveWindow: 1024 * 1024,     // 1 MB
		MaxConnectionReceiveWindow:     15 * 1024 * 1024, // 15 MB
		KeepAlivePeriod:                30 * time.Second,
		EnableDatagrams:                false,
	}

	// Create HTTP/3 server
	server := &http3.Server{
		Addr:       s.addr,
		Handler:    handler,
		TLSConfig:  s.tlsConfig,
		QuicConfig: quicConfig,
	}

	log.Printf("Starting HTTP/3 server on %s", s.addr)
	log.Printf("Test with: curl --http3 https://localhost%s", s.addr)

	return server.ListenAndServe()
}

// Middleware: logging
func (s *Server) loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()

		log.Printf("[%s] %s %s", r.Method, r.URL.Path, r.Proto)

		next.ServeHTTP(w, r)

		log.Printf("[%s] %s completed in %v", r.Method, r.URL.Path, time.Since(start))
	})
}

// Middleware: metrics
func (s *Server) metricsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		s.metrics.IncrementRequests()
		next.ServeHTTP(w, r)
	})
}

// Handler: home page
func (s *Server) handleHome(w http.ResponseWriter, r *http.Request) {
	html := `<!DOCTYPE html>
<html>
<head>
    <title>HTTP/3 Server (Go)</title>
</head>
<body>
    <h1>HTTP/3 Server (Go + quic-go)</h1>
    <p>Protocol: %s</p>
    <p>Server Time: %s</p>

    <h2>Endpoints</h2>
    <ul>
        <li><a href="/api/data">/api/data</a> - JSON data</li>
        <li><a href="/stream">/stream</a> - Server-sent events</li>
        <li><a href="/metrics">/metrics</a> - Server metrics</li>
        <li><a href="/health">/health</a> - Health check</li>
    </ul>
</body>
</html>`

	w.Header().Set("Content-Type", "text/html")
	w.Header().Set("Alt-Svc", `h3=":4433"; ma=86400`)

	fmt.Fprintf(w, html, r.Proto, time.Now().Format(time.RFC3339))
}

// Handler: API endpoint
func (s *Server) handleAPI(w http.ResponseWriter, r *http.Request) {
	data := map[string]interface{}{
		"timestamp": time.Now().Unix(),
		"message":   "Hello from HTTP/3",
		"protocol":  r.Proto,
		"method":    r.Method,
		"path":      r.URL.Path,
		"headers":   r.Header,
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Alt-Svc", `h3=":4433"; ma=86400`)

	json.NewEncoder(w).Encode(data)
}

// Handler: server-sent events stream
func (s *Server) handleStream(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming not supported", http.StatusInternalServerError)
		return
	}

	// Send events
	for i := 0; i < 10; i++ {
		event := map[string]interface{}{
			"id":        i,
			"timestamp": time.Now().Unix(),
			"message":   fmt.Sprintf("Event %d", i),
		}

		data, _ := json.Marshal(event)
		fmt.Fprintf(w, "data: %s\n\n", data)
		flusher.Flush()

		time.Sleep(1 * time.Second)
	}
}

// Handler: metrics endpoint
func (s *Server) handleMetrics(w http.ResponseWriter, r *http.Request) {
	metrics := s.metrics.Get()
	metrics["timestamp"] = time.Now().Unix()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(metrics)
}

// Handler: health check
func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	fmt.Fprint(w, "OK\n")
}

func main() {
	// Configuration
	addr := ":4433"
	certFile := "cert.pem"
	keyFile := "key.pem"

	// Create server
	server, err := NewServer(addr, certFile, keyFile)
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	// Start server
	if err := server.Start(); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}

/*
Generate self-signed certificate:

openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

Test the server:

# Basic request
curl --http3 https://localhost:4433

# API endpoint
curl --http3 https://localhost:4433/api/data | jq

# Stream
curl --http3 -N https://localhost:4433/stream

# Metrics
curl --http3 https://localhost:4433/metrics | jq

# Health check
curl --http3 https://localhost:4433/health

Performance testing:

# With hey (HTTP load testing tool)
hey -n 10000 -c 100 -h2 https://localhost:4433

# Compare HTTP/3 vs HTTP/2
curl -w "@curl-format.txt" --http3 https://localhost:4433
curl -w "@curl-format.txt" --http2 https://localhost:4433

Production deployment notes:

1. Use valid TLS certificates (Let's Encrypt)
2. Configure firewall to allow UDP port 4433
3. Increase UDP buffer sizes:
   sysctl -w net.core.rmem_max=2500000
   sysctl -w net.core.wmem_max=2500000
4. Monitor QUIC connections:
   ss -u -a | grep :4433
5. Enable logging and metrics collection
6. Configure load balancing for multiple instances
7. Test connection migration (WiFi ↔ cellular)
*/
