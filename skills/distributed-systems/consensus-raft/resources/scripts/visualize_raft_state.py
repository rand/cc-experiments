#!/usr/bin/env python3
"""visualize_raft_state.py - Generate RAFT state machine visualizations

Usage:
    ./visualize_raft_state.py [options]

Options:
    --type TYPE              Type of visualization (state-machine, log-replication,
                            leader-election, cluster-status) (default: state-machine)
    --endpoints HOST:PORT    Comma-separated etcd endpoints (default: localhost:2379)
    --output FILE            Output file path (default: stdout for text, raft_state.svg for diagrams)
    --format FORMAT          Output format (mermaid, graphviz, ascii, svg) (default: mermaid)
    --json                   Output JSON format for cluster-status
    --help                   Show this help message

Examples:
    # Generate state machine diagram
    ./visualize_raft_state.py --type state-machine --format svg --output state.svg

    # Visualize log replication
    ./visualize_raft_state.py --type log-replication --format mermaid

    # Show cluster status
    ./visualize_raft_state.py --type cluster-status --endpoints localhost:2379

    # Generate all diagrams
    ./visualize_raft_state.py --type leader-election --format ascii
"""

import argparse
import json
import sys
from typing import Dict, List, Optional

try:
    import etcd3
except ImportError:
    etcd3 = None


