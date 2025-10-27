#!/usr/bin/env python3
"""
Generate postmortem templates from incidents.

This script creates blameless postmortem documents with timeline,
impact analysis, root cause, and action items based on incident data.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


class PostmortemGenerator:
    """Generate postmortem documents from incident data."""

    def __init__(self, incident: Dict[str, Any]):
        """
        Initialize with incident data.

        Args:
            incident: Incident record
        """
        self.incident = incident

    def generate_markdown(
        self,
        authors: List[str],
        root_cause: Optional[str] = None,
        what_went_well: Optional[List[str]] = None,
        what_went_poorly: Optional[List[str]] = None,
        action_items: Optional[List[Dict[str, str]]] = None,
        lessons_learned: Optional[List[str]] = None
    ) -> str:
        """
        Generate postmortem in Markdown format.

        Args:
            authors: List of postmortem authors
            root_cause: Root cause analysis (optional)
            what_went_well: Things that went well (optional)
            what_went_poorly: Things that went poorly (optional)
            action_items: Action items with owners and deadlines (optional)
            lessons_learned: Key lessons learned (optional)

        Returns:
            Markdown-formatted postmortem
        """
        sections = []

        # Header
        sections.append(self._generate_header(authors))

        # Executive Summary
        sections.append(self._generate_executive_summary())

        # Impact
        sections.append(self._generate_impact_section())

        # Timeline
        sections.append(self._generate_timeline())

        # Root Cause
        sections.append(self._generate_root_cause(root_cause))

        # What Went Well
        sections.append(self._generate_what_went_well(what_went_well))

        # What Went Poorly
        sections.append(self._generate_what_went_poorly(what_went_poorly))

        # Action Items
        sections.append(self._generate_action_items(action_items))

        # Lessons Learned
        sections.append(self._generate_lessons_learned(lessons_learned))

        # Appendices
        sections.append(self._generate_appendices())

        return "\n\n".join(sections)

    def _generate_header(self, authors: List[str]) -> str:
        """Generate postmortem header."""
        duration = self._calculate_duration()
        status = "Complete" if self.incident["status"] == "resolved" else "Draft"

        return f"""# Postmortem: {self.incident['title']}

**Incident ID**: {self.incident['incident_id']}
**Date**: {self._format_date(self.incident['timestamps']['created_at'])}
**Duration**: {duration}
**Severity**: {self.incident['severity']}
**Incident Commander**: {self.incident['people'].get('incident_commander') or 'TBD'}
**Authors**: {', '.join(authors)}
**Status**: {status}

---"""

    def _generate_executive_summary(self) -> str:
        """Generate executive summary section."""
        duration = self._calculate_duration()

        template = f"""## Executive Summary

On {self._format_date(self.incident['timestamps']['created_at'])}, our {self.incident['service']} service experienced {self.incident['impact'].lower()} for {duration}.

**Impact**: {self.incident['impact']}

**Root Cause**: [To be determined during postmortem review]

**Resolution**: [Describe how the incident was resolved]

**Current Status**: Service is operating normally. [Action items tracked below / Monitoring for stability]"""

        return template

    def _generate_impact_section(self) -> str:
        """Generate impact assessment section."""
        metadata = self.incident.get('metadata', {})

        users_affected = metadata.get('users_affected') or '[Unknown]'
        error_rate = metadata.get('error_rate') or '[Unknown]'
        revenue_impact = metadata.get('revenue_impact') or '[Unknown]'
        sla_breach = "Yes" if metadata.get('sla_breach') else "No"

        section = f"""## Impact

### User Impact
- **Users Affected**: {users_affected}
- **User-Visible Symptoms**: {self.incident['impact']}
- **Failed Requests**: [Number of failed requests]

### Business Impact
- **Revenue Loss**: {revenue_impact}
- **Support Tickets**: [Number of tickets created]
- **SLA Breach**: {sla_breach}

### Metrics

| Metric | Normal | During Incident | Peak |
|--------|--------|-----------------|------|
| Error Rate | 0.5% | {error_rate} | [Peak value] |
| P95 Latency | [Normal] | [During] | [Peak] |
| Requests/sec | [Normal] | [During] | - |

