#!/usr/bin/env bash
#
# Certbot Automation Examples
#
# Comprehensive examples for automating certificate management with certbot
# (Let's Encrypt ACME client)

set -euo pipefail

# =================================================================
# Example 1: Basic HTTP-01 certificate with webroot
# =================================================================
obtain_http01_cert() {
    echo "=== Obtaining certificate with HTTP-01 (webroot) ==="

    certbot certonly \
        --webroot \
        -w /var/www/html \
        -d example.com \
        -d www.example.com \
        --email admin@example.com \
        --agree-tos \
        --non-interactive

    echo "Certificate obtained: /etc/letsencrypt/live/example.com/"
}

# =================================================================
# Example 2: Nginx plugin (automatic installation)
# =================================================================
obtain_nginx_auto() {
    echo "=== Obtaining and installing certificate with Nginx plugin ==="

    certbot --nginx \
        -d example.com \
        -d www.example.com \
        --email admin@example.com \
        --agree-tos \
        --non-interactive \
        --redirect  # Automatically configure HTTPS redirect

    echo "Certificate installed and Nginx configured"
}

# =================================================================
# Example 3: Wildcard certificate with DNS-01 (manual)
# =================================================================
obtain_wildcard_manual() {
    echo "=== Obtaining wildcard certificate (manual DNS) ==="

    certbot certonly \
        --manual \
        --preferred-challenges dns \
        -d '*.example.com' \
        -d example.com \
        --email admin@example.com \
        --agree-tos

    echo "Follow the prompts to add DNS TXT records"
}

# =================================================================
# Example 4: Wildcard with Cloudflare DNS automation
# =================================================================
obtain_wildcard_cloudflare() {
    echo "=== Obtaining wildcard certificate (Cloudflare DNS automation) ==="

    # Prerequisites:
    # - Install: pip install certbot-dns-cloudflare
    # - Create credentials file with Cloudflare API token

    cat > /root/.cloudflare-credentials.ini <<EOF
# Cloudflare API token
dns_cloudflare_api_token = your-cloudflare-api-token
EOF
    chmod 600 /root/.cloudflare-credentials.ini

    certbot certonly \
        --dns-cloudflare \
        --dns-cloudflare-credentials /root/.cloudflare-credentials.ini \
        -d '*.example.com' \
        -d example.com \
        --email admin@example.com \
        --agree-tos \
        --non-interactive

    echo "Wildcard certificate obtained"
}

# =================================================================
# Example 5: AWS Route53 DNS automation
# =================================================================
obtain_wildcard_route53() {
    echo "=== Obtaining wildcard certificate (Route53 DNS automation) ==="

    # Prerequisites:
    # - Install: pip install certbot-dns-route53
    # - Configure AWS credentials (IAM role or ~/.aws/credentials)

    certbot certonly \
        --dns-route53 \
        -d '*.example.com' \
        -d example.com \
        --email admin@example.com \
        --agree-tos \
        --non-interactive

    echo "Wildcard certificate obtained via Route53"
}

# =================================================================
# Example 6: Renew all certificates
# =================================================================
renew_all_certificates() {
    echo "=== Renewing all certificates ==="

    certbot renew \
        --quiet \
        --post-hook "systemctl reload nginx"

    echo "Renewal complete"
}

# =================================================================
# Example 7: Dry-run renewal (testing)
# =================================================================
test_renewal() {
    echo "=== Testing renewal process (dry-run) ==="

    certbot renew --dry-run

    echo "Dry-run successful - renewal process works"
}

