#!/usr/bin/env python3
"""
Nginx Configuration Generator

Generates Nginx configuration files from templates and parameters.
Useful for programmatically creating configurations for multiple environments.

Usage:
    ./config-generator.py --help
    ./config-generator.py --template reverse-proxy --output nginx.conf
    ./config-generator.py --template ssl --domain example.com --output nginx.conf
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional


@dataclass
class UpstreamServer:
    """Backend server configuration"""
    host: str
    port: int
    weight: int = 1
    max_fails: int = 3
    fail_timeout: str = "30s"


@dataclass
class ServerConfig:
    """Server block configuration"""
    server_name: str
    listen_port: int = 80
    listen_ssl: bool = False
    ssl_certificate: Optional[str] = None
    ssl_certificate_key: Optional[str] = None
    root: Optional[str] = None
    upstream_name: Optional[str] = None
    locations: List[Dict] = None


class NginxConfigGenerator:
    """Generate Nginx configuration files"""

    def __init__(self):
        self.templates = {
            'reverse-proxy': self.generate_reverse_proxy,
            'ssl': self.generate_ssl_termination,
            'static': self.generate_static_server,
            'load-balancer': self.generate_load_balancer,
        }

    def generate_reverse_proxy(self, **kwargs) -> str:
        """Generate reverse proxy configuration"""
        domain = kwargs.get('domain', 'example.com')
        backend_host = kwargs.get('backend_host', 'localhost')
        backend_port = kwargs.get('backend_port', 8080)

        config = f"""# Reverse Proxy Configuration
# Generated for {domain}

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {{
    worker_connections 1024;
}}