class RaftStateVisualizer:
    """Generate RAFT state machine visualizations"""

    @staticmethod
    def generate_state_machine_mermaid() -> str:
        """Generate state machine diagram in Mermaid format"""
        return """stateDiagram-v2
    [*] --> Follower: Start

    Follower --> Candidate: Election timeout
    Candidate --> Candidate: Election timeout,<br/>split vote
    Candidate --> Leader: Receives votes<br/>from majority
    Candidate --> Follower: Discovers current<br/>leader or new term

    Leader --> Follower: Discovers server<br/>with higher term

    Follower --> Follower: Receives valid<br/>AppendEntries RPC

    note right of Follower
        - Responds to RPCs from<br/>candidates and leaders
        - If election timeout,<br/>start election
    end note

    note right of Candidate
        - Increments term
        - Votes for self
        - Sends RequestVote RPCs<br/>to all servers
        - Resets election timer
    end note

    note right of Leader
        - Sends heartbeats<br/>(empty AppendEntries)<br/>to all servers
        - Replicates log entries
        - Commits entries when<br/>majority replicated
    end note
"""

    @staticmethod
    def generate_state_machine_graphviz() -> str:
        """Generate state machine diagram in Graphviz format"""
        return """digraph raft_state_machine {
    rankdir=LR;
    node [shape=circle, style=filled, fillcolor=lightblue];

    start [shape=point, width=0.3];
    follower [label="Follower"];
    candidate [label="Candidate"];
    leader [label="Leader"];

    start -> follower [label="Start"];

    follower -> candidate [label="Election timeout"];
    follower -> follower [label="Valid AppendEntries"];

    candidate -> candidate [label="Election timeout\\nSplit vote"];
    candidate -> leader [label="Majority votes"];
    candidate -> follower [label="Discovers leader\\nor higher term"];

    leader -> follower [label="Discovers\\nhigher term"];

    // Annotations
    follower [xlabel="Responds to RPCs\\nElection timeout -> start election"];
    candidate [xlabel="Increment term\\nVote for self\\nRequest votes"];
    leader [xlabel="Send heartbeats\\nReplicate logs\\nCommit entries"];
}
"""

    @staticmethod
    def generate_state_machine_ascii() -> str:
        """Generate state machine diagram in ASCII format"""
        return """
RAFT State Machine
==================

                   Election timeout
                 ┌──────────────────┐
                 │                  │
                 ▼                  │
         ┌──────────────┐  Election timeout   ┌──────────────┐
    ┌───▶│   Follower   │  (split vote)  ┌───▶│  Candidate   │
    │    └──────────────┘◀────────────────┘    └──────────────┘
    │           │                                      │
    │           │                                      │
    │           │ Valid AppendEntries                  │ Receives votes
    │           │                                      │ from majority
    │           └──────┐                               │
    │                  │                               ▼
    │                  │                        ┌──────────────┐
    │                  │                        │    Leader    │
    │                  │                        └──────────────┘
    │                  │                               │
    │                  │    Discovers server with      │
    │                  │    higher term                │
    └──────────────────┴───────────────────────────────┘

State Descriptions:
-------------------
Follower:  - Responds to RPCs from candidates and leaders
           - If election timeout elapses, transition to Candidate

Candidate: - Increment current term
           - Vote for self
           - Send RequestVote RPCs to all other servers
           - Reset election timer

Leader:    - Send heartbeats (empty AppendEntries RPCs) to all servers
           - Replicate log entries to followers
           - Commit entries when majority have replicated
"""

    @staticmethod
    def generate_log_replication_mermaid() -> str:
        """Generate log replication sequence diagram"""
        return """sequenceDiagram
    participant Client
    participant Leader
    participant Follower1
    participant Follower2

    Client->>Leader: Write(key, value)
    Note over Leader: 1. Append to local log

    Leader->>Follower1: AppendEntries(entry, prev_index, prev_term)
    Leader->>Follower2: AppendEntries(entry, prev_index, prev_term)

    Note over Follower1: 2. Check log consistency<br/>(prev_index, prev_term)
    Note over Follower2: 2. Check log consistency<br/>(prev_index, prev_term)

    Follower1->>Leader: Success
    Follower2->>Leader: Success

    Note over Leader: 3. Entry replicated on majority<br/>Increment commit_index
    Note over Leader: 4. Apply to state machine

    Leader->>Client: Write successful

    Leader->>Follower1: AppendEntries(commit_index)
    Leader->>Follower2: AppendEntries(commit_index)

    Note over Follower1: 5. Apply committed<br/>entries to state machine
    Note over Follower2: 5. Apply committed<br/>entries to state machine
"""

    @staticmethod
    def generate_log_replication_ascii() -> str:
        """Generate log replication ASCII diagram"""
        return """
RAFT Log Replication
====================

Client Request Flow:
--------------------

Client          Leader          Follower 1      Follower 2
  │               │                  │               │
  │─Write(k,v)───▶│                  │               │
  │               │                  │               │
  │               │ 1. Append to     │               │
  │               │    local log     │               │
  │               │                  │               │
  │               │─AppendEntries───▶│               │
  │               │─AppendEntries───────────────────▶│
  │               │                  │               │
  │               │              2. Check            │
  │               │                 prev_log         │
  │               │                  │               │
  │               │◀────Success──────│               │
  │               │◀────Success──────────────────────│
  │               │                  │               │
  │               │ 3. Majority      │               │
  │               │    replicated    │               │
  │               │ 4. Apply to SM   │               │
  │               │                  │               │
  │◀──Success─────│                  │               │
  │               │                  │               │
  │               │─AppendEntries───▶│               │
  │               │  (commit_index)  │               │
  │               │─AppendEntries───────────────────▶│
  │               │                  │               │
  │               │              5. Apply to     5. Apply to
  │               │                 state            state
  │               │                 machine          machine

Log Structure:
--------------

Index:  1    2    3    4    5    6
       ┌────┬────┬────┬────┬────┬────┐
       │ T1 │ T1 │ T2 │ T2 │ T3 │ T3 │
       └────┴────┴────┴────┴────┴────┘
         ^                   ^
         │                   │
    committed           last log entry

    T = Term number
"""

    @staticmethod
    def generate_leader_election_mermaid() -> str:
        """Generate leader election sequence diagram"""
        return """sequenceDiagram
    participant F1 as Follower 1<br/>(Becomes Candidate)
    participant F2 as Follower 2
    participant F3 as Follower 3

    Note over F1: Election timeout
    Note over F1: Increment term to 2<br/>Vote for self

    F1->>F2: RequestVote(term=2, candidateId=1)
    F1->>F3: RequestVote(term=2, candidateId=1)

    Note over F2: Haven't voted this term<br/>Candidate's log is current
    Note over F3: Haven't voted this term<br/>Candidate's log is current

    F2->>F1: VoteGranted=true
    F3->>F1: VoteGranted=true

    Note over F1: Received majority votes<br/>(3/3 total)<br/>Become Leader

    F1->>F2: AppendEntries(heartbeat)
    F1->>F3: AppendEntries(heartbeat)

    Note over F2: Recognize new leader<br/>Reset election timer
    Note over F3: Recognize new leader<br/>Reset election timer
"""

    def get_cluster_status(self, endpoints: str) -> Optional[Dict]:
        """Get live cluster status from etcd"""
        if etcd3 is None:
            return None

        try:
            host, port = endpoints.split(",")[0].split(":")
            client = etcd3.client(host=host, port=int(port))

            # Get cluster members
            members = client.members

            # Get leader info
            status = {"nodes": [], "leader_id": None}

            for member in members:
                node_info = {
                    "id": str(member.id),
                    "name": member.name,
                    "peer_urls": member.peer_urls,
                    "client_urls": member.client_urls
                }
                status["nodes"].append(node_info)

            return status
        except Exception as e:
            return {"error": str(e)}

    def generate_cluster_status_ascii(self, endpoints: str) -> str:
        """Generate ASCII visualization of cluster status"""
        status = self.get_cluster_status(endpoints)

        if status is None:
            return "Error: etcd3 library not installed\nInstall with: pip install etcd3-py"

        if "error" in status:
            return f"Error connecting to cluster: {status['error']}"

        output = "RAFT Cluster Status\n"
        output += "=" * 50 + "\n\n"

        for node in status["nodes"]:
            output += f"Node: {node['name']}\n"
            output += f"  ID: {node['id']}\n"
            output += f"  Peer URLs: {', '.join(node['peer_urls'])}\n"
            output += f"  Client URLs: {', '.join(node['client_urls'])}\n"
            output += "\n"

        return output