# =================================================================
# Example 8: Automated renewal with systemd timer
# =================================================================
setup_systemd_renewal() {
    echo "=== Setting up systemd timer for automatic renewal ==="

    # Create service file
    cat > /etc/systemd/system/certbot-renew.service <<'EOF'
[Unit]
Description=Certbot Certificate Renewal
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet --deploy-hook "systemctl reload nginx"
EOF

    # Create timer file
    cat > /etc/systemd/system/certbot-renew.timer <<'EOF'
[Unit]
Description=Certbot Renewal Timer

[Timer]
# Run twice daily
OnCalendar=*-*-* 00,12:00:00
# Add random delay 0-1 hour to avoid load spikes
RandomizedDelaySec=1h
# Catch up if system was off
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Enable and start timer
    systemctl daemon-reload
    systemctl enable certbot-renew.timer
    systemctl start certbot-renew.timer

    # Check status
    systemctl list-timers certbot-renew.timer

    echo "Systemd timer configured"
}

# =================================================================
# Example 9: Renewal with hooks
# =================================================================
renew_with_hooks() {
    echo "=== Renewal with pre/post/deploy hooks ==="

    certbot renew \
        --pre-hook "systemctl stop nginx" \
        --post-hook "systemctl start nginx" \
        --deploy-hook "systemctl reload nginx && /usr/local/bin/notify-admins.sh"

    echo "Renewal with hooks complete"
}

# =================================================================
# Example 10: Certificate revocation
# =================================================================
revoke_certificate() {
    local domain="${1:-example.com}"
    local reason="${2:-unspecified}"

    echo "=== Revoking certificate for $domain ==="

    # Revocation reasons: unspecified, keyCompromise, affiliationChanged,
    # superseded, cessationOfOperation

    certbot revoke \
        --cert-name "$domain" \
        --reason "$reason" \
        --delete-after-revoke

    echo "Certificate revoked"
}

# =================================================================
# Example 11: Force renewal (before expiry)
# =================================================================
force_renew() {
    local domain="${1:-example.com}"

    echo "=== Force renewing certificate for $domain ==="

    certbot renew \
        --cert-name "$domain" \
        --force-renewal

    echo "Certificate forcibly renewed"
}

# =================================================================
# Example 12: List all certificates
# =================================================================
list_certificates() {
    echo "=== Listing all certificates ==="

    certbot certificates

    echo ""
    echo "Certificate files location:"
    echo "  /etc/letsencrypt/live/<domain>/"
}

# =================================================================
# Example 13: Staging environment (testing)
# =================================================================
obtain_staging_cert() {
    echo "=== Obtaining certificate from staging (testing) ==="

    certbot certonly \
        --webroot \
        -w /var/www/html \
        -d test.example.com \
        --staging \
        --email admin@example.com \
        --agree-tos \
        --non-interactive

    echo "Staging certificate obtained (will not be trusted by browsers)"
}

# =================================================================
# Example 14: Standalone mode (temporary server on port 80)
# =================================================================
obtain_standalone() {
    echo "=== Obtaining certificate with standalone server ==="

    # Requires port 80 to be available
    # Stop web server first if running

    certbot certonly \
        --standalone \
        -d example.com \
        -d www.example.com \
        --email admin@example.com \
        --agree-tos \
        --non-interactive

    echo "Certificate obtained via standalone mode"
}

# =================================================================
# Example 15: Install certificate to Nginx (manual)
# =================================================================
install_cert_nginx() {
    local domain="${1:-example.com}"

    echo "=== Installing certificate to Nginx manually ==="

    # Nginx configuration
    cat > "/etc/nginx/sites-available/$domain" <<EOF
server {
    listen 443 ssl http2;
    server_name $domain www.$domain;

    # SSL/TLS certificates
    ssl_certificate /etc/letsencrypt/live/$domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$domain/privkey.pem;

    # TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/$domain/chain.pem;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        root /var/www/html;
        index index.html;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name $domain www.$domain;
    return 301 https://\$server_name\$request_uri;
}
EOF

    # Enable site
    ln -sf "/etc/nginx/sites-available/$domain" "/etc/nginx/sites-enabled/"

    # Test configuration
    nginx -t

    # Reload Nginx
    systemctl reload nginx

    echo "Certificate installed and Nginx configured"
}

