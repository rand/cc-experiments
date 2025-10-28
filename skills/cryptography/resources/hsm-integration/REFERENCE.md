# HSM Integration Reference Guide

## Table of Contents

1. [Overview](#overview)
2. [HSM Fundamentals](#hsm-fundamentals)
3. [PKCS#11 Standard](#pkcs11-standard)
4. [HSM Vendors](#hsm-vendors)
5. [Key Lifecycle Management](#key-lifecycle-management)
6. [Cryptographic Operations](#cryptographic-operations)
7. [High Availability and Clustering](#high-availability-and-clustering)
8. [Compliance and Certification](#compliance-and-certification)
9. [Performance Optimization](#performance-optimization)
10. [Backup and Disaster Recovery](#backup-and-disaster-recovery)
11. [Integration Patterns](#integration-patterns)
12. [Security Best Practices](#security-best-practices)
13. [Troubleshooting](#troubleshooting)
14. [Reference Implementation](#reference-implementation)

## Overview

### What is an HSM?

A Hardware Security Module (HSM) is a dedicated cryptographic processor designed to protect and manage digital keys, perform encryption and decryption functions, and provide strong authentication. HSMs are physical computing devices that safeguard and manage digital keys, perform cryptographic operations, and can be used to strengthen authentication.

**Key Characteristics**:

- **Tamper-resistant**: Physical and logical protections against unauthorized access
- **FIPS 140-2/3 certified**: Government-approved cryptographic modules
- **High performance**: Dedicated hardware acceleration for crypto operations
- **Secure key storage**: Keys never leave the HSM in plaintext
- **Audit logging**: Comprehensive logging of all operations
- **Multi-tenancy**: Support for multiple applications and users

### Why Use HSMs?

**Security Benefits**:
- Keys are generated and stored in tamper-resistant hardware
- Private keys never exist in software-accessible memory
- Cryptographic operations occur within the HSM boundary
- Physical and logical access controls
- Automatic key zeroization on tamper detection

**Compliance Requirements**:
- PCI-DSS: Payment card industry data security
- HIPAA: Healthcare data protection
- GDPR: European data protection regulation
- FIPS 140-2/3: US government cryptographic standards
- Common Criteria: International security evaluation standard

**Use Cases**:
- Public Key Infrastructure (PKI) and Certificate Authorities
- Code signing for software distribution
- Document signing and timestamping
- Database encryption key management
- SSL/TLS certificate private keys
- Cryptocurrency wallet protection
- Payment processing and ATM networks
- Cloud key management services (KMS)

### HSM Deployment Models

**Network-Attached HSMs**:
- Rackmount appliances connected via Ethernet
- Shared across multiple applications
- High throughput and availability
- Examples: Thales Luna Network HSM, Entrust nShield

**PCIe/Internal HSMs**:
- Installed directly in server PCIe slots
- Lower latency, dedicated to single host
- Limited to physical server capacity
- Examples: Thales Luna PCIe HSM, YubiHSM

**Cloud HSMs**:
- Managed HSM services in cloud environments
- Pay-per-use pricing model
- Automatic scaling and high availability
- Examples: AWS CloudHSM, Azure Dedicated HSM, Google Cloud HSM

**USB HSMs**:
- Portable devices for development/testing
- Limited throughput and capacity
- Suitable for code signing and personal use
- Examples: YubiKey, Nitrokey HSM

## HSM Fundamentals

### Hardware Architecture

**Secure Cryptographic Boundary**:
```
┌─────────────────────────────────────────────┐
│          HSM Physical Enclosure             │
│  ┌───────────────────────────────────────┐  │
│  │    Tamper-Resistant Enclosure         │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │   Crypto Processor (ASIC/FPGA)  │  │  │
│  │  │   - AES acceleration            │  │  │
│  │  │   - RSA/ECC operations          │  │  │
│  │  │   - Random number generator     │  │  │
│  │  └─────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │   Secure Key Storage            │  │  │
│  │  │   - Battery-backed RAM          │  │  │
│  │  │   - Encrypted flash             │  │  │
│  │  └─────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │   Security Mechanisms           │  │  │
│  │  │   - Tamper sensors              │  │  │
│  │  │   - Voltage monitors            │  │  │
│  │  │   - Temperature sensors         │  │  │
│  │  │   - Intrusion detection         │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
│           Network Interface                 │
└─────────────────────────────────────────────┘
```

**Key Components**:

1. **Cryptographic Processor**:
   - Dedicated ASIC or FPGA for cryptographic operations
   - Hardware acceleration for AES, RSA, ECC, SHA
   - True random number generator (TRNG)
   - Side-channel attack countermeasures

2. **Secure Memory**:
   - Volatile RAM for temporary key storage (battery-backed)
   - Non-volatile flash for persistent key storage
   - Memory encryption to protect keys at rest
   - Secure deletion and zeroization capabilities

3. **Security Mechanisms**:
   - Physical tamper detection sensors
   - Voltage and clock monitoring
   - Temperature and light sensors
   - Automatic key zeroization on tamper events
   - Secure boot and firmware validation

4. **Interface Controllers**:
   - Network interface (Ethernet)
   - PCIe interface
   - USB interface
   - Serial/console interface for administration

### Security Levels (FIPS 140-2)

**Level 1**: Software and firmware components
- Basic security requirements
- No physical security mechanisms
- Suitable for non-critical applications

**Level 2**: Role-based authentication
- Tamper-evident physical security
- Role-based access control
- Software authentication required
- Suitable for most commercial applications

**Level 3**: Identity-based authentication
- Tamper-resistant physical security
- Identity-based authentication (smart cards, biometrics)
- Physical or logical separation of interfaces
- Zeroization of critical security parameters
- Suitable for high-security applications

**Level 4**: Complete envelope protection
- Penetration protection for all physical access
- Environmental failure protection (temperature, voltage)
- Automatic zeroization on tamper detection
- Suitable for military and government applications

### Trust Models

**M of N Authorization**:
- Requires M out of N administrators to authorize operations
- Split knowledge: No single person has complete access
- Example: 3 of 5 administrators must approve key backup

**Dual Control**:
- Two authorized individuals must be present
- Prevents insider threats
- Common in financial and payment processing

**Separation of Duties**:
- Different roles for key management, auditing, operations
- Prevents any single role from compromising security
- Required for compliance frameworks

## PKCS#11 Standard

### Overview

PKCS#11 (Public-Key Cryptography Standards #11) is the Cryptoki API standard that defines a platform-independent API for cryptographic tokens such as HSMs, smart cards, and software tokens.

**Key Concepts**:

- **Slot**: Physical or logical reader that can contain a token
- **Token**: Logical device that stores cryptographic objects
- **Session**: Logical connection between application and token
- **Object**: Cryptographic key, certificate, or data stored on token
- **Mechanism**: Cryptographic algorithm supported by the token

### PKCS#11 Architecture

```
┌─────────────────────────────────────────────────────┐
│              Application Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │   Java   │  │  Python  │  │  OpenSSL │          │
│  │  (JCA)   │  │  (PKCS11)│  │ (engine) │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
└───────┼────────────┼────────────┼────────────────────┘
        │            │            │
┌───────┴────────────┴────────────┴────────────────────┐
│         PKCS#11 API (Cryptoki)                       │
│  ┌────────────────────────────────────────────────┐  │
│  │  C_Initialize / C_Finalize                     │  │
│  │  C_GetSlotList / C_GetTokenInfo                │  │
│  │  C_OpenSession / C_CloseSession                │  │
│  │  C_Login / C_Logout                            │  │
│  │  C_GenerateKeyPair / C_CreateObject            │  │
│  │  C_Sign / C_Verify / C_Encrypt / C_Decrypt     │  │
│  └────────────────────────────────────────────────┘  │
└───────┬────────────────────────────────────────────┘
        │
┌───────┴────────────────────────────────────────────┐
│         Vendor PKCS#11 Library (.so/.dll)           │
│  ┌────────────────────────────────────────────────┐  │
│  │  Vendor-specific implementation                │  │
│  │  - Luna: Chrystoki (.so)                       │  │
│  │  - SoftHSM: libsofthsm2 (.so)                  │  │
│  │  - AWS CloudHSM: cloudhsm_mgmt_util            │  │
│  └────────────────────────────────────────────────┘  │
└───────┬────────────────────────────────────────────┘
        │
┌───────┴────────────────────────────────────────────┐
│              HSM Hardware/Service                   │
└─────────────────────────────────────────────────────┘
```

### Core PKCS#11 Functions

**Initialization and Termination**:

```c
CK_RV C_Initialize(CK_VOID_PTR pInitArgs);
CK_RV C_Finalize(CK_VOID_PTR pReserved);
CK_RV C_GetInfo(CK_INFO_PTR pInfo);
```

**Slot and Token Management**:

```c
CK_RV C_GetSlotList(
    CK_BBOOL tokenPresent,
    CK_SLOT_ID_PTR pSlotList,
    CK_ULONG_PTR pulCount
);

CK_RV C_GetSlotInfo(
    CK_SLOT_ID slotID,
    CK_SLOT_INFO_PTR pInfo
);

CK_RV C_GetTokenInfo(
    CK_SLOT_ID slotID,
    CK_TOKEN_INFO_PTR pInfo
);

CK_RV C_InitToken(
    CK_SLOT_ID slotID,
    CK_UTF8CHAR_PTR pPin,
    CK_ULONG ulPinLen,
    CK_UTF8CHAR_PTR pLabel
);
```

**Session Management**:

```c
CK_RV C_OpenSession(
    CK_SLOT_ID slotID,
    CK_FLAGS flags,
    CK_VOID_PTR pApplication,
    CK_NOTIFY Notify,
    CK_SESSION_HANDLE_PTR phSession
);

CK_RV C_CloseSession(CK_SESSION_HANDLE hSession);
CK_RV C_CloseAllSessions(CK_SLOT_ID slotID);

CK_RV C_Login(
    CK_SESSION_HANDLE hSession,
    CK_USER_TYPE userType,
    CK_UTF8CHAR_PTR pPin,
    CK_ULONG ulPinLen
);

CK_RV C_Logout(CK_SESSION_HANDLE hSession);
```

**Object Management**:

```c
CK_RV C_CreateObject(
    CK_SESSION_HANDLE hSession,
    CK_ATTRIBUTE_PTR pTemplate,
    CK_ULONG ulCount,
    CK_OBJECT_HANDLE_PTR phObject
);

CK_RV C_DestroyObject(
    CK_SESSION_HANDLE hSession,
    CK_OBJECT_HANDLE hObject
);

CK_RV C_FindObjectsInit(
    CK_SESSION_HANDLE hSession,
    CK_ATTRIBUTE_PTR pTemplate,
    CK_ULONG ulCount
);

CK_RV C_FindObjects(
    CK_SESSION_HANDLE hSession,
    CK_OBJECT_HANDLE_PTR phObject,
    CK_ULONG ulMaxObjectCount,
    CK_ULONG_PTR pulObjectCount
);

CK_RV C_FindObjectsFinal(CK_SESSION_HANDLE hSession);
```

**Key Generation**:

```c
CK_RV C_GenerateKey(
    CK_SESSION_HANDLE hSession,
    CK_MECHANISM_PTR pMechanism,
    CK_ATTRIBUTE_PTR pTemplate,
    CK_ULONG ulCount,
    CK_OBJECT_HANDLE_PTR phKey
);

CK_RV C_GenerateKeyPair(
    CK_SESSION_HANDLE hSession,
    CK_MECHANISM_PTR pMechanism,
    CK_ATTRIBUTE_PTR pPublicKeyTemplate,
    CK_ULONG ulPublicKeyAttributeCount,
    CK_ATTRIBUTE_PTR pPrivateKeyTemplate,
    CK_ULONG ulPrivateKeyAttributeCount,
    CK_OBJECT_HANDLE_PTR phPublicKey,
    CK_OBJECT_HANDLE_PTR phPrivateKey
);
```

**Cryptographic Operations**:

```c
// Signing
CK_RV C_SignInit(
    CK_SESSION_HANDLE hSession,
    CK_MECHANISM_PTR pMechanism,
    CK_OBJECT_HANDLE hKey
);

CK_RV C_Sign(
    CK_SESSION_HANDLE hSession,
    CK_BYTE_PTR pData,
    CK_ULONG ulDataLen,
    CK_BYTE_PTR pSignature,
    CK_ULONG_PTR pulSignatureLen
);

// Verification
CK_RV C_VerifyInit(
    CK_SESSION_HANDLE hSession,
    CK_MECHANISM_PTR pMechanism,
    CK_OBJECT_HANDLE hKey
);

CK_RV C_Verify(
    CK_SESSION_HANDLE hSession,
    CK_BYTE_PTR pData,
    CK_ULONG ulDataLen,
    CK_BYTE_PTR pSignature,
    CK_ULONG ulSignatureLen
);

// Encryption
CK_RV C_EncryptInit(
    CK_SESSION_HANDLE hSession,
    CK_MECHANISM_PTR pMechanism,
    CK_OBJECT_HANDLE hKey
);

CK_RV C_Encrypt(
    CK_SESSION_HANDLE hSession,
    CK_BYTE_PTR pData,
    CK_ULONG ulDataLen,
    CK_BYTE_PTR pEncryptedData,
    CK_ULONG_PTR pulEncryptedDataLen
);

// Decryption
CK_RV C_DecryptInit(
    CK_SESSION_HANDLE hSession,
    CK_MECHANISM_PTR pMechanism,
    CK_OBJECT_HANDLE hKey
);

CK_RV C_Decrypt(
    CK_SESSION_HANDLE hSession,
    CK_BYTE_PTR pEncryptedData,
    CK_ULONG ulEncryptedDataLen,
    CK_BYTE_PTR pData,
    CK_ULONG_PTR pulDataLen
);
```

### PKCS#11 Object Attributes

**Common Attributes**:

```c
CK_ATTRIBUTE template[] = {
    {CKA_CLASS, &class, sizeof(class)},           // Object class
    {CKA_TOKEN, &token, sizeof(token)},           // Token object vs session
    {CKA_PRIVATE, &private, sizeof(private)},     // Private object
    {CKA_LABEL, label, strlen(label)},            // Human-readable label
    {CKA_ID, id, id_len},                         // Object identifier
    {CKA_KEY_TYPE, &keyType, sizeof(keyType)},    // Key type (RSA, AES, etc)
};
```

**Key Attributes**:

- `CKA_ENCRYPT`: Key can be used for encryption
- `CKA_DECRYPT`: Key can be used for decryption
- `CKA_SIGN`: Key can be used for signing
- `CKA_VERIFY`: Key can be used for verification
- `CKA_WRAP`: Key can be used to wrap other keys
- `CKA_UNWRAP`: Key can be used to unwrap other keys
- `CKA_DERIVE`: Key can be used for key derivation
- `CKA_EXTRACTABLE`: Key can be extracted from token
- `CKA_SENSITIVE`: Key is sensitive and cannot be revealed
- `CKA_ALWAYS_SENSITIVE`: Key has always been sensitive
- `CKA_NEVER_EXTRACTABLE`: Key has never been extractable
- `CKA_MODIFIABLE`: Object attributes can be modified

**RSA Key Attributes**:

```c
// Public key
CK_ATTRIBUTE rsaPublicKeyTemplate[] = {
    {CKA_CLASS, &publicKeyClass, sizeof(publicKeyClass)},
    {CKA_KEY_TYPE, &rsaKeyType, sizeof(rsaKeyType)},
    {CKA_ENCRYPT, &true, sizeof(true)},
    {CKA_VERIFY, &true, sizeof(true)},
    {CKA_WRAP, &true, sizeof(true)},
    {CKA_MODULUS_BITS, &modulusBits, sizeof(modulusBits)},
    {CKA_PUBLIC_EXPONENT, publicExponent, sizeof(publicExponent)},
    {CKA_LABEL, "RSA Public Key", 14},
};

// Private key
CK_ATTRIBUTE rsaPrivateKeyTemplate[] = {
    {CKA_CLASS, &privateKeyClass, sizeof(privateKeyClass)},
    {CKA_KEY_TYPE, &rsaKeyType, sizeof(rsaKeyType)},
    {CKA_DECRYPT, &true, sizeof(true)},
    {CKA_SIGN, &true, sizeof(true)},
    {CKA_UNWRAP, &true, sizeof(true)},
    {CKA_SENSITIVE, &true, sizeof(true)},
    {CKA_EXTRACTABLE, &false, sizeof(false)},
    {CKA_LABEL, "RSA Private Key", 15},
};
```

**AES Key Attributes**:

```c
CK_ATTRIBUTE aesKeyTemplate[] = {
    {CKA_CLASS, &secretKeyClass, sizeof(secretKeyClass)},
    {CKA_KEY_TYPE, &aesKeyType, sizeof(aesKeyType)},
    {CKA_ENCRYPT, &true, sizeof(true)},
    {CKA_DECRYPT, &true, sizeof(true)},
    {CKA_WRAP, &true, sizeof(true)},
    {CKA_UNWRAP, &true, sizeof(true)},
    {CKA_SENSITIVE, &true, sizeof(true)},
    {CKA_EXTRACTABLE, &false, sizeof(false)},
    {CKA_VALUE_LEN, &keyLen, sizeof(keyLen)},
    {CKA_LABEL, "AES Key", 7},
};
```

### PKCS#11 Mechanisms

**Signature Mechanisms**:

- `CKM_RSA_PKCS`: RSA signature with PKCS#1 v1.5 padding
- `CKM_RSA_PKCS_PSS`: RSA signature with PSS padding
- `CKM_SHA256_RSA_PKCS`: RSA signature with SHA-256 hash
- `CKM_ECDSA`: ECDSA signature
- `CKM_ECDSA_SHA256`: ECDSA signature with SHA-256 hash

**Encryption Mechanisms**:

- `CKM_RSA_PKCS`: RSA encryption with PKCS#1 v1.5 padding
- `CKM_RSA_PKCS_OAEP`: RSA encryption with OAEP padding
- `CKM_AES_ECB`: AES encryption in ECB mode
- `CKM_AES_CBC`: AES encryption in CBC mode
- `CKM_AES_CBC_PAD`: AES encryption in CBC mode with padding
- `CKM_AES_GCM`: AES encryption in GCM mode
- `CKM_AES_KEY_WRAP`: AES key wrapping (RFC 3394)

**Key Generation Mechanisms**:

- `CKM_RSA_PKCS_KEY_PAIR_GEN`: RSA key pair generation
- `CKM_EC_KEY_PAIR_GEN`: ECC key pair generation
- `CKM_AES_KEY_GEN`: AES key generation
- `CKM_GENERIC_SECRET_KEY_GEN`: Generic secret key generation

**Key Derivation Mechanisms**:

- `CKM_ECDH1_DERIVE`: ECDH key derivation
- `CKM_SHA256_HMAC`: HMAC-SHA256
- `CKM_PBKDF2`: Password-based key derivation

### Session Types

**Read-Only Sessions**:
```c
CK_FLAGS flags = CKF_SERIAL_SESSION;  // Read-only session
```

**Read-Write Sessions**:
```c
CK_FLAGS flags = CKF_SERIAL_SESSION | CKF_RW_SESSION;  // Read-write session
```

**User Types**:

- `CKU_SO`: Security Officer (admin)
- `CKU_USER`: Normal user
- `CKU_CONTEXT_SPECIFIC`: Context-specific authentication

### Error Handling

**Common Return Values**:

```c
CK_RV rv;

if (rv == CKR_OK) {
    // Success
} else if (rv == CKR_PIN_INCORRECT) {
    // Incorrect PIN
} else if (rv == CKR_USER_NOT_LOGGED_IN) {
    // User must log in first
} else if (rv == CKR_SESSION_HANDLE_INVALID) {
    // Invalid session handle
} else if (rv == CKR_DEVICE_ERROR) {
    // Device error
} else if (rv == CKR_FUNCTION_FAILED) {
    // General failure
}
```

**Common Error Codes**:

- `CKR_OK`: Success
- `CKR_HOST_MEMORY`: Host memory allocation failed
- `CKR_SLOT_ID_INVALID`: Invalid slot ID
- `CKR_TOKEN_NOT_PRESENT`: Token not present in slot
- `CKR_SESSION_CLOSED`: Session closed
- `CKR_PIN_INCORRECT`: Incorrect PIN
- `CKR_PIN_LOCKED`: PIN locked due to too many failed attempts
- `CKR_USER_ALREADY_LOGGED_IN`: User already logged in
- `CKR_USER_NOT_LOGGED_IN`: User not logged in
- `CKR_KEY_HANDLE_INVALID`: Invalid key handle
- `CKR_SIGNATURE_INVALID`: Signature verification failed
- `CKR_MECHANISM_INVALID`: Invalid mechanism
- `CKR_OBJECT_HANDLE_INVALID`: Invalid object handle

## HSM Vendors

### Thales Luna HSMs

**Product Line**:

- **Luna Network HSM**: Network-attached appliance (1U rackmount)
- **Luna PCIe HSM**: PCIe card for direct server attachment
- **Luna USB HSM**: Portable USB device
- **Luna Cloud HSM**: Cloud-deployed virtual HSM
- **Luna HSM as a Service**: Managed cloud service

**Key Features**:

- FIPS 140-2 Level 3 certified
- High-performance cryptographic operations (10,000+ RSA-2048 ops/sec)
- Support for clustering and high availability
- Comprehensive PKCS#11 support
- Java (JCA/JCE), .NET, and OpenSSL integration
- Remote administration and monitoring

**PKCS#11 Library**:

```bash
# Linux library path
/usr/safenet/lunaclient/lib/libCryptoki2_64.so

# Configuration file
/etc/Chrystoki.conf
```

**Configuration Example**:

```conf
# /etc/Chrystoki.conf
Chrystoki2 = {
    LibUNIX64 = /usr/safenet/lunaclient/lib/libCryptoki2_64.so;
}

LunaSA Client = {
    ServerTimeout = 10000;
    ReceiveTimeout = 20000;
}

Luna = {
    DefaultTimeOut = 500000;
    PEDTimeout1 = 100000;
    PEDTimeout2 = 200000;
    PEDTimeout3 = 10000;
}
```

**Slot Configuration**:

```bash
# List available slots
/usr/safenet/lunaclient/bin/vtl verify

# Assign slot to partition
/usr/safenet/lunaclient/bin/lunacm
lunacm:> slot list
lunacm:> slot set -slot 0
```

**Typical Pricing**:
- Luna Network HSM 7: $20,000 - $40,000 (one-time)
- Luna PCIe HSM: $10,000 - $20,000 (one-time)
- Luna Cloud HSM: $1.50 - $3.00 per hour

### AWS CloudHSM

**Overview**:

AWS CloudHSM is a cloud-based HSM service that provides dedicated hardware security modules in the AWS Cloud. It meets corporate, contractual, and regulatory compliance requirements for data security by using dedicated FIPS 140-2 Level 3 validated HSMs.

**Key Features**:

- FIPS 140-2 Level 3 validated
- Dedicated single-tenant HSM instances
- Automatic backups and high availability
- Integration with AWS services (KMS, RDS, S3)
- Standard PKCS#11, JCE, and CNG APIs
- Pay-per-use pricing model

**Architecture**:

```
┌─────────────────────────────────────────────────────┐
│                   AWS Region                        │
│  ┌───────────────────────────────────────────────┐  │
│  │              VPC (Customer)                   │  │
│  │  ┌─────────────┐         ┌─────────────┐      │  │
│  │  │ Application │◄────────┤ CloudHSM    │      │  │
│  │  │   Server    │         │   Client    │      │  │
│  │  └─────────────┘         └──────┬──────┘      │  │
│  │                                 │              │  │
│  │  ┌──────────────────────────────┼──────────┐  │  │
│  │  │    CloudHSM Cluster          │          │  │  │
│  │  │  ┌─────────┐  ┌─────────┐  ┌┴────────┐ │  │  │
│  │  │  │ HSM-1   │  │ HSM-2   │  │ HSM-3   │ │  │  │
│  │  │  │  AZ-1   │  │  AZ-2   │  │  AZ-3   │ │  │  │
│  │  │  └─────────┘  └─────────┘  └─────────┘ │  │  │
│  │  └──────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Setup Process**:

```bash
# 1. Create CloudHSM cluster
aws cloudhsmv2 create-cluster \
    --hsm-type hsm1.medium \
    --subnet-ids subnet-12345678 subnet-87654321

# 2. Initialize cluster
aws cloudhsmv2 create-hsm \
    --cluster-id cluster-abc123 \
    --availability-zone us-east-1a

# 3. Install CloudHSM client
wget https://s3.amazonaws.com/cloudhsmv2-software/CloudHsmClient/EL7/cloudhsm-client-latest.el7.x86_64.rpm
sudo yum install -y ./cloudhsm-client-latest.el7.x86_64.rpm

# 4. Configure client
sudo /opt/cloudhsm/bin/configure -a <cluster-HSM-IP>

# 5. Start client daemon
sudo systemctl start cloudhsm-client
```

**PKCS#11 Library**:

```bash
# Library path
/opt/cloudhsm/lib/libcloudhsm_pkcs11.so

# Configuration
/opt/cloudhsm/etc/cloudhsm_client.cfg
```

**Cluster Management**:

```bash
# Connect to CloudHSM CLI
/opt/cloudhsm/bin/cloudhsm_mgmt_util /opt/cloudhsm/etc/cloudhsm_mgmt_util.cfg

# List users
cloudhsm> listUsers

# Create user
cloudhsm> createUser CU user1 password123

# Login
cloudhsm> loginHSM CU admin password
```

**Pricing**:
- $1.60 per hour per HSM instance
- Data transfer charges apply
- Automatic backups included

### YubiHSM 2

**Overview**:

YubiHSM 2 is a portable USB HSM designed for small to medium deployments. It provides a cost-effective solution for key management, code signing, and cryptographic operations.

**Key Features**:

- FIPS 140-2 Level 3 certified
- USB-A and USB-C form factors
- Compact and portable design
- Support for RSA, ECC, AES, HMAC
- Domain separation for multi-tenancy
- Audit logging and key attestation

**Specifications**:

- RSA-2048 signing: 800 ops/sec
- ECDSA P-256 signing: 1,100 ops/sec
- AES-128 encryption: 40 MB/sec
- Key storage: Up to 256 objects
- Physical dimensions: 18mm x 45mm x 3mm

**PKCS#11 Library**:

```bash
# Library path (Linux)
/usr/lib/x86_64-linux-gnu/pkcs11/yubihsm_pkcs11.so

# Configuration
/etc/yubihsm_pkcs11.conf
```

**Configuration Example**:

```yaml
# /etc/yubihsm_pkcs11.conf
connector = http://127.0.0.1:12345
debug = false
libdebug = false
dinout = false
```

**Setup Process**:

```bash
# 1. Install YubiHSM software
wget https://developers.yubico.com/YubiHSM2/Releases/yubihsm2-sdk-2023-01-ubuntu2004-amd64.tar.gz
tar xzf yubihsm2-sdk-*.tar.gz
sudo dpkg -i yubihsm2-sdk/*.deb

# 2. Start connector service
sudo systemctl start yubihsm-connector
sudo systemctl enable yubihsm-connector

# 3. Test connection
yubihsm-shell --connector http://127.0.0.1:12345

# 4. Change default authentication key
yubihsm> connect
yubihsm> session open 1 password
yubihsm> put authkey 0 0 new-auth-key 1 all all all all password:new-password
yubihsm> session close
```

**Pricing**:
- YubiHSM 2 (USB-A): $650
- YubiHSM 2 FIPS: $850
- SDK and connector software: Free

### SoftHSM

**Overview**:

SoftHSM is an open-source software implementation of a cryptographic store accessible through a PKCS#11 interface. It is primarily used for development, testing, and non-production environments.

**Key Features**:

- Open-source (BSD license)
- PKCS#11 v2.20 compliant
- Support for RSA, ECC, AES, DES, HMAC
- Multiple token support
- Cross-platform (Linux, macOS, Windows)
- No hardware required

**Limitations**:

- Not FIPS certified
- Keys stored in software (encrypted files)
- No tamper resistance
- Not suitable for production use

**Installation**:

```bash
# Ubuntu/Debian
sudo apt-get install softhsm2

# Red Hat/CentOS
sudo yum install softhsm

# macOS
brew install softhsm

# Build from source
git clone https://github.com/opendnssec/SoftHSMv2.git
cd SoftHSMv2
./configure --prefix=/usr/local
make
sudo make install
```

**Configuration**:

```bash
# Configuration file
/etc/softhsm2.conf

# Example configuration
cat > /etc/softhsm2.conf << EOF
directories.tokendir = /var/lib/softhsm/tokens/
objectstore.backend = file
log.level = INFO
EOF
```

**Token Management**:

```bash
# Initialize token
softhsm2-util --init-token --slot 0 --label "Test Token" --so-pin 1234 --pin 5678

# List tokens
softhsm2-util --show-slots

# Import key
softhsm2-util --import key.pem --slot 0 --label "Imported Key" --id A1B2 --pin 5678

# Delete token
softhsm2-util --delete-token --token "Test Token"
```

**PKCS#11 Library**:

```bash
# Linux
/usr/lib/softhsm/libsofthsm2.so

# macOS
/usr/local/lib/softhsm/libsofthsm2.so
```

### Comparison Matrix

| Feature | Thales Luna | AWS CloudHSM | YubiHSM 2 | SoftHSM |
|---------|-------------|--------------|-----------|---------|
| FIPS 140-2 Level | 3 | 3 | 3 | None |
| Form Factor | Network/PCIe | Cloud | USB | Software |
| RSA-2048 Sign/sec | 10,000+ | 2,000+ | 800 | 1,000+ |
| High Availability | Yes | Yes | No | No |
| Multi-tenancy | Yes | Yes | Limited | Limited |
| Price Range | $10k-$40k | $1.60/hr | $650-$850 | Free |
| Production Use | Yes | Yes | Small-scale | No |
| Key Backup | Yes | Automatic | Manual | File-based |

## Key Lifecycle Management

### Key Generation

**Generation Requirements**:

1. **Entropy Source**: Use hardware TRNG in HSM
2. **Key Parameters**: Specify algorithm, key size, attributes
3. **Access Control**: Define who can use the key
4. **Audit Logging**: Record key creation event

**RSA Key Generation**:

```c
CK_MECHANISM mechanism = {CKM_RSA_PKCS_KEY_PAIR_GEN, NULL_PTR, 0};
CK_ULONG modulusBits = 2048;
CK_BYTE publicExponent[] = {0x01, 0x00, 0x01};  // 65537

CK_ATTRIBUTE publicKeyTemplate[] = {
    {CKA_ENCRYPT, &true, sizeof(true)},
    {CKA_VERIFY, &true, sizeof(true)},
    {CKA_WRAP, &true, sizeof(true)},
    {CKA_MODULUS_BITS, &modulusBits, sizeof(modulusBits)},
    {CKA_PUBLIC_EXPONENT, publicExponent, sizeof(publicExponent)},
    {CKA_LABEL, "RSA-2048 Public", 15},
};

CK_ATTRIBUTE privateKeyTemplate[] = {
    {CKA_TOKEN, &true, sizeof(true)},
    {CKA_PRIVATE, &true, sizeof(true)},
    {CKA_SENSITIVE, &true, sizeof(true)},
    {CKA_DECRYPT, &true, sizeof(true)},
    {CKA_SIGN, &true, sizeof(true)},
    {CKA_UNWRAP, &true, sizeof(true)},
    {CKA_EXTRACTABLE, &false, sizeof(false)},
    {CKA_LABEL, "RSA-2048 Private", 16},
};

CK_OBJECT_HANDLE hPublicKey, hPrivateKey;
CK_RV rv = C_GenerateKeyPair(
    hSession,
    &mechanism,
    publicKeyTemplate, sizeof(publicKeyTemplate) / sizeof(CK_ATTRIBUTE),
    privateKeyTemplate, sizeof(privateKeyTemplate) / sizeof(CK_ATTRIBUTE),
    &hPublicKey,
    &hPrivateKey
);
```

**ECC Key Generation**:

```c
CK_MECHANISM mechanism = {CKM_EC_KEY_PAIR_GEN, NULL_PTR, 0};

// P-256 curve OID: 1.2.840.10045.3.1.7
CK_BYTE ecParams[] = {
    0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x03, 0x01, 0x07
};

CK_ATTRIBUTE publicKeyTemplate[] = {
    {CKA_VERIFY, &true, sizeof(true)},
    {CKA_EC_PARAMS, ecParams, sizeof(ecParams)},
    {CKA_LABEL, "ECC-P256 Public", 15},
};

CK_ATTRIBUTE privateKeyTemplate[] = {
    {CKA_TOKEN, &true, sizeof(true)},
    {CKA_PRIVATE, &true, sizeof(true)},
    {CKA_SENSITIVE, &true, sizeof(true)},
    {CKA_SIGN, &true, sizeof(true)},
    {CKA_EXTRACTABLE, &false, sizeof(false)},
    {CKA_LABEL, "ECC-P256 Private", 16},
};
```

**AES Key Generation**:

```c
CK_MECHANISM mechanism = {CKM_AES_KEY_GEN, NULL_PTR, 0};
CK_ULONG keyLen = 32;  // 256-bit key

CK_ATTRIBUTE keyTemplate[] = {
    {CKA_TOKEN, &true, sizeof(true)},
    {CKA_PRIVATE, &true, sizeof(true)},
    {CKA_SENSITIVE, &true, sizeof(true)},
    {CKA_ENCRYPT, &true, sizeof(true)},
    {CKA_DECRYPT, &true, sizeof(true)},
    {CKA_WRAP, &true, sizeof(true)},
    {CKA_UNWRAP, &true, sizeof(true)},
    {CKA_EXTRACTABLE, &false, sizeof(false)},
    {CKA_VALUE_LEN, &keyLen, sizeof(keyLen)},
    {CKA_LABEL, "AES-256 Key", 11},
};

CK_OBJECT_HANDLE hKey;
CK_RV rv = C_GenerateKey(
    hSession,
    &mechanism,
    keyTemplate, sizeof(keyTemplate) / sizeof(CK_ATTRIBUTE),
    &hKey
);
```

### Key Storage

**Token Objects vs Session Objects**:

- **Token Objects**: Persistent, survive session close, stored on HSM
- **Session Objects**: Temporary, deleted when session closes

```c
CK_BBOOL tokenObject = CK_TRUE;   // Persistent
CK_BBOOL sessionObject = CK_FALSE;  // Temporary

CK_ATTRIBUTE template[] = {
    {CKA_TOKEN, &tokenObject, sizeof(tokenObject)},
    // ... other attributes
};
```

**Private Objects**:

```c
CK_BBOOL privateObject = CK_TRUE;  // Requires login to access

CK_ATTRIBUTE template[] = {
    {CKA_PRIVATE, &privateObject, sizeof(privateObject)},
    // ... other attributes
};
```

**Key Labeling and Identification**:

```c
// Human-readable label
char label[] = "Payment Processing Key 2024";

// Unique identifier (binary)
CK_BYTE keyId[] = {0x01, 0x02, 0x03, 0x04};

CK_ATTRIBUTE template[] = {
    {CKA_LABEL, label, strlen(label)},
    {CKA_ID, keyId, sizeof(keyId)},
    // ... other attributes
};
```

### Key Import and Export

**Key Import (Wrapping)**:

```c
// Step 1: Generate or obtain wrapping key in HSM
CK_OBJECT_HANDLE hWrappingKey;

// Step 2: Wrap external key using wrapping key
CK_MECHANISM wrapMechanism = {CKM_AES_KEY_WRAP, NULL_PTR, 0};
CK_BYTE wrappedKey[256];
CK_ULONG wrappedKeyLen = sizeof(wrappedKey);

CK_RV rv = C_WrapKey(
    hSession,
    &wrapMechanism,
    hWrappingKey,
    hExternalKey,
    wrappedKey,
    &wrappedKeyLen
);

// Step 3: Unwrap into HSM
CK_ATTRIBUTE unwrapTemplate[] = {
    {CKA_CLASS, &secretKeyClass, sizeof(secretKeyClass)},
    {CKA_KEY_TYPE, &aesKeyType, sizeof(aesKeyType)},
    {CKA_ENCRYPT, &true, sizeof(true)},
    {CKA_DECRYPT, &true, sizeof(true)},
    {CKA_SENSITIVE, &true, sizeof(true)},
    {CKA_EXTRACTABLE, &false, sizeof(false)},
};

CK_OBJECT_HANDLE hImportedKey;
rv = C_UnwrapKey(
    hSession,
    &wrapMechanism,
    hWrappingKey,
    wrappedKey,
    wrappedKeyLen,
    unwrapTemplate, sizeof(unwrapTemplate) / sizeof(CK_ATTRIBUTE),
    &hImportedKey
);
```

**Key Export**:

```c
// Keys marked as CKA_EXTRACTABLE can be exported
// However, best practice is to never allow key export

CK_BBOOL extractable = CK_FALSE;  // Recommended
CK_ATTRIBUTE template[] = {
    {CKA_EXTRACTABLE, &extractable, sizeof(extractable)},
    // ... other attributes
};
```

### Key Rotation

**Rotation Strategies**:

1. **Time-based**: Rotate keys after fixed period (e.g., annually)
2. **Usage-based**: Rotate after N operations or bytes encrypted
3. **Event-based**: Rotate after security incident or personnel change

**Rotation Process**:

```
1. Generate new key in HSM
2. Update applications to use new key for encryption
3. Keep old key for decryption of existing data
4. Re-encrypt data with new key (optional)
5. Retire old key after grace period
6. Delete or archive old key
```

**Implementation Example**:

```python
def rotate_key(hsm_session, old_key_label, new_key_label):
    """Rotate encryption key."""
    # Generate new key
    new_key = hsm_session.generate_key(
        mechanism=Mechanism.AES_KEY_GEN,
        attributes={
            Attribute.LABEL: new_key_label,
            Attribute.ENCRYPT: True,
            Attribute.DECRYPT: True,
            Attribute.SENSITIVE: True,
            Attribute.EXTRACTABLE: False,
        }
    )

    # Mark old key as decrypt-only
    old_key = hsm_session.find_key(label=old_key_label)
    old_key.set_attributes({
        Attribute.ENCRYPT: False,  # Disable encryption
        Attribute.LABEL: f"{old_key_label}-retired-{datetime.now().isoformat()}",
    })

    # Update application configuration
    update_config(active_key_label=new_key_label)

    return new_key
```

### Key Destruction

**Secure Deletion**:

```c
// Mark key for deletion
CK_RV rv = C_DestroyObject(hSession, hKey);

// HSM performs:
// 1. Zeroize key material in memory
// 2. Mark storage as deleted
// 3. Overwrite storage with random data
// 4. Log destruction event
```

**Key Archival vs Destruction**:

- **Destruction**: Permanently delete key, unrecoverable
- **Archival**: Store encrypted backup for compliance/recovery

**Retention Policies**:

```python
class KeyRetentionPolicy:
    """Key retention policy."""

    IMMEDIATE = 0      # Delete immediately
    SHORT = 30         # 30 days
    MEDIUM = 90        # 90 days
    LONG = 365         # 1 year
    COMPLIANCE = 2555  # 7 years (regulatory requirement)
```

## Cryptographic Operations

### Digital Signatures

**RSA-PSS Signing**:

```c
// Initialize signing operation
CK_RSA_PKCS_PSS_PARAMS pssParams = {
    .hashAlg = CKM_SHA256,
    .mgf = CKG_MGF1_SHA256,
    .sLen = 32  // Salt length equals hash length
};

CK_MECHANISM mechanism = {
    CKM_SHA256_RSA_PKCS_PSS,
    &pssParams,
    sizeof(pssParams)
};

CK_RV rv = C_SignInit(hSession, &mechanism, hPrivateKey);

// Sign data
CK_BYTE data[] = "Message to sign";
CK_BYTE signature[256];
CK_ULONG signatureLen = sizeof(signature);

rv = C_Sign(
    hSession,
    data, sizeof(data),
    signature, &signatureLen
);
```

**ECDSA Signing**:

```c
CK_MECHANISM mechanism = {CKM_ECDSA_SHA256, NULL_PTR, 0};

CK_RV rv = C_SignInit(hSession, &mechanism, hPrivateKey);

CK_BYTE data[] = "Message to sign";
CK_BYTE signature[64];  // P-256 signature is 64 bytes
CK_ULONG signatureLen = sizeof(signature);

rv = C_Sign(
    hSession,
    data, sizeof(data),
    signature, &signatureLen
);
```

**Multi-Part Signing** (for large data):

```c
CK_MECHANISM mechanism = {CKM_SHA256_RSA_PKCS, NULL_PTR, 0};

rv = C_SignInit(hSession, &mechanism, hPrivateKey);

// Process data in chunks
for (each chunk) {
    rv = C_SignUpdate(hSession, chunk, chunkLen);
}

// Finalize signature
CK_BYTE signature[256];
CK_ULONG signatureLen = sizeof(signature);
rv = C_SignFinal(hSession, signature, &signatureLen);
```

### Signature Verification

**RSA-PSS Verification**:

```c
CK_RSA_PKCS_PSS_PARAMS pssParams = {
    .hashAlg = CKM_SHA256,
    .mgf = CKG_MGF1_SHA256,
    .sLen = 32
};

CK_MECHANISM mechanism = {
    CKM_SHA256_RSA_PKCS_PSS,
    &pssParams,
    sizeof(pssParams)
};

CK_RV rv = C_VerifyInit(hSession, &mechanism, hPublicKey);

rv = C_Verify(
    hSession,
    data, dataLen,
    signature, signatureLen
);

if (rv == CKR_OK) {
    // Signature valid
} else if (rv == CKR_SIGNATURE_INVALID) {
    // Signature invalid
}
```

### Encryption and Decryption

**RSA-OAEP Encryption**:

```c
CK_RSA_PKCS_OAEP_PARAMS oaepParams = {
    .hashAlg = CKM_SHA256,
    .mgf = CKG_MGF1_SHA256,
    .source = CKZ_DATA_SPECIFIED,
    .pSourceData = NULL,
    .ulSourceDataLen = 0
};

CK_MECHANISM mechanism = {
    CKM_RSA_PKCS_OAEP,
    &oaepParams,
    sizeof(oaepParams)
};

// Encrypt
CK_RV rv = C_EncryptInit(hSession, &mechanism, hPublicKey);

CK_BYTE plaintext[] = "Secret message";
CK_BYTE ciphertext[256];
CK_ULONG ciphertextLen = sizeof(ciphertext);

rv = C_Encrypt(
    hSession,
    plaintext, sizeof(plaintext),
    ciphertext, &ciphertextLen
);

// Decrypt
rv = C_DecryptInit(hSession, &mechanism, hPrivateKey);

CK_BYTE decrypted[256];
CK_ULONG decryptedLen = sizeof(decrypted);

rv = C_Decrypt(
    hSession,
    ciphertext, ciphertextLen,
    decrypted, &decryptedLen
);
```

**AES-GCM Encryption**:

```c
CK_GCM_PARAMS gcmParams = {
    .pIv = iv,
    .ulIvLen = 12,  // 96-bit IV
    .pAAD = aad,
    .ulAADLen = aadLen,
    .ulTagBits = 128  // 128-bit authentication tag
};

CK_MECHANISM mechanism = {
    CKM_AES_GCM,
    &gcmParams,
    sizeof(gcmParams)
};

// Encrypt
CK_RV rv = C_EncryptInit(hSession, &mechanism, hKey);

CK_BYTE plaintext[] = "Secret message";
CK_BYTE ciphertext[256];
CK_ULONG ciphertextLen = sizeof(ciphertext);

rv = C_Encrypt(
    hSession,
    plaintext, sizeof(plaintext),
    ciphertext, &ciphertextLen
);

// Ciphertext includes authentication tag
// Tag is appended to end of ciphertext
```

### Key Wrapping

**AES Key Wrap (RFC 3394)**:

```c
CK_MECHANISM mechanism = {CKM_AES_KEY_WRAP, NULL_PTR, 0};

// Wrap key
CK_RV rv = C_WrapKey(
    hSession,
    &mechanism,
    hWrappingKey,    // KEK (Key Encryption Key)
    hKeyToWrap,      // Key to wrap
    wrappedKey,      // Output buffer
    &wrappedKeyLen   // Output length
);

// Unwrap key
CK_ATTRIBUTE unwrapTemplate[] = {
    {CKA_CLASS, &secretKeyClass, sizeof(secretKeyClass)},
    {CKA_KEY_TYPE, &aesKeyType, sizeof(aesKeyType)},
    {CKA_ENCRYPT, &true, sizeof(true)},
    {CKA_DECRYPT, &true, sizeof(true)},
};

CK_OBJECT_HANDLE hUnwrappedKey;
rv = C_UnwrapKey(
    hSession,
    &mechanism,
    hWrappingKey,
    wrappedKey,
    wrappedKeyLen,
    unwrapTemplate, sizeof(unwrapTemplate) / sizeof(CK_ATTRIBUTE),
    &hUnwrappedKey
);
```

### Random Number Generation

**Generate Random Bytes**:

```c
CK_BYTE randomBytes[32];
CK_RV rv = C_GenerateRandom(hSession, randomBytes, sizeof(randomBytes));

// Use for:
// - Encryption IVs
// - Salt values
// - Session keys
// - Nonces
```

## High Availability and Clustering

### Clustering Architecture

**Load Balancing**:

```
                    ┌──────────────┐
                    │ Load Balancer│
                    │  (HAProxy)   │
                    └──────┬───────┘
                           │
        ┏━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━┓
        ┃                                    ┃
┌───────┴────────┐                  ┌────────┴───────┐
│   HSM Node 1   │                  │   HSM Node 2   │
│  10.0.1.10     │◄────Replication──┤  10.0.1.11     │
│  Active        │                  │  Standby       │
└────────────────┘                  └────────────────┘
        │                                    │
        └──────────────┬─────────────────────┘
                       │
              ┌────────┴────────┐
              │  Shared Storage │
              │  (Key Backup)   │
              └─────────────────┘
```

**Thales Luna HA Group**:

```bash
# Create HA group on HSM 1
lunash:> hagroup createGroup -serialNum <hsm1-serial> -label "Production HA"

# Add HSM 2 to group
lunash:> hagroup addMember -group Production HA -serialNum <hsm2-serial>

# Enable auto-recovery
lunash:> hagroup autorecovery -group "Production HA" -enable
```

**AWS CloudHSM Cluster**:

```bash
# Create cluster with multiple HSMs across AZs
aws cloudhsmv2 create-cluster \
    --hsm-type hsm1.medium \
    --subnet-ids subnet-az1 subnet-az2 subnet-az3

# Add HSMs to cluster
aws cloudhsmv2 create-hsm \
    --cluster-id cluster-abc123 \
    --availability-zone us-east-1a

aws cloudhsmv2 create-hsm \
    --cluster-id cluster-abc123 \
    --availability-zone us-east-1b
```

### Failover Mechanisms

**Automatic Failover**:

1. **Health Monitoring**: Periodic health checks (heartbeat)
2. **Failure Detection**: Timeout or error response
3. **Failover Trigger**: Promote standby to active
4. **Synchronization**: Replicate state to new standby
5. **Notification**: Alert administrators

**Failover Configuration**:

```python
class HSMFailoverConfig:
    """HSM failover configuration."""

    health_check_interval: int = 30  # seconds
    health_check_timeout: int = 5    # seconds
    max_retries: int = 3
    failover_timeout: int = 60       # seconds
    auto_recovery: bool = True

    primary_hsm: str = "10.0.1.10:1792"
    secondary_hsm: str = "10.0.1.11:1792"
    tertiary_hsm: str = "10.0.1.12:1792"
```

**Manual Failover**:

```bash
# Thales Luna
lunash:> hagroup synchronize -group "Production HA"
lunash:> hagroup recover -group "Production HA"

# AWS CloudHSM
# Automatic failover handled by service
# Manual recovery via HSM replacement
aws cloudhsmv2 delete-hsm --hsm-id hsm-xyz789
aws cloudhsmv2 create-hsm --cluster-id cluster-abc123 --availability-zone us-east-1a
```

### Load Distribution

**Connection Pooling**:

```python
class HSMConnectionPool:
    """Connection pool for HSM sessions."""

    def __init__(self, pkcs11_lib: str, max_sessions: int = 10):
        self.pkcs11 = PyKCS11.PyKCS11Lib()
        self.pkcs11.load(pkcs11_lib)
        self.max_sessions = max_sessions
        self.pool: List[Session] = []
        self.lock = threading.Lock()

    def acquire(self) -> Session:
        """Acquire session from pool."""
        with self.lock:
            if self.pool:
                return self.pool.pop()
            else:
                return self._create_session()

    def release(self, session: Session):
        """Return session to pool."""
        with self.lock:
            if len(self.pool) < self.max_sessions:
                self.pool.append(session)
            else:
                session.close()
```

**Round-Robin Distribution**:

```python
class HSMLoadBalancer:
    """Load balancer for multiple HSMs."""

    def __init__(self, hsm_endpoints: List[str]):
        self.endpoints = hsm_endpoints
        self.current = 0
        self.lock = threading.Lock()

    def get_next_endpoint(self) -> str:
        """Get next HSM endpoint (round-robin)."""
        with self.lock:
            endpoint = self.endpoints[self.current]
            self.current = (self.current + 1) % len(self.endpoints)
            return endpoint
```

## Compliance and Certification

### FIPS 140-2/140-3

**Security Levels**:

**Level 1**:
- Software cryptographic modules
- No physical security requirements
- Suitable for low-risk applications

**Level 2**:
- Tamper-evident physical security
- Role-based authentication
- Suitable for most commercial applications

**Level 3**:
- Tamper-resistant physical security
- Identity-based authentication
- Zeroization of critical parameters
- Suitable for high-security applications

**Level 4**:
- Penetration-resistant enclosure
- Environmental failure protection
- Immediate zeroization on tamper
- Suitable for military/government

**FIPS 140-3 Enhancements**:

- Updated cryptographic standards (SHA-3, AES-XTS)
- Enhanced physical security requirements
- Improved software security requirements
- Supply chain security requirements

### Common Criteria

**Evaluation Assurance Levels (EAL)**:

- **EAL1**: Functionally tested
- **EAL2**: Structurally tested
- **EAL3**: Methodically tested and checked
- **EAL4**: Methodically designed, tested, and reviewed
- **EAL5**: Semiformally designed and tested
- **EAL6**: Semiformally verified design and tested
- **EAL7**: Formally verified design and tested

### PCI-HSM

**PCI HSM Security Requirements**:

1. **Physical Security**:
   - Tamper-resistant enclosure
   - Tamper detection and response
   - Secure key loading procedures

2. **Logical Security**:
   - Authentication and access control
   - Cryptographic key management
   - Audit logging

3. **Key Management**:
   - Secure key generation
   - Key component custodianship (dual control)
   - Key backup and recovery procedures

4. **Operational Security**:
   - Secure installation procedures
   - Personnel security requirements
   - Incident response procedures

### Compliance Documentation

**Audit Trail Requirements**:

```python
class HSMAuditLog:
    """HSM audit log entry."""

    timestamp: datetime
    user: str
    operation: str  # Login, GenerateKey, Sign, etc.
    key_label: str
    result: str  # Success, Failure
    ip_address: str
    session_id: str
```

**Regular Audits**:

```bash
# Extract audit logs
lunash:> audit logs show -numRec 1000

# AWS CloudHSM
aws cloudhsmv2 describe-clusters --cluster-ids cluster-abc123
aws logs tail /aws/cloudhsm/cluster-abc123
```

## Performance Optimization

### Benchmarking

**Metrics to Measure**:

- **Throughput**: Operations per second
- **Latency**: Time per operation
- **Concurrent Sessions**: Simultaneous connections
- **Key Storage**: Number of keys supported

**Benchmark Example**:

```python
def benchmark_signing(hsm_session, private_key, iterations=1000):
    """Benchmark RSA signing performance."""
    import time

    data = b"Test message for signing"

    start = time.time()
    for _ in range(iterations):
        signature = private_key.sign(
            data,
            mechanism=Mechanism.SHA256_RSA_PKCS
        )
    end = time.time()

    elapsed = end - start
    ops_per_sec = iterations / elapsed
    latency_ms = (elapsed / iterations) * 1000

    return {
        'operations': iterations,
        'elapsed_seconds': elapsed,
        'ops_per_second': ops_per_sec,
        'latency_ms': latency_ms,
    }
```

### Performance Tuning

**Session Reuse**:

```python
# Bad: Create new session for each operation
for data in dataset:
    session = hsm.open_session()
    session.login(pin)
    signature = session.sign(data, key)
    session.logout()
    session.close()

# Good: Reuse session
session = hsm.open_session()
session.login(pin)
for data in dataset:
    signature = session.sign(data, key)
session.logout()
session.close()
```

**Batch Operations**:

```python
# Process multiple operations in single session
def batch_sign(session, private_key, data_list):
    """Sign multiple data items efficiently."""
    signatures = []
    for data in data_list:
        sig = private_key.sign(data, mechanism=Mechanism.SHA256_RSA_PKCS)
        signatures.append(sig)
    return signatures
```

**Parallel Processing**:

```python
from concurrent.futures import ThreadPoolExecutor

def parallel_sign(hsm_pool, private_key, data_list, workers=4):
    """Sign data in parallel using connection pool."""
    def sign_item(data):
        session = hsm_pool.acquire()
        try:
            return private_key.sign(data, mechanism=Mechanism.SHA256_RSA_PKCS)
        finally:
            hsm_pool.release(session)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        signatures = list(executor.map(sign_item, data_list))

    return signatures
```

**Algorithm Selection**:

```
Performance Comparison (operations/second):

RSA-2048 Sign:     1,000 - 10,000
RSA-4096 Sign:       200 - 2,000
ECDSA P-256 Sign: 2,000 - 20,000
ECDSA P-384 Sign: 1,000 - 10,000

AES-128 Encrypt:   100 MB/s - 1 GB/s
AES-256 Encrypt:    80 MB/s - 800 MB/s

Recommendation: Use ECDSA P-256 for best performance
```

## Backup and Disaster Recovery

### Backup Strategies

**Key Backup Methods**:

1. **Wrapped Backup**: Keys wrapped with backup KEK
2. **Split Knowledge**: Key shares distributed to multiple custodians
3. **Secure Transport**: Encrypted backup to offline storage
4. **Cloud Backup**: Encrypted backup to cloud storage

**Thales Luna Backup**:

```bash
# Create backup user
lunash:> user add -userName backup_admin -password <password>

# Perform backup
lunash:> partition backup -partition prod_keys -domain cloning

# Export backup to file
lunash:> backup export -partition prod_keys -file /backup/prod_keys.bak
```

**AWS CloudHSM Backup**:

```bash
# Automatic daily backups (default)
# Manual backup
aws cloudhsmv2 copy-backup-to-region \
    --backup-id backup-abc123 \
    --destination-region us-west-2
```

### Recovery Procedures

**Disaster Recovery Plan**:

```
1. Assess Damage
   - Identify failed HSMs
   - Determine data loss extent
   - Verify backup integrity

2. Provision Replacement HSMs
   - Order new hardware
   - Configure network access
   - Initialize HSMs

3. Restore from Backup
   - Restore key material
   - Verify key integrity
   - Test cryptographic operations

4. Update Applications
   - Reconfigure HSM connections
   - Test application functionality
   - Monitor for issues

5. Post-Recovery
   - Document incident
   - Update procedures
   - Train personnel
```

**Restore Example**:

```bash
# Thales Luna restore
lunash:> partition restore -partition prod_keys -file /backup/prod_keys.bak -domain cloning

# Verify restored keys
lunash:> partition show -partition prod_keys
lunash:> partition showContents -partition prod_keys

# AWS CloudHSM restore
# Automatic restore from latest backup
aws cloudhsmv2 restore-backup --backup-id backup-abc123
```

### Business Continuity

**RTO and RPO**:

- **RTO (Recovery Time Objective)**: Maximum acceptable downtime
- **RPO (Recovery Point Objective)**: Maximum acceptable data loss

**Example Targets**:

```
Tier 1 (Mission Critical):
  RTO: 1 hour
  RPO: 15 minutes
  Solution: Active-active HA cluster with real-time replication

Tier 2 (Business Critical):
  RTO: 4 hours
  RPO: 1 hour
  Solution: Active-passive HA cluster with hourly backups

Tier 3 (Standard):
  RTO: 24 hours
  RPO: 24 hours
  Solution: Single HSM with daily backups
```

## Integration Patterns

### KMS Integration

**AWS KMS Custom Key Store**:

```python
import boto3

# Create custom key store backed by CloudHSM
kms = boto3.client('kms')

response = kms.create_custom_key_store(
    CustomKeyStoreName='MyCloudHSMKeyStore',
    CloudHsmClusterId='cluster-abc123',
    TrustAnchorCertificate='<certificate>',
    KeyStorePassword='<password>'
)

# Create KMS key in custom key store
key = kms.create_key(
    Description='CloudHSM-backed key',
    KeyUsage='ENCRYPT_DECRYPT',
    CustomKeyStoreId=response['CustomKeyStoreId']
)
```

**HashiCorp Vault with PKCS#11**:

```hcl
# /etc/vault.d/vault.hcl
seal "pkcs11" {
  lib     = "/usr/lib/softhsm/libsofthsm2.so"
  slot    = "0"
  pin     = "1234"
  key_label = "vault-master-key"
  mechanism = "0x0009"  # CKM_AES_CBC
}
```

### Certificate Authority

**OpenSSL with PKCS#11 Engine**:

```bash
# Generate CSR with HSM private key
openssl req -new \
    -engine pkcs11 \
    -keyform engine \
    -key "pkcs11:object=CA-Key;type=private" \
    -out ca.csr \
    -config openssl.cnf

# Sign certificate with HSM
openssl ca \
    -engine pkcs11 \
    -keyform engine \
    -key "pkcs11:object=CA-Key;type=private" \
    -in server.csr \
    -out server.crt \
    -config openssl.cnf
```

**EJBCA Integration**:

```xml
<!-- conf/cesecore.properties -->
<cryptotoken>
    <property name="type" value="PKCS11CryptoToken"/>
    <property name="sharedlibrary" value="/usr/lib/libCryptoki2_64.so"/>
    <property name="slot" value="0"/>
    <property name="pin" value="${encrypted:pin}"/>
</cryptotoken>
```

### Code Signing

**Signtool with HSM** (Windows):

```cmd
signtool sign /f "pkcs11:object=CodeSigningKey" /fd SHA256 /tr http://timestamp.digicert.com application.exe
```

**Jarsigner with HSM** (Java):

```bash
jarsigner \
    -keystore NONE \
    -storetype PKCS11 \
    -providerClass sun.security.pkcs11.SunPKCS11 \
    -providerArg /etc/pkcs11.cfg \
    application.jar \
    "CodeSigningKey"
```

**Codesign with HSM** (macOS):

```bash
codesign \
    --sign "Developer ID Application: Company Name" \
    --keychain /Library/Keychains/hsm.keychain \
    --timestamp \
    Application.app
```

## Security Best Practices

### Access Control

**Principle of Least Privilege**:

```python
# Create user with minimal permissions
attributes = {
    Attribute.LABEL: "app-user",
    Attribute.SIGN: True,      # Can sign
    Attribute.VERIFY: True,    # Can verify
    Attribute.DECRYPT: False,  # Cannot decrypt
    Attribute.UNWRAP: False,   # Cannot unwrap keys
}
```

**Multi-Factor Authentication**:

- Something you know: PIN/password
- Something you have: Smart card, YubiKey
- Something you are: Biometric

**Role Separation**:

```python
class HSMRole(Enum):
    SECURITY_OFFICER = "so"  # Administers HSM, cannot use keys
    CRYPTO_OFFICER = "co"    # Manages keys, cannot perform operations
    CRYPTO_USER = "cu"       # Performs cryptographic operations
    AUDITOR = "audit"        # Reviews logs, read-only access
```

### Key Management Policies

**Key Attributes**:

```python
# Production key attributes
PRODUCTION_KEY_POLICY = {
    Attribute.SENSITIVE: True,      # Cannot be read
    Attribute.EXTRACTABLE: False,   # Cannot be exported
    Attribute.WRAP_WITH_TRUSTED: True,  # Only wrap with trusted keys
    Attribute.ALWAYS_AUTHENTICATE: True,  # Require auth for each use
}

# Development key attributes
DEVELOPMENT_KEY_POLICY = {
    Attribute.SENSITIVE: True,
    Attribute.EXTRACTABLE: True,  # Can be exported for testing
}
```

**Key Lifecycle**:

```
Generate → Activate → Use → Deactivate → Archive → Destroy
   ↓          ↓        ↓        ↓          ↓         ↓
 Log      Approve   Audit   Retire    Backup    Zeroize
```

### Audit and Monitoring

**Security Events to Log**:

- User authentication (success/failure)
- Key generation, import, export
- Cryptographic operations
- Administrative actions
- Tamper detection events
- Backup and restore operations

**Log Analysis**:

```python
def analyze_audit_log(log_file: str) -> Dict[str, int]:
    """Analyze HSM audit log for security events."""
    events = {
        'failed_logins': 0,
        'key_generations': 0,
        'key_deletions': 0,
        'unusual_operations': 0,
    }

    with open(log_file) as f:
        for line in f:
            if 'LOGIN_FAILED' in line:
                events['failed_logins'] += 1
            elif 'KEY_GENERATE' in line:
                events['key_generations'] += 1
            elif 'KEY_DELETE' in line:
                events['key_deletions'] += 1
            # ... analyze other events

    return events
```

### Incident Response

**Security Incident Procedures**:

```
1. Detection
   - Monitor audit logs
   - Alert on suspicious activity
   - Verify tamper sensors

2. Containment
   - Disable compromised accounts
   - Isolate affected HSMs
   - Prevent further damage

3. Investigation
   - Review audit logs
   - Identify root cause
   - Assess impact

4. Recovery
   - Restore from backup
   - Rotate compromised keys
   - Update security controls

5. Post-Incident
   - Document findings
   - Update procedures
   - Train personnel
```

## Troubleshooting

### Common Issues

**Issue: CKR_SESSION_HANDLE_INVALID**:

```python
# Cause: Session expired or closed
# Solution: Check session timeout settings

# Configure longer session timeout
session = hsm.open_session()
session.set_operation_timeout(300)  # 5 minutes
```

**Issue: CKR_PIN_LOCKED**:

```bash
# Cause: Too many failed login attempts
# Solution: Reset PIN as Security Officer

lunash:> user changePw -userName admin
```

**Issue: CKR_DEVICE_ERROR**:

```bash
# Cause: HSM hardware failure or network issue
# Solution: Check hardware status and network connectivity

# Verify HSM status
lunash:> hsm show

# Test network connectivity
ping <hsm-ip>
telnet <hsm-ip> 1792
```

**Issue: Performance Degradation**:

```python
# Cause: Session leaks, inefficient code
# Solution: Implement connection pooling

# Always close sessions
try:
    session = hsm.open_session()
    # ... operations ...
finally:
    session.close()
```

### Debugging Techniques

**Enable PKCS#11 Logging**:

```bash
# Set environment variable
export PKCS11SPY=/usr/lib/libsofthsm2.so
export PKCS11SPY_OUTPUT=/tmp/pkcs11-spy.log

# Run application with spy wrapper
LD_PRELOAD=/usr/lib/pkcs11-spy.so ./myapp
```

**Verbose Logging**:

```bash
# Thales Luna
export ChrystokiLogLevel=DEBUG

# AWS CloudHSM
export CLOUDHSM_DEBUG=1

# SoftHSM
export SOFTHSM2_CONF=/etc/softhsm2.conf
# Edit config: log.level = DEBUG
```

## Reference Implementation

### Complete PKCS#11 Example (C)

```c
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "pkcs11.h"

#define CHECK_RV(rv, msg) \
    if (rv != CKR_OK) { \
        fprintf(stderr, "%s: 0x%lx\n", msg, rv); \
        return -1; \
    }

int main() {
    CK_RV rv;
    CK_SESSION_HANDLE hSession;
    CK_SLOT_ID slotID = 0;

    // Load PKCS#11 library
    void *module = dlopen("/usr/lib/softhsm/libsofthsm2.so", RTLD_NOW);
    if (!module) {
        fprintf(stderr, "Failed to load PKCS#11 library\n");
        return -1;
    }

    // Get function list
    CK_C_GetFunctionList C_GetFunctionList =
        (CK_C_GetFunctionList)dlsym(module, "C_GetFunctionList");

    CK_FUNCTION_LIST_PTR pFunctionList;
    rv = C_GetFunctionList(&pFunctionList);
    CHECK_RV(rv, "C_GetFunctionList");

    // Initialize
    rv = pFunctionList->C_Initialize(NULL);
    CHECK_RV(rv, "C_Initialize");

    // Open session
    rv = pFunctionList->C_OpenSession(
        slotID,
        CKF_SERIAL_SESSION | CKF_RW_SESSION,
        NULL, NULL,
        &hSession
    );
    CHECK_RV(rv, "C_OpenSession");

    // Login
    CK_UTF8CHAR pin[] = "1234";
    rv = pFunctionList->C_Login(hSession, CKU_USER, pin, sizeof(pin) - 1);
    CHECK_RV(rv, "C_Login");

    // Generate RSA key pair
    CK_MECHANISM mechanism = {CKM_RSA_PKCS_KEY_PAIR_GEN, NULL, 0};
    CK_ULONG modulusBits = 2048;
    CK_BYTE publicExponent[] = {0x01, 0x00, 0x01};
    CK_BBOOL true = CK_TRUE;
    CK_BBOOL false = CK_FALSE;

    CK_ATTRIBUTE publicKeyTemplate[] = {
        {CKA_ENCRYPT, &true, sizeof(true)},
        {CKA_VERIFY, &true, sizeof(true)},
        {CKA_WRAP, &true, sizeof(true)},
        {CKA_MODULUS_BITS, &modulusBits, sizeof(modulusBits)},
        {CKA_PUBLIC_EXPONENT, publicExponent, sizeof(publicExponent)},
    };

    CK_ATTRIBUTE privateKeyTemplate[] = {
        {CKA_TOKEN, &true, sizeof(true)},
        {CKA_PRIVATE, &true, sizeof(true)},
        {CKA_SENSITIVE, &true, sizeof(true)},
        {CKA_DECRYPT, &true, sizeof(true)},
        {CKA_SIGN, &true, sizeof(true)},
        {CKA_UNWRAP, &true, sizeof(true)},
    };

    CK_OBJECT_HANDLE hPublicKey, hPrivateKey;
    rv = pFunctionList->C_GenerateKeyPair(
        hSession,
        &mechanism,
        publicKeyTemplate, 5,
        privateKeyTemplate, 6,
        &hPublicKey,
        &hPrivateKey
    );
    CHECK_RV(rv, "C_GenerateKeyPair");

    printf("Generated RSA key pair:\n");
    printf("  Public key handle: %lu\n", hPublicKey);
    printf("  Private key handle: %lu\n", hPrivateKey);

    // Sign data
    CK_MECHANISM signMechanism = {CKM_SHA256_RSA_PKCS, NULL, 0};
    CK_BYTE data[] = "Test data to sign";
    CK_BYTE signature[256];
    CK_ULONG signatureLen = sizeof(signature);

    rv = pFunctionList->C_SignInit(hSession, &signMechanism, hPrivateKey);
    CHECK_RV(rv, "C_SignInit");

    rv = pFunctionList->C_Sign(
        hSession,
        data, sizeof(data) - 1,
        signature, &signatureLen
    );
    CHECK_RV(rv, "C_Sign");

    printf("Signature length: %lu bytes\n", signatureLen);

    // Verify signature
    rv = pFunctionList->C_VerifyInit(hSession, &signMechanism, hPublicKey);
    CHECK_RV(rv, "C_VerifyInit");

    rv = pFunctionList->C_Verify(
        hSession,
        data, sizeof(data) - 1,
        signature, signatureLen
    );
    if (rv == CKR_OK) {
        printf("Signature verification: SUCCESS\n");
    } else {
        printf("Signature verification: FAILED\n");
    }

    // Cleanup
    pFunctionList->C_Logout(hSession);
    pFunctionList->C_CloseSession(hSession);
    pFunctionList->C_Finalize(NULL);
    dlclose(module);

    return 0;
}
```

### Python PyKCS11 Example

```python
#!/usr/bin/env python3
"""Complete HSM integration example using PyKCS11."""

import PyKCS11
from PyKCS11 import PyKCS11Error
import binascii

def main():
    # Load PKCS#11 library
    pkcs11 = PyKCS11.PyKCS11Lib()
    pkcs11.load("/usr/lib/softhsm/libsofthsm2.so")

    # Get slot list
    slots = pkcs11.getSlotList(tokenPresent=True)
    if not slots:
        print("No tokens found")
        return

    slot = slots[0]
    print(f"Using slot: {slot}")

    # Open session
    session = pkcs11.openSession(slot, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)

    # Login
    pin = "1234"
    session.login(pin)

    try:
        # Generate RSA key pair
        print("Generating RSA-2048 key pair...")

        public_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
            (PyKCS11.CKA_ENCRYPT, True),
            (PyKCS11.CKA_VERIFY, True),
            (PyKCS11.CKA_WRAP, True),
            (PyKCS11.CKA_MODULUS_BITS, 2048),
            (PyKCS11.CKA_PUBLIC_EXPONENT, (0x01, 0x00, 0x01)),
            (PyKCS11.CKA_LABEL, "Test RSA Public Key"),
        ]

        private_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
            (PyKCS11.CKA_TOKEN, True),
            (PyKCS11.CKA_PRIVATE, True),
            (PyKCS11.CKA_SENSITIVE, True),
            (PyKCS11.CKA_DECRYPT, True),
            (PyKCS11.CKA_SIGN, True),
            (PyKCS11.CKA_UNWRAP, True),
            (PyKCS11.CKA_EXTRACTABLE, False),
            (PyKCS11.CKA_LABEL, "Test RSA Private Key"),
        ]

        (public_key, private_key) = session.generateKeyPair(
            public_template,
            private_template,
            mecha=PyKCS11.MechanismRSAPKCSKeyPairGen
        )

        print(f"Generated key pair:")
        print(f"  Public key: {public_key}")
        print(f"  Private key: {private_key}")

        # Sign data
        print("\nSigning data...")
        data = b"Test message for signing"
        mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)

        signature = session.sign(private_key, data, mechanism)
        print(f"Signature: {binascii.hexlify(bytes(signature))[:64].decode()}...")

        # Verify signature
        print("\nVerifying signature...")
        try:
            session.verify(public_key, data, signature, mechanism)
            print("Signature verification: SUCCESS")
        except PyKCS11Error as e:
            print(f"Signature verification: FAILED - {e}")

        # Find all keys
        print("\nListing all keys in token:")
        objects = session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY)])
        for obj in objects:
            attrs = session.getAttributeValue(obj, [PyKCS11.CKA_LABEL])
            label = ''.join(chr(c) for c in attrs[0] if c != 0)
            print(f"  Key: {label} (handle: {obj})")

    finally:
        # Cleanup
        session.logout()
        session.closeSession()

if __name__ == "__main__":
    main()
```

This comprehensive reference guide covers all aspects of HSM integration, from fundamentals to advanced topics. Use it as a complete resource for implementing secure cryptographic solutions with hardware security modules.
