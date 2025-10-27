#!/usr/bin/env python3
"""
Create and track incidents with structured templates.

This script provides an interactive CLI for creating incident records,
war rooms, and notification workflows following incident response best practices.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
import uuid


class Severity(str, Enum):
    """Incident severity levels."""
    SEV1 = "SEV-1"
    SEV2 = "SEV-2"
    SEV3 = "SEV-3"
    SEV4 = "SEV-4"


class Status(str, Enum):
    """Incident status values."""
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class IncidentTemplate:
    """Incident data templates and structure."""

    @staticmethod
    def severity_criteria() -> Dict[str, Dict[str, Any]]:
        """Severity classification criteria."""
        return {
            "SEV-1": {
                "name": "Critical",
                "description": "Complete service outage or severe degradation",
                "impact": "Business-critical functions unavailable",
                "user_percentage": ">50%",
                "response_time": "Immediate, 24/7, all hands",
                "acknowledgment_target": "5 minutes",
                "examples": [
                    "Main website down",
                    "Payment processing broken",
                    "Data breach detected",
                    "Complete service outage"
                ]
            },
            "SEV-2": {
                "name": "High",
                "description": "Significant degradation affecting many users",
                "impact": "Major features impaired, subset of users affected",
                "user_percentage": "10-50%",
                "response_time": "Urgent, engage specialized team",
                "acknowledgment_target": "15 minutes",
                "examples": [
                    "Major feature broken",
                    "Performance degradation (>50% slower)",
                    "Regional outage",
                    "Database replication lag"
                ]
            },
            "SEV-3": {
                "name": "Medium",
                "description": "Minor degradation affecting some users",
                "impact": "Non-critical features impaired, workarounds available",
                "user_percentage": "1-10%",
                "response_time": "Standard on-call response",
                "acknowledgment_target": "30 minutes",
                "examples": [
                    "Minor feature broken",
                    "Non-critical API endpoint failing",
                    "Elevated error rates (<5%)",
                    "Performance issues for specific feature"
                ]
            },
            "SEV-4": {
                "name": "Low",
                "description": "Minimal or no user impact",
                "impact": "Internal tools affected, cosmetic issues",
                "user_percentage": "<1%",
                "response_time": "Normal business hours",
                "acknowledgment_target": "2 hours",
                "examples": [
                    "Internal dashboard broken",
                    "UI cosmetic issue",
                    "Non-critical batch job failed",
                    "Documentation errors"
                ]
            }
        }

    @staticmethod
    def war_room_template(incident_id: str, title: str,
                         severity: str) -> Dict[str, Any]:
        """Generate war room setup template."""
        return {
            "channel_name": f"incident-{datetime.now().strftime('%Y%m%d')}-{incident_id.lower()}",
            "topic": f"{severity}: {title} | IC: TBD | Started: {datetime.now(timezone.utc).strftime('%H:%M UTC')}",
            "initial_message": {
                "type": "header",
                "content": f"Incident {incident_id} - {severity}",
                "details": title
            },
            "roles": {
                "incident_commander": "TBD - Coordinates response, makes decisions",
                "tech_lead": "TBD - Hands on keyboard, implements fixes",
                "comms_lead": "TBD - Stakeholder updates",
                "scribe": "TBD - Documents timeline"
            },
            "pinned_links": [
                {"name": "Incident Ticket", "url": f"https://jira.example.com/{incident_id}"},
                {"name": "Dashboard", "url": "https://grafana.example.com/d/overview"},
                {"name": "Runbooks", "url": "https://runbooks.example.com"}
            ]
        }

    @staticmethod
    def communication_template(severity: str, title: str,
                              impact: str) -> Dict[str, List[str]]:
        """Generate communication templates by severity."""
        base = {
            "initial": [
                f"Subject: [{severity}] Service Disruption - {title}",
                "",
                "We are currently experiencing an issue affecting our service.",
                "",
                "IMPACT:",
                f"- {impact}",
                f"- Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                "",
                "STATUS:",
                "- Issue identified and team actively investigating",
                "- Working on mitigation",
                "",
                "NEXT UPDATE:",
                f"- Will provide update in {30 if severity == 'SEV-1' else 60} minutes",
                "- Status page: https://status.example.com",
                "",
                "[Incident Commander Name]"
            ]
        }

        if severity in ["SEV-1", "SEV-2"]:
            base["stakeholders"] = [
                "To: leadership@example.com, support@example.com",
                f"Subject: [{severity}] Active Incident - {title}",
                "",
                "INCIDENT SUMMARY:",
                f"- Severity: {severity}",
                f"- Started: {datetime.now(timezone.utc).strftime('%H:%M UTC')}",
                f"- Impact: {impact}",
                "",
                "CURRENT STATUS: Investigating",
                "",
                "TEAM ENGAGED:",
                "- Incident Commander: [Name]",
                "- On-call engineers: [Names]",
                "",
                "NEXT UPDATE: [Time]"
            ]

        return base

    @staticmethod
    def runbook_template(title: str, service: str) -> Dict[str, Any]:
        """Generate incident-specific runbook template."""
        return {
            "title": f"Runbook: {title}",
            "service": service,
            "sections": {
                "symptoms": [
                    "- Alert name and conditions",
                    "- User-visible symptoms",
                    "- Metric thresholds exceeded"
                ],
                "impact": [
                    "- User-facing features affected",
                    "- Business processes impacted",
                    "- Dependencies affected"
                ],
                "diagnosis": [
                    "1. Check recent deployments",
                    "2. Verify error rates and types",
                    "3. Check dependency health",
                    "4. Review resource utilization"
                ],
                "mitigation": {
                    "quick_fix": "< 5 minutes - Rollback/Scale/Disable",
                    "temporary_workaround": "5-30 minutes - Hotfix/Failover",
                    "proper_fix": "30+ minutes - Root cause fix"
                },
                "escalation": [
                    "If error rate > 20%: Page specialist team",
                    "If duration > 30 min: Page engineering manager",
                    "If data at risk: Page security team"
                ]
            }
        }


class IncidentManager:
    """Manage incident creation and tracking."""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize incident manager.

        Args:
            storage_path: Path to store incident data (default: ./incidents/)
        """
        self.storage_path = storage_path or Path("./incidents")
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def create_incident(
        self,
        title: str,
        severity: Severity,
        impact: str,
        service: str,
        detected_by: str = "monitoring",
        initial_status: Status = Status.INVESTIGATING
    ) -> Dict[str, Any]:
        """
        Create a new incident record.

        Args:
            title: Brief description of the incident
            severity: Incident severity level
            impact: Description of user impact
            service: Affected service/component
            detected_by: How incident was detected
            initial_status: Initial incident status

        Returns:
            Complete incident record
        """
        incident_id = self._generate_incident_id()
        timestamp = datetime.now(timezone.utc)

        incident = {
            "incident_id": incident_id,
            "title": title,
            "severity": severity.value,
            "status": initial_status.value,
            "service": service,
            "impact": impact,
            "detected_by": detected_by,
            "timestamps": {
                "created_at": timestamp.isoformat(),
                "detected_at": timestamp.isoformat(),
                "acknowledged_at": None,
                "resolved_at": None
            },
            "people": {
                "incident_commander": None,
                "tech_lead": None,
                "comms_lead": None,
                "responders": []
            },
            "timeline": [
                {
                    "timestamp": timestamp.isoformat(),
                    "event": "Incident created",
                    "author": "system",
                    "details": f"Severity: {severity.value}, Status: {initial_status.value}"
                }
            ],
            "communication": {
                "war_room_channel": None,
                "notifications_sent": [],
                "status_page_incident_id": None
            },
            "metadata": {
                "error_rate": None,
                "users_affected": None,
                "revenue_impact": None,
                "sla_breach": False
            },
            "resolution": {
                "summary": None,
                "root_cause": None,
                "actions_taken": [],
                "postmortem_url": None
            }
        }

        self._save_incident(incident)
        return incident

    def update_incident(
        self,
        incident_id: str,
        status: Optional[Status] = None,
        event: Optional[str] = None,
        author: str = "unknown",
        details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing incident.

        Args:
            incident_id: Incident identifier
            status: New status (if changing)
            event: Timeline event description
            author: Person making the update
            details: Additional event details
            metadata: Metadata updates (error_rate, users_affected, etc.)

        Returns:
            Updated incident record
        """
        incident = self._load_incident(incident_id)
        timestamp = datetime.now(timezone.utc)

        if status:
            incident["status"] = status.value
            if status == Status.RESOLVED:
                incident["timestamps"]["resolved_at"] = timestamp.isoformat()

        if event:
            incident["timeline"].append({
                "timestamp": timestamp.isoformat(),
                "event": event,
                "author": author,
                "details": details or ""
            })

        if metadata:
            incident["metadata"].update(metadata)

        self._save_incident(incident)
        return incident

    def acknowledge_incident(
        self,
        incident_id: str,
        acknowledger: str
    ) -> Dict[str, Any]:
        """
        Acknowledge an incident.

        Args:
            incident_id: Incident identifier
            acknowledger: Person acknowledging the incident

        Returns:
            Updated incident record
        """
        incident = self._load_incident(incident_id)
        timestamp = datetime.now(timezone.utc)

        incident["timestamps"]["acknowledged_at"] = timestamp.isoformat()
        incident["timeline"].append({
            "timestamp": timestamp.isoformat(),
            "event": "Incident acknowledged",
            "author": acknowledger,
            "details": f"Acknowledged by {acknowledger}"
        })

        self._save_incident(incident)
        return incident

    def assign_roles(
        self,
        incident_id: str,
        incident_commander: Optional[str] = None,
        tech_lead: Optional[str] = None,
        comms_lead: Optional[str] = None,
        responders: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Assign people to incident roles.

        Args:
            incident_id: Incident identifier
            incident_commander: IC name
            tech_lead: Tech lead name
            comms_lead: Comms lead name
            responders: List of additional responders

        Returns:
            Updated incident record
        """
        incident = self._load_incident(incident_id)
        timestamp = datetime.now(timezone.utc)

        if incident_commander:
            incident["people"]["incident_commander"] = incident_commander
            incident["timeline"].append({
                "timestamp": timestamp.isoformat(),
                "event": "Incident Commander assigned",
                "author": "system",
                "details": incident_commander
            })

        if tech_lead:
            incident["people"]["tech_lead"] = tech_lead

        if comms_lead:
            incident["people"]["comms_lead"] = comms_lead

        if responders:
            incident["people"]["responders"].extend(responders)

        self._save_incident(incident)
        return incident

    def generate_templates(
        self,
        incident_id: str
    ) -> Dict[str, Any]:
        """
        Generate all templates for an incident.

        Args:
            incident_id: Incident identifier

        Returns:
            Dictionary with war_room, communication, and runbook templates
        """
        incident = self._load_incident(incident_id)

        templates = {
            "war_room": IncidentTemplate.war_room_template(
                incident_id,
                incident["title"],
                incident["severity"]
            ),
            "communication": IncidentTemplate.communication_template(
                incident["severity"],
                incident["title"],
                incident["impact"]
            ),
            "runbook": IncidentTemplate.runbook_template(
                incident["title"],
                incident["service"]
            )
        }

        return templates

    def list_incidents(
        self,
        severity: Optional[Severity] = None,
        status: Optional[Status] = None,
        service: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List incidents with optional filters.

        Args:
            severity: Filter by severity
            status: Filter by status
            service: Filter by service

        Returns:
            List of matching incidents
        """
        incidents = []
        for incident_file in self.storage_path.glob("*.json"):
            incident = json.loads(incident_file.read_text())

            if severity and incident["severity"] != severity.value:
                continue
            if status and incident["status"] != status.value:
                continue
            if service and incident["service"] != service:
                continue

            incidents.append(incident)

        # Sort by created_at descending
        incidents.sort(
            key=lambda x: x["timestamps"]["created_at"],
            reverse=True
        )

        return incidents

    def get_incident(self, incident_id: str) -> Dict[str, Any]:
        """
        Get incident by ID.

        Args:
            incident_id: Incident identifier

        Returns:
            Incident record
        """
        return self._load_incident(incident_id)

    def _generate_incident_id(self) -> str:
        """Generate unique incident ID."""
        timestamp = datetime.now().strftime("%Y%m%d")
        short_uuid = str(uuid.uuid4())[:8].upper()
        return f"INC-{timestamp}-{short_uuid}"

    def _save_incident(self, incident: Dict[str, Any]) -> None:
        """Save incident to storage."""
        incident_file = self.storage_path / f"{incident['incident_id']}.json"
        incident_file.write_text(json.dumps(incident, indent=2))

    def _load_incident(self, incident_id: str) -> Dict[str, Any]:
        """Load incident from storage."""
        incident_file = self.storage_path / f"{incident_id}.json"
        if not incident_file.exists():
            raise ValueError(f"Incident {incident_id} not found")
        return json.loads(incident_file.read_text())


def format_incident(incident: Dict[str, Any], verbose: bool = False) -> str:
    """
    Format incident for display.

    Args:
        incident: Incident record
        verbose: Include full details

    Returns:
        Formatted string
    """
    output = []
    output.append(f"Incident: {incident['incident_id']}")
    output.append(f"Title: {incident['title']}")
    output.append(f"Severity: {incident['severity']}")
    output.append(f"Status: {incident['status']}")
    output.append(f"Service: {incident['service']}")
    output.append(f"Impact: {incident['impact']}")
    output.append(f"Created: {incident['timestamps']['created_at']}")

    if verbose:
        output.append("\nPeople:")
        for role, person in incident["people"].items():
            if person:
                output.append(f"  {role}: {person}")

        output.append("\nTimeline:")
        for event in incident["timeline"]:
            output.append(f"  [{event['timestamp']}] {event['event']}")
            if event['details']:
                output.append(f"    {event['details']}")

        if incident["metadata"]["error_rate"]:
            output.append("\nMetadata:")
            for key, value in incident["metadata"].items():
                if value is not None:
                    output.append(f"  {key}: {value}")

    return "\n".join(output)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Create and track incidents with structured templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new incident
  %(prog)s create --title "High error rates in API" \\
    --severity SEV-1 --impact "Users unable to login" --service api

  # Update incident status
  %(prog)s update INC-20251027-ABC123 --status monitoring \\
    --event "Error rate decreased to 2%%" --author alice

  # Acknowledge incident
  %(prog)s acknowledge INC-20251027-ABC123 --acknowledger bob

  # Assign incident commander
  %(prog)s assign INC-20251027-ABC123 --ic alice --tech-lead bob

  # Generate templates
  %(prog)s templates INC-20251027-ABC123

  # List all active incidents
  %(prog)s list --status investigating

  # Get incident details
  %(prog)s get INC-20251027-ABC123 --verbose

  # List severity criteria
  %(prog)s severity-guide
        """
    )

    parser.add_argument(
        "--storage-path",
        type=Path,
        default=Path("./incidents"),
        help="Path to store incident data (default: ./incidents/)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create incident
    create_parser = subparsers.add_parser("create", help="Create new incident")
    create_parser.add_argument("--title", required=True, help="Incident title")
    create_parser.add_argument(
        "--severity",
        type=Severity,
        required=True,
        choices=list(Severity),
        help="Incident severity"
    )
    create_parser.add_argument("--impact", required=True, help="User impact description")
    create_parser.add_argument("--service", required=True, help="Affected service")
    create_parser.add_argument(
        "--detected-by",
        default="monitoring",
        help="Detection method (default: monitoring)"
    )

    # Update incident
    update_parser = subparsers.add_parser("update", help="Update incident")
    update_parser.add_argument("incident_id", help="Incident ID")
    update_parser.add_argument(
        "--status",
        type=Status,
        choices=list(Status),
        help="New status"
    )
    update_parser.add_argument("--event", help="Timeline event description")
    update_parser.add_argument("--author", default="unknown", help="Event author")
    update_parser.add_argument("--details", help="Event details")
    update_parser.add_argument("--error-rate", type=float, help="Current error rate")
    update_parser.add_argument("--users-affected", type=int, help="Users affected count")

    # Acknowledge incident
    ack_parser = subparsers.add_parser("acknowledge", help="Acknowledge incident")
    ack_parser.add_argument("incident_id", help="Incident ID")
    ack_parser.add_argument("--acknowledger", required=True, help="Person acknowledging")

    # Assign roles
    assign_parser = subparsers.add_parser("assign", help="Assign incident roles")
    assign_parser.add_argument("incident_id", help="Incident ID")
    assign_parser.add_argument("--ic", help="Incident Commander name")
    assign_parser.add_argument("--tech-lead", help="Tech Lead name")
    assign_parser.add_argument("--comms-lead", help="Communications Lead name")
    assign_parser.add_argument(
        "--responders",
        nargs="+",
        help="Additional responders"
    )

    # Generate templates
    templates_parser = subparsers.add_parser("templates", help="Generate incident templates")
    templates_parser.add_argument("incident_id", help="Incident ID")

    # List incidents
    list_parser = subparsers.add_parser("list", help="List incidents")
    list_parser.add_argument(
        "--severity",
        type=Severity,
        choices=list(Severity),
        help="Filter by severity"
    )
    list_parser.add_argument(
        "--status",
        type=Status,
        choices=list(Status),
        help="Filter by status"
    )
    list_parser.add_argument("--service", help="Filter by service")

    # Get incident
    get_parser = subparsers.add_parser("get", help="Get incident details")
    get_parser.add_argument("incident_id", help="Incident ID")
    get_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # Severity guide
    subparsers.add_parser("severity-guide", help="Show severity classification guide")

    parser.add_argument("--help", action="help", help="Show this help message and exit")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    manager = IncidentManager(storage_path=args.storage_path)

    try:
        if args.command == "create":
            incident = manager.create_incident(
                title=args.title,
                severity=args.severity,
                impact=args.impact,
                service=args.service,
                detected_by=args.detected_by
            )

            if args.json:
                print(json.dumps(incident, indent=2))
            else:
                print(f"Created incident: {incident['incident_id']}")
                print(format_incident(incident, verbose=True))

        elif args.command == "update":
            metadata = {}
            if args.error_rate is not None:
                metadata["error_rate"] = args.error_rate
            if args.users_affected is not None:
                metadata["users_affected"] = args.users_affected

            incident = manager.update_incident(
                incident_id=args.incident_id,
                status=args.status,
                event=args.event,
                author=args.author,
                details=args.details,
                metadata=metadata if metadata else None
            )

            if args.json:
                print(json.dumps(incident, indent=2))
            else:
                print(f"Updated incident: {args.incident_id}")
                print(format_incident(incident))

        elif args.command == "acknowledge":
            incident = manager.acknowledge_incident(
                incident_id=args.incident_id,
                acknowledger=args.acknowledger
            )

            if args.json:
                print(json.dumps(incident, indent=2))
            else:
                print(f"Acknowledged incident: {args.incident_id}")
                print(format_incident(incident))

        elif args.command == "assign":
            incident = manager.assign_roles(
                incident_id=args.incident_id,
                incident_commander=args.ic,
                tech_lead=args.tech_lead,
                comms_lead=args.comms_lead,
                responders=args.responders
            )

            if args.json:
                print(json.dumps(incident, indent=2))
            else:
                print(f"Assigned roles for incident: {args.incident_id}")
                print(format_incident(incident, verbose=True))

        elif args.command == "templates":
            templates = manager.generate_templates(args.incident_id)

            if args.json:
                print(json.dumps(templates, indent=2))
            else:
                print("=== War Room Template ===")
                print(f"Channel: #{templates['war_room']['channel_name']}")
                print(f"Topic: {templates['war_room']['topic']}")
                print("\nRoles:")
                for role, desc in templates['war_room']['roles'].items():
                    print(f"  {role}: {desc}")

                print("\n=== Communication Template ===")
                print("\n".join(templates['communication']['initial']))

        elif args.command == "list":
            incidents = manager.list_incidents(
                severity=args.severity,
                status=args.status,
                service=args.service
            )

            if args.json:
                print(json.dumps(incidents, indent=2))
            else:
                if not incidents:
                    print("No incidents found")
                else:
                    print(f"Found {len(incidents)} incident(s):\n")
                    for incident in incidents:
                        print(format_incident(incident))
                        print("-" * 80)

        elif args.command == "get":
            incident = manager.get_incident(args.incident_id)

            if args.json:
                print(json.dumps(incident, indent=2))
            else:
                print(format_incident(incident, verbose=args.verbose))

        elif args.command == "severity-guide":
            criteria = IncidentTemplate.severity_criteria()

            if args.json:
                print(json.dumps(criteria, indent=2))
            else:
                for sev, info in criteria.items():
                    print(f"\n=== {sev}: {info['name']} ===")
                    print(f"Description: {info['description']}")
                    print(f"Impact: {info['impact']}")
                    print(f"Users Affected: {info['user_percentage']}")
                    print(f"Response Time: {info['response_time']}")
                    print(f"Acknowledgment Target: {info['acknowledgment_target']}")
                    print("\nExamples:")
                    for example in info['examples']:
                        print(f"  - {example}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
