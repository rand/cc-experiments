// Go + Sentry Integration Example
//
// Production-ready Go HTTP server with comprehensive Sentry error tracking.
//
// Usage:
//   export SENTRY_DSN="https://..."
//   export GO_ENV=production
//   go run sentry-middleware.go

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/getsentry/sentry-go"
	sentryhttp "github.com/getsentry/sentry-go/http"
)

func main() {
	// Initialize Sentry
	err := sentry.Init(sentry.ClientOptions{
		Dsn:              os.Getenv("SENTRY_DSN"),
		Environment:      getEnv("GO_ENV", "development"),
		Release:          getEnv("RELEASE", "1.0.0"),
		TracesSampleRate: getTracesSampleRate(),
		AttachStacktrace: true,

		BeforeSend: func(event *sentry.Event, hint *sentry.EventHint) *sentry.Event {
			// Remove sensitive data
			if event.Request != nil {
				// Remove sensitive headers
				if event.Request.Headers != nil {
					delete(event.Request.Headers, "Authorization")
					delete(event.Request.Headers, "Cookie")
					delete(event.Request.Headers, "X-Api-Key")
				}

				// Remove query parameters with sensitive data
				if event.Request.QueryString != "" {
					event.Request.QueryString = scrubQueryString(event.Request.QueryString)
				}
			}

			return event
		},
	})

	if err != nil {
		log.Fatalf("sentry.Init: %s", err)
	}
	defer sentry.Flush(2 * time.Second)

	// Create HTTP server with Sentry middleware
	sentryHandler := sentryhttp.New(sentryhttp.Options{
		Repanic: true,
	})

	http.Handle("/", sentryHandler.Handle(http.HandlerFunc(indexHandler)))
	http.Handle("/api/users/", sentryHandler.Handle(http.HandlerFunc(getUserHandler)))
	http.Handle("/api/orders", sentryHandler.Handle(http.HandlerFunc(createOrderHandler)))
	http.Handle("/api/test-error", sentryHandler.Handle(http.HandlerFunc(testErrorHandler)))

	port := getEnv("PORT", "8080")
	log.Printf("Starting server on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

func getTracesSampleRate() float64 {
	env := os.Getenv("GO_ENV")
	switch env {
	case "production":
		return 0.05 // 5%
	case "staging":
		return 0.5 // 50%
	default:
		return 1.0 // 100%
	}
}

func indexHandler(w http.ResponseWriter, r *http.Request) {
	hub := sentry.GetHubFromContext(r.Context())

	// Add breadcrumb
	hub.AddBreadcrumb(&sentry.Breadcrumb{
		Category: "request",
		Message:  fmt.Sprintf("%s %s", r.Method, r.URL.Path),
		Level:    sentry.LevelInfo,
	}, nil)

	response := map[string]string{
		"status":      "healthy",
		"service":     "go-api",
		"environment": os.Getenv("GO_ENV"),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func getUserHandler(w http.ResponseWriter, r *http.Request) {
	hub := sentry.GetHubFromContext(r.Context())

	// Extract user ID from URL
	userID := r.URL.Path[len("/api/users/"):]

	// Set user context
	hub.ConfigureScope(func(scope *sentry.Scope) {
		scope.SetUser(sentry.User{
			ID:        userID,
			IPAddress: r.RemoteAddr,
		})
	})

	// Add breadcrumb
	hub.AddBreadcrumb(&sentry.Breadcrumb{
		Category: "database",
		Message:  fmt.Sprintf("Looking up user %s", userID),
		Level:    sentry.LevelInfo,
	}, nil)

	// Simulate error for testing
	if userID == "999" {
		err := fmt.Errorf("User not found: %s", userID)
		hub.CaptureException(err)
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}

	response := map[string]string{
		"id":    userID,
		"name":  fmt.Sprintf("User %s", userID),
		"email": fmt.Sprintf("user%s@example.com", userID),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func createOrderHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	hub := sentry.GetHubFromContext(r.Context())

	// Parse request body
	var order struct {
		Items []string `json:"items"`
		Total float64  `json:"total"`
	}

	if err := json.NewDecoder(r.Body).Decode(&order); err != nil {
		hub.CaptureException(err)
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Set order context
	hub.ConfigureScope(func(scope *sentry.Scope) {
		scope.SetContext("order", map[string]interface{}{
			"items_count": len(order.Items),
			"total":       order.Total,
		})
	})

	// Add breadcrumb
	hub.AddBreadcrumb(&sentry.Breadcrumb{
		Category: "business",
		Message:  "Creating order",
		Level:    sentry.LevelInfo,
		Data: map[string]interface{}{
			"items_count": len(order.Items),
			"total":       order.Total,
		},
	}, nil)

	// Validate order
	if order.Total <= 0 {
		err := fmt.Errorf("Order total must be positive")
		hub.CaptureException(err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Simulate external API call
	hub.AddBreadcrumb(&sentry.Breadcrumb{
		Category: "http",
		Message:  "Calling payment API",
		Level:    sentry.LevelInfo,
	}, nil)

	response := map[string]string{
		"order_id": "ORD-12345",
		"status":   "created",
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteStatus(http.StatusCreated)
	json.NewEncoder(w).Encode(response)
}

func testErrorHandler(w http.ResponseWriter, r *http.Request) {
	hub := sentry.GetHubFromContext(r.Context())

	// Set test tag
	hub.ConfigureScope(func(scope *sentry.Scope) {
		scope.SetTag("test", "true")
	})

	// Trigger test error
	err := fmt.Errorf("Test error from Go API")
	hub.CaptureException(err)

	http.Error(w, "Test error triggered", http.StatusInternalServerError)
}

func scrubQueryString(queryString string) string {
	// Remove sensitive query parameters
	// Implementation would use url.ParseQuery and filter
	return "[Filtered]"
}

func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}
