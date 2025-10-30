#!/usr/bin/env python3
"""
Agent State Manager

Manages agent state persistence with memory types (short-term, long-term, working).
Provides state versioning, history tracking, and querying capabilities.

Usage:
    python state_manager.py save --agent-id agent1 --state state.json
    python state_manager.py load --agent-id agent1
    python state_manager.py query --agent-id agent1 --memory-type long_term
    python state_manager.py history --agent-id agent1 --limit 10
    python state_manager.py clear --agent-id agent1 --memory-type short_term
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class MemoryType(str, Enum):
    """Memory type classification for agent states."""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    WORKING = "working"


class StateManager:
    """Manages agent state persistence with versioning and history."""

    def __init__(self, db_path: str = ".agent_states.db"):
        """
        Initialize StateManager with SQLite database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main states table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    state_data TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(agent_id, memory_type, version)
                )
            """)

            # History table for audit trail
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    state_data TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    operation TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            # Indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_memory
                ON agent_states(agent_id, memory_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_agent
                ON state_history(agent_id, timestamp)
            """)

            conn.commit()

    def _serialize_state(self, state: Dict[str, Any]) -> str:
        """
        Serialize state to JSON string.

        Args:
            state: State dictionary to serialize

        Returns:
            JSON string representation
        """
        def json_serializer(obj):
            """Handle non-JSON-serializable objects."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return json.dumps(state, indent=2, default=json_serializer)

    def _deserialize_state(self, state_json: str) -> Dict[str, Any]:
        """
        Deserialize JSON string to state dictionary.

        Args:
            state_json: JSON string to deserialize

        Returns:
            State dictionary
        """
        return json.loads(state_json)

    def _get_latest_version(self, agent_id: str, memory_type: MemoryType) -> int:
        """
        Get latest version number for agent and memory type.

        Args:
            agent_id: Agent identifier
            memory_type: Type of memory

        Returns:
            Latest version number (0 if none exists)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(version) FROM agent_states
                WHERE agent_id = ? AND memory_type = ?
            """, (agent_id, memory_type.value))
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0

    def save(
        self,
        agent_id: str,
        state: Dict[str, Any],
        memory_type: MemoryType = MemoryType.WORKING
    ) -> bool:
        """
        Save agent state with versioning.

        Args:
            agent_id: Agent identifier
            state: State dictionary to save
            memory_type: Type of memory

        Returns:
            True if successful
        """
        try:
            state_json = self._serialize_state(state)
            timestamp = datetime.utcnow().isoformat()
            version = self._get_latest_version(agent_id, memory_type) + 1

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Insert new state
                cursor.execute("""
                    INSERT INTO agent_states
                    (agent_id, memory_type, state_data, version, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (agent_id, memory_type.value, state_json, version, timestamp))

                # Record in history
                cursor.execute("""
                    INSERT INTO state_history
                    (agent_id, memory_type, state_data, version, operation, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (agent_id, memory_type.value, state_json, version, "SAVE", timestamp))

                conn.commit()
                return True

        except Exception as e:
            print(f"Error saving state: {e}", file=sys.stderr)
            return False

    def load(
        self,
        agent_id: str,
        memory_type: Optional[MemoryType] = None,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load agent state.

        Args:
            agent_id: Agent identifier
            memory_type: Type of memory (if None, loads all types)
            version: Specific version to load (if None, loads latest)

        Returns:
            State dictionary or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if memory_type is None:
                    # Load all memory types
                    cursor.execute("""
                        SELECT memory_type, state_data, version, created_at
                        FROM agent_states
                        WHERE agent_id = ?
                        ORDER BY memory_type, version DESC
                    """, (agent_id,))

                    results = cursor.fetchall()
                    if not results:
                        return None

                    # Group by memory type, take latest version
                    state = {}
                    seen_types = set()
                    for mem_type, data, ver, created in results:
                        if mem_type not in seen_types:
                            state[mem_type] = self._deserialize_state(data)
                            state[mem_type]["_version"] = ver
                            state[mem_type]["_created_at"] = created
                            seen_types.add(mem_type)
                    return state

                else:
                    # Load specific memory type
                    if version is None:
                        cursor.execute("""
                            SELECT state_data, version, created_at
                            FROM agent_states
                            WHERE agent_id = ? AND memory_type = ?
                            ORDER BY version DESC
                            LIMIT 1
                        """, (agent_id, memory_type.value))
                    else:
                        cursor.execute("""
                            SELECT state_data, version, created_at
                            FROM agent_states
                            WHERE agent_id = ? AND memory_type = ? AND version = ?
                        """, (agent_id, memory_type.value, version))

                    result = cursor.fetchone()
                    if result:
                        state = self._deserialize_state(result[0])
                        state["_version"] = result[1]
                        state["_created_at"] = result[2]
                        return state
                    return None

        except Exception as e:
            print(f"Error loading state: {e}", file=sys.stderr)
            return None

    def query(
        self,
        agent_id: str,
        memory_type: Optional[MemoryType] = None
    ) -> List[Dict[str, Any]]:
        """
        Query all states for an agent.

        Args:
            agent_id: Agent identifier
            memory_type: Filter by memory type (optional)

        Returns:
            List of state dictionaries with metadata
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if memory_type:
                    cursor.execute("""
                        SELECT memory_type, state_data, version, created_at
                        FROM agent_states
                        WHERE agent_id = ? AND memory_type = ?
                        ORDER BY version DESC
                    """, (agent_id, memory_type.value))
                else:
                    cursor.execute("""
                        SELECT memory_type, state_data, version, created_at
                        FROM agent_states
                        WHERE agent_id = ?
                        ORDER BY memory_type, version DESC
                    """, (agent_id,))

                results = []
                for mem_type, data, version, created in cursor.fetchall():
                    state = self._deserialize_state(data)
                    results.append({
                        "memory_type": mem_type,
                        "version": version,
                        "created_at": created,
                        "state": state
                    })
                return results

        except Exception as e:
            print(f"Error querying states: {e}", file=sys.stderr)
            return []

    def history(
        self,
        agent_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get state history for an agent.

        Args:
            agent_id: Agent identifier
            limit: Maximum number of history entries

        Returns:
            List of history entries with metadata
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT memory_type, operation, version, timestamp
                    FROM state_history
                    WHERE agent_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (agent_id, limit))

                history = []
                for mem_type, operation, version, timestamp in cursor.fetchall():
                    history.append({
                        "memory_type": mem_type,
                        "operation": operation,
                        "version": version,
                        "timestamp": timestamp
                    })
                return history

        except Exception as e:
            print(f"Error retrieving history: {e}", file=sys.stderr)
            return []

    def clear(
        self,
        agent_id: str,
        memory_type: Optional[MemoryType] = None
    ) -> bool:
        """
        Clear agent state(s).

        Args:
            agent_id: Agent identifier
            memory_type: Type of memory to clear (if None, clears all)

        Returns:
            True if successful
        """
        try:
            timestamp = datetime.utcnow().isoformat()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if memory_type:
                    # Clear specific memory type
                    cursor.execute("""
                        DELETE FROM agent_states
                        WHERE agent_id = ? AND memory_type = ?
                    """, (agent_id, memory_type.value))

                    # Record in history
                    cursor.execute("""
                        INSERT INTO state_history
                        (agent_id, memory_type, state_data, version, operation, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (agent_id, memory_type.value, "{}", 0, "CLEAR", timestamp))
                else:
                    # Clear all memory types
                    cursor.execute("""
                        DELETE FROM agent_states
                        WHERE agent_id = ?
                    """, (agent_id,))

                    # Record in history
                    for mem_type in MemoryType:
                        cursor.execute("""
                            INSERT INTO state_history
                            (agent_id, memory_type, state_data, version, operation, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (agent_id, mem_type.value, "{}", 0, "CLEAR", timestamp))

                conn.commit()
                return True

        except Exception as e:
            print(f"Error clearing state: {e}", file=sys.stderr)
            return False


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Agent State Manager - Manage agent state persistence"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Save command
    save_parser = subparsers.add_parser("save", help="Save agent state")
    save_parser.add_argument("--agent-id", required=True, help="Agent identifier")
    save_parser.add_argument("--state", required=True, help="Path to state JSON file")
    save_parser.add_argument(
        "--memory-type",
        choices=[m.value for m in MemoryType],
        default=MemoryType.WORKING.value,
        help="Memory type"
    )
    save_parser.add_argument("--db", default=".agent_states.db", help="Database path")

    # Load command
    load_parser = subparsers.add_parser("load", help="Load agent state")
    load_parser.add_argument("--agent-id", required=True, help="Agent identifier")
    load_parser.add_argument(
        "--memory-type",
        choices=[m.value for m in MemoryType],
        help="Memory type (optional, loads all if not specified)"
    )
    load_parser.add_argument("--version", type=int, help="Specific version to load")
    load_parser.add_argument("--db", default=".agent_states.db", help="Database path")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query agent states")
    query_parser.add_argument("--agent-id", required=True, help="Agent identifier")
    query_parser.add_argument(
        "--memory-type",
        choices=[m.value for m in MemoryType],
        help="Memory type filter"
    )
    query_parser.add_argument("--db", default=".agent_states.db", help="Database path")

    # History command
    history_parser = subparsers.add_parser("history", help="Get state history")
    history_parser.add_argument("--agent-id", required=True, help="Agent identifier")
    history_parser.add_argument("--limit", type=int, default=10, help="History limit")
    history_parser.add_argument("--db", default=".agent_states.db", help="Database path")

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear agent state")
    clear_parser.add_argument("--agent-id", required=True, help="Agent identifier")
    clear_parser.add_argument(
        "--memory-type",
        choices=[m.value for m in MemoryType],
        help="Memory type to clear (clears all if not specified)"
    )
    clear_parser.add_argument("--db", default=".agent_states.db", help="Database path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize state manager
    manager = StateManager(db_path=args.db)

    # Execute command
    if args.command == "save":
        state_path = Path(args.state)
        if not state_path.exists():
            print(f"Error: State file not found: {args.state}", file=sys.stderr)
            return 1

        with open(state_path) as f:
            state = json.load(f)

        memory_type = MemoryType(args.memory_type)
        if manager.save(args.agent_id, state, memory_type):
            print(f"State saved: agent={args.agent_id}, type={memory_type.value}")
            return 0
        return 1

    elif args.command == "load":
        memory_type = MemoryType(args.memory_type) if args.memory_type else None
        state = manager.load(args.agent_id, memory_type, args.version)
        if state:
            print(json.dumps(state, indent=2))
            return 0
        print(f"No state found for agent: {args.agent_id}", file=sys.stderr)
        return 1

    elif args.command == "query":
        memory_type = MemoryType(args.memory_type) if args.memory_type else None
        results = manager.query(args.agent_id, memory_type)
        print(json.dumps(results, indent=2))
        return 0

    elif args.command == "history":
        history = manager.history(args.agent_id, args.limit)
        print(json.dumps(history, indent=2))
        return 0

    elif args.command == "clear":
        memory_type = MemoryType(args.memory_type) if args.memory_type else None
        if manager.clear(args.agent_id, memory_type):
            type_str = memory_type.value if memory_type else "all"
            print(f"State cleared: agent={args.agent_id}, type={type_str}")
            return 0
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
