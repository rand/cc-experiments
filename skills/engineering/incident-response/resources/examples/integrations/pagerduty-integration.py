#!/usr/bin/env python3
"""
PagerDuty Integration for Incident Management

This module provides a complete integration with PagerDuty for:
- Creating incidents with proper severity and context
- Updating incidents with timeline events
- Escalating incidents through policies
- Resolving incidents
- Querying on-call schedules
"""

import os
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum


class Urgency(str, Enum):
    """PagerDuty urgency levels."""
    HIGH = "high"
    LOW = "low"


class Status(str, Enum):
    """PagerDuty incident status."""
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class PagerDutyClient:
    """
    PagerDuty API client for incident management.

    Environment Variables:
        PAGERDUTY_API_KEY: API key for authentication
        PAGERDUTY_USER_EMAIL: Email for API requests (from)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        user_email: Optional[str] = None
    ):
        """
        Initialize PagerDuty client.

        Args:
            api_key: PagerDuty API key (default: env PAGERDUTY_API_KEY)
            user_email: User email for requests (default: env PAGERDUTY_USER_EMAIL)
        """
        self.api_key = api_key or os.getenv("PAGERDUTY_API_KEY")
        self.user_email = user_email or os.getenv("PAGERDUTY_USER_EMAIL")

        if not self.api_key:
            raise ValueError("PagerDuty API key required")
        if not self.user_email:
            raise ValueError("PagerDuty user email required")

        self.base_url = "https://api.pagerduty.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Token token={self.api_key}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json",
            "From": self.user_email
        })

    def create_incident(
        self,
        title: str,
        service_id: str,
        urgency: Urgency = Urgency.HIGH,
        body: Optional[str] = None,
        incident_key: Optional[str] = None,
        escalation_policy_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new PagerDuty incident.

        Args:
            title: Incident title
            service_id: PagerDuty service ID
            urgency: Incident urgency (high/low)
            body: Detailed incident description
            incident_key: Unique key for deduplication
            escalation_policy_id: Override default escalation policy

        Returns:
            Created incident data

        Example:
            >>> client = PagerDutyClient()
            >>> incident = client.create_incident(
            ...     title="High Error Rate in API",
            ...     service_id="PXXXXXX",
            ...     urgency=Urgency.HIGH,
            ...     body="Error rate at 25%, affecting 30% of users"
            ... )
            >>> print(incident['id'])
        """
        payload = {
            "incident": {
                "type": "incident",
                "title": title,
                "service": {
                    "id": service_id,
                    "type": "service_reference"
                },
                "urgency": urgency.value,
                "body": {
                    "type": "incident_body",
                    "details": body or title
                }
            }
        }

        if incident_key:
            payload["incident"]["incident_key"] = incident_key

        if escalation_policy_id:
            payload["incident"]["escalation_policy"] = {
                "id": escalation_policy_id,
                "type": "escalation_policy_reference"
            }

        response = self.session.post(
            f"{self.base_url}/incidents",
            json=payload
        )
        response.raise_for_status()
        return response.json()["incident"]

    def get_incident(self, incident_id: str) -> Dict[str, Any]:
        """
        Get incident details.

        Args:
            incident_id: PagerDuty incident ID

        Returns:
            Incident data
        """
        response = self.session.get(
            f"{self.base_url}/incidents/{incident_id}"
        )
        response.raise_for_status()
        return response.json()["incident"]

    def update_incident(
        self,
        incident_id: str,
        status: Optional[Status] = None,
        priority_id: Optional[str] = None,
        urgency: Optional[Urgency] = None,
        escalation_level: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update an existing incident.

        Args:
            incident_id: PagerDuty incident ID
            status: New status (triggered/acknowledged/resolved)
            priority_id: Priority ID
            urgency: New urgency level
            escalation_level: Escalation level to assign

        Returns:
            Updated incident data
        """
        # Get current incident
        incident = self.get_incident(incident_id)

        # Build update payload
        updates = {}
        if status:
            updates["status"] = status.value
        if priority_id:
            updates["priority"] = {
                "id": priority_id,
                "type": "priority_reference"
            }
        if urgency:
            updates["urgency"] = urgency.value
        if escalation_level is not None:
            updates["escalation_level"] = escalation_level

        payload = {
            "incident": {
                "type": "incident_reference",
                **updates
            }
        }

        response = self.session.put(
            f"{self.base_url}/incidents/{incident_id}",
            json=payload
        )
        response.raise_for_status()
        return response.json()["incident"]

    def acknowledge_incident(self, incident_id: str) -> Dict[str, Any]:
        """
        Acknowledge an incident.

        Args:
            incident_id: PagerDuty incident ID

        Returns:
            Updated incident data
        """
        return self.update_incident(incident_id, status=Status.ACKNOWLEDGED)

    def resolve_incident(
        self,
        incident_id: str,
        resolution: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolve an incident.

        Args:
            incident_id: PagerDuty incident ID
            resolution: Resolution note

        Returns:
            Updated incident data
        """
        if resolution:
            self.add_note(incident_id, f"Resolution: {resolution}")

        return self.update_incident(incident_id, status=Status.RESOLVED)

    def add_note(self, incident_id: str, note: str) -> Dict[str, Any]:
        """
        Add a note to an incident.

        Args:
            incident_id: PagerDuty incident ID
            note: Note content

        Returns:
            Created note data
        """
        payload = {
            "note": {
                "content": note
            }
        }

        response = self.session.post(
            f"{self.base_url}/incidents/{incident_id}/notes",
            json=payload
        )
        response.raise_for_status()
        return response.json()["note"]

    def escalate_incident(
        self,
        incident_id: str,
        escalation_level: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Escalate an incident to next level or specific level.

        Args:
            incident_id: PagerDuty incident ID
            escalation_level: Specific level to escalate to (optional)

        Returns:
            Updated incident data
        """
        if escalation_level is None:
            # Escalate to next level
            incident = self.get_incident(incident_id)
            current_level = incident.get("escalation_level", 0)
            escalation_level = current_level + 1

        return self.update_incident(
            incident_id,
            escalation_level=escalation_level
        )

    def reassign_incident(
        self,
        incident_id: str,
        user_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Reassign incident to specific users.

        Args:
            incident_id: PagerDuty incident ID
            user_ids: List of PagerDuty user IDs

        Returns:
            Updated incident data
        """
        payload = {
            "incident": {
                "type": "incident_reference",
                "assignments": [
                    {
                        "assignee": {
                            "id": user_id,
                            "type": "user_reference"
                        }
                    }
                    for user_id in user_ids
                ]
            }
        }

        response = self.session.put(
            f"{self.base_url}/incidents/{incident_id}",
            json=payload
        )
        response.raise_for_status()
        return response.json()["incident"]

    def list_incidents(
        self,
        statuses: Optional[List[Status]] = None,
        urgencies: Optional[List[Urgency]] = None,
        service_ids: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        List incidents with filters.

        Args:
            statuses: Filter by status (triggered/acknowledged/resolved)
            urgencies: Filter by urgency (high/low)
            service_ids: Filter by service IDs
            since: Filter incidents created after this time
            until: Filter incidents created before this time
            limit: Maximum number of incidents to return

        Returns:
            List of incidents
        """
        params = {
            "limit": limit,
            "sort_by": "created_at:desc"
        }

        if statuses:
            params["statuses[]"] = [s.value for s in statuses]
        if urgencies:
            params["urgencies[]"] = [u.value for u in urgencies]
        if service_ids:
            params["service_ids[]"] = service_ids
        if since:
            params["since"] = since.isoformat()
        if until:
            params["until"] = until.isoformat()

        response = self.session.get(
            f"{self.base_url}/incidents",
            params=params
        )
        response.raise_for_status()
        return response.json()["incidents"]

    def get_oncall(
        self,
        schedule_id: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get on-call users for a schedule.

        Args:
            schedule_id: PagerDuty schedule ID
            since: Start time (default: now)
            until: End time (default: now + 24 hours)

        Returns:
            List of on-call entries
        """
        if since is None:
            since = datetime.now(timezone.utc)
        if until is None:
            until = since.replace(hour=23, minute=59, second=59)

        params = {
            "since": since.isoformat(),
            "until": until.isoformat()
        }

        response = self.session.get(
            f"{self.base_url}/schedules/{schedule_id}/users",
            params=params
        )
        response.raise_for_status()
        return response.json()["users"]

    def trigger_incident_via_integration(
        self,
        routing_key: str,
        summary: str,
        source: str,
        severity: str = "error",
        custom_details: Optional[Dict[str, Any]] = None,
        dedup_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trigger incident via Events API v2 (integration key).

        This is useful for automated alerting from monitoring systems.

        Args:
            routing_key: Integration key (routing key)
            summary: Brief incident summary
            source: Source of the event (e.g., hostname, service)
            severity: critical/error/warning/info
            custom_details: Additional context
            dedup_key: Deduplication key

        Returns:
            Event response

        Example:
            >>> client = PagerDutyClient()
            >>> client.trigger_incident_via_integration(
            ...     routing_key="R123ABC",
            ...     summary="High CPU on web-server-01",
            ...     source="web-server-01",
            ...     severity="error",
            ...     custom_details={"cpu_percent": 95, "region": "us-west-2"}
            ... )
        """
        payload = {
            "routing_key": routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": summary,
                "source": source,
                "severity": severity,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

        if custom_details:
            payload["payload"]["custom_details"] = custom_details

        if dedup_key:
            payload["dedup_key"] = dedup_key

        response = requests.post(
            "https://events.pagerduty.com/v2/enqueue",
            json=payload
        )
        response.raise_for_status()
        return response.json()


# Example Usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PagerDuty incident management")
    parser.add_argument("--create", action="store_true", help="Create test incident")
    parser.add_argument("--list", action="store_true", help="List active incidents")
    parser.add_argument("--service-id", help="Service ID for incident creation")
    args = parser.parse_args()

    client = PagerDutyClient()

    if args.create:
        if not args.service_id:
            print("Error: --service-id required for creating incident")
            exit(1)

        incident = client.create_incident(
            title="Test Incident - High Error Rate",
            service_id=args.service_id,
            urgency=Urgency.HIGH,
            body="This is a test incident created via API"
        )
        print(f"Created incident: {incident['id']}")
        print(f"URL: {incident['html_url']}")

        # Add a note
        client.add_note(incident['id'], "Initial investigation started")
        print("Added note to incident")

        # Acknowledge
        client.acknowledge_incident(incident['id'])
        print("Acknowledged incident")

    elif args.list:
        incidents = client.list_incidents(
            statuses=[Status.TRIGGERED, Status.ACKNOWLEDGED],
            limit=10
        )
        print(f"Found {len(incidents)} active incidents:\n")
        for inc in incidents:
            print(f"ID: {inc['id']}")
            print(f"Title: {inc['title']}")
            print(f"Status: {inc['status']}")
            print(f"Urgency: {inc['urgency']}")
            print(f"URL: {inc['html_url']}")
            print("-" * 80)
    else:
        parser.print_help()
