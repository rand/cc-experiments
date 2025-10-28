package main

/*
OpenTelemetry Go HTTP Distributed Tracing Example

Complete example showing auto-instrumentation and manual spans in Go HTTP server
with trace context propagation.

Requirements:
	go get go.opentelemetry.io/otel
	go get go.opentelemetry.io/otel/sdk
	go get go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc
	go get go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp

Usage:
	go run otel_http_tracing.go

	# With custom OTLP endpoint
	OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317 go run otel_http_tracing.go
*/

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.17.0"
	"go.opentelemetry.io/otel/trace"
)

// Configuration
var (
	serviceName    = getEnv("SERVICE_NAME", "payment-api")
	otlpEndpoint   = getEnv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
	port           = getEnv("PORT", "8003")
	tracer         trace.Tracer
)

// Payment represents a payment record
type Payment struct {
	ID          string    `json:"id"`
	OrderID     string    `json:"order_id"`
	UserID      string    `json:"user_id"`
	Amount      float64   `json:"amount"`
	Currency    string    `json:"currency"`
	Status      string    `json:"status"`
	Method      string    `json:"method"`
	CreatedAt   time.Time `json:"created_at"`
}

// In-memory payment database (mock)
var paymentsDB = map[string]*Payment{
	"pay-1": {
		ID:        "pay-1",
		OrderID:   "order-1",
		UserID:    "123",
		Amount:    109.97,
		Currency:  "USD",
		Status:    "completed",
		Method:    "credit_card",
		CreatedAt: time.Now().Add(-24 * time.Hour),
	},
}

func main() {
	// Initialize OpenTelemetry
	shutdown := initTracer()
	defer shutdown()

	// Create HTTP server with tracing
	mux := http.NewServeMux()

	// Register handlers
	mux.HandleFunc("/", handleRoot)
	mux.HandleFunc("/payments/", handleGetPayment)
	mux.HandleFunc("/payments", handleCreatePayment)

	// Wrap with otelhttp for auto-instrumentation
	handler := otelhttp.NewHandler(mux, "http-server")

	// Start server
	addr := ":" + port
	log.Printf("Starting %s on %s", serviceName, addr)
	log.Printf("Traces will be sent to: %s", otlpEndpoint)
	log.Println("\nEndpoints:")
	log.Println("  GET  /")
	log.Println("  GET  /payments/{id}")
	log.Println("  POST /payments")
	log.Println()

	if err := http.ListenAndServe(addr, handler); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

// initTracer initializes OpenTelemetry tracer
func initTracer() func() {
	ctx := context.Background()

	// Create resource with service identity
	res, err := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceName(serviceName),
			semconv.ServiceVersion("1.0.0"),
			semconv.DeploymentEnvironment("development"),
		),
	)
	if err != nil {
		log.Fatalf("Failed to create resource: %v", err)
	}

	// Create OTLP exporter
	exporter, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithEndpoint(otlpEndpoint),
		otlptracegrpc.WithInsecure(), // Use for development only
	)
	if err != nil {
		log.Fatalf("Failed to create exporter: %v", err)
	}

	// Create trace provider
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)

	// Set global tracer provider
	otel.SetTracerProvider(tp)

	// Set global propagator (W3C Trace Context)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))

	// Get tracer
	tracer = otel.Tracer(serviceName)

	// Return shutdown function
	return func() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := tp.Shutdown(ctx); err != nil {
			log.Printf("Error shutting down tracer provider: %v", err)
		}
	}
}

