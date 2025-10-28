package main

/*
Go HTTP Server with Prometheus Metrics

Demonstrates comprehensive Prometheus instrumentation for a Go HTTP server
including middleware, custom metrics, and best practices.

Usage:
	go mod init example
	go get github.com/prometheus/client_golang/prometheus
	go get github.com/prometheus/client_golang/prometheus/promhttp
	go get github.com/prometheus/client_golang/prometheus/promauto
	go run http_metrics.go

Metrics available at: http://localhost:8080/metrics
*/

import (
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"runtime"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// ============================================================================
// HTTP Request Metrics
// ============================================================================

var (
	httpRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total HTTP requests",
		},
		[]string{"method", "endpoint", "status"},
	)

	httpRequestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "HTTP request latency in seconds",
			Buckets: []float64{0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0},
		},
		[]string{"method", "endpoint"},
	)

	httpRequestsInProgress = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "http_requests_in_progress",
			Help: "Number of HTTP requests in progress",
		},
		[]string{"method", "endpoint"},
	)

	httpRequestSize = promauto.NewSummaryVec(
		prometheus.SummaryOpts{
			Name: "http_request_size_bytes",
			Help: "HTTP request size in bytes",
		},
		[]string{"method", "endpoint"},
	)

	httpResponseSize = promauto.NewSummaryVec(
		prometheus.SummaryOpts{
			Name: "http_response_size_bytes",
			Help: "HTTP response size in bytes",
		},
		[]string{"method", "endpoint"},
	)
)

// ============================================================================
// Application Info
// ============================================================================

var (
	appInfo = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "app_info",
			Help: "Application information",
		},
		[]string{"version", "go_version"},
	)
)

func init() {
	appInfo.WithLabelValues("1.0.0", runtime.Version()).Set(1)
}

// ============================================================================
// Business Metrics
// ============================================================================

var (
	userLoginTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "user_login_total",
			Help: "Total user logins",
		},
		[]string{"status"},
	)

	userSessionsActive = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "user_sessions_active",
			Help: "Number of active user sessions",
		},
	)

	orderValueDollars = promauto.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "order_value_dollars",
			Help:    "Order value in dollars",
			Buckets: []float64{1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000},
		},
	)

	ordersTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "orders_total",
			Help: "Total orders processed",
		},
		[]string{"product_category", "payment_method"},
	)

	databaseQueriesTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "database_queries_total",
			Help: "Total database queries",
		},
		[]string{"operation", "table"},
	)

	databaseQueryDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "database_query_duration_seconds",
			Help:    "Database query duration",
			Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0},
		},
		[]string{"operation", "table"},
	)

	cacheOperationsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "cache_operations_total",
			Help: "Total cache operations",
		},
		[]string{"operation", "result"},
	)
)

// ============================================================================
// System Metrics
// ============================================================================

var (
	processGoroutines = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "process_goroutines",
			Help: "Number of goroutines",
		},
	)

	processMemoryBytes = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "process_memory_bytes",
			Help: "Process memory usage in bytes",
		},
	)
)

func updateSystemMetrics() {
	var m runtime.MemStats
	runtime.ReadMemStats(&m)

	processGoroutines.Set(float64(runtime.NumGoroutine()))
	processMemoryBytes.Set(float64(m.Alloc))
}

// ============================================================================
// Middleware
// ============================================================================

type responseWriter struct {
	http.ResponseWriter
	statusCode int
	size       int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}

func (rw *responseWriter) Write(b []byte) (int, error) {
	size, err := rw.ResponseWriter.Write(b)
	rw.size += size
	return size, err
}

func metricsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()

		// Normalize endpoint
		endpoint := r.URL.Path

		// Increment in-progress gauge
		httpRequestsInProgress.WithLabelValues(r.Method, endpoint).Inc()
		defer httpRequestsInProgress.WithLabelValues(r.Method, endpoint).Dec()

		// Track request size
		httpRequestSize.WithLabelValues(r.Method, endpoint).Observe(float64(r.ContentLength))

		// Wrap response writer
		rw := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}

		// Process request
		next.ServeHTTP(rw, r)

		// Calculate duration
		duration := time.Since(start).Seconds()

		// Record metrics
		httpRequestsTotal.WithLabelValues(
			r.Method,
			endpoint,
			http.StatusText(rw.statusCode),
		).Inc()

		httpRequestDuration.WithLabelValues(
			r.Method,
			endpoint,
		).Observe(duration)

		// Track response size
		httpResponseSize.WithLabelValues(r.Method, endpoint).Observe(float64(rw.size))
	})
}

// ============================================================================
// Database Query Tracker
// ============================================================================

func trackDBQuery(operation, table string, fn func()) {
	start := time.Now()

	defer func() {
		duration := time.Since(start).Seconds()

		databaseQueriesTotal.WithLabelValues(operation, table).Inc()
		databaseQueryDuration.WithLabelValues(operation, table).Observe(duration)
	}()

	fn()
}

