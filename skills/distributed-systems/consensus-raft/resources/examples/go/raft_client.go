package main

/*
Production-ready etcd RAFT client in Go

Demonstrates:
- Key-value operations
- Transactions (atomic compare-and-swap)
- Leases (TTL-based keys)
- Watches (real-time notifications)
- Distributed locking
- Leader election

Requirements:
	go get go.etcd.io/etcd/client/v3

Usage:
	go run raft_client.go
*/

import (
	"context"
	"fmt"
	"log"
	"time"

	clientv3 "go.etcd.io/etcd/client/v3"
	"go.etcd.io/etcd/client/v3/concurrency"
)

// RAFTClient wraps etcd client with common operations
type RAFTClient struct {
	client *clientv3.Client
}

// NewRAFTClient creates new etcd client
func NewRAFTClient(endpoints []string) (*RAFTClient, error) {
	cli, err := clientv3.New(clientv3.Config{
		Endpoints:   endpoints,
		DialTimeout: 5 * time.Second,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to connect: %w", err)
	}

	return &RAFTClient{client: cli}, nil
}

// Close closes the client connection
func (c *RAFTClient) Close() error {
	return c.client.Close()
}

// Put writes key-value pair (goes through RAFT consensus)
func (c *RAFTClient) Put(ctx context.Context, key, value string) error {
	_, err := c.client.Put(ctx, key, value)
	if err != nil {
		return fmt.Errorf("put failed: %w", err)
	}
	return nil
}

// Get reads value for key (linearizable read from leader by default)
func (c *RAFTClient) Get(ctx context.Context, key string) (string, error) {
	resp, err := c.client.Get(ctx, key)
	if err != nil {
		return "", fmt.Errorf("get failed: %w", err)
	}

	if len(resp.Kvs) == 0 {
		return "", fmt.Errorf("key not found")
	}

	return string(resp.Kvs[0].Value), nil
}

// GetPrefix retrieves all keys with given prefix
func (c *RAFTClient) GetPrefix(ctx context.Context, prefix string) (map[string]string, error) {
	resp, err := c.client.Get(ctx, prefix, clientv3.WithPrefix())
	if err != nil {
		return nil, fmt.Errorf("get prefix failed: %w", err)
	}

	results := make(map[string]string)
	for _, kv := range resp.Kvs {
		results[string(kv.Key)] = string(kv.Value)
	}

	return results, nil
}

// Delete removes key
func (c *RAFTClient) Delete(ctx context.Context, key string) error {
	_, err := c.client.Delete(ctx, key)
	if err != nil {
		return fmt.Errorf("delete failed: %w", err)
	}
	return nil
}

// CompareAndSwap performs atomic compare-and-swap
func (c *RAFTClient) CompareAndSwap(ctx context.Context, key, expectedValue, newValue string) (bool, error) {
	txn := c.client.Txn(ctx).
		If(clientv3.Compare(clientv3.Value(key), "=", expectedValue)).
		Then(clientv3.OpPut(key, newValue)).
		Else(clientv3.OpGet(key))

	resp, err := txn.Commit()
	if err != nil {
		return false, fmt.Errorf("transaction failed: %w", err)
	}

	return resp.Succeeded, nil
}

// IncrementCounter atomically increments counter
func (c *RAFTClient) IncrementCounter(ctx context.Context, key string) (int64, error) {
	for {
		// Get current value
		currentVal, err := c.Get(ctx, key)
		if err != nil && err.Error() != "key not found" {
			return 0, err
		}

		var current int64 = 0
		if currentVal != "" {
			fmt.Sscanf(currentVal, "%d", &current)
		}

		newVal := current + 1

		// Try CAS
		success, err := c.CompareAndSwap(ctx, key, fmt.Sprintf("%d", current), fmt.Sprintf("%d", newVal))
		if err != nil {
			return 0, err
		}

		if success {
			return newVal, nil
		}

		// CAS failed, retry
		time.Sleep(time.Millisecond)
	}
}

// PutWithLease creates key with TTL
func (c *RAFTClient) PutWithLease(ctx context.Context, key, value string, ttl int64) (clientv3.LeaseID, error) {
	// Create lease
	lease, err := c.client.Grant(ctx, ttl)
	if err != nil {
		return 0, fmt.Errorf("lease grant failed: %w", err)
	}

	// Put with lease
	_, err = c.client.Put(ctx, key, value, clientv3.WithLease(lease.ID))
	if err != nil {
		return 0, fmt.Errorf("put with lease failed: %w", err)
	}

	return lease.ID, nil
}

// KeepAlive keeps lease alive
func (c *RAFTClient) KeepAlive(ctx context.Context, leaseID clientv3.LeaseID) (<-chan *clientv3.LeaseKeepAliveResponse, error) {
	return c.client.KeepAlive(ctx, leaseID)
}

// Watch watches for changes to key
func (c *RAFTClient) Watch(ctx context.Context, key string, prefix bool) clientv3.WatchChan {
	if prefix {
		return c.client.Watch(ctx, key, clientv3.WithPrefix())
	}
	return c.client.Watch(ctx, key)
}

// DistributedLock represents a distributed lock
type DistributedLock struct {
	session *concurrency.Session
	mutex   *concurrency.Mutex
}

// NewDistributedLock creates new distributed lock
func (c *RAFTClient) NewDistributedLock(ctx context.Context, lockName string, ttl int) (*DistributedLock, error) {
	session, err := concurrency.NewSession(c.client, concurrency.WithTTL(ttl))
	if err != nil {
		return nil, fmt.Errorf("session creation failed: %w", err)
	}

	mutex := concurrency.NewMutex(session, "/locks/"+lockName)

	return &DistributedLock{
		session: session,
		mutex:   mutex,
	}, nil
}

// Lock acquires the distributed lock
func (l *DistributedLock) Lock(ctx context.Context) error {
	return l.mutex.Lock(ctx)
}

// Unlock releases the distributed lock
func (l *DistributedLock) Unlock(ctx context.Context) error {
	return l.mutex.Unlock(ctx)
}

// Close closes the session
func (l *DistributedLock) Close() error {
	return l.session.Close()
}

// LeaderElection manages leader election
type LeaderElection struct {
	session  *concurrency.Session
	election *concurrency.Election
	nodeID   string
}

// NewLeaderElection creates new leader election
func (c *RAFTClient) NewLeaderElection(ctx context.Context, electionName, nodeID string, ttl int) (*LeaderElection, error) {
	session, err := concurrency.NewSession(c.client, concurrency.WithTTL(ttl))
	if err != nil {
		return nil, fmt.Errorf("session creation failed: %w", err)
	}

	election := concurrency.NewElection(session, "/elections/"+electionName)

	return &LeaderElection{
		session:  session,
		election: election,
		nodeID:   nodeID,
	}, nil
}

// Campaign attempts to become leader (blocking)
func (e *LeaderElection) Campaign(ctx context.Context) error {
	return e.election.Campaign(ctx, e.nodeID)
}

// Resign resigns from leadership
func (e *LeaderElection) Resign(ctx context.Context) error {
	return e.election.Resign(ctx)
}

// Leader returns current leader
func (e *LeaderElection) Leader(ctx context.Context) (string, error) {
	resp, err := e.election.Leader(ctx)
	if err != nil {
		return "", err
	}
	return string(resp.Kvs[0].Value), nil
}

// Close closes the session
func (e *LeaderElection) Close() error {
	return e.session.Close()
}

// Example usage
func main() {
	fmt.Println("=== RAFT Client Examples (Go) ===\n")

	// Initialize client
	client, err := NewRAFTClient([]string{"localhost:2379"})
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer client.Close()

	ctx := context.Background()

	// 1. Basic key-value operations
	fmt.Println("1. Basic Operations:")
	err = client.Put(ctx, "/config/app_name", "my-go-app")
	if err != nil {
		log.Printf("   PUT error: %v", err)
	}

	value, err := client.Get(ctx, "/config/app_name")
	if err != nil {
		log.Printf("   GET error: %v", err)
	} else {
		fmt.Printf("   GET /config/app_name = %s\n", value)
	}

	// 2. Atomic counter
	fmt.Println("\n2. Atomic Counter:")
	for i := 0; i < 5; i++ {
		count, err := client.IncrementCounter(ctx, "/counters/requests")
		if err != nil {
			log.Printf("   INCREMENT error: %v", err)
		} else {
			fmt.Printf("   Request count: %d\n", count)
		}
	}

	// 3. Compare-and-swap
	fmt.Println("\n3. Compare-and-Swap:")
	client.Put(ctx, "/status", "idle")
	success, _ := client.CompareAndSwap(ctx, "/status", "idle", "processing")
	fmt.Printf("   CAS idle->processing: %v\n", success)
	success, _ = client.CompareAndSwap(ctx, "/status", "idle", "done")
	fmt.Printf("   CAS idle->done: %v (expected false)\n", success)

	// 4. Lease (TTL)
	fmt.Println("\n4. Lease (TTL):")
	leaseID, err := client.PutWithLease(ctx, "/temp/session", "active", 10)
	if err != nil {
		log.Printf("   Lease error: %v", err)
	} else {
		fmt.Printf("   Created ephemeral key with 10s TTL (lease: %d)\n", leaseID)
	}

	// 5. Distributed lock
	fmt.Println("\n5. Distributed Lock:")
	lock, err := client.NewDistributedLock(ctx, "my-resource", 60)
	if err != nil {
		log.Printf("   Lock creation error: %v", err)
	} else {
		defer lock.Close()

		err = lock.Lock(ctx)
		if err != nil {
			log.Printf("   Lock acquire error: %v", err)
		} else {
			fmt.Println("   Lock acquired")
			time.Sleep(1 * time.Second)
			lock.Unlock(ctx)
			fmt.Println("   Lock released")
		}
	}

	// 6. Leader election
	fmt.Println("\n6. Leader Election:")
	election, err := client.NewLeaderElection(ctx, "my-go-service", "node-1", 60)
	if err != nil {
		log.Printf("   Election creation error: %v", err)
	} else {
		defer election.Close()

		// Try to become leader (non-blocking)
		ctx2, cancel := context.WithTimeout(ctx, 2*time.Second)
		defer cancel()

		err = election.Campaign(ctx2)
		if err == nil {
			fmt.Printf("   Node %s became leader\n", election.nodeID)
			time.Sleep(1 * time.Second)
			election.Resign(ctx)
			fmt.Println("   Resigned leadership")
		} else {
			leader, _ := election.Leader(ctx)
			fmt.Printf("   Current leader: %s\n", leader)
		}
	}

	// 7. Watch for changes
	fmt.Println("\n7. Watch (run 'etcdctl put /watch/test value' in another terminal):")
	fmt.Println("   Watching /watch/* for 5 seconds...")

	watchChan := client.Watch(ctx, "/watch/", true)

	ctx3, cancel3 := context.WithTimeout(ctx, 5*time.Second)
	defer cancel3()

	go func() {
		for watchResp := range watchChan {
			for _, event := range watchResp.Events {
				fmt.Printf("   Change detected: %s = %s\n", event.Kv.Key, event.Kv.Value)
			}
		}
	}()

	<-ctx3.Done()

	fmt.Println("\n=== Examples Complete ===")
}
