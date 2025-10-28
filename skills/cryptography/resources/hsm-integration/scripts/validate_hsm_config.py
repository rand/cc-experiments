#!/usr/bin/env python3
"""
HSM Configuration Validator

Validates HSM configuration, checks PKCS#11 settings, verifies key attributes,
audits slot configuration, performs compliance checking, and supports multiple vendors.

Supports: SoftHSM, Thales Luna, AWS CloudHSM, YubiHSM
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import configparser
import subprocess
import re

try:
    import PyKCS11
    PKCS11_AVAILABLE = True
except ImportError:
    PKCS11_AVAILABLE = False


class Severity(Enum):
    """Validation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComplianceStandard(Enum):
    """Compliance standards."""
    FIPS_140_2 = "fips-140-2"
    FIPS_140_3 = "fips-140-3"
    PCI_DSS = "pci-dss"
    COMMON_CRITERIA = "common-criteria"


class HSMVendor(Enum):
    """Supported HSM vendors."""
    SOFTHSM = "softhsm"
    THALES_LUNA = "thales-luna"
    AWS_CLOUDHSM = "aws-cloudhsm"
    YUBIHSM = "yubihsm"
    UNKNOWN = "unknown"


@dataclass
class ValidationResult:
    """Single validation check result."""
    check_id: str
    severity: Severity
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    remediation: Optional[str] = None


@dataclass
class HSMConfig:
    """HSM configuration details."""
    vendor: HSMVendor
    library_path: str
    config_path: Optional[str] = None
    slot_id: Optional[int] = None
    token_label: Optional[str] = None
    pin: Optional[str] = None
    config_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KeyAttributes:
    """PKCS#11 key attributes."""
    label: str
    key_type: str
    key_id: bytes
    sensitive: bool
    extractable: bool
    private: bool
    token: bool
    modifiable: bool
    encrypt: bool = False
    decrypt: bool = False
    sign: bool = False
    verify: bool = False
    wrap: bool = False
    unwrap: bool = False
    derive: bool = False


@dataclass
class SlotInfo:
    """HSM slot information."""
    slot_id: int
    slot_description: str
    manufacturer_id: str
    hardware_version: str
    firmware_version: str
    token_present: bool
    token_label: Optional[str] = None
    serial_number: Optional[str] = None
    flags: List[str] = field(default_factory=list)


