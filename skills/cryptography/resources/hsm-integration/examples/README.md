# HSM Integration Examples

Production-ready examples demonstrating HSM integration patterns.

## Examples

### 01-pkcs11-key-generation.py
PKCS#11 key generation for RSA, EC, and AES keys.

**Usage**:
```bash
# Edit configuration in script
python3 01-pkcs11-key-generation.py
```

**Features**:
- RSA-2048/3072/4096 key generation
- EC P-256/P-384/P-521 key generation
- AES-128/192/256 key generation
- Proper key attributes (sensitive, non-extractable)
- Error handling and cleanup

### 02-aws-cloudhsm-integration.py
AWS CloudHSM integration with PKCS#11.

**Usage**:
```bash
export CLOUDHSM_USER="user1"
export CLOUDHSM_PASSWORD="your-password"
python3 02-aws-cloudhsm-integration.py
```

**Prerequisites**:
- AWS CloudHSM cluster configured
- CloudHSM client installed and configured
- Valid crypto user credentials

**Features**:
- CloudHSM connection management
- Key generation and management
- Digital signatures
- Encryption/decryption
- Key listing and cleanup

### 03-yubihsm-setup.py
YubiHSM 2 setup and basic operations.

**Usage**:
```bash
# Ensure YubiHSM connector is running
sudo systemctl start yubihsm-connector
python3 03-yubihsm-setup.py
```

**Prerequisites**:
- YubiHSM 2 device
- YubiHSM connector service running
- YubiHSM SDK installed

**Features**:
- YubiHSM connection
- Key generation
- Signing operations
- Signature verification

### 04-hsm-backed-ca.py
Certificate Authority with HSM-protected private keys.

**Usage**:
```bash
python3 04-hsm-backed-ca.py
```

**Features**:
- CA key pair generation (4096-bit RSA)
- Self-signed CA certificate
- Certificate issuance from CSR
- HSM-based signing
- Non-extractable CA keys

**Note**: Simplified example for demonstration. Production CA requires proper ASN.1 encoding and full PKCS#11 signing integration.

### 05-code-signing.py
Code signing with HSM-protected keys.

**Usage**:
```bash
python3 05-code-signing.py
```

**Features**:
- Code signing key generation (3072-bit RSA)
- File signing with SHA-256
- Signature verification
- Tamper detection
- Non-extractable signing keys

**Use Cases**:
- Software distribution
- Firmware signing
- Document signing
- Container image signing

### 06-high-availability.sh
High availability configuration for Thales Luna HSM.

**Usage**:
```bash
# Edit configuration variables
bash 06-high-availability.sh
```

**Prerequisites**:
- Two or more Luna HSMs
- Luna client installed
- Network connectivity to HSMs
- HSM admin credentials

**Features**:
- HA group creation
- HSM registration
- Synchronization setup
- Automatic recovery configuration
- Failover testing

**Architecture**:
```
Application
    |
Load Balancer
    |
+---+---+
|       |
HSM-1  HSM-2
(Primary) (Standby)
```

### 07-disaster-recovery.sh
Disaster recovery procedures and testing.

**Usage**:
```bash
bash 07-disaster-recovery.sh
```

**Features**:
- Backup procedures (Luna, CloudHSM)
- Restore procedures
- Recovery testing
- DR runbook generation
- Backup encryption and verification

**Recovery Scenarios**:
- Single HSM failure
- Complete HSM loss
- Key corruption
- Site disaster

**Best Practices**:
- Test backups monthly
- Store backups in multiple locations
- Encrypt backups at rest
- Document procedures
- Conduct DR drills quarterly

### 08-docker-softhsm.dockerfile
Docker container for SoftHSM testing.

**Usage**:
```bash
# Build image
docker build -f 08-docker-softhsm.dockerfile -t softhsm-test .

# Run container
docker run -it --rm softhsm-test

# Inside container
list-tokens
test-hsm.py
```

**Features**:
- Multi-stage build (minimal image)
- SoftHSM built from source
- Python PKCS#11 support
- Pre-configured test token
- Helper scripts included
- Health checks
- Volume for persistent storage

**Useful For**:
- Development and testing
- CI/CD pipelines
- Learning PKCS#11
- Integration testing

## Prerequisites

### General
- Python 3.8+
- PyKCS11: `pip install PyKCS11`
- cryptography: `pip install cryptography`

### Vendor-Specific

**SoftHSM**:
```bash
# Ubuntu/Debian
apt-get install softhsm2

# Red Hat/CentOS
yum install softhsm

# macOS
brew install softhsm
```

**Thales Luna**:
- Luna client software from Thales support portal
- Network connectivity to Luna HSM(s)
- Valid partition credentials