def main():
    parser = argparse.ArgumentParser(
        description="Generate RAFT state machine visualizations",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--type",
        choices=["state-machine", "log-replication", "leader-election", "cluster-status"],
        default="state-machine",
        help="Type of visualization (default: state-machine)"
    )
    parser.add_argument(
        "--endpoints",
        default="localhost:2379",
        help="Comma-separated etcd endpoints (default: localhost:2379)"
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--format",
        choices=["mermaid", "graphviz", "ascii"],
        default="mermaid",
        help="Output format (default: mermaid)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON format for cluster-status"
    )

    args = parser.parse_args()

    visualizer = RaftStateVisualizer()

    # Generate visualization
    if args.type == "state-machine":
        if args.format == "mermaid":
            output = visualizer.generate_state_machine_mermaid()
        elif args.format == "graphviz":
            output = visualizer.generate_state_machine_graphviz()
        else:  # ascii
            output = visualizer.generate_state_machine_ascii()

    elif args.type == "log-replication":
        if args.format == "mermaid":
            output = visualizer.generate_log_replication_mermaid()
        else:  # ascii (graphviz not implemented for this type)
            output = visualizer.generate_log_replication_ascii()

    elif args.type == "leader-election":
        if args.format == "mermaid":
            output = visualizer.generate_leader_election_mermaid()
        else:  # ascii
            output = "Leader election ASCII visualization not implemented yet.\nUse --format mermaid"

    elif args.type == "cluster-status":
        if args.json:
            status = visualizer.get_cluster_status(args.endpoints)
            output = json.dumps(status, indent=2)
        else:
            output = visualizer.generate_cluster_status_ascii(args.endpoints)

    # Write output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Visualization written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