# =================================================================
# Example 16: Monitoring expiration
# =================================================================
check_expiration() {
    echo "=== Checking certificate expiration ==="

    for cert_dir in /etc/letsencrypt/live/*/; do
        domain=$(basename "$cert_dir")
        cert_file="$cert_dir/cert.pem"

        if [[ -f "$cert_file" ]]; then
            expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)
            expiry_epoch=$(date -d "$expiry_date" +%s)
            now_epoch=$(date +%s)
            days_remaining=$(( (expiry_epoch - now_epoch) / 86400 ))

            printf "%-30s %3d days\n" "$domain:" "$days_remaining"

            if (( days_remaining < 7 )); then
                echo "  WARNING: Expires soon!"
            fi
        fi
    done
}

# =================================================================
# Example 17: Delete certificate
# =================================================================
delete_certificate() {
    local domain="${1:-example.com}"

    echo "=== Deleting certificate for $domain ==="

    certbot delete --cert-name "$domain"

    echo "Certificate deleted"
}

# =================================================================
# Example 18: Custom CSR (bring your own key)
# =================================================================
obtain_with_custom_csr() {
    echo "=== Obtaining certificate with custom CSR ==="

    # Generate private key
    openssl genrsa -out custom.key 3072

    # Generate CSR
    openssl req -new -key custom.key -out custom.csr \
        -subj "/CN=example.com" \
        -addext "subjectAltName=DNS:example.com,DNS:www.example.com"

    # Obtain certificate with custom CSR
    certbot certonly \
        --webroot \
        -w /var/www/html \
        --csr custom.csr \
        --email admin@example.com \
        --agree-tos \
        --non-interactive

    echo "Certificate obtained with custom CSR"
}

# =================================================================
# Main menu
# =================================================================
show_menu() {
    cat <<EOF

Certbot Automation Examples
============================

1.  Obtain HTTP-01 certificate (webroot)
2.  Obtain with Nginx plugin (auto)
3.  Obtain wildcard (manual DNS)
4.  Obtain wildcard (Cloudflare DNS)
5.  Obtain wildcard (Route53 DNS)
6.  Renew all certificates
7.  Test renewal (dry-run)
8.  Setup systemd auto-renewal
9.  Renew with hooks
10. Revoke certificate
11. Force renewal
12. List certificates
13. Obtain staging certificate (testing)
14. Obtain standalone certificate
15. Install certificate to Nginx
16. Check expiration
17. Delete certificate
18. Obtain with custom CSR

0. Exit

EOF
}

main() {
    if [[ $# -eq 0 ]]; then
        # Interactive menu
        while true; do
            show_menu
            read -p "Select option: " choice

            case $choice in
                1) obtain_http01_cert ;;
                2) obtain_nginx_auto ;;
                3) obtain_wildcard_manual ;;
                4) obtain_wildcard_cloudflare ;;
                5) obtain_wildcard_route53 ;;
                6) renew_all_certificates ;;
                7) test_renewal ;;
                8) setup_systemd_renewal ;;
                9) renew_with_hooks ;;
                10) read -p "Domain: " domain; read -p "Reason: " reason; revoke_certificate "$domain" "$reason" ;;
                11) read -p "Domain: " domain; force_renew "$domain" ;;
                12) list_certificates ;;
                13) obtain_staging_cert ;;
                14) obtain_standalone ;;
                15) read -p "Domain: " domain; install_cert_nginx "$domain" ;;
                16) check_expiration ;;
                17) read -p "Domain: " domain; delete_certificate "$domain" ;;
                18) obtain_with_custom_csr ;;
                0) exit 0 ;;
                *) echo "Invalid option" ;;
            esac

            echo ""
            read -p "Press Enter to continue..."
        done
    else
        # Command-line mode
        case "$1" in
            renew) renew_all_certificates ;;
            list) list_certificates ;;
            check) check_expiration ;;
            test) test_renewal ;;
            *) echo "Usage: $0 {renew|list|check|test}" ;;
        esac
    fi
}

main "$@"
