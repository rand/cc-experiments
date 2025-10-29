#!/usr/bin/env python3
"""
Automated Error Tracking Setup

This script automates the deployment of Sentry error tracking infrastructure,
including:
- Project creation and configuration
- Integration setup (Slack, PagerDuty, GitHub)
- Alert rule generation
- Release tracking configuration
- Team setup and permissions
- Source map configuration

Usage:
    setup_error_tracking.py --org myorg --project backend-api --sentry-token <token>
    setup_error_tracking.py --config config.yml --apply
    setup_error_tracking.py --list-projects --json

Examples:
    # Create new project with defaults
    setup_error_tracking.py --org acme --project api --sentry-token $SENTRY_TOKEN

    # Create project from config file
    setup_error_tracking.py --config sentry-config.yml --apply

    # List existing projects
    setup_error_tracking.py --list-projects --json

    # Dry run (preview changes)
    setup_error_tracking.py --config config.yml --dry-run
"""

import argparse
import json
import sys
import os
import requests
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProjectConfig:
    """Error tracking project configuration."""
    name: str
    platform: str
    team: str
    environments: List[str]
    alert_rules: List[Dict[str, Any]]
    integrations: Dict[str, Any]
    data_scrubbing: Dict[str, Any]
    retention_days: int
    sample_rate: float


@dataclass
class IntegrationConfig:
    """Integration configuration (Slack, PagerDuty, etc.)."""
    type: str
    enabled: bool
    config: Dict[str, Any]


