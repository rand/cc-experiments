#!/usr/bin/env bash
# Sigstore Cosign Container Signing Example
#
# Demonstrates container image signing using Sigstore's cosign tool.
# Cosign provides keyless signing (using OIDC identity) or traditional key-based signing
# with transparency via Rekor (signature transparency log).
#
# Features:
# - Keyless signing with OIDC (GitHub, Google, Microsoft)
# - Traditional key-based signing
# - Signature transparency via Rekor
# - SBOM (Software Bill of Materials) attachment
# - Policy enforcement with admission controllers
#
# Production Considerations:
# - Use keyless signing for public projects
# - Use key-based signing with HSMs for enterprise
# - Always verify signatures before deployment
# - Implement admission controller policies
# - Store public keys in trusted locations

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Sigstore Cosign Container Signing Example"
echo "=========================================="

# Check if cosign is installed
if ! command -v cosign &> /dev/null; then
    echo -e "${RED}Error: cosign not found${NC}"
    echo "Install with: brew install cosign"
    echo "Or: go install github.com/sigstore/cosign/v2/cmd/cosign@latest"
    exit 1
fi

echo -e "\n${GREEN}1. Generating signing key pair${NC}"
echo "   Creating ephemeral key for demonstration..."

# Generate key pair (use HSM or KMS in production)
if [[ ! -f cosign.key ]]; then
    COSIGN_PASSWORD="" cosign generate-key-pair
    echo "   ✓ Keys generated: cosign.key (private), cosign.pub (public)"
else
    echo "   ✓ Using existing keys"
fi

echo -e "\n${GREEN}2. Building demo container image${NC}"
echo "   Creating simple container image..."

# Create demo Dockerfile
cat > Dockerfile.demo <<EOF
FROM alpine:latest
RUN echo "Demo application" > /app.txt
CMD cat /app.txt
EOF

# Build image
IMAGE="localhost:5000/demo-app:v1.0.0"
docker build -f Dockerfile.demo -t "${IMAGE}" .
echo "   ✓ Built image: ${IMAGE}"

echo -e "\n${GREEN}3. Signing container image (key-based)${NC}"
echo "   Signing with cosign..."

# Sign image
COSIGN_PASSWORD="" cosign sign --key cosign.key "${IMAGE}"
echo "   ✓ Image signed successfully"

echo -e "\n${GREEN}4. Verifying signature${NC}"
echo "   Verifying with public key..."

# Verify signature
if cosign verify --key cosign.pub "${IMAGE}"; then
    echo "   ✓ Signature verification successful"
else
    echo "   ✗ Signature verification failed"
    exit 1
fi

echo -e "\n${GREEN}5. Attaching SBOM (Software Bill of Materials)${NC}"
echo "   Creating and attaching SBOM..."

# Create demo SBOM (in production, use syft or similar)
cat > sbom.json <<EOF
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "version": 1,
  "components": [
    {
      "type": "library",
      "name": "alpine",
      "version": "latest"
    }
  ]
}
EOF

# Attach SBOM
cosign attach sbom --sbom sbom.json "${IMAGE}"
echo "   ✓ SBOM attached to image"

echo -e "\n${GREEN}6. Demonstrating keyless signing (simulation)${NC}"
echo "   Keyless signing requires OIDC authentication..."
echo "   Command for keyless signing:"
echo "   $ cosign sign ${IMAGE}"
echo "   "
echo "   This will:"
echo "   - Open browser for OIDC authentication (GitHub/Google/Microsoft)"
echo "   - Generate ephemeral certificate from Fulcio CA"
echo "   - Sign image with ephemeral key"
echo "   - Upload signature to Rekor transparency log"
echo "   - Discard ephemeral key"

echo -e "\n${GREEN}7. Inspecting signatures${NC}"
echo "   Retrieving signature metadata..."

# Get signature information
cosign tree "${IMAGE}"

echo -e "\n${GREEN}8. Policy enforcement example${NC}"
echo "   Creating admission policy..."

# Create example admission policy (for use with Kyverno or OPA)
cat > admission-policy.yaml <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: cosign-policy
data:
  policy.yaml: |
    apiVersion: policy.sigstore.dev/v1beta1
    kind: ClusterImagePolicy
    metadata:
      name: require-signature
    spec:
      images:
      - glob: "localhost:5000/demo-app:*"
      authorities:
      - key:
          data: |
$(sed 's/^/            /' cosign.pub)
EOF

echo "   ✓ Policy created: admission-policy.yaml"
echo "   Apply with: kubectl apply -f admission-policy.yaml"

echo -e "\n${GREEN}9. Multi-signature example${NC}"
echo "   Images can have multiple signatures from different parties..."

# Generate second key pair
if [[ ! -f cosign-dev.key ]]; then
    COSIGN_PASSWORD="" cosign generate-key-pair -o cosign-dev
    echo "   ✓ Second key pair generated"
fi