[Insert graphs and dashboards showing impact]"""

        return section

    def _generate_timeline(self) -> str:
        """Generate incident timeline."""
        lines = ["## Timeline", "", "All times in UTC. Key decisions in **bold**.", ""]
        lines.append("| Time | Event |")
        lines.append("|------|-------|")

        for event in self.incident.get('timeline', []):
            timestamp = self._format_time(event['timestamp'])
            event_text = event['event']

            # Bold decision events
            if any(keyword in event_text.lower() for keyword in ['decision', 'rollback', 'deployed']):
                event_text = f"**{event_text}**"

            details = f" - {event['details']}" if event.get('details') else ""
            lines.append(f"| {timestamp} | {event_text}{details} |")

        return "\n".join(lines)

    def _generate_root_cause(self, root_cause: Optional[str]) -> str:
        """Generate root cause analysis section."""
        section = ["## Root Cause Analysis", ""]

        if root_cause:
            section.append(root_cause)
        else:
            section.extend([
                "### The Five Whys",
                "",
                "1. **Why did [service] fail?**",
                "   - [Answer]",
                "",
                "2. **Why did [that happen]?**",
                "   - [Answer]",
                "",
                "3. **Why did [that happen]?**",
                "   - [Answer]",
                "",
                "4. **Why did [that happen]?**",
                "   - [Answer]",
                "",
                "5. **Why did [that happen]?**",
                "   - [Answer]",
                "",
                "### Root Causes",
                "",
                "1. **Immediate Cause**: [What directly caused the failure]",
                "2. **Contributing Factors**:",
                "   - [Factor 1]",
                "   - [Factor 2]",
                "3. **Latent Conditions**:",
                "   - [Underlying system weakness 1]",
                "   - [Underlying system weakness 2]"
            ])

        return "\n".join(section)

    def _generate_what_went_well(self, items: Optional[List[str]]) -> str:
        """Generate 'what went well' section."""
        section = ["## What Went Well", ""]

        if items:
            for item in items:
                section.append(f"- ✅ {item}")
        else:
            section.extend([
                "Highlight positive aspects to reinforce good practices:",
                "",
                "1. ✅ **Fast Detection**: [How quickly we detected]",
                "2. ✅ **Quick Response**: [How quickly we responded]",
                "3. ✅ **Clear Communication**: [How well we communicated]",
                "4. ✅ **Effective Mitigation**: [What mitigation worked]",
                "5. ✅ **Good Documentation**: [How well we documented]"
            ])

        return "\n".join(section)

    def _generate_what_went_poorly(self, items: Optional[List[str]]) -> str:
        """Generate 'what went poorly' section."""
        section = ["## What Went Poorly", ""]

        if items:
            for item in items:
                section.append(f"- ❌ {item}")
        else:
            section.extend([
                "Identify areas for improvement without blame:",
                "",
                "1. ❌ **[Area 1]**: [What didn't work well]",
                "2. ❌ **[Area 2]**: [What didn't work well]",
                "3. ❌ **[Area 3]**: [What didn't work well]",
                "",
                "*Remember: Focus on systems and processes, not individuals*"
            ])

        return "\n".join(section)

    def _generate_action_items(self, items: Optional[List[Dict[str, str]]]) -> str:
        """Generate action items section."""
        section = ["## Action Items", ""]
        section.append("Concrete, actionable improvements with owners and deadlines.")
        section.append("")

        if items:
            # Organize by category
            categories = {
                "prevent": [],
                "detect": [],
                "respond": [],
                "process": []
            }

            for item in items:
                category = item.get('category', 'prevent')
                categories[category].append(item)

            for category, category_items in categories.items():
                if category_items:
                    category_title = {
                        "prevent": "Prevent Recurrence",
                        "detect": "Improve Detection",
                        "respond": "Improve Response",
                        "process": "Improve Processes"
                    }[category]

                    section.append(f"### {category_title}")
                    section.append("")
                    section.append("| Action | Owner | Deadline | Status |")
                    section.append("|--------|-------|----------|--------|")

                    for item in category_items:
                        section.append(
                            f"| {item['action']} | "
                            f"{item.get('owner', 'TBD')} | "
                            f"{item.get('deadline', 'TBD')} | "
                            f"{item.get('status', 'Open')} |"
                        )
                    section.append("")
        else:
            # Template
            section.extend([
                "### Prevent Recurrence",
                "| Action | Owner | Deadline | Status |",
                "|--------|-------|----------|--------|",
                "| [Action to prevent this type of incident] | @owner | YYYY-MM-DD | Open |",
                "",
                "### Improve Detection",
                "| Action | Owner | Deadline | Status |",
                "|--------|-------|----------|--------|",
                "| [Action to detect faster] | @owner | YYYY-MM-DD | Open |",
                "",
                "### Improve Response",
                "| Action | Owner | Deadline | Status |",
                "|--------|-------|----------|--------|",
                "| [Action to respond faster] | @owner | YYYY-MM-DD | Open |",
                "",
                "### Improve Processes",
                "| Action | Owner | Deadline | Status |",
                "|--------|-------|----------|--------|",
                "| [Process improvement] | @owner | YYYY-MM-DD | Open |"
            ])

        return "\n".join(section)

    def _generate_lessons_learned(self, lessons: Optional[List[str]]) -> str:
        """Generate lessons learned section."""
        section = ["## Lessons Learned", ""]

        if lessons:
            for i, lesson in enumerate(lessons, 1):
                section.append(f"{i}. **{lesson}**")
        else:
            section.extend([
                "Key takeaways for the organization:",
                "",
                "1. **[Lesson 1]** - [Explanation]",
                "2. **[Lesson 2]** - [Explanation]",
                "3. **[Lesson 3]** - [Explanation]"
            ])

        return "\n".join(section)

    def _generate_appendices(self) -> str:
        """Generate appendices section."""
        section = ["## Appendices", ""]

        # Related incidents
        section.extend([
            "### Appendix A: Related Incidents",
            "- [INC-XXX](link): Similar incident description",
            ""
        ])

        # Dashboards and graphs
        section.extend([
            "### Appendix B: Dashboards and Graphs",
            "- [Grafana Dashboard During Incident](https://grafana.example.com/...)",
            "- [Error Rate Graph](https://grafana.example.com/...)",
            ""
        ])

        # Customer communication
        section.extend([
            "### Appendix C: Customer Communication",
            "- [Initial Notification](https://status.example.com/incidents/...)",
            "- [Resolution Notice](https://status.example.com/incidents/...)",
            ""
        ])

        # Code changes
        if self.incident.get('resolution', {}).get('actions_taken'):
            section.extend([
                "### Appendix D: Code Changes",
            ])
            for action in self.incident['resolution']['actions_taken']:
                section.append(f"- {action}")
        else:
            section.extend([
                "### Appendix D: Code Changes",
                "- [Deployment that caused issue](https://github.com/...)",
                "- [Rollback commit](https://github.com/...)",
                "- [Fix PR](https://github.com/...)"
            ])

        return "\n".join(section)

    def _calculate_duration(self) -> str:
        """Calculate incident duration."""
        started = datetime.fromisoformat(self.incident['timestamps']['created_at'])

        if self.incident['timestamps'].get('resolved_at'):
            resolved = datetime.fromisoformat(self.incident['timestamps']['resolved_at'])
        else:
            resolved = datetime.now(timezone.utc)

        delta = resolved - started
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

        if delta.days > 0:
            return f"{delta.days} days, {hours} hours, {minutes} minutes"
        elif hours > 0:
            return f"{hours} hours, {minutes} minutes"
        else:
            return f"{minutes} minutes"

    def _format_date(self, iso_date: str) -> str:
        """Format ISO date to readable format."""
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%Y-%m-%d")

    def _format_time(self, iso_date: str) -> str:
        """Format ISO date to time."""
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%H:%M")


class PostmortemTemplateLibrary:
    """Library of postmortem templates for common incident types."""

    @staticmethod
    def deployment_failure_template() -> Dict[str, Any]:
        """Template for deployment-caused incidents."""
        return {
            "root_cause_template": """
