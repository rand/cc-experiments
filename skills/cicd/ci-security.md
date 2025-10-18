---
name: cicd-ci-security
description: Managing secrets and credentials in CI/CD pipelines
---



# CI Security

**Scope**: Secret management, OIDC authentication, supply chain security, SBOM generation, vulnerability scanning, and secure pipeline patterns

**Lines**: 390

**Last Updated**: 2025-10-18

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Use this skill when:
- Managing secrets and credentials in CI/CD pipelines
- Implementing OIDC for passwordless authentication
- Securing supply chain with dependency scanning
- Generating and verifying Software Bill of Materials (SBOM)
- Implementing container image scanning
- Setting up security gates in pipelines
- Auditing and logging security events
- Implementing least-privilege access patterns

Don't use this skill for:
- General workflow configuration (see `github-actions-workflows.md`)
- Testing strategies (see `ci-testing-strategy.md`)
- Deployment patterns (see `cd-deployment-patterns.md`)

---

## Core Concepts

### Security Layers in CI/CD

```
1. Source Control Security
   ↓
2. Pipeline Security (secrets, permissions)
   ↓
3. Build Security (SBOM, signing)
   ↓
4. Dependency Security (scanning, verification)
   ↓
5. Runtime Security (container scanning)
   ↓
6. Deployment Security (OIDC, least privilege)
```

### Threat Model

```
Threat                          | Mitigation
────────────────────────────────|─────────────────────────────
Leaked secrets                  | OIDC, secret scanning
Compromised dependencies        | Dependency review, SBOM
Malicious code injection        | Branch protection, reviews
Supply chain attacks            | Provenance, signing
Container vulnerabilities       | Image scanning
Privilege escalation            | Least privilege, RBAC
```

---

## Patterns

### Secret Management with GitHub Secrets

```yaml
name: Secure Secrets

on: [push]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      # Access secrets from environment
      - name: Deploy with secrets
        run: ./deploy.sh
        env:
          API_KEY: ${{ secrets.API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      # Never log secrets
      - name: Safe logging
        run: |
          echo "Deploying to production"
          # DON'T: echo "API Key: $API_KEY"

      # Mask custom values
      - name: Mask sensitive values
        run: |
          echo "::add-mask::$SENSITIVE_VALUE"
          echo "Value: $SENSITIVE_VALUE"  # Will be masked in logs
```

### OIDC Authentication (No Long-Lived Secrets)

```yaml
name: OIDC Deploy

on: [push]

permissions:
  id-token: write  # Required for OIDC
  contents: read

jobs:
  deploy-aws:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # AWS via OIDC
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: us-east-1

      - name: Deploy to AWS
        run: |
          aws s3 sync dist/ s3://my-bucket/

  deploy-gcp:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # GCP via OIDC
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: 'projects/123/locations/global/workloadIdentityPools/pool/providers/provider'
          service_account: 'github-actions@project.iam.gserviceaccount.com'

      - name: Deploy to GCP
        run: gcloud app deploy

  deploy-azure:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Azure via OIDC
      - name: Azure Login
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Deploy to Azure
        run: az webapp deploy --name myapp --resource-group rg
```

### Dependency Scanning and Review

```yaml
name: Dependency Security

on:
  pull_request:
  schedule:
    - cron: '0 0 * * *'  # Daily

jobs:
  dependency-review:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'

    steps:
      - uses: actions/checkout@v4

      # GitHub native dependency review
      - name: Dependency Review
        uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: moderate
          deny-licenses: GPL-3.0, AGPL-3.0

  vulnerability-scan:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # npm audit
      - name: npm audit
        run: |
          npm audit --audit-level=moderate
          npm audit --json > audit-results.json

      # Snyk scanning
      - name: Run Snyk
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

      # OWASP Dependency Check
      - name: OWASP Dependency Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: 'myapp'
          path: '.'
          format: 'HTML'
          args: >
            --failOnCVSS 7
            --enableRetired

      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: dependency-check-report
          path: reports/

  license-check:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # License compliance
      - name: Check licenses
        run: |
          npx license-checker \
            --production \
            --onlyAllow="MIT;Apache-2.0;BSD-2-Clause;BSD-3-Clause;ISC" \
            --excludePackages "problematic-package@1.0.0"
```

