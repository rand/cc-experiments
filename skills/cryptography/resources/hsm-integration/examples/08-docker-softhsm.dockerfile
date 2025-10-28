# Dockerfile for SoftHSM Testing Environment
# Production-ready container for HSM development and testing
# Multi-stage build for minimal final image

# Stage 1: Build environment
FROM ubuntu:22.04 AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    autoconf \
    automake \
    libtool \
    pkg-config \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Build SoftHSM from source
WORKDIR /tmp
RUN git clone https://github.com/opendnssec/SoftHSMv2.git && \
    cd SoftHSMv2 && \
    sh autogen.sh && \
    ./configure --prefix=/usr/local --with-crypto-backend=openssl && \
    make && \
    make install

# Stage 2: Runtime environment
FROM ubuntu:22.04

LABEL maintainer="HSM Team"
LABEL description="SoftHSM testing environment with Python PKCS#11 support"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3 \
    python3 \
    python3-pip \
    opensc \
    && rm -rf /var/lib/apt/lists/*

# Copy SoftHSM from builder
COPY --from=builder /usr/local/bin/softhsm2-util /usr/local/bin/
COPY --from=builder /usr/local/lib/softhsm /usr/local/lib/softhsm
COPY --from=builder /usr/local/share/man/man1/softhsm2* /usr/local/share/man/man1/
COPY --from=builder /usr/local/share/man/man5/softhsm2* /usr/local/share/man/man5/

# Install Python packages
RUN pip3 install --no-cache-dir \
    PyKCS11 \
    cryptography

# Create directories
RUN mkdir -p /var/lib/softhsm/tokens && \
    mkdir -p /etc/softhsm

# Create SoftHSM configuration
RUN echo "directories.tokendir = /var/lib/softhsm/tokens/" > /etc/softhsm/softhsm2.conf && \
    echo "objectstore.backend = file" >> /etc/softhsm/softhsm2.conf && \
    echo "log.level = INFO" >> /etc/softhsm/softhsm2.conf

# Set environment variables
ENV SOFTHSM2_CONF=/etc/softhsm/softhsm2.conf
ENV LD_LIBRARY_PATH=/usr/local/lib/softhsm:$LD_LIBRARY_PATH

# Initialize default token
RUN softhsm2-util --init-token --slot 0 --label "TestToken" --so-pin 1234 --pin 1234

# Create test script
RUN cat > /usr/local/bin/test-hsm.py << 'EOF'
#!/usr/bin/env python3
"""Test SoftHSM functionality."""

import PyKCS11

def test_softhsm():
    """Test basic SoftHSM operations."""
    print("Testing SoftHSM...")

    # Load library
    pkcs11 = PyKCS11.PyKCS11Lib()
    pkcs11.load("/usr/local/lib/softhsm/libsofthsm2.so")

    # Get info
    info = pkcs11.getInfo()
    print(f"Library: {info.manufacturerID}")

    # Open session
    session = pkcs11.openSession(0, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)
    session.login("1234")

    # Generate test key
    template = [
        (PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
        (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_AES),
        (PyKCS11.CKA_TOKEN, True),
        (PyKCS11.CKA_ENCRYPT, True),
        (PyKCS11.CKA_DECRYPT, True),
        (PyKCS11.CKA_VALUE_LEN, 32),
        (PyKCS11.CKA_LABEL, "Test AES Key"),
    ]

    key = session.generateKey(template, mecha=PyKCS11.MechanismAESKeyGen)
    print(f"Generated AES key: {key}")

    # Test encryption
    plaintext = b"Test message"
    iv = bytes([0] * 16)
    mechanism = PyKCS11.Mechanism(PyKCS11.CKM_AES_CBC_PAD, iv)

    ciphertext = session.encrypt(key, plaintext, mechanism)
    print(f"Encrypted: {len(ciphertext)} bytes")

    decrypted = session.decrypt(key, ciphertext, mechanism)
    print(f"Decrypted: {bytes(decrypted)}")

    assert bytes(decrypted) == plaintext, "Decryption failed"

    # Cleanup
    session.destroyObject(key)
    session.logout()
    session.closeSession()

    print("✓ All tests passed")

if __name__ == "__main__":
    test_softhsm()
EOF

RUN chmod +x /usr/local/bin/test-hsm.py

# Create helper scripts
RUN cat > /usr/local/bin/list-tokens << 'EOF'
#!/bin/bash
echo "SoftHSM Tokens:"
softhsm2-util --show-slots
EOF

RUN cat > /usr/local/bin/init-token << 'EOF'
#!/bin/bash
SLOT=${1:-0}
LABEL=${2:-"TestToken"}
SO_PIN=${3:-"1234"}
PIN=${4:-"1234"}

echo "Initializing token..."
softhsm2-util --init-token --slot $SLOT --label "$LABEL" --so-pin $SO_PIN --pin $PIN
EOF

RUN chmod +x /usr/local/bin/list-tokens /usr/local/bin/init-token

# Set working directory
WORKDIR /workspace

# Default command
CMD ["/bin/bash"]

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD test-hsm.py || exit 1

# Expose no ports (local testing only)

# Volume for persistent token storage
VOLUME ["/var/lib/softhsm/tokens"]

# Usage information
RUN cat > /etc/motd << 'EOF'
========================================
SoftHSM Testing Container
========================================

Available commands:
  list-tokens       - List all tokens
  init-token        - Initialize new token
  test-hsm.py       - Run basic tests
  softhsm2-util     - SoftHSM management

Examples:
  # List tokens
  list-tokens

  # Initialize token
  init-token 0 MyToken 1234 5678

  # Run tests
  test-hsm.py

  # Use pkcs11-tool
  pkcs11-tool --module /usr/local/lib/softhsm/libsofthsm2.so -L

Configuration:
  Library: /usr/local/lib/softhsm/libsofthsm2.so
  Config:  /etc/softhsm/softhsm2.conf
  Tokens:  /var/lib/softhsm/tokens/

Python PKCS#11:
  import PyKCS11
  pkcs11 = PyKCS11.PyKCS11Lib()
  pkcs11.load("/usr/local/lib/softhsm/libsofthsm2.so")

========================================
EOF

# Show welcome message on startup
RUN echo "cat /etc/motd" >> /root/.bashrc