### The Five Whys

1. **Why did the service fail?**
   - A recent deployment introduced a bug

2. **Why did the deployment introduce a bug?**
   - Code changes weren't adequately tested in staging

3. **Why weren't they tested adequately?**
   - Staging environment doesn't match production configuration

4. **Why doesn't staging match production?**
   - Configuration drift over time, no automated parity checks

5. **Why is there configuration drift?**
   - No process to keep environments in sync

### Root Causes

1. **Immediate Cause**: Deployment v2.X.Y contained bug in [component]
2. **Contributing Factors**:
   - Staging/production environment mismatch
   - Insufficient test coverage for [scenario]
3. **Latent Conditions**:
   - No automated environment parity checks
   - No gradual rollout strategy (canary/blue-green)
            """,
            "action_items": [
                {
                    "category": "prevent",
                    "action": "Implement automated environment parity checks",
                    "owner": "TBD",
                    "deadline": "TBD"
                },
                {
                    "category": "prevent",
                    "action": "Add test coverage for [scenario]",
                    "owner": "TBD",
                    "deadline": "TBD"
                },
                {
                    "category": "respond",
                    "action": "Implement canary deployment strategy",
                    "owner": "TBD",
                    "deadline": "TBD"
                },
                {
                    "category": "respond",
                    "action": "Add automated rollback on error threshold",
                    "owner": "TBD",
                    "deadline": "TBD"
                }
            ]
        }

    @staticmethod
    def resource_exhaustion_template() -> Dict[str, Any]:
        """Template for resource exhaustion incidents."""
        return {
            "root_cause_template": """
