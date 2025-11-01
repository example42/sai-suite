"""Sample observation fixtures for testing.

This module provides pre-configured Observation objects for use in tests.
"""

from saitest.models.observation import Observation


# File observations
FILE_OBSERVATION_NGINX_BINARY = Observation(
    type="file",
    platform="ubuntu:22.04",
    provider="apt",
    timestamp="2025-10-30T10:30:00Z",
    data={"path": "/usr/bin/nginx", "purpose": "binary"},
    confidence=1.0
)

FILE_OBSERVATION_NGINX_CONFIG = Observation(
    type="file",
    platform="ubuntu:22.04",
    provider="apt",
    timestamp="2025-10-30T10:30:05Z",
    data={"path": "/etc/nginx/nginx.conf", "purpose": "config"},
    confidence=0.95
)

FILE_OBSERVATION_APACHE_BINARY = Observation(
    type="file",
    platform="debian:12",
    provider="apt",
    timestamp="2025-10-30T10:35:00Z",
    data={"path": "/usr/sbin/apache2", "purpose": "binary"},
    confidence=1.0
)

FILE_OBSERVATION_APACHE_CONFIG = Observation(
    type="file",
    platform="debian:12",
    provider="apt",
    timestamp="2025-10-30T10:35:05Z",
    data={"path": "/etc/apache2/apache2.conf", "purpose": "config"},
    confidence=0.95
)

# Service observations
SERVICE_OBSERVATION_NGINX = Observation(
    type="service",
    platform="ubuntu:22.04",
    provider="apt",
    timestamp="2025-10-30T10:30:10Z",
    data={
        "path": "/lib/systemd/system/nginx.service",
        "name": "nginx",
        "enabled": True
    },
    confidence=0.9
)

SERVICE_OBSERVATION_APACHE = Observation(
    type="service",
    platform="debian:12",
    provider="apt",
    timestamp="2025-10-30T10:35:10Z",
    data={
        "path": "/lib/systemd/system/apache2.service",
        "name": "apache2",
        "enabled": True
    },
    confidence=0.9
)

# Port observations
PORT_OBSERVATION_HTTP = Observation(
    type="port",
    platform="ubuntu:22.04",
    provider="apt",
    timestamp="2025-10-30T10:30:15Z",
    data={"port": 80, "protocol": "tcp"},
    confidence=0.8
)

PORT_OBSERVATION_HTTPS = Observation(
    type="port",
    platform="ubuntu:22.04",
    provider="apt",
    timestamp="2025-10-30T10:30:20Z",
    data={"port": 443, "protocol": "tcp"},
    confidence=0.8
)

# Command observations
COMMAND_OBSERVATION_NGINX = Observation(
    type="command",
    platform="ubuntu:22.04",
    provider="apt",
    timestamp="2025-10-30T10:30:25Z",
    data={"name": "nginx", "path": "/usr/bin/nginx"},
    confidence=1.0
)

COMMAND_OBSERVATION_APACHE = Observation(
    type="command",
    platform="debian:12",
    provider="apt",
    timestamp="2025-10-30T10:35:15Z",
    data={"name": "apache2", "path": "/usr/sbin/apache2"},
    confidence=1.0
)

# Package observations
PACKAGE_OBSERVATION_NGINX_APT = Observation(
    type="package",
    platform="ubuntu:22.04",
    provider="apt",
    timestamp="2025-10-30T10:30:30Z",
    data={
        "name": "nginx",
        "package_name": "nginx-full",
        "version": "1.18.0"
    },
    confidence=1.0
)

PACKAGE_OBSERVATION_NGINX_PIP = Observation(
    type="package",
    platform="ubuntu:22.04",
    provider="pip",
    timestamp="2025-10-30T10:40:00Z",
    data={
        "name": "nginx",
        "package_name": "nginx-config-builder",
        "version": "0.5.2"
    },
    confidence=0.7
)

# Multi-provider observations for the same software
NGINX_OBSERVATIONS_APT = [
    FILE_OBSERVATION_NGINX_BINARY,
    FILE_OBSERVATION_NGINX_CONFIG,
    SERVICE_OBSERVATION_NGINX,
    PORT_OBSERVATION_HTTP,
    PORT_OBSERVATION_HTTPS,
    COMMAND_OBSERVATION_NGINX,
    PACKAGE_OBSERVATION_NGINX_APT
]

NGINX_OBSERVATIONS_PIP = [
    Observation(
        type="file",
        platform="ubuntu:22.04",
        provider="pip",
        timestamp="2025-10-30T10:40:05Z",
        data={"path": "/usr/local/bin/nginx-config-builder", "purpose": "binary"},
        confidence=0.8
    ),
    PACKAGE_OBSERVATION_NGINX_PIP
]

# Platform-specific observations
DEBIAN_OBSERVATIONS = [
    FILE_OBSERVATION_APACHE_BINARY,
    FILE_OBSERVATION_APACHE_CONFIG,
    SERVICE_OBSERVATION_APACHE,
    COMMAND_OBSERVATION_APACHE,
    Observation(
        type="package",
        platform="debian:12",
        provider="apt",
        timestamp="2025-10-30T10:35:20Z",
        data={
            "name": "apache2",
            "package_name": "apache2",
            "version": "2.4.57"
        },
        confidence=1.0
    )
]

# Low confidence observations (for testing quality checks)
LOW_CONFIDENCE_OBSERVATIONS = [
    Observation(
        type="file",
        platform="ubuntu:22.04",
        provider="source",
        timestamp="2025-10-30T11:00:00Z",
        data={"path": "/opt/custom/bin/app", "purpose": "binary"},
        confidence=0.4
    ),
    Observation(
        type="service",
        platform="ubuntu:22.04",
        provider="source",
        timestamp="2025-10-30T11:00:05Z",
        data={"path": "/etc/systemd/system/custom.service", "name": "custom"},
        confidence=0.3
    )
]

# All sample observations
ALL_OBSERVATIONS = (
    NGINX_OBSERVATIONS_APT +
    NGINX_OBSERVATIONS_PIP +
    DEBIAN_OBSERVATIONS +
    LOW_CONFIDENCE_OBSERVATIONS
)
