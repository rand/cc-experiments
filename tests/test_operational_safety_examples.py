#!/usr/bin/env python3
"""
Test examples for operational safety validator.
This file intentionally contains operational safety issues for testing.
"""

import os
import time
import requests
import psycopg2
import threading
from typing import Any


# CATEGORY: Destructive Operations Without Warnings
def dangerous_delete():
    """Example of DELETE without WHERE clause."""
    cursor.execute("DELETE FROM users")  # CRITICAL: Missing WHERE clause


def dangerous_drop():
    """Example of DROP without confirmation."""
    cursor.execute("DROP TABLE users")  # HIGH: No confirmation


def dangerous_file_delete():
    """Example of rm -rf without confirmation."""
    os.system("rm -rf /tmp/data")  # CRITICAL: No confirmation


# CATEGORY: Database Transaction Safety
def unsafe_transaction():
    """Example of transaction without proper error handling."""
    conn = psycopg2.connect("dbname=test")
    cursor = conn.cursor()

    cursor.execute("BEGIN TRANSACTION")  # HIGH: No visible COMMIT/ROLLBACK
    cursor.execute("UPDATE accounts SET balance = balance - 100")
    # Missing COMMIT or ROLLBACK


def transaction_without_error_handling():
    """Transaction without try/except."""
    cursor.execute("BEGIN")  # MEDIUM: No error handling
    cursor.execute("INSERT INTO logs VALUES (1, 'test')")
    cursor.execute("COMMIT")


# CATEGORY: Network Retry/Timeout Patterns
def http_without_timeout():
    """Example of HTTP request without timeout."""
    response = requests.get("https://api.example.com")  # MEDIUM: No timeout


def retry_without_backoff():
    """Example of retry without exponential backoff."""
    retry_count = 0
    while retry_count < 5:  # MEDIUM: No backoff
        try:
            response = requests.get("https://api.example.com")
            break
        except requests.RequestException:
            retry_count += 1
        # Missing sleep/backoff


def network_error_ignored():
    """Example of network error silently ignored."""
    try:
        response = requests.get("https://api.example.com")
    except requests.ConnectionError:
        pass  # HIGH: Error silently ignored


# CATEGORY: Resource Cleanup
def file_without_context_manager():
    """Example of file opened without context manager."""
    f = open("data.txt", "r")  # MEDIUM: No context manager
    content = f.read()
    # Missing f.close()


def db_connection_without_cleanup():
    """Example of database connection without cleanup."""
    conn = psycopg2.connect("dbname=test")  # HIGH: No cleanup
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    # Missing conn.close()


def subprocess_without_wait():
    """Example of subprocess without wait."""
    import subprocess
    proc = subprocess.Popen(["ls", "-la"])  # MEDIUM: No wait


# CATEGORY: Race Condition Patterns
def toctou_race_condition():
    """Example of TOCTOU race condition."""
    if os.path.exists("data.txt"):  # HIGH: Check-then-act
        with open("data.txt", "r") as f:
            content = f.read()


def shared_state_without_lock():
    """Example of shared state modification without lock."""
    counter = 0

    def increment():
        global counter
        counter += 1  # HIGH: No synchronization

    threads = [threading.Thread(target=increment) for _ in range(10)]
    for t in threads:
        t.start()


def lazy_init_without_lock():
    """Example of lazy initialization without lock."""
    _cache = None

    def get_cache():
        global _cache
        if _cache is None:  # MEDIUM: No lock for lazy init
            _cache = {}
        return _cache


# CATEGORY: Graceful Degradation
def health_check_without_error_handling():
    """Example of health check without error handling."""
    def health():  # MEDIUM: No try/except
        db.execute("SELECT 1")
        return {"status": "ok"}


def infinite_loop_without_signal_handling():
    """Example of infinite loop without signal handling."""
    while True:  # LOW: No signal handling
        process_item()
        # Missing signal handlers


def external_service_without_fallback():
    """Example of external service call without fallback."""
    response = requests.get("https://api.example.com")  # LOW: No fallback
    return response.json()


# CATEGORY: Database Connection Management
def connection_without_pooling():
    """Example of database connection without pooling."""
    conn = psycopg2.connect(  # MEDIUM: No pooling
        host="localhost",
        database="mydb",
        user="user",
        password="pass"
    )


def connection_in_loop():
    """Example of connection created in loop."""
    for i in range(100):
        conn = psycopg2.connect("dbname=test")  # HIGH: Connection in loop
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (i,))


# CATEGORY: Observability
def exception_silently_swallowed():
    """Example of exception silently swallowed."""
    try:
        risky_operation()
    except Exception:
        pass  # HIGH: Exception silently swallowed


def long_sleep_without_logging():
    """Example of long sleep without logging."""
    time.sleep(60)  # LOW: No logging


# CATEGORY: Additional Patterns
def create_table_without_if_not_exists():
    """Example of CREATE TABLE without IF NOT EXISTS."""
    cursor.execute("CREATE TABLE users (id INT, name VARCHAR(100))")  # LOW: No IF NOT EXISTS


def thread_without_join():
    """Example of non-daemon thread without join."""
    t = threading.Thread(target=lambda: time.sleep(1), daemon=False)  # LOW: No join
    t.start()


# Example of good patterns (should not trigger warnings)
def safe_file_handling():
    """Correct: Using context manager."""
    with open("data.txt", "r") as f:
        content = f.read()


def safe_transaction():
    """Correct: Transaction with proper error handling."""
    conn = psycopg2.connect("dbname=test")
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute("BEGIN")
                cursor.execute("UPDATE accounts SET balance = balance - 100")
                cursor.execute("COMMIT")
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def safe_http_request():
    """Correct: HTTP request with timeout and retry."""
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get("https://api.example.com", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise


def safe_shared_state():
    """Correct: Shared state with lock."""
    counter = 0
    lock = threading.Lock()

    def increment():
        global counter
        with lock:
            counter += 1


if __name__ == "__main__":
    print("This file contains intentional operational safety issues for testing.")
