#!/usr/bin/env python3
"""
Demo script showing the template engine functionality.

This script demonstrates how the template resolution engine works
with various saidata structures and template patterns.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sai.providers.template_engine import TemplateEngine, SaidataContextBuilder
from sai.models.provider_data import Action, Step
from saigen.models.saidata import (
    SaiData,
    Metadata,
    Package,
    Service,
    File,
    Directory,
    Command,
    Port,
    Container,
    ServiceType,
    FileType,
    Protocol,
)


def demo_basic_templates():
    """Demonstrate basic template resolution."""
    print("=== Basic Template Resolution ===")
    
    # Create sample saidata
    metadata = Metadata(
        name="nginx",
        display_name="Nginx Web Server",
        version="1.20.1",
        description="High-performance web server and reverse proxy",
        category="web",
        license="BSD-2-Clause",
    )
    
    packages = [
        Package(name="nginx", version="1.20.1"),
        Package(name="nginx-common"),
        Package(name="nginx-extras"),
    ]
    
    services = [
        Service(name="nginx", service_name="nginx", type=ServiceType.SYSTEMD, enabled=True),
    ]
    
    saidata = SaiData(
        version="0.2",
        metadata=metadata,
        packages=packages,
        services=services,
    )
    
    engine = TemplateEngine()
    
    # Basic metadata templates
    templates = [
        "Installing {{display_name}} ({{name}}) version {{version}}",
        "Package: {{name}} - {{metadata.description}}",
        "License: {{metadata.license}}",
    ]
    
    for template in templates:
        result = engine.resolve_template(template, saidata)
        print(f"Template: {template}")
        print(f"Result:   {result}")
        print()


def demo_array_expansion():
    """Demonstrate array expansion functionality."""
    print("=== Array Expansion Templates ===")
    
    metadata = Metadata(name="lamp-stack", display_name="LAMP Stack")
    packages = [
        Package(name="apache2", version="2.4.41"),
        Package(name="mysql-server", version="8.0.28"),
        Package(name="php", version="7.4.3"),
        Package(name="php-mysql"),
        Package(name="libapache2-mod-php"),
    ]
    
    services = [
        Service(name="apache2", service_name="apache2", type=ServiceType.SYSTEMD),
        Service(name="mysql", service_name="mysql", type=ServiceType.SYSTEMD),
    ]
    
    saidata = SaiData(
        version="0.2",
        metadata=metadata,
        packages=packages,
        services=services,
    )
    
    engine = TemplateEngine()
    
    # Array expansion templates
    templates = [
        "apt-get install -y {{saidata.packages.*.name}}",
        "systemctl enable {{saidata.services.*.service_name}}",
        "systemctl start {{saidata.services.*.service_name}}",
    ]
    
    for template in templates:
        result = engine.resolve_template(template, saidata)
        print(f"Template: {template}")
        print(f"Result:   {result}")
        print()


def demo_complex_templates():
    """Demonstrate complex template scenarios."""
    print("=== Complex Template Scenarios ===")
    
    metadata = Metadata(name="postgresql", version="13.7", display_name="PostgreSQL")
    packages = [
        Package(name="postgresql-13", version="13.7"),
        Package(name="postgresql-client-13"),
        Package(name="postgresql-contrib-13"),
    ]
    
    services = [
        Service(name="postgresql", service_name="postgresql", type=ServiceType.SYSTEMD),
    ]
    
    files = [
        File(name="postgresql.conf", path="/etc/postgresql/13/main/postgresql.conf", type=FileType.CONFIG),
        File(name="pg_hba.conf", path="/etc/postgresql/13/main/pg_hba.conf", type=FileType.CONFIG),
    ]
    
    directories = [
        Directory(name="data", path="/var/lib/postgresql/13/main", owner="postgres", mode="700"),
        Directory(name="logs", path="/var/log/postgresql", owner="postgres", mode="755"),
    ]
    
    ports = [
        Port(port=5432, protocol=Protocol.TCP, service="postgresql"),
    ]
    
    saidata = SaiData(
        version="0.2",
        metadata=metadata,
        packages=packages,
        services=services,
        files=files,
        directories=directories,
        ports=ports,
    )
    
    engine = TemplateEngine()
    
    # Complex templates with conditionals
    templates = [
        # Conditional installation
        """
        {%- if version -%}
        apt-get install -y {{saidata.packages.*.name}}={{version}}*
        {%- else -%}
        apt-get install -y {{saidata.packages.*.name}}
        {%- endif -%}
        """,
        
        # File operations
        "chown {{saidata.directories.0.owner}} {{saidata.directories.*.path}}",
        
        # Port configuration
        "Opening port {{saidata.ports.0.port}}/{{saidata.ports.0.protocol}} for {{saidata.ports.0.service}}",
        
        # Service management
        "systemctl enable {{saidata.services.*.service_name}} && systemctl start {{saidata.services.*.service_name}}",
    ]
    
    for template in templates:
        result = engine.resolve_template(template, saidata)
        print(f"Template: {template.strip()}")
        print(f"Result:   {result}")
        print()


def demo_action_resolution():
    """Demonstrate action template resolution."""
    print("=== Action Template Resolution ===")
    
    metadata = Metadata(name="redis", version="6.2.7", display_name="Redis")
    packages = [Package(name="redis-server", version="6.2.7")]
    services = [Service(name="redis", service_name="redis-server", type=ServiceType.SYSTEMD)]
    
    saidata = SaiData(
        version="0.2",
        metadata=metadata,
        packages=packages,
        services=services,
    )
    
    # Create a multi-step action
    steps = [
        Step(
            name="Install Redis",
            command="apt-get update && apt-get install -y {{saidata.packages.*.name}}",
        ),
        Step(
            name="Configure Redis",
            command="sed -i 's/^# maxmemory <bytes>/maxmemory 256mb/' /etc/redis/redis.conf",
        ),
        Step(
            name="Start Redis service",
            command="systemctl start {{saidata.services.*.service_name}}",
        ),
        Step(
            name="Enable Redis service",
            command="systemctl enable {{saidata.services.*.service_name}}",
        ),
    ]
    
    action = Action(
        description="Install and configure Redis server",
        steps=steps,
        timeout=300,
        rollback="systemctl stop {{saidata.services.*.service_name}} && apt-get remove -y {{saidata.packages.*.name}}",
        variables={
            "config_file": "/etc/redis/redis.conf",
            "data_dir": "/var/lib/redis",
            "log_file": "/var/log/redis/redis-server.log",
        }
    )
    
    engine = TemplateEngine()
    result = engine.resolve_action_template(action, saidata)
    
    print("Action Description:", action.description)
    print("Resolved Steps:")
    for i, step in enumerate(result['steps'], 1):
        print(f"  {i}. {step['name']}")
        print(f"     Command: {step['command']}")
    
    print(f"\nRollback Command: {result['rollback']}")
    print(f"Variables: {result['variables']}")
    print()


def demo_additional_context():
    """Demonstrate templates with additional context."""
    print("=== Templates with Additional Context ===")
    
    metadata = Metadata(name="custom-app", version="1.0.0")
    saidata = SaiData(version="0.2", metadata=metadata)
    
    additional_context = {
        'install_prefix': '/opt/custom-app',
        'user': 'appuser',
        'group': 'appgroup',
        'port': 8080,
        'environment': 'production',
    }
    
    templates = [
        "Installing {{display_name}} to {{install_prefix}}",
        "Creating user {{user}} in group {{group}}",
        "Service will run on port {{port}} in {{environment}} mode",
        "mkdir -p {{install_prefix}}/{bin,etc,var/log} && chown -R {{user}}:{{group}} {{install_prefix}}",
    ]
    
    engine = TemplateEngine()
    
    for template in templates:
        result = engine.resolve_template(template, saidata, additional_context)
        print(f"Template: {template}")
        print(f"Result:   {result}")
        print()


def main():
    """Run all template engine demonstrations."""
    print("SAI Template Engine Demonstration")
    print("=" * 50)
    print()
    
    try:
        demo_basic_templates()
        demo_array_expansion()
        demo_complex_templates()
        demo_action_resolution()
        demo_additional_context()
        
        print("=== Demo Complete ===")
        print("The template engine successfully resolved all templates!")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())