// handleRoot is the health check endpoint
func handleRoot(w http.ResponseWriter, r *http.Request) {
	response := map[string]string{
		"service": serviceName,
		"status":  "healthy",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleGetPayment gets a payment by ID
func handleGetPayment(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract payment ID from path
	paymentID := r.URL.Path[len("/payments/"):]
	if paymentID == "" {
		http.Error(w, "Payment ID required", http.StatusBadRequest)
		return
	}

	// Get current span (created by otelhttp)
	ctx := r.Context()
	span := trace.SpanFromContext(ctx)
	span.SetAttributes(attribute.String("payment.id", paymentID))

	// Create manual span for database lookup
	ctx, dbSpan := tracer.Start(ctx, "db.get_payment",
		trace.WithAttributes(
			attribute.String("db.system", "in-memory"),
			attribute.String("db.operation", "SELECT"),
			attribute.String("db.table", "payments"),
			attribute.String("payment.id", paymentID),
		),
	)
	defer dbSpan.End()

	// Simulate database query
	time.Sleep(30 * time.Millisecond)

	payment, exists := paymentsDB[paymentID]
	if !exists {
		dbSpan.AddEvent("payment.not_found",
			trace.WithAttributes(attribute.String("payment_id", paymentID)),
		)
		dbSpan.SetStatus(codes.Error, "Payment not found")

		http.Error(w, "Payment not found", http.StatusNotFound)
		return
	}

	dbSpan.AddEvent("payment.found",
		trace.WithAttributes(attribute.String("payment_id", paymentID)),
	)
	dbSpan.SetAttributes(
		attribute.String("payment.status", payment.Status),
		attribute.Float64("payment.amount", payment.Amount),
	)
	dbSpan.SetStatus(codes.Ok, "")

	// Return payment
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(payment)
}

// handleCreatePayment creates a new payment
func handleCreatePayment(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	ctx := r.Context()

	// Parse request body
	var req struct {
		OrderID  string  `json:"order_id"`
		UserID   string  `json:"user_id"`
		Amount   float64 `json:"amount"`
		Currency string  `json:"currency"`
		Method   string  `json:"method"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate input
	ctx, validateSpan := tracer.Start(ctx, "validate_payment_input",
		trace.WithAttributes(
			attribute.String("order.id", req.OrderID),
			attribute.String("user.id", req.UserID),
			attribute.Float64("payment.amount", req.Amount),
		),
	)

	if req.OrderID == "" || req.UserID == "" || req.Amount <= 0 {
		validateSpan.AddEvent("validation.failed",
			trace.WithAttributes(attribute.String("reason", "missing_required_fields")),
		)
		validateSpan.SetStatus(codes.Error, "Invalid input")
		validateSpan.End()

		http.Error(w, "order_id, user_id, and amount are required", http.StatusBadRequest)
		return
	}

	validateSpan.AddEvent("validation.passed")
	validateSpan.SetStatus(codes.Ok, "")
	validateSpan.End()

	// Process payment
	ctx, processSpan := tracer.Start(ctx, "process_payment",
		trace.WithAttributes(
			attribute.String("payment.method", req.Method),
			attribute.Float64("payment.amount", req.Amount),
			attribute.String("payment.currency", req.Currency),
		),
	)
	defer processSpan.End()

	// Step 1: Authorize payment
	ctx, authSpan := tracer.Start(ctx, "payment.authorize")
	authSpan.SetAttributes(
		attribute.String("payment.method", req.Method),
		attribute.Float64("payment.amount", req.Amount),
	)

	// Simulate authorization
	time.Sleep(50 * time.Millisecond)

	authSpan.AddEvent("payment.authorized")
	authSpan.SetStatus(codes.Ok, "")
	authSpan.End()

	// Step 2: Capture payment
	ctx, captureSpan := tracer.Start(ctx, "payment.capture")
	captureSpan.SetAttributes(
		attribute.String("payment.method", req.Method),
		attribute.Float64("payment.amount", req.Amount),
	)

	// Simulate capture
	time.Sleep(30 * time.Millisecond)

	captureSpan.AddEvent("payment.captured")
	captureSpan.SetStatus(codes.Ok, "")
	captureSpan.End()

	// Create payment record
	paymentID := fmt.Sprintf("pay-%d", time.Now().UnixNano())

	ctx, dbSpan := tracer.Start(ctx, "db.insert_payment",
		trace.WithAttributes(
			attribute.String("db.system", "in-memory"),
			attribute.String("db.operation", "INSERT"),
			attribute.String("db.table", "payments"),
			attribute.String("payment.id", paymentID),
		),
	)

	// Simulate database insert
	time.Sleep(20 * time.Millisecond)

	payment := &Payment{
		ID:        paymentID,
		OrderID:   req.OrderID,
		UserID:    req.UserID,
		Amount:    req.Amount,
		Currency:  req.Currency,
		Status:    "completed",
		Method:    req.Method,
		CreatedAt: time.Now(),
	}

	paymentsDB[paymentID] = payment

	dbSpan.AddEvent("payment.created",
		trace.WithAttributes(attribute.String("payment_id", paymentID)),
	)
	dbSpan.SetStatus(codes.Ok, "")
	dbSpan.End()

	// Publish event (fire and forget)
	go publishPaymentEvent(ctx, paymentID, "payment.completed")

	processSpan.AddEvent("payment.completed",
		trace.WithAttributes(attribute.String("payment_id", paymentID)),
	)
	processSpan.SetStatus(codes.Ok, "")

	// Return payment
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(payment)
}

// publishPaymentEvent publishes a payment event
func publishPaymentEvent(ctx context.Context, paymentID, eventType string) {
	ctx, span := tracer.Start(ctx, "publish_payment_event",
		trace.WithSpanKind(trace.SpanKindProducer),
		trace.WithAttributes(
			attribute.String("messaging.system", "kafka"),
			attribute.String("messaging.destination", "payment.events"),
			attribute.String("messaging.operation", "send"),
			attribute.String("payment.id", paymentID),
			attribute.String("event.type", eventType),
		),
	)
	defer span.End()

	// Simulate publishing to message queue
	time.Sleep(10 * time.Millisecond)

	span.AddEvent("event.published",
		trace.WithAttributes(
			attribute.String("event_type", eventType),
			attribute.String("payment_id", paymentID),
		),
	)
	span.SetStatus(codes.Ok, "")
}

// getEnv gets environment variable with default value
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
