#!/bin/bash
# High Availability HSM Configuration Example
# Demonstrates setting up HA for Thales Luna HSM

set -e

echo "====================================================="
echo "High Availability HSM Configuration"
echo "====================================================="

# Configuration
HSM1_IP="10.0.1.10"
HSM2_IP="10.0.1.11"
HA_GROUP_LABEL="Production-HA"

echo ""
echo "Prerequisites:"
echo "  - Two or more Luna HSMs on the network"
echo "  - Luna client installed on this host"
echo "  - Network connectivity to all HSMs"
echo ""

# Check if Luna client is installed
if [ ! -f "/usr/safenet/lunaclient/bin/lunacm" ]; then
    echo "Error: Luna client not installed"
    echo "Install from: https://supportportal.thalesgroup.com"
    exit 1
fi

echo "Step 1: Register HSMs"
echo "-----------------------------------------------------"
echo "Registering HSM 1: $HSM1_IP"
/usr/safenet/lunaclient/bin/vtl addServer -n $HSM1_IP -c /tmp/hsm1.pem
echo "  ✓ HSM 1 registered"

echo "Registering HSM 2: $HSM2_IP"
/usr/safenet/lunaclient/bin/vtl addServer -n $HSM2_IP -c /tmp/hsm2.pem
echo "  ✓ HSM 2 registered"

echo ""
echo "Step 2: Verify Connectivity"
echo "-----------------------------------------------------"
/usr/safenet/lunaclient/bin/vtl verify

echo ""
echo "Step 3: Create HA Group"
echo "-----------------------------------------------------"
echo "Creating HA group: $HA_GROUP_LABEL"

# Note: These commands should be run in lunash (HSM admin shell)
cat << 'EOF' > /tmp/ha-setup.txt
# Run these commands in lunash on HSM1:

lunash:> hagroup createGroup -serialNum <hsm1-serial> -label "Production-HA"
lunash:> hagroup addMember -group "Production-HA" -serialNum <hsm2-serial>
lunash:> hagroup synchronize -group "Production-HA"
lunash:> hagroup autorecovery -group "Production-HA" -enable

# Verify HA status:
lunash:> hagroup show -group "Production-HA"
EOF

echo "HA setup commands saved to /tmp/ha-setup.txt"
echo ""
echo "Manual steps required:"
echo "  1. SSH to primary HSM admin interface"
echo "  2. Run commands from /tmp/ha-setup.txt"
echo "  3. Verify HA synchronization"

echo ""
echo "Step 4: Client Configuration"
echo "-----------------------------------------------------"

cat << 'EOF' > /etc/Chrystoki.conf
# Luna Client Configuration with HA

Chrystoki2 = {
    LibUNIX64 = /usr/safenet/lunaclient/lib/libCryptoki2_64.so;
}

LunaSA Client = {
    ServerTimeout = 10000;
    ReceiveTimeout = 20000;
    NetClient = 1;
    # HA-specific settings
    HAAutoRecover = 1;
    HARecoveryInterval = 60;
}

Luna = {
    DefaultTimeOut = 500000;
    PEDTimeout1 = 100000;
    PEDTimeout2 = 200000;
    PEDTimeout3 = 10000;
}

CardReader = {
    RemoteCommand = 1;
}
EOF

echo "  ✓ Client configuration updated"

echo ""
echo "Step 5: Test HA Failover"
echo "-----------------------------------------------------"

cat << 'EOF' > /tmp/test-ha-failover.py
#!/usr/bin/env python3
"""Test HA failover by simulating HSM failure."""

import PyKCS11
import time

def test_ha_operations(session, key):
    """Perform operations to test HA."""
    data = b"Test data for HA"
    mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)

    for i in range(100):
        try:
            sig = session.sign(key, data, mechanism)
            if i % 10 == 0:
                print(f"  Operation {i}: Success")
            time.sleep(0.1)
        except Exception as e:
            print(f"  Operation {i}: Failed - {e}")
            print("  Waiting for HA recovery...")
            time.sleep(5)

print("Testing HA failover...")
print("Disconnect primary HSM network cable during this test")

pkcs11 = PyKCS11.PyKCS11Lib()
pkcs11.load("/usr/safenet/lunaclient/lib/libCryptoki2_64.so")

session = pkcs11.openSession(0)
session.login("1234")

# Find a key to test with
keys = session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY)])
if keys:
    test_ha_operations(session, keys[0])
else:
    print("No keys found for testing")

session.logout()
session.closeSession()
EOF

chmod +x /tmp/test-ha-failover.py
echo "  ✓ HA failover test script created: /tmp/test-ha-failover.py"

echo ""
echo "====================================================="
echo "HA Configuration Guide Completed"
echo "====================================================="
echo ""
echo "Next Steps:"
echo "  1. Complete HSM-side HA setup (see /tmp/ha-setup.txt)"
echo "  2. Test HA functionality: /tmp/test-ha-failover.py"
echo "  3. Monitor HA status: lunacm > partition showHA"
echo "  4. Configure application connection pooling"
echo ""
echo "HA Benefits:"
echo "  ✓ Automatic failover on HSM failure"
echo "  ✓ Transparent to applications"
echo "  ✓ No single point of failure"
echo "  ✓ Key synchronization across members"
echo ""