http {{
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;

    upstream backend {{
        server {backend_host}:{backend_port};
        keepalive 16;
    }}

    server {{
        listen 80;
        server_name {domain};

        location / {{
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}

        location /health {{
            access_log off;
            return 200 "OK\\n";
            add_header Content-Type text/plain;
        }}
    }}
}}
"""
        return config

    def generate_ssl_termination(self, **kwargs) -> str:
        """Generate SSL termination configuration"""
        domain = kwargs.get('domain', 'example.com')
        cert_path = kwargs.get('cert_path', f'/etc/ssl/certs/{domain}.crt')
        key_path = kwargs.get('key_path', f'/etc/ssl/private/{domain}.key')
        backend_host = kwargs.get('backend_host', 'localhost')
        backend_port = kwargs.get('backend_port', 8080)

        config = f"""# SSL Termination Configuration
# Generated for {domain}

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {{
    worker_connections 1024;
}}

http {{
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;
    server_tokens off;

    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    upstream backend {{
        server {backend_host}:{backend_port};
        keepalive 16;
    }}

    # HTTP redirect to HTTPS
    server {{
        listen 80;
        server_name {domain};

        location /.well-known/acme-challenge/ {{
            root /var/www/certbot;
        }}

        location / {{
            return 301 https://$host$request_uri;
        }}
    }}

    # HTTPS server
    server {{
        listen 443 ssl http2;
        server_name {domain};

        ssl_certificate {cert_path};
        ssl_certificate_key {key_path};
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers off;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;

        location / {{
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}

        location /health {{
            access_log off;
            return 200 "OK\\n";
            add_header Content-Type text/plain;
        }}
    }}
}}
"""
        return config

    def generate_static_server(self, **kwargs) -> str:
        """Generate static file server configuration"""
        domain = kwargs.get('domain', 'example.com')
        root_path = kwargs.get('root', '/var/www/html')

        config = f"""# Static File Server Configuration
# Generated for {domain}

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {{
    worker_connections 1024;
}}

http {{
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss;

    # File cache
    open_file_cache max=1000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;

    server {{
        listen 80;
        server_name {domain};

        root {root_path};
        index index.html index.htm;

        # Static files
        location / {{
            try_files $uri $uri/ /index.html;
            expires 1d;
            add_header Cache-Control "public, max-age=86400";
        }}

        # Long cache for assets
        location ~* \\.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {{
            expires 1y;
            add_header Cache-Control "public, immutable";
            access_log off;
        }}

        # Health check
        location /health {{
            access_log off;
            return 200 "OK\\n";
            add_header Content-Type text/plain;
        }}
    }}
}}
"""
        return config

    def generate_load_balancer(self, **kwargs) -> str:
        """Generate load balancer configuration"""
        domain = kwargs.get('domain', 'example.com')
        backends = kwargs.get('backends', [
            {'host': 'backend1.internal', 'port': 8080},
            {'host': 'backend2.internal', 'port': 8080},
        ])

        upstream_servers = '\n        '.join([
            f"server {b['host']}:{b['port']} weight={b.get('weight', 1)} max_fails=3 fail_timeout=30s;"
            for b in backends
        ])

        config = f"""# Load Balancer Configuration
# Generated for {domain}

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {{
    worker_connections 2048;
}}

http {{
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" upstream=$upstream_addr';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;

    upstream backend_pool {{
        least_conn;
        {upstream_servers}
        keepalive 32;
    }}

    server {{
        listen 80;
        server_name {domain};

        location / {{
            proxy_pass http://backend_pool;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            proxy_connect_timeout 5s;
            proxy_send_timeout 10s;
            proxy_read_timeout 30s;

            proxy_next_upstream error timeout http_502 http_503 http_504;
            proxy_next_upstream_tries 2;
        }}

        location /health {{
            access_log off;
            return 200 "OK\\n";
            add_header Content-Type text/plain;
        }}
    }}
}}
"""
        return config

    def generate(self, template: str, **kwargs) -> str:
        """Generate configuration from template"""
        if template not in self.templates:
            raise ValueError(f"Unknown template: {template}. Available: {list(self.templates.keys())}")

        return self.templates[template](**kwargs)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Nginx configuration files from templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Templates:
  reverse-proxy  - Reverse proxy configuration
  ssl            - SSL termination configuration
  static         - Static file server configuration
  load-balancer  - Load balancer configuration

Examples:
  # Generate reverse proxy config
  %(prog)s --template reverse-proxy --domain example.com --output nginx.conf

  # Generate SSL termination config
  %(prog)s --template ssl --domain secure.example.com \\
           --cert-path /etc/ssl/certs/cert.crt --output nginx.conf

  # Generate static server config
  %(prog)s --template static --domain static.example.com \\
           --root /var/www/static --output nginx.conf

  # Generate load balancer with custom backends
  %(prog)s --template load-balancer --domain lb.example.com \\
           --backends '{"backends":[{"host":"app1","port":8080},{"host":"app2","port":8080}]}' \\
           --output nginx.conf
        """
    )

    parser.add_argument(
        '--template',
        required=True,
        choices=['reverse-proxy', 'ssl', 'static', 'load-balancer'],
        help='Configuration template to use'
    )

    parser.add_argument(
        '--domain',
        default='example.com',
        help='Domain name (default: example.com)'
    )

    parser.add_argument(
        '--backend-host',
        default='localhost',
        help='Backend host (default: localhost)'
    )

    parser.add_argument(
        '--backend-port',
        type=int,
        default=8080,
        help='Backend port (default: 8080)'
    )

    parser.add_argument(
        '--cert-path',
        help='SSL certificate path'
    )

    parser.add_argument(
        '--key-path',
        help='SSL key path'
    )

    parser.add_argument(
        '--root',
        help='Document root path'
    )

    parser.add_argument(
        '--backends',
        help='JSON string with backend servers (for load balancer)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        help='Output file (default: stdout)'
    )

    args = parser.parse_args()

    # Build kwargs
    kwargs = {
        'domain': args.domain,
        'backend_host': args.backend_host,
        'backend_port': args.backend_port,
    }

    if args.cert_path:
        kwargs['cert_path'] = args.cert_path
    if args.key_path:
        kwargs['key_path'] = args.key_path
    if args.root:
        kwargs['root'] = args.root
    if args.backends:
        backends_data = json.loads(args.backends)
        kwargs['backends'] = backends_data.get('backends', [])

    # Generate configuration
    generator = NginxConfigGenerator()
    try:
        config = generator.generate(args.template, **kwargs)
    except Exception as e:
        print(f"Error generating configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.output:
        args.output.write_text(config)
        print(f"Configuration written to {args.output}")
    else:
        print(config)

    sys.exit(0)


if __name__ == '__main__':
    main()
