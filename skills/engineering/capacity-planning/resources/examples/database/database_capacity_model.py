#!/usr/bin/env python3
"""
Database Capacity Planning Model

Calculates database capacity requirements for:
- Connection pool sizing
- Storage requirements
- IOPS requirements
- Memory requirements

Usage:
    python database_capacity_model.py --connections 1000 --qps 5000
"""

import argparse


def calculate_connection_pool(concurrent_requests, avg_query_time_ms, avg_request_time_ms):
    """Calculate optimal connection pool size."""
    queries_per_request = avg_query_time_ms / avg_request_time_ms
    base_pool_size = concurrent_requests * queries_per_request
    recommended_size = int(base_pool_size * 1.3)  # 30% safety factor

    print(f"\n=== Connection Pool Sizing ===")
    print(f"Concurrent requests: {concurrent_requests}")
    print(f"Queries per request: {queries_per_request:.2f}")
    print(f"Base pool size: {base_pool_size:.0f}")
    print(f"Recommended pool size: {recommended_size}")

    return recommended_size


def calculate_storage_requirements(tables):
    """Calculate storage requirements."""
    total_gb = 0

    print(f"\n=== Storage Requirements ===")

    for table, config in tables.items():
        rows = config['rows']
        avg_row_bytes = config['avg_row_bytes']
        size_gb = (rows * avg_row_bytes) / (1024 ** 3)
        total_gb += size_gb

        print(f"{table}:")
        print(f"  Rows: {rows:,}")
        print(f"  Size: {size_gb:.2f} GB")

    # Add index overhead (30%)
    index_gb = total_gb * 0.3
    total_with_index = total_gb + index_gb

    # Add 30% growth buffer
    total_with_buffer = total_with_index * 1.3

    print(f"\nTotal data: {total_gb:.2f} GB")
    print(f"Index overhead (30%): {index_gb:.2f} GB")
    print(f"Total with buffer (30%): {total_with_buffer:.2f} GB")

    return total_with_buffer


def calculate_iops_requirements(qps, reads_per_query=2, writes_per_query=0.5):
    """Calculate IOPS requirements."""
    read_iops = qps * reads_per_query
    write_iops = qps * writes_per_query
    total_iops = read_iops + write_iops

    print(f"\n=== IOPS Requirements ===")
    print(f"QPS: {qps}")
    print(f"Read IOPS: {read_iops:.0f}")
    print(f"Write IOPS: {write_iops:.0f}")
    print(f"Total IOPS: {total_iops:.0f}")

    if total_iops < 3000:
        storage_type = "gp3 (General Purpose SSD)"
    elif total_iops < 16000:
        storage_type = "io1 (Provisioned IOPS SSD)"
    else:
        storage_type = "io2 Block Express"

    print(f"Recommended storage: {storage_type}")

    return total_iops


def main():
    parser = argparse.ArgumentParser(description='Database capacity planning')
    parser.add_argument('--connections', type=int, default=1000, help='Max concurrent connections')
    parser.add_argument('--qps', type=int, default=5000, help='Queries per second')

    args = parser.parse_args()

    # Example table configuration
    tables = {
        'users': {'rows': 1000000, 'avg_row_bytes': 200},
        'orders': {'rows': 5000000, 'avg_row_bytes': 150},
        'order_items': {'rows': 15000000, 'avg_row_bytes': 100},
    }

    calculate_connection_pool(200, 50, 200)
    calculate_storage_requirements(tables)
    calculate_iops_requirements(args.qps)


if __name__ == '__main__':
    main()
