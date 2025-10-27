#!/usr/bin/env python3
"""
MQTT Config Validator

Validates MQTT broker configurations (Mosquitto, EMQX), topic naming conventions,
security settings, and ACL rules.

Usage:
    ./validate_mqtt_config.py --config mosquitto.conf
    ./validate_mqtt_config.py --config mosquitto.conf --check-acl --json
    ./validate_mqtt_config.py --check-topics --topics-file topics.txt
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Optional

@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    severity: str  # error, warning, info
    category: str  # config, security, topics, acl
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class ValidationResult:
    """Validation results"""
    valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)

    def add_error(self, category: str, message: str, line: Optional[int] = None, suggestion: Optional[str] = None):
        self.valid = False
        self.issues.append(ValidationIssue("error", category, message, line, suggestion))

    def add_warning(self, category: str, message: str, line: Optional[int] = None, suggestion: Optional[str] = None):
        self.issues.append(ValidationIssue("warning", category, message, line, suggestion))

    def add_info(self, category: str, message: str, line: Optional[int] = None):
        self.issues.append(ValidationIssue("info", category, message, line))

class MosquittoConfigValidator:
    """Validates Mosquitto configuration files"""

    def __init__(self):
        self.config = {}
        self.listeners = []
        self.has_tls = False
        self.has_auth = False
        self.has_acl = False

    def validate_file(self, config_path: str) -> ValidationResult:
        """Validate Mosquitto configuration file"""
        result = ValidationResult()

        if not os.path.exists(config_path):
            result.add_error("config", f"Config file not found: {config_path}")
            return result

        # Parse config
        try:
            with open(config_path, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            result.add_error("config", f"Failed to read config: {e}")
            return result

        # Parse lines
        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse key-value
            if ' ' in line:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    key, value = parts
                    self.config[key] = value

                    # Track specific settings
                    if key == 'listener':
                        self.listeners.append(value)
                    elif key in ('cafile', 'certfile', 'keyfile'):
                        self.has_tls = True
                    elif key in ('password_file', 'auth_plugin'):
                        self.has_auth = True
                    elif key == 'acl_file':
                        self.has_acl = True

        # Validate settings
        self._validate_listeners(result)
        self._validate_security(result)
        self._validate_persistence(result)
        self._validate_limits(result)

        # Stats
        result.stats = {
            "listeners": len(self.listeners),
            "has_tls": self.has_tls,
            "has_auth": self.has_auth,
            "has_acl": self.has_acl,
            "settings_count": len(self.config)
        }

        return result

    def _validate_listeners(self, result: ValidationResult):
        """Validate listener configuration"""
        if not self.listeners:
            result.add_warning("config", "No listeners defined, using default 1883")

        for listener in self.listeners:
            parts = listener.split()
            if len(parts) < 1:
                result.add_error("config", f"Invalid listener: {listener}")
                continue

            port = parts[0]
            try:
                port_num = int(port)
                if port_num < 1 or port_num > 65535:
                    result.add_error("config", f"Invalid port: {port}")
            except ValueError:
                result.add_error("config", f"Invalid port: {port}")

            # Check common ports
            if port == "1883":
                result.add_info("config", "Using default MQTT port 1883 (unencrypted)")
            elif port == "8883":
                result.add_info("config", "Using MQTT TLS port 8883")
                if not self.has_tls:
                    result.add_warning("security", "Port 8883 but no TLS certificates configured")
            elif port == "9001":
                result.add_info("config", "Using WebSocket port 9001")

    def _validate_security(self, result: ValidationResult):
        """Validate security configuration"""
        # Anonymous access
        allow_anonymous = self.config.get('allow_anonymous', 'true')
        if allow_anonymous.lower() == 'true':
            result.add_warning(
                "security",
                "Anonymous access enabled",
                suggestion="Set allow_anonymous=false and configure password_file"
            )

        # TLS
        if self.has_tls:
            # Check certificate files exist
            for cert_key in ('cafile', 'certfile', 'keyfile'):
                if cert_key in self.config:
                    cert_path = self.config[cert_key]
                    if not os.path.exists(cert_path):
                        result.add_error(
                            "security",
                            f"Certificate file not found: {cert_path}",
                            suggestion=f"Create or fix path for {cert_key}"
                        )

            # Check TLS version
            tls_version = self.config.get('tls_version')
            if tls_version:
                if tls_version in ('tlsv1', 'tlsv1.1'):
                    result.add_warning(
                        "security",
                        f"Weak TLS version: {tls_version}",
                        suggestion="Use tlsv1.2 or tlsv1.3"
                    )
            else:
                result.add_info("security", "TLS version not specified, using default")
        else:
            result.add_warning(
                "security",
                "No TLS configuration found",
                suggestion="Configure TLS with cafile, certfile, keyfile"
            )

        # Authentication
        if not self.has_auth:
            result.add_warning(
                "security",
                "No authentication configured",
                suggestion="Configure password_file or auth_plugin"
            )
        else:
            # Check password file exists
            password_file = self.config.get('password_file')
            if password_file and not os.path.exists(password_file):
                result.add_error(
                    "security",
                    f"Password file not found: {password_file}",
                    suggestion="Create password file with mosquitto_passwd"
                )

        # ACL
        if not self.has_acl:
            result.add_warning(
                "security",
                "No ACL configuration found",
                suggestion="Configure acl_file for topic access control"
            )
        else:
            # Check ACL file exists
            acl_file = self.config.get('acl_file')
            if acl_file and not os.path.exists(acl_file):
                result.add_error(
                    "security",
                    f"ACL file not found: {acl_file}",
                    suggestion="Create ACL file"
                )

    def _validate_persistence(self, result: ValidationResult):
        """Validate persistence configuration"""
        persistence = self.config.get('persistence', 'false')

        if persistence.lower() == 'true':
            result.add_info("config", "Persistence enabled")

            # Check persistence location
            persistence_location = self.config.get('persistence_location')
            if persistence_location:
                if not os.path.exists(persistence_location):
                    result.add_error(
                        "config",
                        f"Persistence directory not found: {persistence_location}",
                        suggestion="Create directory or fix path"
                    )
            else:
                result.add_warning(
                    "config",
                    "Persistence enabled but no persistence_location set",
                    suggestion="Set persistence_location to avoid default"
                )

            # Check autosave interval
            autosave = self.config.get('autosave_interval')
            if autosave:
                try:
                    interval = int(autosave)
                    if interval < 60:
                        result.add_warning(
                            "config",
                            f"Autosave interval very short: {interval}s",
                            suggestion="Consider 300s or higher for production"
                        )
                except ValueError:
                    result.add_error("config", f"Invalid autosave_interval: {autosave}")
        else:
            result.add_warning(
                "config",
                "Persistence disabled, messages will be lost on restart",
                suggestion="Enable persistence for production"
            )

    def _validate_limits(self, result: ValidationResult):
        """Validate resource limits"""
        # Max connections
        max_connections = self.config.get('max_connections')
        if max_connections:
            try:
                max_conn = int(max_connections)
                if max_conn < 100:
                    result.add_warning("config", f"Low max_connections: {max_conn}")
            except ValueError:
                result.add_error("config", f"Invalid max_connections: {max_connections}")
        else:
            result.add_info("config", "No max_connections limit set (unlimited)")

        # Max queued messages
        max_queued = self.config.get('max_queued_messages')
        if max_queued:
            try:
                max_q = int(max_queued)
                if max_q < 100:
                    result.add_warning("config", f"Low max_queued_messages: {max_q}")
            except ValueError:
                result.add_error("config", f"Invalid max_queued_messages: {max_queued}")

        # Message size limit
        msg_size = self.config.get('message_size_limit')
        if msg_size:
            try:
                # Parse size (e.g., "1MB", "1024")
                size_str = msg_size.upper()
                if 'MB' in size_str:
                    size_bytes = int(size_str.replace('MB', '')) * 1024 * 1024
                elif 'KB' in size_str:
                    size_bytes = int(size_str.replace('KB', '')) * 1024
                else:
                    size_bytes = int(msg_size)

                if size_bytes > 10 * 1024 * 1024:  # 10 MB
                    result.add_warning(
                        "config",
                        f"Large message_size_limit: {msg_size}",
                        suggestion="MQTT is designed for small messages (<10 KB)"
                    )
            except ValueError:
                result.add_error("config", f"Invalid message_size_limit: {msg_size}")

class TopicValidator:
    """Validates MQTT topic naming conventions"""

    # Valid topic characters (simplified, UTF-8 allowed)
    TOPIC_PATTERN = re.compile(r'^[a-zA-Z0-9/_\-]+$')

    def validate_topic(self, topic: str) -> ValidationResult:
        """Validate a single topic"""
        result = ValidationResult()

        if not topic:
            result.add_error("topics", "Empty topic")
            return result

        # Check wildcards (wildcards not allowed in published topics)
        if '+' in topic or '#' in topic:
            result.add_warning(
                "topics",
                f"Wildcards in topic (only for subscriptions): {topic}"
            )

        # Check leading/trailing slashes
        if topic.startswith('/'):
            result.add_warning(
                "topics",
                f"Topic starts with /: {topic}",
                suggestion="Remove leading slash"
            )
        if topic.endswith('/'):
            result.add_warning(
                "topics",
                f"Topic ends with /: {topic}",
                suggestion="Remove trailing slash"
            )

        # Check reserved topics
        if topic.startswith('$'):
            result.add_info("topics", f"Reserved system topic: {topic}")

        # Check depth
        levels = topic.count('/') + 1
        if levels > 7:
            result.add_warning(
                "topics",
                f"Topic very deep ({levels} levels): {topic}",
                suggestion="Keep topics to 3-7 levels"
            )

        # Check special characters
        if not self.TOPIC_PATTERN.match(topic):
            result.add_warning(
                "topics",
                f"Topic contains special characters: {topic}",
                suggestion="Use only alphanumeric, /, _, -"
            )

        # Check spaces
        if ' ' in topic:
            result.add_error(
                "topics",
                f"Topic contains spaces: {topic}",
                suggestion="Use underscores instead of spaces"
            )

        # Check naming conventions
        if not topic.islower():
            result.add_info(
                "topics",
                f"Topic not lowercase: {topic}",
                suggestion="Use lowercase for consistency"
            )

        # Check for data in topic
        if any(c.isdigit() for c in topic.split('/')[-1]):
            if topic.split('/')[-1].replace('.', '').replace('-', '').isdigit():
                result.add_warning(
                    "topics",
                    f"Possible data embedded in topic: {topic}",
                    suggestion="Put data in payload, not topic"
                )

        return result

    def validate_topics_file(self, topics_file: str) -> ValidationResult:
        """Validate topics from a file"""
        result = ValidationResult()

        if not os.path.exists(topics_file):
            result.add_error("topics", f"Topics file not found: {topics_file}")
            return result

        try:
            with open(topics_file, 'r') as f:
                topics = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except Exception as e:
            result.add_error("topics", f"Failed to read topics file: {e}")
            return result

        # Validate each topic
        all_topics_valid = True
        for topic in topics:
            topic_result = self.validate_topic(topic)
            if not topic_result.valid:
                all_topics_valid = False
            result.issues.extend(topic_result.issues)

        result.valid = all_topics_valid
        result.stats = {"total_topics": len(topics)}

        return result

class ACLValidator:
    """Validates Mosquitto ACL files"""

    def validate_acl_file(self, acl_file: str) -> ValidationResult:
        """Validate ACL file"""
        result = ValidationResult()

        if not os.path.exists(acl_file):
            result.add_error("acl", f"ACL file not found: {acl_file}")
            return result

        try:
            with open(acl_file, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            result.add_error("acl", f"Failed to read ACL file: {e}")
            return result

        current_user = None
        rules = []

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse user directive
            if line.startswith('user '):
                current_user = line[5:].strip()
                if not current_user:
                    result.add_error("acl", "Empty user", line_num)
                continue

            # Parse topic directive
            if line.startswith('topic '):
                if not current_user:
                    result.add_error(
                        "acl",
                        "Topic rule without user",
                        line_num,
                        suggestion="Add 'user <username>' before topic rules"
                    )
                    continue

                parts = line[6:].strip().split(None, 1)
                if len(parts) < 2:
                    result.add_error("acl", f"Invalid topic rule: {line}", line_num)
                    continue

                permission, topic = parts
                if permission not in ('read', 'write', 'readwrite'):
                    result.add_error(
                        "acl",
                        f"Invalid permission: {permission}",
                        line_num,
                        suggestion="Use read, write, or readwrite"
                    )
                    continue

                rules.append((current_user, permission, topic))

                # Validate topic
                topic_validator = TopicValidator()
                topic_result = topic_validator.validate_topic(topic.replace('%u', 'user').replace('%c', 'client'))
                for issue in topic_result.issues:
                    issue.line = line_num
                    result.issues.append(issue)

        # Check for wildcard subscriptions
        for user, permission, topic in rules:
            if permission == 'read' and topic == '#':
                result.add_warning(
                    "acl",
                    f"User {user} can subscribe to all topics (#)",
                    suggestion="Restrict to specific topic patterns"
                )

        result.stats = {
            "total_users": len(set(r[0] for r in rules)),
            "total_rules": len(rules)
        }

        return result

def format_output(result: ValidationResult, output_json: bool = False) -> str:
    """Format validation results"""
    if output_json:
        # JSON output
        output = {
            "valid": result.valid,
            "stats": result.stats,
            "issues": [asdict(issue) for issue in result.issues]
        }
        return json.dumps(output, indent=2)
    else:
        # Human-readable output
        lines = []

        # Header
        if result.valid:
            lines.append("✓ Validation passed\n")
        else:
            lines.append("✗ Validation failed\n")

        # Stats
        if result.stats:
            lines.append("Statistics:")
            for key, value in result.stats.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        # Issues
        if result.issues:
            # Group by severity
            errors = [i for i in result.issues if i.severity == 'error']
            warnings = [i for i in result.issues if i.severity == 'warning']
            infos = [i for i in result.issues if i.severity == 'info']

            if errors:
                lines.append(f"Errors ({len(errors)}):")
                for issue in errors:
                    line_str = f" (line {issue.line})" if issue.line else ""
                    lines.append(f"  ✗ [{issue.category}]{line_str} {issue.message}")
                    if issue.suggestion:
                        lines.append(f"    → {issue.suggestion}")
                lines.append("")

            if warnings:
                lines.append(f"Warnings ({len(warnings)}):")
                for issue in warnings:
                    line_str = f" (line {issue.line})" if issue.line else ""
                    lines.append(f"  ⚠ [{issue.category}]{line_str} {issue.message}")
                    if issue.suggestion:
                        lines.append(f"    → {issue.suggestion}")
                lines.append("")

            if infos:
                lines.append(f"Info ({len(infos)}):")
                for issue in infos:
                    line_str = f" (line {issue.line})" if issue.line else ""
                    lines.append(f"  ℹ [{issue.category}]{line_str} {issue.message}")
                lines.append("")

        return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(
        description="Validate MQTT broker configurations and topics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate Mosquitto config
  %(prog)s --config /etc/mosquitto/mosquitto.conf

  # Validate with ACL
  %(prog)s --config mosquitto.conf --check-acl

  # Validate topics from file
  %(prog)s --check-topics --topics-file topics.txt

  # JSON output
  %(prog)s --config mosquitto.conf --json
        """
    )

    parser.add_argument(
        '--config',
        help='Mosquitto config file to validate'
    )
    parser.add_argument(
        '--check-acl',
        action='store_true',
        help='Also validate ACL file (if specified in config)'
    )
    parser.add_argument(
        '--check-topics',
        action='store_true',
        help='Validate topic naming conventions'
    )
    parser.add_argument(
        '--topics-file',
        help='File containing topics to validate (one per line)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    if not any([args.config, args.check_topics]):
        parser.print_help()
        sys.exit(1)

    all_results = []

    # Validate config
    if args.config:
        validator = MosquittoConfigValidator()
        result = validator.validate_file(args.config)
        all_results.append(("Config", result))

        # Check ACL if requested
        if args.check_acl and validator.has_acl:
            acl_file = validator.config.get('acl_file')
            if acl_file:
                acl_validator = ACLValidator()
                acl_result = acl_validator.validate_acl_file(acl_file)
                all_results.append(("ACL", acl_result))

    # Validate topics
    if args.check_topics:
        if not args.topics_file:
            print("Error: --topics-file required with --check-topics")
            sys.exit(1)

        topic_validator = TopicValidator()
        topic_result = topic_validator.validate_topics_file(args.topics_file)
        all_results.append(("Topics", topic_result))

    # Output results
    if args.json:
        # Combine results for JSON
        combined = {
            "valid": all(r[1].valid for r in all_results),
            "results": {
                name: {
                    "valid": result.valid,
                    "stats": result.stats,
                    "issues": [asdict(issue) for issue in result.issues]
                }
                for name, result in all_results
            }
        }
        print(json.dumps(combined, indent=2))
    else:
        # Human-readable output
        for name, result in all_results:
            print(f"=== {name} Validation ===\n")
            print(format_output(result))

    # Exit code
    exit_code = 0 if all(r[1].valid for r in all_results) else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
