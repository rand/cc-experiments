package main

// Custom Prometheus Exporter (Go)
//
// Production-ready custom exporter using prometheus/client_golang.
//
// Usage:
//   go mod init custom-exporter
//   go get github.com/prometheus/client_golang/prometheus
//   go get github.com/prometheus/client_golang/prometheus/promauto
//   go get github.com/prometheus/client_golang/prometheus/promhttp
//   go get github.com/shirou/gopsutil/v3
//   go run custom-exporter.go
//
// Metrics available at: http://localhost:8080/metrics

import (
	"log"
	"math/rand"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/mem"
)

var (
	// System metrics
	cpuUsage = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "custom_cpu_usage_percent",
		Help: "CPU usage percentage",
	})

	cpuCores = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "custom_cpu_cores",
		Help: "Number of CPU cores",
	})

	memoryUsageBytes = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "custom_memory_usage_bytes",
		Help: "Memory usage in bytes",
	})

	memoryTotalBytes = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "custom_memory_total_bytes",
		Help: "Total memory in bytes",
	})

	// Application metrics
	appRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "custom_app_requests_total",
			Help: "Total application requests",
		},
		[]string{"endpoint", "method", "status"},
	)

	appRequestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "custom_app_request_duration_seconds",
			Help:    "Application request duration",
			Buckets: []float64{0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0},
		},
		[]string{"endpoint", "method"},
	)

	appErrorsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "custom_app_errors_total",
			Help: "Total application errors",
		},
		[]string{"error_type"},
	)

	appActiveConnections = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "custom_app_active_connections",
		Help: "Number of active connections",
	})

	appQueueSize = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "custom_app_queue_size",
			Help: "Queue size",
		},
		[]string{"queue_name"},
	)

	// Business metrics
	ordersTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "custom_orders_total",
			Help: "Total orders processed",
		},
		[]string{"product_category", "status"},
	)

	orderValueDollars = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "custom_order_value_dollars",
		Help:    "Order value in dollars",
		Buckets: []float64{10, 25, 50, 100, 250, 500, 1000, 5000},
	})

	revenueTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "custom_revenue_total_dollars",
			Help: "Total revenue in dollars",
		},
		[]string{"product_category"},
	)

	// Build info
	buildInfo = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "custom_app_build_info",
			Help: "Application build information",
		},
		[]string{"version", "commit", "build_date"},
	)
)

func init() {
	// Set build info
	buildInfo.WithLabelValues("1.2.3", "abc123", "2025-10-27").Set(1)
}

func collectSystemMetrics() {
	// CPU
	cpuPercent, err := cpu.Percent(time.Second, false)
	if err == nil && len(cpuPercent) > 0 {
		cpuUsage.Set(cpuPercent[0])
	}

	cpuCount, err := cpu.Counts(true)
	if err == nil {
		cpuCores.Set(float64(cpuCount))
	}

	// Memory
	vmem, err := mem.VirtualMemory()
	if err == nil {
		memoryUsageBytes.Set(float64(vmem.Used))
		memoryTotalBytes.Set(float64(vmem.Total))
	}
}

func simulateApplicationMetrics() {
	endpoints := []string{"/api/users", "/api/orders", "/api/products"}
	methods := []string{"GET", "POST", "PUT"}
	statuses := []string{"200", "201", "400", "404", "500"}

	endpoint := endpoints[rand.Intn(len(endpoints))]
	method := methods[rand.Intn(len(methods))]
	status := statuses[rand.Intn(len(statuses))]

	// Record request
	appRequestsTotal.WithLabelValues(endpoint, method, status).Inc()

	// Record duration
	duration := rand.Float64() * 2.0
	appRequestDuration.WithLabelValues(endpoint, method).Observe(duration)

	// Simulate errors (10% chance)
	if rand.Float64() < 0.1 {
		errorTypes := []string{"database_error", "validation_error", "timeout"}
		errorType := errorTypes[rand.Intn(len(errorTypes))]
		appErrorsTotal.WithLabelValues(errorType).Inc()
	}

	// Update gauges
	appActiveConnections.Set(float64(rand.Intn(490) + 10))
	appQueueSize.WithLabelValues("tasks").Set(float64(rand.Intn(100)))
	appQueueSize.WithLabelValues("emails").Set(float64(rand.Intn(50)))
}

func simulateBusinessMetrics() {
	// Simulate orders (20% chance)
	if rand.Float64() < 0.2 {
		categories := []string{"electronics", "clothing", "books", "home"}
		statuses := []string{"completed", "pending", "cancelled"}

		category := categories[rand.Intn(len(categories))]
		status := statuses[rand.Intn(len(statuses))]
		value := rand.Float64()*4990 + 10

		ordersTotal.WithLabelValues(category, status).Inc()
		orderValueDollars.Observe(value)

		if status == "completed" {
			revenueTotal.WithLabelValues(category).Add(value)
		}
	}
}

func collectMetrics() {
	for {
		collectSystemMetrics()
		simulateApplicationMetrics()
		simulateBusinessMetrics()
		time.Sleep(5 * time.Second)
	}
}

func main() {
	port := ":8080"

	// Start metrics collector in background
	go collectMetrics()

	// Expose metrics endpoint
	http.Handle("/metrics", promhttp.Handler())

	log.Printf("Custom exporter started on %s\n", port)
	log.Printf("Metrics available at http://localhost%s/metrics\n", port)

	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatal(err)
	}
}