// ============================================================================
// Handlers
// ============================================================================

func indexHandler(w http.ResponseWriter, r *http.Request) {
	response := map[string]interface{}{
		"name":        "Go Metrics Demo",
		"version":     "1.0.0",
		"metrics_url": "/metrics",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getUsersHandler(w http.ResponseWriter, r *http.Request) {
	// Check cache (simulated)
	cacheHit := rand.Float32() > 0.3

	cacheOp := "miss"
	if cacheHit {
		cacheOp = "hit"
	}
	cacheOperationsTotal.WithLabelValues("get", cacheOp).Inc()

	var users []map[string]interface{}

	if !cacheHit {
		// Simulate database query
		trackDBQuery("select", "users", func() {
			time.Sleep(time.Duration(rand.Intn(50)) * time.Millisecond)
		})

		users = []map[string]interface{}{
			{"id": 1, "name": "Alice"},
			{"id": 2, "name": "Bob"},
		}

		// Cache result
		cacheOperationsTotal.WithLabelValues("set", "success").Inc()
	} else {
		users = []map[string]interface{}{
			{"id": 1, "name": "Alice"},
			{"id": 2, "name": "Bob"},
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"users": users})
}

func loginHandler(w http.ResponseWriter, r *http.Request) {
	// Simulate login logic (90% success rate)
	success := rand.Float32() > 0.1

	status := "failure"
	if success {
		status = "success"
		userSessionsActive.Inc()
	}

	userLoginTotal.WithLabelValues(status).Inc()

	w.Header().Set("Content-Type", "application/json")
	if success {
		json.NewEncoder(w).Encode(map[string]string{
			"status": "success",
			"token":  "fake-token",
		})
	} else {
		w.WriteHeader(http.StatusUnauthorized)
		json.NewEncoder(w).Encode(map[string]string{
			"status": "failure",
			"error":  "Invalid credentials",
		})
	}
}

func logoutHandler(w http.ResponseWriter, r *http.Request) {
	userSessionsActive.Dec()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "success"})
}

func createOrderHandler(w http.ResponseWriter, r *http.Request) {
	// Simulate order data
	orderValue := rand.Float64()*490 + 10
	categories := []string{"electronics", "books", "clothing"}
	paymentMethods := []string{"credit_card", "paypal", "bank_transfer"}

	productCategory := categories[rand.Intn(len(categories))]
	paymentMethod := paymentMethods[rand.Intn(len(paymentMethods))]

	// Track business metrics
	orderValueDollars.Observe(orderValue)
	ordersTotal.WithLabelValues(productCategory, paymentMethod).Inc()

	// Simulate database insert
	trackDBQuery("insert", "orders", func() {
		time.Sleep(time.Duration(rand.Intn(60)+20) * time.Millisecond)
	})

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"order_id":       rand.Intn(9000) + 1000,
		"value":          orderValue,
		"category":       productCategory,
		"payment_method": paymentMethod,
	})
}

func slowHandler(w http.ResponseWriter, r *http.Request) {
	// Intentionally slow
	time.Sleep(time.Duration(rand.Intn(2000)+1000) * time.Millisecond)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "slow response"})
}

func errorHandler(w http.ResponseWriter, r *http.Request) {
	// Randomly fail
	if rand.Float32() > 0.5 {
		w.WriteHeader(http.StatusInternalServerError)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"error": "Simulated error"})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	// Update system metrics
	updateSystemMetrics()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

// ============================================================================
// Main
// ============================================================================

func main() {
	rand.Seed(time.Now().UnixNano())

	// Create router
	mux := http.NewServeMux()

	// API endpoints
	mux.HandleFunc("/", indexHandler)
	mux.HandleFunc("/api/users", getUsersHandler)
	mux.HandleFunc("/api/login", loginHandler)
	mux.HandleFunc("/api/logout", logoutHandler)
	mux.HandleFunc("/api/orders", createOrderHandler)
	mux.HandleFunc("/api/slow", slowHandler)
	mux.HandleFunc("/api/error", errorHandler)
	mux.HandleFunc("/health", healthHandler)

	// Metrics endpoint
	mux.Handle("/metrics", promhttp.Handler())

	// Apply middleware
	handler := metricsMiddleware(mux)

	// Start server
	addr := ":8080"
	fmt.Println("Starting Go HTTP server with Prometheus metrics...")
	fmt.Printf("Metrics endpoint: http://localhost%s/metrics\n", addr)
	fmt.Println("API endpoints:")
	fmt.Println("  - GET  /api/users")
	fmt.Println("  - POST /api/login")
	fmt.Println("  - POST /api/logout")
	fmt.Println("  - POST /api/orders")
	fmt.Println("  - GET  /api/slow")
	fmt.Println("  - GET  /api/error")
	fmt.Println("  - GET  /health")

	log.Fatal(http.ListenAndServe(addr, handler))
}