### SBOM Generation and Verification

```yaml
name: SBOM and Provenance

on:
  push:
    branches: [main]
  release:
    types: [published]

jobs:
  sbom:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Generate SBOM with Syft
      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          format: spdx-json
          output-file: sbom.spdx.json

      # Generate CycloneDX SBOM
      - name: Generate CycloneDX SBOM
        run: |
          npm install -g @cyclonedx/cyclonedx-npm
          cyclonedx-npm --output-file sbom.cdx.json

      # Upload SBOM as artifact
      - uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: |
            sbom.spdx.json
            sbom.cdx.json

      # Attach SBOM to release
      - name: Upload to release
        if: github.event_name == 'release'
        uses: softprops/action-gh-release@v1
        with:
          files: |
            sbom.spdx.json
            sbom.cdx.json

  provenance:
    runs-on: ubuntu-latest
    permissions:
      actions: read
      id-token: write
      contents: write

    steps:
      - uses: actions/checkout@v4

      # Build artifacts
      - run: npm ci && npm run build

      # Generate SLSA provenance
      - name: Generate provenance
        uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v1.9.0
        with:
          base64-subjects: "${{ needs.build.outputs.digests }}"

      # Sign with Sigstore
      - name: Sign artifacts
        uses: sigstore/gh-action-sigstore-python@v2.1.1
        with:
          inputs: ./dist/*
          upload-signing-artifacts: true
```

### Container Image Scanning

```yaml
name: Container Security

on: [push]

jobs:
  scan:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Build image
      - name: Build Docker image
        run: docker build -t myapp:${{ github.sha }} .

      # Trivy vulnerability scanning
      - name: Run Trivy scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      # Upload to GitHub Security
      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

      # Grype scanning
      - name: Scan with Grype
        uses: anchore/scan-action@v3
        with:
          image: myapp:${{ github.sha }}
          fail-build: true
          severity-cutoff: high

      # Snyk container scanning
      - name: Snyk Container scan
        uses: snyk/actions/docker@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          image: myapp:${{ github.sha }}
          args: --severity-threshold=high

      # Docker Scout (Docker Hub)
      - name: Docker Scout
        uses: docker/scout-action@v1
        with:
          command: cves
          image: myapp:${{ github.sha }}
          exit-code: true
          only-severities: critical,high
```

### Code Scanning (SAST)

```yaml
name: Code Security Scanning

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  codeql:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read

    strategy:
      matrix:
        language: [javascript, python]

    steps:
      - uses: actions/checkout@v4

      # Initialize CodeQL
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
          queries: security-extended

      # Autobuild
      - name: Autobuild
        uses: github/codeql-action/autobuild@v3

      # Run analysis
      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3

  semgrep:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Semgrep SAST
      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/secrets
            p/owasp-top-ten

  sonarcloud:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for accurate analysis

      # SonarCloud scan
      - name: SonarCloud Scan
        uses: SonarSource/sonarcloud-github-action@master
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        with:
          args: >
            -Dsonar.projectKey=myproject
            -Dsonar.organization=myorg
```

### Secret Scanning

```yaml
name: Secret Detection

on: [push, pull_request]

jobs:
  scan-secrets:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      # Gitleaks
      - name: Gitleaks scan
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      # TruffleHog
      - name: TruffleHog scan
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD

      # detect-secrets
      - name: detect-secrets scan
        run: |
          pip install detect-secrets
          detect-secrets scan --baseline .secrets.baseline
          detect-secrets audit .secrets.baseline
```

### Least Privilege Permissions

```yaml
name: Minimal Permissions

on: [push]

# Default: read-only
permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    # Explicit minimal permissions
    permissions:
      contents: read
      packages: write  # Only for publishing

    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production
    # OIDC requires id-token
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE }}
          aws-region: us-east-1

      - run: ./deploy.sh
```

### Security Gates

