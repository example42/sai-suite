#!/usr/bin/env python3
"""
Demonstration of SAI's new consistent output formatting.

This script shows how the SAI CLI now provides:
- Clear separation between different providers
- Highlighted provider names and commands
- Color-coded output (stdout in white, stderr in red)
- Consistent formatting across all actions
"""

import sys
import os

# Add the parent directory to the path so we can import sai modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sai.utils.output_formatter import OutputFormatter, OutputType
import click


def demo_single_provider():
    """Demonstrate output for a single provider action."""
    print(click.style("=== Single Provider Action ===", bold=True))
    
    formatter = OutputFormatter(quiet=False, verbose=False)
    
    # Simulate successful installation
    formatter.print_single_provider_output(
        provider_name="apt",
        command="sudo apt install nginx",
        stdout="Reading package lists... Done\nBuilding dependency tree... Done\nThe following NEW packages will be installed:\n  nginx\n0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.\nNeed to get 3,596 B of archives.\nAfter this operation, 40.0 kB of additional disk space will be used.\nGet:1 http://archive.ubuntu.com/ubuntu jammy/main amd64 nginx all 1.18.0-6ubuntu14.3 [3,596 B]\nFetched 3,596 B in 0s (15.2 kB/s)\nSelecting previously unselected package nginx.\n(Reading database ... 185534 files and directories currently installed.)\nPreparing to unpack .../nginx_1.18.0-6ubuntu14.3_all.deb ...\nUnpacking nginx (1.18.0-6ubuntu14.3) ...\nSetting up nginx (1.18.0-6ubuntu14.3) ...",
        success=True,
        show_provider=False
    )
    
    print("\n" + "="*50 + "\n")


def demo_multiple_providers():
    """Demonstrate output for multiple providers (informational action)."""
    print(click.style("=== Multiple Providers (Info Action) ===", bold=True))
    
    formatter = OutputFormatter(quiet=False, verbose=False)
    
    # Simulate info command on multiple providers
    providers_data = [
        {
            "name": "apt",
            "command": "apt show nginx",
            "stdout": "Package: nginx\nVersion: 1.18.0-6ubuntu14.3\nPriority: optional\nSection: web\nOrigin: Ubuntu\nMaintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>\nBugs: https://bugs.launchpad.net/ubuntu/+filebug\nInstalled-Size: 40.0 kB\nDepends: nginx-core (<< 1.18.0-6ubuntu14.3.1~) | nginx-full (<< 1.18.0-6ubuntu14.3.1~) | nginx-light (<< 1.18.0-6ubuntu14.3.1~) | nginx-extras (<< 1.18.0-6ubuntu14.3.1~), nginx-core (>= 1.18.0-6ubuntu14.3) | nginx-full (>= 1.18.0-6ubuntu14.3) | nginx-light (>= 1.18.0-6ubuntu14.3) | nginx-extras (>= 1.18.0-6ubuntu14.3)\nHomepage: http://nginx.org\nDownload-Size: 3,596 B\nAPT-Manual-Installed: no\nAPT-Sources: http://archive.ubuntu.com/ubuntu jammy/main amd64 Packages\nDescription: small, powerful, scalable web/proxy server\n nginx (\"engine X\") is a high-performance web and reverse proxy server\n created by Igor Sysoev. It can be used both as a standalone web server\n and as a reverse proxy server before some Apache or another web server\n to reduce the load to backend servers by many times.",
            "stderr": "",
            "success": True
        },
        {
            "name": "snap",
            "command": "snap info nginx",
            "stdout": "name:      nginx\nsummary:   Nginx HTTP server\npublisher: Canonical✓\nstore-url: https://snapcraft.io/nginx\ncontact:   https://github.com/canonical/nginx-snap/issues\nlicense:   unset\ndescription: |\n  Nginx [engine x] is an HTTP and reverse proxy server, a mail proxy server, and a generic\n  TCP/UDP proxy server, originally written by Igor Sysoev.\ncommands:\n  - nginx\nservices:\n  nginx.daemon: simple, enabled, active\nsnap-id:      kJWM6jE9OfyAWJO5VkqpYJG7ZbqKuUuM\ntracking:     latest/stable\nrefresh-date: today at 14:32 UTC\nchannels:\n  latest/stable:    1.18.0 2023-02-07 (598) 2MB -\n  latest/candidate: ↑\n  latest/beta:      ↑\n  latest/edge:      1.25.3 2023-10-24 (1004) 2MB -\ninstalled:          1.18.0            (598) 2MB disabled",
            "stderr": "",
            "success": True
        },
        {
            "name": "brew",
            "command": "brew info nginx",
            "stdout": "",
            "stderr": "Error: No available formula with name \"nginx\".\n==> Searching for similarly named formulae...\nError: No similarly named formulae found.\n==> Searching for a previously deleted formula (in the last month)...\nError: No previously deleted formula found.\n==> Searching taps on GitHub...\nError: No formulae found in taps.",
            "success": False
        }
    ]
    
    for provider_data in providers_data:
        formatter.print_provider_section(
            provider_name=provider_data["name"],
            command=provider_data["command"],
            stdout=provider_data["stdout"],
            stderr=provider_data["stderr"],
            success=provider_data["success"],
            show_command=True
        )
    
    print("\n" + "="*50 + "\n")