**AWS CloudHSM**:
```bash
# Install client
wget https://s3.amazonaws.com/cloudhsmv2-software/CloudHsmClient/EL7/cloudhsm-client-latest.el7.x86_64.rpm
sudo yum install -y ./cloudhsm-client-latest.el7.x86_64.rpm

# Configure
sudo /opt/cloudhsm/bin/configure -a <cluster-ip>

# Start daemon
sudo systemctl start cloudhsm-client
```

**YubiHSM 2**:
```bash
# Install SDK (Ubuntu/Debian)
wget https://developers.yubico.com/YubiHSM2/Releases/yubihsm2-sdk-2023-01-ubuntu2004-amd64.tar.gz
tar xzf yubihsm2-sdk-*.tar.gz
sudo dpkg -i yubihsm2-sdk/*.deb

# Start connector
sudo systemctl start yubihsm-connector
```

## Configuration

### SoftHSM Configuration
```bash
# /etc/softhsm2.conf
directories.tokendir = /var/lib/softhsm/tokens/
objectstore.backend = file
log.level = INFO
```

### Initialize Test Token
```bash
softhsm2-util --init-token --slot 0 --label "TestToken" --so-pin 1234 --pin 1234
```

### Verify Installation
```bash
# List tokens
softhsm2-util --show-slots

# Test with pkcs11-tool
pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so -L

# Test with Python
python3 -c "import PyKCS11; print('PyKCS11 OK')"
```

## Security Notes

### Production Considerations

1. **PIN Management**:
   - Never hardcode PINs in scripts
   - Use secure credential management (HSM, vault)
   - Rotate PINs regularly
   - Enforce strong PIN policies

2. **Key Attributes**:
   - Always set `CKA_SENSITIVE = True`
   - Always set `CKA_EXTRACTABLE = False`
   - Use `CKA_TOKEN = True` for persistent keys
   - Apply principle of least privilege

3. **Access Control**:
   - Implement role-based access control
   - Separate admin and user roles
   - Audit all HSM access
   - Enable multi-factor authentication

4. **Network Security**:
   - Use TLS for HSM communication
   - Implement network segmentation
   - Firewall rules for HSM access
   - Monitor network traffic

5. **Backup and Recovery**:
   - Test backups regularly
   - Store backups securely (encrypted, offline)
   - Document recovery procedures
   - Conduct DR drills

6. **Compliance**:
   - FIPS 140-2 Level 3 for production
   - PCI-DSS requirements for payment processing
   - HIPAA for healthcare data
   - Regular compliance audits

## Troubleshooting

### Common Issues

**PKCS#11 Library Not Found**:
```bash
# Find library
find / -name "libsofthsm2.so" 2>/dev/null
find / -name "libCryptoki2*.so" 2>/dev/null

# Set LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/usr/lib/softhsm:$LD_LIBRARY_PATH
```

**CKR_SESSION_HANDLE_INVALID**:
- Session expired or closed
- Check session timeout settings
- Implement connection pooling

**CKR_PIN_LOCKED**:
- Too many failed login attempts
- Reset PIN as Security Officer
- Check PIN policy settings

**CKR_DEVICE_ERROR**:
- HSM hardware failure
- Network connectivity issue
- Check HSM status and logs

### Debug Logging

**Enable PKCS#11 Spy**:
```bash
export PKCS11SPY=/usr/lib/softhsm/libsofthsm2.so
export PKCS11SPY_OUTPUT=/tmp/pkcs11-spy.log
LD_PRELOAD=/usr/lib/pkcs11-spy.so python3 your-script.py
```

**CloudHSM Debug**:
```bash
export CLOUDHSM_DEBUG=1
```

**SoftHSM Debug**:
```bash
# Edit /etc/softhsm2.conf
log.level = DEBUG
```

## Performance Tips

1. **Session Reuse**: Open session once, reuse for multiple operations
2. **Connection Pooling**: Maintain pool of sessions for concurrent access
3. **Batch Operations**: Group operations together when possible
4. **Key Caching**: Cache key handles instead of searching repeatedly
5. **Algorithm Selection**: Use ECDSA P-256 for best performance

## Additional Resources

- [PKCS#11 Specification](http://docs.oasis-open.org/pkcs11/pkcs11-base/v2.40/pkcs11-base-v2.40.html)
- [PyKCS11 Documentation](https://github.com/LudovicRousseau/PyKCS11)
- [AWS CloudHSM User Guide](https://docs.aws.amazon.com/cloudhsm/latest/userguide/)
- [Thales Luna Documentation](https://thalesdocs.com/gphsm/luna/)
- [YubiHSM 2 Documentation](https://developers.yubico.com/YubiHSM2/)
- [SoftHSM Project](https://github.com/opendnssec/SoftHSMv2)

## License

These examples are provided for educational purposes. Adapt for your specific use case and security requirements.