```yaml
name: Security Gates

on:
  pull_request:
  push:
    branches: [main]

jobs:
  security-gate:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Gate 1: No secrets
      - name: Secret scan
        uses: gitleaks/gitleaks-action@v2

      # Gate 2: No critical vulnerabilities
      - name: Dependency scan
        run: |
          npm audit --audit-level=critical

      # Gate 3: No license violations
      - name: License check
        run: |
          npx license-checker --onlyAllow "MIT;Apache-2.0;BSD-3-Clause"

      # Gate 4: Code quality
      - name: SonarCloud gate
        uses: SonarSource/sonarcloud-github-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

      # Gate 5: Container security
      - name: Container scan
        if: success()
        run: |
          docker build -t myapp:test .
          trivy image --exit-code 1 --severity CRITICAL myapp:test

      # All gates passed
      - name: Security approval
        if: success()
        run: |
          echo "All security gates passed"
          echo "SECURITY_APPROVED=true" >> $GITHUB_ENV
```

### Audit Logging

```yaml
name: Security Audit

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      # Log security-relevant events
      - name: Audit log
        run: |
          cat <<EOF > audit.json
          {
            "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
            "event": "${{ github.event_name }}",
            "actor": "${{ github.actor }}",
            "repository": "${{ github.repository }}",
            "ref": "${{ github.ref }}",
            "sha": "${{ github.sha }}",
            "workflow": "${{ github.workflow }}"
          }
          EOF

      # Send to SIEM
      - name: Send to logging service
        run: |
          curl -X POST https://logs.example.com/api/events \
            -H "Authorization: Bearer ${{ secrets.LOG_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d @audit.json

      # Store audit trail
      - uses: actions/upload-artifact@v4
        with:
          name: audit-log-${{ github.run_id }}
          path: audit.json
          retention-days: 90
```

---

## Quick Reference

### OIDC Setup (AWS)

```bash
# 1. Create OIDC provider in AWS
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com

# 2. Create IAM role with trust policy
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:owner/repo:ref:refs/heads/main"
      }
    }
  }]
}
```

### Security Scanning Tools

```yaml
Secrets:         gitleaks, trufflehog, detect-secrets
Dependencies:    npm audit, snyk, dependabot
Containers:      trivy, grype, snyk container
Code (SAST):     codeql, semgrep, sonarcloud
License:         license-checker, fossa
SBOM:            syft, cyclonedx
```

### Severity Thresholds

```yaml
Development:  Allow MEDIUM and below
Staging:      Allow LOW and below
Production:   Block HIGH and CRITICAL
```

---

## Anti-Patterns

### ❌ Logging Secrets

```yaml
# WRONG: Secrets in logs
- run: echo "API Key: ${{ secrets.API_KEY }}"
```

```yaml
# CORRECT: Never log secrets
- run: echo "Deploying with credentials"
  env:
    API_KEY: ${{ secrets.API_KEY }}
```

### ❌ Using Long-Lived Credentials

```yaml
# WRONG: Static credentials
- env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_KEY }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET }}
```

```yaml
# CORRECT: OIDC
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE }}
```

### ❌ Overly Permissive Access

```yaml
# WRONG: Write access to everything
permissions: write-all
```

```yaml
# CORRECT: Minimal permissions
permissions:
  contents: read
  id-token: write
```

### ❌ No Vulnerability Scanning

```yaml
# WRONG: Deploy without scanning
- run: docker push myapp:latest
```

```yaml
# CORRECT: Scan before push
- run: trivy image --exit-code 1 myapp:latest
- run: docker push myapp:latest
```

### ❌ Ignoring Security Alerts

```yaml
# WRONG: Bypass security
- run: npm audit || true
```

```yaml
# CORRECT: Fail on vulnerabilities
- run: npm audit --audit-level=moderate
```

---

## Related Skills

- `github-actions-workflows.md` - Workflow configuration basics
- `ci-testing-strategy.md` - Security testing integration
- `cd-deployment-patterns.md` - Secure deployment practices
- `ci-optimization.md` - Optimizing security scans

---

**Last Updated**: 2025-10-18

**Format Version**: 1.0 (Atomic)