# Sign with second key
COSIGN_PASSWORD="" cosign sign --key cosign-dev.key "${IMAGE}"
echo "   ✓ Image signed with second key"

# Verify both signatures exist
echo "   Verifying multiple signatures..."
cosign verify --key cosign.pub "${IMAGE}" > /dev/null && echo "   ✓ First signature valid"
cosign verify --key cosign-dev.pub "${IMAGE}" > /dev/null && echo "   ✓ Second signature valid"

echo -e "\n${GREEN}10. Signing container with annotations${NC}"
echo "   Adding custom metadata to signature..."

# Sign with annotations
COSIGN_PASSWORD="" cosign sign --key cosign.key \
    -a "environment=production" \
    -a "approved-by=security-team" \
    -a "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "${IMAGE}"

echo "   ✓ Signed with annotations"

# Verify and show annotations
echo "   Signature annotations:"
cosign verify --key cosign.pub "${IMAGE}" | jq -r '.[].optional'

echo -e "\n${GREEN}11. Integration with CI/CD${NC}"
echo "   Example GitHub Actions workflow:"

cat > .github-workflow-example.yml <<'EOF'
name: Build and Sign Container

on:
  push:
    tags:
      - 'v*'

jobs:
  build-and-sign:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write  # Required for keyless signing

    steps:
      - uses: actions/checkout@v4

      - name: Install cosign
        uses: sigstore/cosign-installer@v3

      - name: Log in to registry
        run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u $ --password-stdin

      - name: Build image
        run: |
          docker build -t ghcr.io/${{ github.repository }}:${{ github.ref_name }} .

      - name: Push image
        run: |
          docker push ghcr.io/${{ github.repository }}:${{ github.ref_name }}

      - name: Sign image (keyless)
        run: |
          cosign sign --yes ghcr.io/${{ github.repository }}:${{ github.ref_name }}

      - name: Verify signature
        run: |
          cosign verify \
            --certificate-identity-regexp "^https://github.com/${{ github.repository }}/" \
            --certificate-oidc-issuer https://token.actions.githubusercontent.com \
            ghcr.io/${{ github.repository }}:${{ github.ref_name }}
EOF

echo "   ✓ Example workflow saved to .github-workflow-example.yml"

echo -e "\n${GREEN}12. Verification in deployment${NC}"
echo "   Example Kubernetes deployment with verification:"

cat > deployment-example.yaml <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: signed-app
spec:
  containers:
  - name: app
    image: ${IMAGE}
    # Signature verified by admission controller before deployment
EOF

echo "   ✓ Deployment example saved to deployment-example.yaml"

echo -e "\n=========================================="
echo -e "${YELLOW}Production Recommendations:${NC}"
echo ""
echo "Key Management:"
echo "  • Use keyless signing for public/OSS projects"
echo "  • Use key-based signing with HSM/KMS for enterprise"
echo "  • Never commit private keys to version control"
echo "  • Rotate keys regularly (annually)"
echo ""
echo "Transparency:"
echo "  • All signatures logged to Rekor (public transparency log)"
echo "  • Provides non-repudiation and tamper evidence"
echo "  • Query Rekor for signature history"
echo ""
echo "Policy Enforcement:"
echo "  • Deploy Sigstore Policy Controller in Kubernetes"
echo "  • Require signatures on all production images"
echo "  • Implement multi-signature requirements for critical images"
echo "  • Use ClusterImagePolicy for admission control"
echo ""
echo "SBOM Management:"
echo "  • Attach SBOMs to all images"
echo "  • Generate SBOMs with Syft or similar tools"
echo "  • Verify SBOM signatures"
echo "  • Use SBOMs for vulnerability scanning"
echo ""
echo "CI/CD Integration:"
echo "  • Sign images as part of build pipeline"
echo "  • Verify signatures before deployment"
echo "  • Use OIDC for keyless signing in CI"
echo "  • Store public keys in source control"
echo ""
echo "Useful Commands:"
echo "  cosign generate-key-pair                    # Generate keys"
echo "  cosign sign --key cosign.key IMAGE          # Sign image"
echo "  cosign verify --key cosign.pub IMAGE        # Verify signature"
echo "  cosign sign IMAGE                           # Keyless signing"
echo "  cosign attach sbom --sbom sbom.json IMAGE   # Attach SBOM"
echo "  cosign tree IMAGE                           # View all artifacts"
echo "  cosign triangulate IMAGE                    # Get signature location"
echo ""
echo "Learn more: https://docs.sigstore.dev/"
echo ""

# Cleanup
echo -e "\n${GREEN}Cleanup${NC}"
echo "To remove demo artifacts, run:"
echo "  docker rmi ${IMAGE}"
echo "  rm -f cosign.key cosign.pub cosign-dev.key cosign-dev.pub"
echo "  rm -f Dockerfile.demo sbom.json admission-policy.yaml"
echo "  rm -f .github-workflow-example.yml deployment-example.yaml"