### The Five Whys

1. **Why did the service fail?**
   - Service ran out of [CPU/Memory/Connections]

2. **Why did it run out of resources?**
   - Traffic spike / Resource leak / Query slowdown

3. **Why wasn't there enough capacity?**
   - Autoscaling didn't trigger fast enough / No autoscaling configured

4. **Why didn't autoscaling work?**
   - Threshold set too high / Metric not monitored

5. **Why weren't proper thresholds set?**
   - No load testing to determine capacity limits

### Root Causes

1. **Immediate Cause**: [Resource] exhaustion under [condition]
2. **Contributing Factors**:
   - Insufficient capacity planning
   - Autoscaling configuration inadequate
3. **Latent Conditions**:
   - No load testing to validate capacity
   - Missing monitoring for resource utilization
            """,
            "action_items": [
                {
                    "category": "prevent",
                    "action": "Configure autoscaling with appropriate thresholds",
                    "owner": "TBD",
                    "deadline": "TBD"
                },
                {
                    "category": "prevent",
                    "action": "Conduct load testing to determine capacity",
                    "owner": "TBD",
                    "deadline": "TBD"
                },
                {
                    "category": "detect",
                    "action": "Add resource utilization monitoring and alerts",
                    "owner": "TBD",
                    "deadline": "TBD"
                }
            ]
        }

    @staticmethod
    def dependency_failure_template() -> Dict[str, Any]:
        """Template for external dependency failures."""
        return {
            "root_cause_template": """
### The Five Whys

1. **Why did the service fail?**
   - External dependency [service/API] became unavailable

2. **Why did that cause our service to fail?**
   - No graceful degradation or fallback mechanism

3. **Why was there no fallback?**
   - Service designed with tight coupling to dependency

4. **Why was it tightly coupled?**
   - Assumed dependency would always be available

5. **Why didn't we plan for failure?**
   - Insufficient chaos engineering and failure scenario planning

### Root Causes

1. **Immediate Cause**: [Dependency] became unavailable
2. **Contributing Factors**:
   - No circuit breaker or timeout handling
   - No graceful degradation strategy