class SentryAPIClient:
    """Client for Sentry API operations."""

    def __init__(self, api_token: str, base_url: str = "https://sentry.io/api/0"):
        self.api_token = api_token
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make API request with error handling."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            logger.error(f"API request failed: {e}")
            logger.error(f"Response: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET request."""
        response = self._request("GET", endpoint, **kwargs)
        return response.json()

    def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """POST request."""
        response = self._request("POST", endpoint, **kwargs)
        return response.json()

    def put(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """PUT request."""
        response = self._request("PUT", endpoint, **kwargs)
        return response.json()

    def delete(self, endpoint: str, **kwargs) -> None:
        """DELETE request."""
        self._request("DELETE", endpoint, **kwargs)

    def list_organizations(self) -> List[Dict[str, Any]]:
        """List all organizations."""
        return self.get("/organizations/")

    def get_organization(self, org_slug: str) -> Dict[str, Any]:
        """Get organization details."""
        return self.get(f"/organizations/{org_slug}/")

    def list_projects(self, org_slug: str) -> List[Dict[str, Any]]:
        """List projects in organization."""
        return self.get(f"/organizations/{org_slug}/projects/")

    def create_project(
        self,
        org_slug: str,
        name: str,
        platform: str,
        team_slug: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new project."""
        data = {
            "name": name,
            "platform": platform
        }
        if team_slug:
            data["team_slug"] = team_slug

        return self.post(f"/teams/{org_slug}/{team_slug or 'default'}/projects/", json=data)

    def update_project(
        self,
        org_slug: str,
        project_slug: str,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update project settings."""
        return self.put(f"/projects/{org_slug}/{project_slug}/", json=settings)

    def create_alert_rule(
        self,
        org_slug: str,
        project_slug: str,
        rule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create alert rule."""
        return self.post(
            f"/projects/{org_slug}/{project_slug}/rules/",
            json=rule
        )

    def list_integrations(self, org_slug: str) -> List[Dict[str, Any]]:
        """List organization integrations."""
        return self.get(f"/organizations/{org_slug}/integrations/")

    def create_integration(
        self,
        org_slug: str,
        provider: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create integration."""
        return self.post(
            f"/organizations/{org_slug}/integrations/",
            json={"provider": provider, "config": config}
        )


class ErrorTrackingSetup:
    """Automated error tracking setup."""

    def __init__(self, client: SentryAPIClient, verbose: bool = False):
        self.client = client
        self.verbose = verbose

    def setup_project(
        self,
        org_slug: str,
        config: ProjectConfig,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Set up error tracking project."""
        logger.info(f"Setting up project: {config.name}")

        # Check if project exists
        existing_projects = self.client.list_projects(org_slug)
        project = None

        for p in existing_projects:
            if p['name'] == config.name or p['slug'] == config.name.lower():
                project = p
                logger.info(f"Project already exists: {config.name}")
                break

        # Create project if doesn't exist
        if not project:
            if dry_run:
                logger.info(f"[DRY RUN] Would create project: {config.name}")
            else:
                logger.info(f"Creating project: {config.name}")
                project = self.client.create_project(
                    org_slug,
                    config.name,
                    config.platform,
                    config.team
                )

        project_slug = project['slug']

        # Configure project settings
        settings = self._build_project_settings(config)

        if dry_run:
            logger.info(f"[DRY RUN] Would update settings: {json.dumps(settings, indent=2)}")
        else:
            logger.info("Updating project settings")
            self.client.update_project(org_slug, project_slug, settings)

        # Create alert rules
        for rule in config.alert_rules:
            if dry_run:
                logger.info(f"[DRY RUN] Would create alert rule: {rule['name']}")
            else:
                logger.info(f"Creating alert rule: {rule['name']}")
                self.client.create_alert_rule(org_slug, project_slug, rule)

        # Setup integrations
        for integration_type, integration_config in config.integrations.items():
            if integration_config.get('enabled'):
                self._setup_integration(org_slug, integration_type, integration_config, dry_run)

        logger.info(f"✓ Project setup complete: {config.name}")

        return {
            "project": project,
            "dsn": project.get('dsn', {}).get('public'),
            "url": f"https://sentry.io/{org_slug}/{project_slug}/"
        }

    def _build_project_settings(self, config: ProjectConfig) -> Dict[str, Any]:
        """Build project settings from config."""
        settings = {
            "name": config.name,
            "platform": config.platform,

            # Data scrubbing
            "dataScrubbing": config.data_scrubbing.get('enabled', True),
            "dataScrubberDefaults": config.data_scrubbing.get('defaults', True),
            "sensitiveFields": config.data_scrubbing.get('sensitive_fields', []),
            "safeFields": config.data_scrubbing.get('safe_fields', []),
            "scrubIPAddresses": config.data_scrubbing.get('scrub_ip', True),

            # Retention
            "retentionDays": config.retention_days,

            # Sampling
            "dynamicSampling": {
                "rules": [
                    {
                        "sampleRate": config.sample_rate,
                        "type": "trace",
                        "condition": {
                            "op": "and",
                            "inner": []
                        },
                        "id": 1
                    }
                ]
            },

            # Environments
            "environments": config.environments,
        }

        return settings

    def _setup_integration(
        self,
        org_slug: str,
        integration_type: str,
        integration_config: Dict[str, Any],
        dry_run: bool
    ) -> None:
        """Set up integration (Slack, PagerDuty, etc.)."""
        logger.info(f"Setting up {integration_type} integration")

        # Check if integration already exists
        existing_integrations = self.client.list_integrations(org_slug)

        for integration in existing_integrations:
            if integration['provider']['key'] == integration_type:
                logger.info(f"{integration_type} integration already exists")
                return

        if dry_run:
            logger.info(f"[DRY RUN] Would create {integration_type} integration")
        else:
            try:
                self.client.create_integration(
                    org_slug,
                    integration_type,
                    integration_config
                )
                logger.info(f"✓ {integration_type} integration created")
            except Exception as e:
                logger.warning(f"Failed to create {integration_type} integration: {e}")

    def generate_alert_rules(
        self,
        project_type: str,
        environments: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate standard alert rules."""
        rules = []

        # Rule 1: New errors in production
        rules.append({
            "name": "New Error in Production",
            "conditions": [
                {"id": "sentry.rules.conditions.first_seen_event.FirstSeenEventCondition"}
            ],
            "filters": [
                {
                    "id": "sentry.rules.filters.tagged_event.TaggedEventFilter",
                    "key": "environment",
                    "match": "eq",
                    "value": "production"
                },
                {
                    "id": "sentry.rules.filters.level.LevelFilter",
                    "match": "gte",
                    "level": "40"  # Error level
                }
            ],
            "actions": [
                {
                    "id": "sentry.mail.actions.NotifyEmailAction",
                    "targetType": "Team",
                    "targetIdentifier": "all"
                }
            ],
            "actionMatch": "all",
            "frequency": 30,
            "environment": "production"
        })

        # Rule 2: High error frequency
        rules.append({
            "name": "High Error Frequency",
            "conditions": [
                {
                    "id": "sentry.rules.conditions.event_frequency.EventFrequencyCondition",
                    "value": 100,
                    "interval": "1h",
                    "comparisonType": "count"
                }
            ],
            "filters": [
                {
                    "id": "sentry.rules.filters.tagged_event.TaggedEventFilter",
                    "key": "environment",
                    "match": "eq",
                    "value": "production"
                }
            ],
            "actions": [
                {
                    "id": "sentry.mail.actions.NotifyEmailAction",
                    "targetType": "Team",
                    "targetIdentifier": "all"
                }
            ],
            "actionMatch": "all",
            "frequency": 30,
            "environment": "production"
        })

        # Rule 3: High user impact
        rules.append({
            "name": "High User Impact",
            "conditions": [
                {
                    "id": "sentry.rules.conditions.event_frequency.EventUniqueUserFrequencyCondition",
                    "value": 50,
                    "interval": "1h",
                    "comparisonType": "count"
                }
            ],
            "filters": [
                {
                    "id": "sentry.rules.filters.tagged_event.TaggedEventFilter",
                    "key": "environment",
                    "match": "eq",
                    "value": "production"
                }
            ],
            "actions": [
                {
                    "id": "sentry.mail.actions.NotifyEmailAction",
                    "targetType": "Team",
                    "targetIdentifier": "all"
                }
            ],
            "actionMatch": "all",
            "frequency": 30,
            "environment": "production"
        })

        # Rule 4: Regression detected
        rules.append({
            "name": "Regression Detected",
            "conditions": [
                {"id": "sentry.rules.conditions.regression_event.RegressionEventCondition"}
            ],
            "filters": [
                {
                    "id": "sentry.rules.filters.tagged_event.TaggedEventFilter",
                    "key": "environment",
                    "match": "eq",
                    "value": "production"
                }
            ],
            "actions": [
                {
                    "id": "sentry.mail.actions.NotifyEmailAction",
                    "targetType": "Team",
                    "targetIdentifier": "all"
                }
            ],
            "actionMatch": "all",
            "frequency": 30,
            "environment": "production"
        })

        return rules

    def generate_sdk_config(
        self,
        platform: str,
        dsn: str,
        environment: str,
        release: str = "1.0.0"
    ) -> str:
        """Generate SDK initialization code."""
        configs = {
            "python": f"""
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn="{dsn}",
    environment="{environment}",
    release="{release}",

    # Integrations
    integrations=[
        FlaskIntegration(),
        SqlalchemyIntegration(),
    ],

    # Sampling
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,

    # Privacy
    send_default_pii=False,

    # Hooks
    before_send=scrub_sensitive_data,
)

def scrub_sensitive_data(event, hint):
    # Remove sensitive headers
    if 'request' in event and 'headers' in event['request']:
        event['request']['headers'].pop('Authorization', None)
        event['request']['headers'].pop('Cookie', None)
    return event
""",
            "javascript": f"""
import * as Sentry from "@sentry/browser";
import {{ BrowserTracing }} from "@sentry/tracing";

Sentry.init({{
  dsn: "{dsn}",
  environment: "{environment}",
  release: "{release}",

  integrations: [
    new BrowserTracing({{
      tracingOrigins: ["localhost", /^\\\//],
    }}),
  ],

  tracesSampleRate: 0.1,

  beforeSend(event, hint) {{
    // Scrub sensitive data
    if (event.request && event.request.url) {{
      event.request.url = event.request.url.replace(
        /token=[^&]+/g,
        'token=[Filtered]'
      );
    }}
    return event;
  }},
}});
""",
            "go": f"""
package main

import (
    "github.com/getsentry/sentry-go"
    sentryhttp "github.com/getsentry/sentry-go/http"
)

func main() {{
    err := sentry.Init(sentry.ClientOptions{{
        Dsn: "{dsn}",
        Environment: "{environment}",
        Release: "{release}",
        TracesSampleRate: 0.1,
    }})
    if err != nil {{
        log.Fatalf("sentry.Init: %s", err)
    }}
    defer sentry.Flush(2 * time.Second)

    // HTTP handler
    sentryHandler := sentryhttp.New(sentryhttp.Options{{}})
    http.Handle("/", sentryHandler.Handle(handler))
}}
""",
            "ruby": f"""
Sentry.init do |config|
  config.dsn = '{dsn}'
  config.environment = '{environment}'
  config.release = '{release}'
  config.traces_sample_rate = 0.1

  config.before_send = lambda do |event, hint|
    # Scrub sensitive data
    if event.request && event.request.headers
      event.request.headers.delete('Authorization')
      event.request.headers.delete('Cookie')
    end
    event
  end
end
""",
        }

        return configs.get(platform, f"# SDK config for {platform} not available")

    def validate_config(self, config: ProjectConfig) -> List[str]:
        """Validate project configuration."""
        errors = []

        # Validate required fields
        if not config.name:
            errors.append("Project name is required")

        if not config.platform:
            errors.append("Platform is required")

        # Validate environments
        if not config.environments:
            errors.append("At least one environment is required")

        valid_platforms = [
            "python", "python-django", "python-flask", "python-fastapi",
            "javascript", "javascript-react", "javascript-nextjs",
            "node", "node-express", "node-koa",
            "go", "ruby", "ruby-rails", "java", "php"
        ]
        if config.platform not in valid_platforms:
            errors.append(f"Invalid platform: {config.platform}")

        # Validate sample rate
        if not 0 <= config.sample_rate <= 1:
            errors.append("Sample rate must be between 0 and 1")

        # Validate retention
        if config.retention_days < 1 or config.retention_days > 365:
            errors.append("Retention days must be between 1 and 365")

        return errors


def load_config_file(path: str) -> ProjectConfig:
    """Load configuration from YAML file."""
    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    return ProjectConfig(
        name=data['name'],
        platform=data['platform'],
        team=data.get('team', 'default'),
        environments=data.get('environments', ['production', 'staging']),
        alert_rules=data.get('alert_rules', []),
        integrations=data.get('integrations', {}),
        data_scrubbing=data.get('data_scrubbing', {
            'enabled': True,
            'defaults': True,
            'sensitive_fields': [],
            'safe_fields': [],
            'scrub_ip': True
        }),
        retention_days=data.get('retention_days', 90),
        sample_rate=data.get('sample_rate', 1.0)
    )


def create_default_config(name: str, platform: str, team: str) -> ProjectConfig:
    """Create default project configuration."""
    setup = ErrorTrackingSetup(None)

    return ProjectConfig(
        name=name,
        platform=platform,
        team=team,
        environments=['production', 'staging', 'development'],
        alert_rules=setup.generate_alert_rules(platform, ['production']),
        integrations={
            'slack': {'enabled': False},
            'pagerduty': {'enabled': False},
            'github': {'enabled': False},
        },
        data_scrubbing={
            'enabled': True,
            'defaults': True,
            'sensitive_fields': ['password', 'api_key', 'token', 'secret'],
            'safe_fields': ['username', 'user_id'],
            'scrub_ip': True
        },
        retention_days=90,
        sample_rate=1.0
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated error tracking setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--sentry-token',
        default=os.getenv('SENTRY_AUTH_TOKEN'),
        help='Sentry API token (or set SENTRY_AUTH_TOKEN env var)'
    )

    parser.add_argument(
        '--org',
        help='Sentry organization slug'
    )

    parser.add_argument(
        '--project',
        help='Project name'
    )

    parser.add_argument(
        '--platform',
        help='Platform (python, javascript, go, etc.)'
    )

    parser.add_argument(
        '--team',
        default='default',
        help='Team slug (default: default)'
    )

    parser.add_argument(
        '--config',
        help='Configuration file (YAML)'
    )

    parser.add_argument(
        '--list-projects',
        action='store_true',
        help='List existing projects'
    )

    parser.add_argument(
        '--list-orgs',
        action='store_true',
        help='List organizations'
    )

    parser.add_argument(
        '--generate-config',
        action='store_true',
        help='Generate default configuration file'
    )

    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply configuration (create/update project)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Validate token
    if not args.sentry_token and not (args.list_orgs or args.list_projects or args.generate_config):
        logger.error("Sentry API token required (--sentry-token or SENTRY_AUTH_TOKEN)")
        sys.exit(1)

    # Create API client
    client = SentryAPIClient(args.sentry_token) if args.sentry_token else None

    # List organizations
    if args.list_orgs:
        if not client:
            logger.error("API token required for listing organizations")
            sys.exit(1)

        orgs = client.list_organizations()

        if args.json:
            print(json.dumps(orgs, indent=2))
        else:
            print("\nOrganizations:")
            for org in orgs:
                print(f"  - {org['slug']} ({org['name']})")

        sys.exit(0)

    # List projects
    if args.list_projects:
        if not client:
            logger.error("API token required for listing projects")
            sys.exit(1)

        if not args.org:
            logger.error("--org required for listing projects")
            sys.exit(1)

        projects = client.list_projects(args.org)

        if args.json:
            print(json.dumps(projects, indent=2))
        else:
            print(f"\nProjects in {args.org}:")
            for project in projects:
                print(f"  - {project['slug']} ({project['platform']})")

        sys.exit(0)

    # Generate config
    if args.generate_config:
        if not args.project or not args.platform:
            logger.error("--project and --platform required for generating config")
            sys.exit(1)

        config = create_default_config(args.project, args.platform, args.team)

        output = yaml.dump(asdict(config), default_flow_style=False)
        print(output)

        sys.exit(0)

    # Setup project
    if args.config:
        # Load from file
        config = load_config_file(args.config)
    elif args.project and args.platform:
        # Create default config
        config = create_default_config(args.project, args.platform, args.team)
    else:
        logger.error("Either --config or (--project and --platform) required")
        parser.print_help()
        sys.exit(1)

    if not args.org:
        logger.error("--org required")
        sys.exit(1)

    # Validate configuration
    setup = ErrorTrackingSetup(client, verbose=args.verbose)
    errors = setup.validate_config(config)

    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    # Apply configuration
    if args.apply or args.dry_run:
        result = setup.setup_project(args.org, config, dry_run=args.dry_run)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("\n✓ Setup complete!")
            print(f"\nProject URL: {result['url']}")
            print(f"DSN: {result['dsn']}")
            print("\nSDK Configuration:")
            print(setup.generate_sdk_config(
                config.platform,
                result['dsn'],
                'production',
                '1.0.0'
            ))
    else:
        logger.info("Configuration valid. Use --apply to create/update project.")
        logger.info("Use --dry-run to preview changes.")


if __name__ == "__main__":
    main()
