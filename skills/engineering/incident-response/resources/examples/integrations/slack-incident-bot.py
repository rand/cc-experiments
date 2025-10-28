#!/usr/bin/env python3
"""
Slack Incident Bot

Automated bot for incident management in Slack:
- Creates war room channels
- Posts structured updates
- Manages incident timeline
- Coordinates team communication
- Sends notifications
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class IncidentSlackBot:
    """
    Slack bot for incident management.

    Environment Variables:
        SLACK_BOT_TOKEN: Bot OAuth token
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize Slack bot.

        Args:
            token: Slack bot token (default: env SLACK_BOT_TOKEN)
        """
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        if not self.token:
            raise ValueError("Slack bot token required")

        self.client = WebClient(token=self.token)

    def create_war_room(
        self,
        incident_id: str,
        title: str,
        severity: str,
        ic_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create dedicated incident war room channel.

        Args:
            incident_id: Unique incident identifier
            title: Incident title
            severity: SEV-1, SEV-2, etc.
            ic_user_id: Slack user ID of incident commander

        Returns:
            Channel information

        Example:
            >>> bot = IncidentSlackBot()
            >>> war_room = bot.create_war_room(
            ...     incident_id="INC-123",
            ...     title="High Error Rate in API",
            ...     severity="SEV-1",
            ...     ic_user_id="U123ABC"
            ... )
            >>> print(war_room['channel_id'])
        """
        # Create channel name (max 80 chars, lowercase, no spaces)
        timestamp = datetime.now().strftime("%Y%m%d")
        channel_name = f"incident-{timestamp}-{incident_id.lower()}"
        channel_name = channel_name[:80]  # Slack limit

        try:
            # Create public channel
            response = self.client.conversations_create(
                name=channel_name,
                is_private=False
            )
            channel_id = response['channel']['id']

            # Set channel topic
            ic_mention = f"<@{ic_user_id}>" if ic_user_id else "TBD"
            topic = f"{severity}: {title} | IC: {ic_mention} | Started: {datetime.now(timezone.utc).strftime('%H:%M UTC')}"

            self.client.conversations_setTopic(
                channel=channel_id,
                topic=topic
            )

            # Post initial message with structure
            self.post_war_room_header(
                channel_id=channel_id,
                incident_id=incident_id,
                title=title,
                severity=severity
            )

            return {
                'channel_id': channel_id,
                'channel_name': channel_name,
                'topic': topic
            }

        except SlackApiError as e:
            raise Exception(f"Failed to create war room: {e.response['error']}")

    def post_war_room_header(
        self,
        channel_id: str,
        incident_id: str,
        title: str,
        severity: str
    ) -> None:
        """Post initial war room header with structure."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f":rotating_light: {severity} Incident: {incident_id}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*\n\nIncident declared at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Roles*\n• IC: TBD\n• Tech Lead: TBD\n• Comms: TBD\n• Scribe: TBD"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": ":information_source: Use this channel for incident coordination only. Post updates in format: `[HH:MM] [@person] [ACTION/DECISION/OBSERVATION] Description`"
                    }
                ]
            }
        ]

        self.client.chat_postMessage(
            channel=channel_id,
            text=f"Incident {incident_id} war room",
            blocks=blocks
        )

    def post_status_update(
        self,
        channel_id: str,
        status: str,
        message: str,
        author: Optional[str] = None
    ) -> None:
        """
        Post structured status update.

        Args:
            channel_id: Slack channel ID
            status: Current status (Investigating/Identified/Mitigating/Resolved)
            message: Update message
            author: User who posted update
        """
        timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")

        # Status emoji mapping
        status_emoji = {
            "Investigating": ":mag:",
            "Identified": ":white_check_mark:",
            "Mitigating": ":hammer_and_wrench:",
            "Monitoring": ":eyes:",
            "Resolved": ":tada:"
        }

        emoji = status_emoji.get(status, ":information_source:")

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *Status: {status}* ({timestamp})"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]

        if author:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Posted by <@{author}>"
                    }
                ]
            })

        self.client.chat_postMessage(
            channel=channel_id,
            text=f"Status Update: {status}",
            blocks=blocks
        )

    def post_resolution(
        self,
        channel_id: str,
        incident_id: str,
        duration: str,
        resolution: str
    ) -> None:
        """
        Post incident resolution message.

        Args:
            channel_id: Slack channel ID
            incident_id: Incident identifier
            duration: Incident duration string
            resolution: Resolution description
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f":white_check_mark: Incident {incident_id} Resolved"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Duration*\n{duration}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Resolved at*\n{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Resolution*\n{resolution}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Next Steps*\n• Postmortem scheduled\n• Action items will be tracked\n• War room will remain open for documentation"
                }
            }
        ]

        self.client.chat_postMessage(
            channel=channel_id,
            text=f"Incident {incident_id} resolved",
            blocks=blocks
        )

    def assign_roles(
        self,
        channel_id: str,
        ic: Optional[str] = None,
        tech_lead: Optional[str] = None,
        comms: Optional[str] = None,
        scribe: Optional[str] = None
    ) -> None:
        """
        Announce role assignments.

        Args:
            channel_id: Slack channel ID
            ic: Incident Commander user ID
            tech_lead: Tech Lead user ID
            comms: Communications Lead user ID
            scribe: Scribe user ID
        """
        roles = []
        if ic:
            roles.append(f"• *IC*: <@{ic}>")
        if tech_lead:
            roles.append(f"• *Tech Lead*: <@{tech_lead}>")
        if comms:
            roles.append(f"• *Communications*: <@{comms}>")
        if scribe:
            roles.append(f"• *Scribe*: <@{scribe}>")

        if not roles:
            return

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":busts_in_silhouette: *Roles Assigned*\n" + "\n".join(roles)
                }
            }
        ]

        self.client.chat_postMessage(
            channel=channel_id,
            text="Roles assigned",
            blocks=blocks
        )

    def post_timeline_event(
        self,
        channel_id: str,
        event_type: str,
        description: str,
        author: str
    ) -> None:
        """
        Post timeline event in structured format.

        Args:
            channel_id: Slack channel ID
            event_type: ACTION/DECISION/OBSERVATION/QUESTION/ANSWER
            description: Event description
            author: User who performed action
        """
        timestamp = datetime.now(timezone.utc).strftime("%H:%M")

        # Emoji mapping for event types
        emoji_map = {
            "ACTION": ":hammer_and_wrench:",
            "DECISION": ":white_check_mark:",
            "OBSERVATION": ":eyes:",
            "QUESTION": ":question:",
            "ANSWER": ":bulb:",
            "NOTIFICATION": ":bell:"
        }

        emoji = emoji_map.get(event_type, ":information_source:")

        text = f"[{timestamp}] <@{author}> {emoji} *{event_type}*: {description}"

        self.client.chat_postMessage(
            channel=channel_id,
            text=text
        )

    def notify_channel(
        self,
        channel: str,
        incident_id: str,
        title: str,
        severity: str,
        war_room_id: str
    ) -> None:
        """
        Notify main incidents channel of new incident.

        Args:
            channel: Channel to notify (e.g., #incidents)
            incident_id: Incident identifier
            title: Incident title
            severity: Severity level
            war_room_id: War room channel ID
        """
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":rotating_light: *{severity} Incident Declared*\n*{incident_id}*: {title}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"War room: <#{war_room_id}>"
                }
            }
        ]

        self.client.chat_postMessage(
            channel=channel,
            text=f"{severity} incident declared",
            blocks=blocks
        )

    def pin_important_links(
        self,
        channel_id: str,
        links: Dict[str, str]
    ) -> None:
        """
        Pin important links to channel.

        Args:
            channel_id: Slack channel ID
            links: Dictionary of link names to URLs
        """
        link_list = []
        for name, url in links.items():
            link_list.append(f"• <{url}|{name}>")

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":pushpin: *Important Links*\n" + "\n".join(link_list)
                }
            }
        ]

        response = self.client.chat_postMessage(
            channel=channel_id,
            text="Important Links",
            blocks=blocks
        )

        # Pin the message
        self.client.pins_add(
            channel=channel_id,
            timestamp=response['ts']
        )

    def invite_users(self, channel_id: str, user_ids: List[str]) -> None:
        """
        Invite users to war room.

        Args:
            channel_id: Slack channel ID
            user_ids: List of Slack user IDs to invite
        """
        try:
            self.client.conversations_invite(
                channel=channel_id,
                users=",".join(user_ids)
            )
        except SlackApiError as e:
            if e.response['error'] != 'already_in_channel':
                raise

    def get_channel_history(
        self,
        channel_id: str,
        oldest: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get channel message history for timeline compilation.

        Args:
            channel_id: Slack channel ID
            oldest: Oldest timestamp to fetch
            limit: Maximum messages to fetch

        Returns:
            List of messages
        """
        response = self.client.conversations_history(
            channel=channel_id,
            oldest=oldest,
            limit=limit
        )
        return response['messages']

    def create_incident_workflow(
        self,
        incident_id: str,
        title: str,
        severity: str,
        ic_user_id: str,
        notification_channels: List[str],
        important_links: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Complete workflow for incident declaration.

        This combines multiple actions into single workflow:
        1. Create war room
        2. Post header
        3. Assign IC
        4. Pin links
        5. Notify channels

        Args:
            incident_id: Incident identifier
            title: Incident title
            severity: Severity level
            ic_user_id: Slack user ID of IC
            notification_channels: Channels to notify
            important_links: Links to pin (optional)

        Returns:
            Workflow results
        """
        # Create war room
        war_room = self.create_war_room(
            incident_id=incident_id,
            title=title,
            severity=severity,
            ic_user_id=ic_user_id
        )

        # Assign IC role
        self.assign_roles(
            channel_id=war_room['channel_id'],
            ic=ic_user_id
        )

        # Pin important links
        if important_links:
            self.pin_important_links(
                channel_id=war_room['channel_id'],
                links=important_links
            )

        # Notify other channels
        for channel in notification_channels:
            self.notify_channel(
                channel=channel,
                incident_id=incident_id,
                title=title,
                severity=severity,
                war_room_id=war_room['channel_id']
            )

        return war_room


# Example usage and CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Slack incident bot")
    parser.add_argument("--create-war-room", action="store_true")
    parser.add_argument("--incident-id", required=True)
    parser.add_argument("--title", help="Incident title")
    parser.add_argument("--severity", choices=["SEV-1", "SEV-2", "SEV-3"], default="SEV-2")
    parser.add_argument("--ic-user-id", help="Slack user ID of IC")
    args = parser.parse_args()

    bot = IncidentSlackBot()

    if args.create_war_room:
        if not args.title:
            print("Error: --title required")
            exit(1)

        war_room = bot.create_war_room(
            incident_id=args.incident_id,
            title=args.title,
            severity=args.severity,
            ic_user_id=args.ic_user_id
        )

        print(f"Created war room: #{war_room['channel_name']}")
        print(f"Channel ID: {war_room['channel_id']}")

        # Pin some example links
        bot.pin_important_links(
            channel_id=war_room['channel_id'],
            links={
                "Incident Ticket": f"https://jira.example.com/{args.incident_id}",
                "Dashboard": "https://grafana.example.com/d/overview",
                "Runbooks": "https://runbooks.example.com"
            }
        )

        # Post example timeline event
        if args.ic_user_id:
            bot.post_timeline_event(
                channel_id=war_room['channel_id'],
                event_type="ACTION",
                description="War room created and initial investigation started",
                author=args.ic_user_id
            )
    else:
        parser.print_help()