3. **Latent Conditions**:
   - Tight coupling to external dependencies
   - No chaos engineering to test failure scenarios
            """,
            "action_items": [
                {
                    "category": "prevent",
                    "action": "Implement circuit breaker for [dependency]",
                    "owner": "TBD",
                    "deadline": "TBD"
                },
                {
                    "category": "prevent",
                    "action": "Add graceful degradation / fallback mechanism",
                    "owner": "TBD",
                    "deadline": "TBD"
                },
                {
                    "category": "detect",
                    "action": "Add synthetic monitoring for dependency health",
                    "owner": "TBD",
                    "deadline": "TBD"
                },
                {
                    "category": "process",
                    "action": "Conduct chaos engineering for dependency failures",
                    "owner": "TBD",
                    "deadline": "TBD"
                }
            ]
        }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate postmortem templates from incidents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate postmortem from incident
  %(prog)s --incident-id INC-20251027-ABC123 --authors alice,bob \\
    --output postmortems/INC-20251027-ABC123.md

  # Use template for deployment failure
  %(prog)s --incident-id INC-20251027-ABC123 --authors alice \\
    --template deployment --output postmortem.md

  # Generate with custom root cause and action items
  %(prog)s --incident-id INC-20251027-ABC123 --authors alice \\
    --root-cause "Database connection pool exhausted" \\
    --action-items actions.json --output postmortem.md

  # Preview without saving
  %(prog)s --incident-id INC-20251027-ABC123 --authors alice --preview

  # List available templates
  %(prog)s --list-templates
        """
    )

    parser.add_argument(
        "--incidents-path",
        type=Path,
        default=Path("./incidents"),
        help="Path to incidents directory (default: ./incidents/)"
    )

    parser.add_argument(
        "--incident-id",
        help="Incident ID to generate postmortem for"
    )

    parser.add_argument(
        "--authors",
        help="Comma-separated list of postmortem authors"
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: stdout)"
    )

    parser.add_argument(
        "--template",
        choices=["deployment", "resource", "dependency"],
        help="Use predefined template"
    )

    parser.add_argument(
        "--root-cause",
        help="Custom root cause description"
    )

    parser.add_argument(
        "--action-items",
        type=Path,
        help="JSON file with action items"
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview postmortem without saving"
    )

    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List available templates"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    parser.add_argument("--help", action="help", help="Show this help message and exit")

    args = parser.parse_args()

    if args.list_templates:
        templates = {
            "deployment": "Deployment-caused incidents (bugs, config errors)",
            "resource": "Resource exhaustion (CPU, memory, connections)",
            "dependency": "External dependency failures (APIs, services)"
        }
        print("Available Templates:")
        for name, description in templates.items():
            print(f"  {name:12s} - {description}")
        sys.exit(0)

    if not args.incident_id:
        parser.print_help()
        sys.exit(1)

    if not args.authors and not args.preview:
        print("Error: --authors required (or use --preview)", file=sys.stderr)
        sys.exit(1)

    try:
        # Load incident
        incident_file = args.incidents_path / f"{args.incident_id}.json"
        if not incident_file.exists():
            print(f"Error: Incident {args.incident_id} not found", file=sys.stderr)
            sys.exit(1)

        incident = json.loads(incident_file.read_text())

        # Generate postmortem
        generator = PostmortemGenerator(incident)

        # Get template data if requested
        template_data = {}
        if args.template:
            library = PostmortemTemplateLibrary()
            if args.template == "deployment":
                template_data = library.deployment_failure_template()
            elif args.template == "resource":
                template_data = library.resource_exhaustion_template()
            elif args.template == "dependency":
                template_data = library.dependency_failure_template()

        # Load action items if provided
        action_items = None
        if args.action_items:
            action_items = json.loads(args.action_items.read_text())
        elif template_data.get('action_items'):
            action_items = template_data['action_items']

        # Generate postmortem
        authors = args.authors.split(',') if args.authors else ['TBD']
        root_cause = args.root_cause or template_data.get('root_cause_template')

        postmortem = generator.generate_markdown(
            authors=authors,
            root_cause=root_cause,
            action_items=action_items
        )

        # Output
        if args.json:
            output_data = {
                "incident_id": args.incident_id,
                "postmortem_markdown": postmortem,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            output_text = json.dumps(output_data, indent=2)
        else:
            output_text = postmortem

        if args.output and not args.preview:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output_text)
            print(f"Postmortem written to {args.output}")
        else:
            print(output_text)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