def demo_verbose_mode():
    """Demonstrate verbose mode output."""
    print(click.style("=== Verbose Mode ===", bold=True))
    
    formatter = OutputFormatter(quiet=False, verbose=True)
    
    # Show command execution with multiple steps
    commands = [
        "sudo apt update",
        "sudo apt install -y nginx",
        "sudo systemctl enable nginx",
        "sudo systemctl start nginx"
    ]
    
    formatter.print_info_message("Installing and configuring nginx...")
    formatter.print_commands_list(commands, "Commands to be executed")
    
    # Simulate execution
    formatter.print_provider_section(
        provider_name="apt",
        command="sudo apt install -y nginx",
        stdout="Reading package lists... Done\nBuilding dependency tree... Done\nnginx is already the newest version (1.18.0-6ubuntu14.3).\n0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.",
        stderr="",
        success=True,
        show_command=True
    )
    
    formatter.print_success_message("Installation completed successfully")
    formatter.print_info_message("Execution time: 2.34s")
    formatter.print_info_message("Success rate: 100.0%")
    
    print("\n" + "="*50 + "\n")


def demo_error_handling():
    """Demonstrate error output formatting."""
    print(click.style("=== Error Handling ===", bold=True))
    
    formatter = OutputFormatter(quiet=False, verbose=True)
    
    # Simulate failed installation
    formatter.print_provider_section(
        provider_name="apt",
        command="sudo apt install nonexistent-package",
        stdout="Reading package lists... Done\nBuilding dependency tree... Done",
        stderr="E: Unable to locate package nonexistent-package\nE: Couldn't find any package by glob 'nonexistent-package'\nE: Couldn't find any package by regex 'nonexistent-package'",
        success=False,
        show_command=True
    )
    
    formatter.print_error_message(
        "Package installation failed", 
        "Package 'nonexistent-package' not found in any repository"
    )
    
    formatter.print_warning_message("Consider checking package name spelling or updating package lists")
    
    print("\n" + "="*50 + "\n")


def demo_quiet_mode():
    """Demonstrate quiet mode output."""
    print(click.style("=== Quiet Mode ===", bold=True))
    
    formatter = OutputFormatter(quiet=True, verbose=False)
    
    print("In quiet mode, only essential output is shown:")
    
    # This would normally show headers and commands, but in quiet mode only shows output
    formatter.print_provider_section(
        provider_name="apt",
        command="apt list --installed | grep nginx",
        stdout="nginx/jammy,now 1.18.0-6ubuntu14.3 all [installed,automatic]\nnginx-common/jammy,now 1.18.0-6ubuntu14.3 all [installed,automatic]\nnginx-core/jammy,now 1.18.0-6ubuntu14.3 amd64 [installed,automatic]",
        stderr="",
        success=True,
        show_command=True
    )
    
    print("\n" + "="*50 + "\n")


if __name__ == "__main__":
    print(click.style("SAI Output Formatting Demonstration", bold=True, fg='cyan'))
    print("This demo shows the new consistent output formatting across SAI commands.\n")
    
    demo_single_provider()
    demo_multiple_providers()
    demo_verbose_mode()
    demo_error_handling()
    demo_quiet_mode()
    
    print(click.style("Key Features:", bold=True, fg='green'))
    print("✓ Clear provider separation with styled headers")
    print("✓ Highlighted commands with provider context")
    print("✓ Color-coded output (white for stdout, red for stderr)")
    print("✓ Consistent success/error/warning message formatting")
    print("✓ Responsive to quiet/verbose modes")
    print("✓ Sensitive information redaction in commands")