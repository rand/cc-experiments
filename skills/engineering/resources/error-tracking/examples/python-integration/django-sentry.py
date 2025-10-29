"""
Django + Sentry Integration Example

Complete Django configuration with comprehensive Sentry error tracking.

Add to Django settings.py:
    from .sentry_config import init_sentry
    init_sentry()

Features:
- Automatic exception capture
- User tracking with Django auth
- Database query breadcrumbs
- Cache operation tracking
- Celery task monitoring
- Custom middleware for context enrichment
"""

import os
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def init_sentry():
    """Initialize Sentry for Django application."""

    logging_integration = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR
    )

    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        environment=os.environ.get('DJANGO_ENV', 'development'),
        release=os.environ.get('RELEASE', 'unknown'),

        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
            logging_integration,
        ],

        traces_sample_rate=get_sample_rate(),
        send_default_pii=False,
        before_send=before_send_handler,
    )


def get_sample_rate():
    """Get traces sample rate based on environment."""
    env = os.environ.get('DJANGO_ENV', 'development')
    return {'production': 0.05, 'staging': 0.5}.get(env, 1.0)


def before_send_handler(event, hint):
    """Scrub sensitive data before sending."""
    # Remove sensitive data from request
    if 'request' in event:
        if 'cookies' in event['request']:
            event['request']['cookies'] = {}
        if 'headers' in event['request']:
            for header in ['Authorization', 'Cookie']:
                event['request']['headers'].pop(header, None)

    return event


# Custom Middleware
class SentryContextMiddleware:
    """Add Django-specific context to Sentry events."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add user context
        if request.user.is_authenticated:
            sentry_sdk.set_user({
                "id": request.user.id,
                "email": request.user.email,
                "username": request.user.username,
            })

        # Add request context
        sentry_sdk.set_context("django", {
            "view": request.resolver_match.view_name if request.resolver_match else None,
            "url_name": request.resolver_match.url_name if request.resolver_match else None,
        })

        response = self.get_response(request)
        return response