class HSMConfigValidator:
    """HSM configuration validator."""

    def __init__(
        self,
        config_file: Optional[str] = None,
        library_path: Optional[str] = None,
        vendor: Optional[HSMVendor] = None,
        compliance_standards: Optional[List[ComplianceStandard]] = None,
        verbose: bool = False
    ):
        """Initialize validator."""
        self.config_file = config_file
        self.library_path = library_path
        self.vendor = vendor or HSMVendor.UNKNOWN
        self.compliance_standards = compliance_standards or []
        self.verbose = verbose
        self.results: List[ValidationResult] = []
        self.hsm_config: Optional[HSMConfig] = None
        self.pkcs11_lib: Optional[PyKCS11.PyKCS11Lib] = None

    def validate_all(self) -> List[ValidationResult]:
        """Run all validation checks."""
        self._log("Starting HSM configuration validation...")

        # Load configuration
        if not self._load_configuration():
            return self.results

        # Run validation checks
        self._validate_library_path()
        self._validate_config_file()
        self._detect_vendor()
        self._validate_vendor_specific()

        if PKCS11_AVAILABLE:
            self._validate_pkcs11_interface()
            self._validate_slots()
            self._validate_token_configuration()
            self._validate_key_attributes()
            self._validate_mechanisms()
        else:
            self._add_result(
                "pkcs11-library",
                Severity.WARNING,
                False,
                "PyKCS11 library not available, skipping PKCS#11 checks",
                remediation="Install PyKCS11: pip install PyKCS11"
            )

        # Compliance checks
        for standard in self.compliance_standards:
            self._validate_compliance(standard)

        # Security checks
        self._validate_security_configuration()

        return self.results

    def _load_configuration(self) -> bool:
        """Load HSM configuration."""
        try:
            config_data = {}

            # Load from config file if provided
            if self.config_file:
                if not os.path.exists(self.config_file):
                    self._add_result(
                        "config-file",
                        Severity.ERROR,
                        False,
                        f"Configuration file not found: {self.config_file}",
                        remediation="Provide valid configuration file path"
                    )
                    return False

                config_data = self._parse_config_file(self.config_file)

            # Determine library path
            library_path = self.library_path
            if not library_path and config_data.get("library"):
                library_path = config_data["library"]
            elif not library_path:
                library_path = self._find_default_library()

            if not library_path:
                self._add_result(
                    "library-path",
                    Severity.ERROR,
                    False,
                    "No PKCS#11 library path specified or found",
                    remediation="Specify library path with --library option"
                )
                return False

            self.hsm_config = HSMConfig(
                vendor=self.vendor,
                library_path=library_path,
                config_path=self.config_file,
                config_data=config_data
            )

            return True

        except Exception as e:
            self._add_result(
                "config-load",
                Severity.ERROR,
                False,
                f"Failed to load configuration: {e}",
                details={"error": str(e)}
            )
            return False

    def _parse_config_file(self, config_path: str) -> Dict[str, Any]:
        """Parse configuration file."""
        config_data = {}

        try:
            # Try as JSON first
            with open(config_path) as f:
                try:
                    config_data = json.load(f)
                    return config_data
                except json.JSONDecodeError:
                    pass

            # Try as INI format (Chrystoki.conf, softhsm2.conf)
            config = configparser.ConfigParser()
            config.read(config_path)

            for section in config.sections():
                config_data[section] = dict(config[section])

            # Also read key=value pairs outside sections
            with open(config_path) as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config_data[key.strip()] = value.strip()

        except Exception as e:
            self._log(f"Warning: Failed to parse config file: {e}")

        return config_data

    def _find_default_library(self) -> Optional[str]:
        """Find default PKCS#11 library path."""
        possible_paths = [
            # SoftHSM
            "/usr/lib/softhsm/libsofthsm2.so",
            "/usr/lib/x86_64-linux-gnu/softhsm/libsofthsm2.so",
            "/usr/local/lib/softhsm/libsofthsm2.so",
            # Thales Luna
            "/usr/safenet/lunaclient/lib/libCryptoki2_64.so",
            "/usr/lib/libCryptoki2_64.so",
            # AWS CloudHSM
            "/opt/cloudhsm/lib/libcloudhsm_pkcs11.so",
            # YubiHSM
            "/usr/lib/x86_64-linux-gnu/pkcs11/yubihsm_pkcs11.so",
            "/usr/local/lib/pkcs11/yubihsm_pkcs11.so",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    def _validate_library_path(self):
        """Validate PKCS#11 library path."""
        if not self.hsm_config:
            return

        library_path = self.hsm_config.library_path

        # Check existence
        if not os.path.exists(library_path):
            self._add_result(
                "library-exists",
                Severity.CRITICAL,
                False,
                f"PKCS#11 library not found: {library_path}",
                remediation="Install HSM client software or verify library path"
            )
            return

        # Check permissions
        if not os.access(library_path, os.R_OK):
            self._add_result(
                "library-readable",
                Severity.ERROR,
                False,
                f"PKCS#11 library not readable: {library_path}",
                remediation=f"Fix permissions: chmod +r {library_path}"
            )
            return

        # Check if it's a valid shared library
        try:
            result = subprocess.run(
                ["file", library_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "shared object" not in result.stdout.lower():
                self._add_result(
                    "library-valid",
                    Severity.ERROR,
                    False,
                    f"File is not a shared library: {library_path}",
                    details={"file_type": result.stdout.strip()}
                )
                return
        except Exception as e:
            self._log(f"Warning: Could not verify library type: {e}")

        self._add_result(
            "library-path",
            Severity.INFO,
            True,
            f"PKCS#11 library found: {library_path}"
        )

    def _validate_config_file(self):
        """Validate configuration file."""
        if not self.config_file:
            self._add_result(
                "config-file",
                Severity.INFO,
                True,
                "No configuration file specified (using defaults)"
            )
            return

        if not os.path.exists(self.config_file):
            self._add_result(
                "config-file-exists",
                Severity.ERROR,
                False,
                f"Configuration file not found: {self.config_file}"
            )
            return

        # Check permissions
        stat_info = os.stat(self.config_file)
        mode = stat_info.st_mode & 0o777

        if mode & 0o077:
            self._add_result(
                "config-file-permissions",
                Severity.WARNING,
                False,
                f"Configuration file has overly permissive permissions: {oct(mode)}",
                remediation=f"Restrict permissions: chmod 600 {self.config_file}"
            )

        self._add_result(
            "config-file",
            Severity.INFO,
            True,
            f"Configuration file found: {self.config_file}"
        )

    def _detect_vendor(self):
        """Detect HSM vendor from library path."""
        if self.vendor != HSMVendor.UNKNOWN:
            return

        if not self.hsm_config:
            return

        library_path = self.hsm_config.library_path.lower()

        if "softhsm" in library_path:
            self.vendor = HSMVendor.SOFTHSM
        elif "cryptoki" in library_path or "luna" in library_path:
            self.vendor = HSMVendor.THALES_LUNA
        elif "cloudhsm" in library_path:
            self.vendor = HSMVendor.AWS_CLOUDHSM
        elif "yubihsm" in library_path:
            self.vendor = HSMVendor.YUBIHSM

        self.hsm_config.vendor = self.vendor

        self._add_result(
            "vendor-detection",
            Severity.INFO,
            True,
            f"Detected HSM vendor: {self.vendor.value}"
        )

    def _validate_vendor_specific(self):
        """Validate vendor-specific configuration."""
        if self.vendor == HSMVendor.SOFTHSM:
            self._validate_softhsm_config()
        elif self.vendor == HSMVendor.THALES_LUNA:
            self._validate_luna_config()
        elif self.vendor == HSMVendor.AWS_CLOUDHSM:
            self._validate_cloudhsm_config()
        elif self.vendor == HSMVendor.YUBIHSM:
            self._validate_yubihsm_config()

    def _validate_softhsm_config(self):
        """Validate SoftHSM-specific configuration."""
        # Check for config file
        config_paths = [
            "/etc/softhsm2.conf",
            "/etc/softhsm/softhsm2.conf",
            os.path.expanduser("~/.config/softhsm2/softhsm2.conf"),
        ]

        env_config = os.environ.get("SOFTHSM2_CONF")
        if env_config:
            config_paths.insert(0, env_config)

        config_found = False
        for path in config_paths:
            if os.path.exists(path):
                config_found = True
                self._add_result(
                    "softhsm-config",
                    Severity.INFO,
                    True,
                    f"SoftHSM configuration found: {path}"
                )

                # Parse config
                config = configparser.ConfigParser()
                config.read(path)

                # Check token directory
                if config.has_option("directories", "tokendir"):
                    tokendir = config.get("directories", "tokendir")
                    if not os.path.exists(tokendir):
                        self._add_result(
                            "softhsm-tokendir",
                            Severity.ERROR,
                            False,
                            f"SoftHSM token directory does not exist: {tokendir}",
                            remediation=f"Create directory: mkdir -p {tokendir}"
                        )
                    elif not os.access(tokendir, os.W_OK):
                        self._add_result(
                            "softhsm-tokendir-writable",
                            Severity.ERROR,
                            False,
                            f"SoftHSM token directory not writable: {tokendir}",
                            remediation=f"Fix permissions: chmod 700 {tokendir}"
                        )
                break

        if not config_found:
            self._add_result(
                "softhsm-config",
                Severity.WARNING,
                False,
                "SoftHSM configuration file not found",
                remediation="Create /etc/softhsm2.conf with token directory"
            )

    def _validate_luna_config(self):
        """Validate Thales Luna-specific configuration."""
        # Check for Chrystoki.conf
        config_path = "/etc/Chrystoki.conf"

        if not os.path.exists(config_path):
            self._add_result(
                "luna-config",
                Severity.ERROR,
                False,
                f"Luna configuration file not found: {config_path}",
                remediation="Run Luna client installation"
            )
            return

        self._add_result(
            "luna-config",
            Severity.INFO,
            True,
            f"Luna configuration found: {config_path}"
        )

        # Check for Luna client tools
        vtl_path = "/usr/safenet/lunaclient/bin/vtl"
        if os.path.exists(vtl_path):
            try:
                result = subprocess.run(
                    [vtl_path, "verify"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    self._add_result(
                        "luna-connectivity",
                        Severity.INFO,
                        True,
                        "Luna HSM connectivity verified"
                    )
                else:
                    self._add_result(
                        "luna-connectivity",
                        Severity.WARNING,
                        False,
                        "Luna HSM connectivity check failed",
                        details={"output": result.stderr}
                    )
            except Exception as e:
                self._log(f"Warning: Could not verify Luna connectivity: {e}")

    def _validate_cloudhsm_config(self):
        """Validate AWS CloudHSM-specific configuration."""
        # Check for CloudHSM client
        client_path = "/opt/cloudhsm/bin/cloudhsm_client"

        if not os.path.exists(client_path):
            self._add_result(
                "cloudhsm-client",
                Severity.ERROR,
                False,
                "AWS CloudHSM client not installed",
                remediation="Install CloudHSM client from AWS"
            )
            return

        # Check configuration
        config_path = "/opt/cloudhsm/etc/cloudhsm_client.cfg"

        if not os.path.exists(config_path):
            self._add_result(
                "cloudhsm-config",
                Severity.ERROR,
                False,
                f"CloudHSM configuration not found: {config_path}",
                remediation="Run: /opt/cloudhsm/bin/configure -a <cluster-ip>"
            )
            return

        # Check if client daemon is running
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "cloudhsm-client"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self._add_result(
                    "cloudhsm-daemon",
                    Severity.INFO,
                    True,
                    "CloudHSM client daemon is running"
                )
            else:
                self._add_result(
                    "cloudhsm-daemon",
                    Severity.ERROR,
                    False,
                    "CloudHSM client daemon not running",
                    remediation="Start daemon: systemctl start cloudhsm-client"
                )
        except Exception:
            pass

    def _validate_yubihsm_config(self):
        """Validate YubiHSM-specific configuration."""
        # Check for YubiHSM connector
        connector_url = "http://127.0.0.1:12345"

        try:
            import urllib.request
            with urllib.request.urlopen(connector_url, timeout=2) as response:
                if response.status == 200:
                    self._add_result(
                        "yubihsm-connector",
                        Severity.INFO,
                        True,
                        "YubiHSM connector is running"
                    )
                else:
                    self._add_result(
                        "yubihsm-connector",
                        Severity.ERROR,
                        False,
                        f"YubiHSM connector returned status {response.status}",
                        remediation="Restart connector: systemctl restart yubihsm-connector"
                    )
        except Exception as e:
            self._add_result(
                "yubihsm-connector",
                Severity.ERROR,
                False,
                "YubiHSM connector not accessible",
                details={"error": str(e)},
                remediation="Start connector: systemctl start yubihsm-connector"
            )

        # Check config file
        config_path = "/etc/yubihsm_pkcs11.conf"
        if os.path.exists(config_path):
            self._add_result(
                "yubihsm-config",
                Severity.INFO,
                True,
                f"YubiHSM PKCS#11 configuration found: {config_path}"
            )

    def _validate_pkcs11_interface(self):
        """Validate PKCS#11 interface."""
        if not PKCS11_AVAILABLE or not self.hsm_config:
            return

        try:
            self.pkcs11_lib = PyKCS11.PyKCS11Lib()
            self.pkcs11_lib.load(self.hsm_config.library_path)

            self._add_result(
                "pkcs11-load",
                Severity.INFO,
                True,
                "PKCS#11 library loaded successfully"
            )

            # Get library info
            info = self.pkcs11_lib.getInfo()
            self._add_result(
                "pkcs11-info",
                Severity.INFO,
                True,
                f"PKCS#11 library info: {info.manufacturerID} v{info.libraryVersion}",
                details={
                    "manufacturer": info.manufacturerID,
                    "description": info.libraryDescription,
                    "version": f"{info.libraryVersion.major}.{info.libraryVersion.minor}",
                    "cryptoki_version": f"{info.cryptokiVersion.major}.{info.cryptokiVersion.minor}",
                }
            )

        except Exception as e:
            self._add_result(
                "pkcs11-load",
                Severity.ERROR,
                False,
                f"Failed to load PKCS#11 library: {e}",
                details={"error": str(e)}
            )

    def _validate_slots(self):
        """Validate HSM slots."""
        if not self.pkcs11_lib:
            return

        try:
            slots = self.pkcs11_lib.getSlotList(tokenPresent=True)

            if not slots:
                self._add_result(
                    "slots-available",
                    Severity.ERROR,
                    False,
                    "No slots with tokens found",
                    remediation="Initialize token: softhsm2-util --init-token --slot 0"
                )
                return

            self._add_result(
                "slots-available",
                Severity.INFO,
                True,
                f"Found {len(slots)} slot(s) with tokens"
            )

            # Validate each slot
            for slot_id in slots:
                self._validate_slot(slot_id)

        except Exception as e:
            self._add_result(
                "slots-enumerate",
                Severity.ERROR,
                False,
                f"Failed to enumerate slots: {e}",
                details={"error": str(e)}
            )

    def _validate_slot(self, slot_id: int):
        """Validate individual slot."""
        if not self.pkcs11_lib:
            return

        try:
            # Get slot info
            slot_info = self.pkcs11_lib.getSlotInfo(slot_id)
            token_info = self.pkcs11_lib.getTokenInfo(slot_id)

            details = {
                "slot_id": slot_id,
                "description": slot_info.slotDescription.strip(),
                "manufacturer": slot_info.manufacturerID.strip(),
                "hardware_version": f"{slot_info.hardwareVersion.major}.{slot_info.hardwareVersion.minor}",
                "firmware_version": f"{slot_info.firmwareVersion.major}.{slot_info.firmwareVersion.minor}",
                "token_label": token_info.label.strip(),
                "serial": token_info.serialNumber.strip(),
            }

            self._add_result(
                f"slot-{slot_id}",
                Severity.INFO,
                True,
                f"Slot {slot_id}: {token_info.label.strip()}",
                details=details
            )

            # Check token flags
            flags = []
            if token_info.flags & PyKCS11.CKF_RNG:
                flags.append("RNG")
            if token_info.flags & PyKCS11.CKF_WRITE_PROTECTED:
                flags.append("WRITE_PROTECTED")
            if token_info.flags & PyKCS11.CKF_LOGIN_REQUIRED:
                flags.append("LOGIN_REQUIRED")
            if token_info.flags & PyKCS11.CKF_USER_PIN_INITIALIZED:
                flags.append("USER_PIN_INITIALIZED")
            if token_info.flags & PyKCS11.CKF_PROTECTED_AUTHENTICATION_PATH:
                flags.append("PROTECTED_AUTH_PATH")
            if token_info.flags & PyKCS11.CKF_TOKEN_INITIALIZED:
                flags.append("TOKEN_INITIALIZED")

            self._log(f"  Token flags: {', '.join(flags)}")

            # Check if token is initialized
            if not (token_info.flags & PyKCS11.CKF_TOKEN_INITIALIZED):
                self._add_result(
                    f"slot-{slot_id}-initialized",
                    Severity.WARNING,
                    False,
                    f"Token in slot {slot_id} not initialized",
                    remediation=f"Initialize token: softhsm2-util --init-token --slot {slot_id}"
                )

        except Exception as e:
            self._add_result(
                f"slot-{slot_id}-info",
                Severity.ERROR,
                False,
                f"Failed to get info for slot {slot_id}: {e}",
                details={"error": str(e)}
            )

    def _validate_token_configuration(self):
        """Validate token configuration."""
        if not self.pkcs11_lib:
            return

        try:
            slots = self.pkcs11_lib.getSlotList(tokenPresent=True)
            if not slots:
                return

            for slot_id in slots:
                token_info = self.pkcs11_lib.getTokenInfo(slot_id)

                # Check free space
                free_private = token_info.ulFreePrivateMemory
                total_private = token_info.ulTotalPrivateMemory

                if total_private > 0:
                    usage_percent = ((total_private - free_private) / total_private) * 100

                    if usage_percent > 90:
                        self._add_result(
                            f"slot-{slot_id}-storage",
                            Severity.WARNING,
                            False,
                            f"Token storage {usage_percent:.1f}% full",
                            details={
                                "free_bytes": free_private,
                                "total_bytes": total_private,
                                "usage_percent": usage_percent,
                            },
                            remediation="Delete unused keys or use additional token"
                        )

        except Exception as e:
            self._log(f"Warning: Could not validate token configuration: {e}")

    def _validate_key_attributes(self):
        """Validate key attributes in HSM."""
        if not self.pkcs11_lib:
            return

        try:
            slots = self.pkcs11_lib.getSlotList(tokenPresent=True)
            if not slots:
                return

            total_keys = 0
            weak_keys = 0

            for slot_id in slots:
                try:
                    session = self.pkcs11_lib.openSession(slot_id)

                    # Find all private keys
                    objects = session.findObjects([
                        (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY)
                    ])

                    total_keys += len(objects)

                    for obj in objects:
                        try:
                            # Get key attributes
                            attrs = session.getAttributeValue(obj, [
                                PyKCS11.CKA_LABEL,
                                PyKCS11.CKA_KEY_TYPE,
                                PyKCS11.CKA_SENSITIVE,
                                PyKCS11.CKA_EXTRACTABLE,
                            ])

                            label = ''.join(chr(c) for c in attrs[0] if c != 0)
                            key_type = attrs[1]
                            sensitive = attrs[2]
                            extractable = attrs[3]

                            # Check for weak configuration
                            if not sensitive:
                                weak_keys += 1
                                self._add_result(
                                    f"key-sensitive-{obj}",
                                    Severity.WARNING,
                                    False,
                                    f"Key '{label}' is not marked as sensitive",
                                    details={"key_handle": obj, "label": label},
                                    remediation="Regenerate key with CKA_SENSITIVE=True"
                                )

                            if extractable:
                                weak_keys += 1
                                self._add_result(
                                    f"key-extractable-{obj}",
                                    Severity.WARNING,
                                    False,
                                    f"Key '{label}' is extractable",
                                    details={"key_handle": obj, "label": label},
                                    remediation="Regenerate key with CKA_EXTRACTABLE=False"
                                )

                            # Check key type and size
                            if key_type == PyKCS11.CKK_RSA:
                                modulus_attrs = session.getAttributeValue(obj, [PyKCS11.CKA_MODULUS])
                                modulus = bytes(modulus_attrs[0])
                                key_bits = len(modulus) * 8

                                if key_bits < 2048:
                                    weak_keys += 1
                                    self._add_result(
                                        f"key-size-{obj}",
                                        Severity.ERROR,
                                        False,
                                        f"RSA key '{label}' has weak size: {key_bits} bits",
                                        details={"key_handle": obj, "label": label, "bits": key_bits},
                                        remediation="Regenerate with 2048+ bits"
                                    )

                        except Exception as e:
                            self._log(f"Warning: Could not validate key {obj}: {e}")

                    session.closeSession()

                except Exception as e:
                    self._log(f"Warning: Could not validate keys in slot {slot_id}: {e}")

            if total_keys == 0:
                self._add_result(
                    "keys-present",
                    Severity.INFO,
                    True,
                    "No keys found in HSM"
                )
            else:
                self._add_result(
                    "keys-validated",
                    Severity.INFO,
                    True,
                    f"Validated {total_keys} key(s), found {weak_keys} issue(s)"
                )

        except Exception as e:
            self._log(f"Warning: Could not validate key attributes: {e}")

    def _validate_mechanisms(self):
        """Validate supported cryptographic mechanisms."""
        if not self.pkcs11_lib:
            return

        try:
            slots = self.pkcs11_lib.getSlotList(tokenPresent=True)
            if not slots:
                return

            required_mechanisms = {
                PyKCS11.CKM_RSA_PKCS_KEY_PAIR_GEN: "RSA key generation",
                PyKCS11.CKM_SHA256_RSA_PKCS: "RSA-SHA256 signing",
                PyKCS11.CKM_AES_KEY_GEN: "AES key generation",
                PyKCS11.CKM_AES_CBC: "AES-CBC encryption",
            }

            for slot_id in slots:
                mechanisms = self.pkcs11_lib.getMechanismList(slot_id)

                missing = []
                for mech_id, mech_name in required_mechanisms.items():
                    if mech_id not in mechanisms:
                        missing.append(mech_name)

                if missing:
                    self._add_result(
                        f"slot-{slot_id}-mechanisms",
                        Severity.WARNING,
                        False,
                        f"Slot {slot_id} missing mechanisms: {', '.join(missing)}",
                        details={"missing_mechanisms": missing}
                    )
                else:
                    self._add_result(
                        f"slot-{slot_id}-mechanisms",
                        Severity.INFO,
                        True,
                        f"Slot {slot_id} supports all required mechanisms"
                    )

        except Exception as e:
            self._log(f"Warning: Could not validate mechanisms: {e}")

    def _validate_compliance(self, standard: ComplianceStandard):
        """Validate compliance with standard."""
        if standard == ComplianceStandard.FIPS_140_2:
            self._validate_fips_140_2()
        elif standard == ComplianceStandard.PCI_DSS:
            self._validate_pci_dss()

    def _validate_fips_140_2(self):
        """Validate FIPS 140-2 compliance."""
        # Check if HSM is FIPS certified
        if self.vendor == HSMVendor.SOFTHSM:
            self._add_result(
                "fips-140-2",
                Severity.WARNING,
                False,
                "SoftHSM is not FIPS 140-2 certified",
                remediation="Use certified HSM for production"
            )
        else:
            self._add_result(
                "fips-140-2",
                Severity.INFO,
                True,
                f"{self.vendor.value} supports FIPS 140-2 compliance"
            )

        # Check for weak algorithms
        if self.pkcs11_lib:
            try:
                slots = self.pkcs11_lib.getSlotList(tokenPresent=True)
                for slot_id in slots:
                    mechanisms = self.pkcs11_lib.getMechanismList(slot_id)

                    # Check for deprecated mechanisms
                    deprecated = []
                    if PyKCS11.CKM_MD5 in mechanisms:
                        deprecated.append("MD5")
                    if PyKCS11.CKM_SHA_1 in mechanisms:
                        deprecated.append("SHA-1")

                    if deprecated:
                        self._add_result(
                            f"fips-deprecated-{slot_id}",
                            Severity.WARNING,
                            False,
                            f"Slot {slot_id} supports deprecated algorithms: {', '.join(deprecated)}",
                            remediation="Avoid using deprecated algorithms"
                        )

            except Exception as e:
                self._log(f"Warning: Could not validate FIPS compliance: {e}")

    def _validate_pci_dss(self):
        """Validate PCI-DSS compliance."""
        # Check for dual control
        self._add_result(
            "pci-dss-dual-control",
            Severity.INFO,
            True,
            "Manual verification required for dual control procedures"
        )

        # Check audit logging
        self._add_result(
            "pci-dss-audit-logging",
            Severity.INFO,
            True,
            "Manual verification required for audit logging configuration"
        )

    def _validate_security_configuration(self):
        """Validate security configuration."""
        # Check for default PINs
        if self.vendor == HSMVendor.SOFTHSM:
            self._add_result(
                "security-default-pin",
                Severity.WARNING,
                False,
                "Ensure default PINs have been changed",
                remediation="Change PIN: softhsm2-util --change-pin --slot 0"
            )

        # Check file permissions
        if self.hsm_config and self.hsm_config.config_path:
            stat_info = os.stat(self.hsm_config.config_path)
            mode = stat_info.st_mode & 0o777

            if mode & 0o044:
                self._add_result(
                    "security-config-readable",
                    Severity.WARNING,
                    False,
                    "Configuration file is world/group readable",
                    remediation=f"Restrict permissions: chmod 600 {self.hsm_config.config_path}"
                )

    def _add_result(
        self,
        check_id: str,
        severity: Severity,
        passed: bool,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        remediation: Optional[str] = None
    ):
        """Add validation result."""
        result = ValidationResult(
            check_id=check_id,
            severity=severity,
            passed=passed,
            message=message,
            details=details,
            remediation=remediation
        )
        self.results.append(result)

        if self.verbose:
            status = "✓" if passed else "✗"
            print(f"{status} [{severity.value.upper()}] {message}")

    def _log(self, message: str):
        """Log message if verbose."""
        if self.verbose:
            print(message)


def format_results_text(results: List[ValidationResult]) -> str:
    """Format results as text."""
    output = []
    output.append("HSM Configuration Validation Results")
    output.append("=" * 50)
    output.append("")

    # Group by severity
    by_severity = {severity: [] for severity in Severity}
    for result in results:
        by_severity[result.severity].append(result)

    # Display results
    for severity in [Severity.CRITICAL, Severity.ERROR, Severity.WARNING, Severity.INFO]:
        severity_results = by_severity[severity]
        if not severity_results:
            continue

        output.append(f"\n{severity.value.upper()}: {len(severity_results)} check(s)")
        output.append("-" * 50)

        for result in severity_results:
            status = "PASS" if result.passed else "FAIL"
            output.append(f"\n[{status}] {result.check_id}")
            output.append(f"  {result.message}")

            if result.remediation:
                output.append(f"  Remediation: {result.remediation}")

            if result.details:
                output.append(f"  Details: {json.dumps(result.details, indent=2)}")

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    output.append("\n" + "=" * 50)
    output.append(f"Total: {total} checks, {passed} passed, {failed} failed")

    return "\n".join(output)


def format_results_json(results: List[ValidationResult]) -> str:
    """Format results as JSON."""
    data = {
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "by_severity": {
                severity.value: sum(1 for r in results if r.severity == severity)
                for severity in Severity
            }
        },
        "checks": [
            {
                "check_id": r.check_id,
                "severity": r.severity.value,
                "passed": r.passed,
                "message": r.message,
                "details": r.details,
                "remediation": r.remediation,
            }
            for r in results
        ]
    }

    return json.dumps(data, indent=2)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Validate HSM configuration and PKCS#11 settings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate with auto-detection
  %(prog)s

  # Validate specific configuration
  %(prog)s --config /etc/softhsm2.conf --library /usr/lib/softhsm/libsofthsm2.so

  # Validate with compliance checks
  %(prog)s --compliance fips-140-2 --compliance pci-dss

  # JSON output
  %(prog)s --json
        """
    )

    parser.add_argument(
        "--config",
        help="Path to HSM configuration file"
    )

    parser.add_argument(
        "--library",
        help="Path to PKCS#11 library"
    )

    parser.add_argument(
        "--vendor",
        choices=[v.value for v in HSMVendor],
        help="HSM vendor (auto-detected if not specified)"
    )

    parser.add_argument(
        "--compliance",
        action="append",
        choices=[s.value for s in ComplianceStandard],
        help="Compliance standard to validate against (can specify multiple)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Parse vendor
    vendor = HSMVendor(args.vendor) if args.vendor else HSMVendor.UNKNOWN

    # Parse compliance standards
    compliance_standards = []
    if args.compliance:
        compliance_standards = [ComplianceStandard(s) for s in args.compliance]

    # Create validator
    validator = HSMConfigValidator(
        config_file=args.config,
        library_path=args.library,
        vendor=vendor,
        compliance_standards=compliance_standards,
        verbose=args.verbose
    )

    # Run validation
    results = validator.validate_all()

    # Output results
    if args.json:
        print(format_results_json(results))
    else:
        print(format_results_text(results))

    # Exit with error code if any checks failed
    failed = sum(1 for r in results if not r.passed and r.severity in [Severity.ERROR, Severity.CRITICAL])
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
