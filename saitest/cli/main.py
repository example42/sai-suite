"""Main CLI interface for saitest.

This module provides the command-line interface for saitest, including
the verify and test commands for software verification and validation.
"""

import asyncio
import logging
import sys
import subprocess
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

import click

from saitest import __version__


# Import logging configuration
from saitest.utils.logging_config import setup_logging, get_logger

# Initialize logger (will be configured per command)
logger = get_logger(__name__)


def check_docker_available() -> bool:
    """Check if Docker is available and running.
    
    Returns:
        True if Docker is available, False otherwise
    """
    try:
        # Try to run docker version command
        result = subprocess.run(
            ['docker', 'version'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False


def display_docker_installation_help() -> None:
    """Display helpful message about Docker installation."""
    click.echo()
    click.echo("=" * 60)
    click.echo("❌ Docker Not Found")
    click.echo("=" * 60)
    click.echo()
    click.echo("Saitest requires Docker to run software installations in")
    click.echo("isolated containers. Docker is not installed or not running.")
    click.echo()
    click.echo("📦 Installation Instructions:")
    click.echo()
    click.echo("  macOS:")
    click.echo("    • Download Docker Desktop from https://docker.com/products/docker-desktop")
    click.echo("    • Or install via Homebrew: brew install --cask docker")
    click.echo()
    click.echo("  Linux:")
    click.echo("    • Ubuntu/Debian: sudo apt-get install docker.io")
    click.echo("    • Fedora/RHEL: sudo dnf install docker")
    click.echo("    • Arch: sudo pacman -S docker")
    click.echo()
    click.echo("  Windows:")
    click.echo("    • Download Docker Desktop from https://docker.com/products/docker-desktop")
    click.echo()
    click.echo("After installation, make sure Docker is running:")
    click.echo("  • Start Docker Desktop (macOS/Windows)")
    click.echo("  • Or start the Docker daemon: sudo systemctl start docker (Linux)")
    click.echo()
    click.echo("Verify installation with: docker version")
    click.echo()
    click.echo("=" * 60)
    click.echo()


@click.group()
@click.version_option(version=__version__, prog_name="saitest")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Saitest - Agent-based software verification and saidata generation.
    
    Saitest uses LangGraph agents to automatically verify software installations
    across multiple platforms and providers, generating validated saidata files.
    
    Examples:
    
        # Verify nginx and generate saidata
        saitest verify nginx
        
        # Verify with specific platforms
        saitest verify apache --platforms ubuntu:22.04,debian:12
        
        # Test existing saidata
        saitest test software/nginx/default.yaml
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


@cli.command()
@click.argument('software', type=str)
@click.option(
    '--platforms', '-p',
    type=str,
    help='Comma-separated list of platforms to test (e.g., ubuntu:22.04,debian:12)'
)
@click.option(
    '--output-dir', '-o',
    type=click.Path(path_type=Path),
    default=Path('./saidata'),
    help='Output directory for generated saidata files (default: ./saidata)'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['yaml', 'json'], case_sensitive=False),
    default='yaml',
    help='Output format for saidata files (default: yaml)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output with detailed progress'
)
@click.pass_context
def verify(
    ctx: click.Context,
    software: str,
    platforms: Optional[str],
    output_dir: Path,
    format: str,
    verbose: bool
) -> None:
    """Verify software installation and generate saidata.
    
    This command runs the verification workflow for the specified software,
    testing installations across multiple platforms and providers, then
    generating validated saidata files.
    
    ARGUMENTS:
    
        SOFTWARE: Name of the software to verify (e.g., nginx, apache, redis)
    
    EXAMPLES:
    
        # Verify nginx with automatic platform selection
        saitest verify nginx
        
        # Verify apache on specific platforms
        saitest verify apache --platforms ubuntu:22.04,debian:12
        
        # Verify with custom output directory
        saitest verify redis --output-dir /path/to/output
        
        # Verbose mode for detailed progress
        saitest verify nginx --verbose
    """
    # Import here to avoid loading heavy dependencies at CLI startup
    from saitest.core.orchestrator import run_verification
    from saitest.agents.generation import write_saidata_files
    from pathlib import Path as PathLib
    
    # Configure logging based on verbose flag
    log_file = PathLib.home() / '.saitest' / 'logs' / f'verify-{software}-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'
    setup_logging(
        level=logging.INFO,
        log_file=log_file if verbose else None,
        verbose=verbose,
        quiet=False
    )
    
    # Check Docker availability
    if not check_docker_available():
        display_docker_installation_help()
        sys.exit(1)
    
    # Parse platforms if provided
    platform_list = None
    if platforms:
        platform_list = [p.strip() for p in platforms.split(',')]
        logger.info(f"Target platforms: {', '.join(platform_list)}")
    
    # Display start message
    click.echo(f"\n🔍 Starting verification for: {software}")
    if platform_list:
        click.echo(f"📦 Target platforms: {', '.join(platform_list)}")
    else:
        click.echo("📦 Platforms: Auto-select")
    click.echo(f"📁 Output directory: {output_dir}")
    click.echo()
    
    try:
        # Run verification workflow
        click.echo("⚙️  Running verification workflow...")
        
        # Run the async workflow
        result = asyncio.run(run_verification(
            software=software,
            platforms=platform_list,
            config={}
        ))
        
        # Display results
        click.echo()
        click.echo("=" * 60)
        click.echo("📊 Verification Results")
        click.echo("=" * 60)
        
        # Confidence score
        confidence = result.get('overall_confidence', 0.0)
        confidence_emoji = "✅" if confidence >= 0.7 else "⚠️" if confidence >= 0.5 else "❌"
        click.echo(f"{confidence_emoji} Overall Confidence: {confidence:.2%}")
        
        # Platform count
        platform_results = result.get('platform_results', [])
        click.echo(f"🖥️  Platforms Tested: {len(platform_results)}")
        
        # Show platform-provider combinations
        if platform_results and verbose:
            click.echo("\nTested combinations:")
            for pr in platform_results:
                status = "✓" if pr.success else "✗"
                click.echo(f"  {status} {pr.platform} with {pr.provider}")
        
        # Errors
        validation_errors = result.get('validation_errors', [])
        if validation_errors:
            click.echo(f"\n⚠️  Validation Errors: {len(validation_errors)}")
            if verbose:
                for error in validation_errors[:5]:  # Show first 5
                    click.echo(f"  - {error}")
        
        # Human review flag
        needs_review = result.get('needs_human_review', False)
        if needs_review:
            click.echo("\n⚠️  Human review recommended (low confidence or validation errors)")
        
        # Write saidata files
        generated_saidata = result.get('generated_saidata')
        if generated_saidata:
            click.echo()
            click.echo("📝 Writing saidata files...")
            
            write_saidata_files(
                software=software,
                saidata=generated_saidata,
                output_dir=output_dir
            )
            
            # Show file locations
            click.echo()
            click.echo("✅ Generated files:")
            click.echo(f"  📄 {output_dir / software / 'default.yaml'}")
            
            overrides = generated_saidata.get('overrides', {})
            for os_name, versions in overrides.items():
                for version in versions.keys():
                    click.echo(f"  📄 {output_dir / software / os_name / f'{version}.yaml'}")
        else:
            click.echo("\n❌ No saidata generated")
            sys.exit(1)
        
        # Messages
        messages = result.get('messages', [])
        if messages and verbose:
            click.echo("\n📋 Workflow Messages:")
            for msg in messages:
                click.echo(f"  • {msg}")
        
        click.echo()
        click.echo("=" * 60)
        
        # Exit with appropriate code
        if confidence < 0.5:
            click.echo("⚠️  Verification completed with low confidence")
            sys.exit(2)
        elif needs_review:
            click.echo("✅ Verification completed (review recommended)")
            sys.exit(0)
        else:
            click.echo("✅ Verification completed successfully")
            sys.exit(0)
            
    except KeyboardInterrupt:
        click.echo("\n\n⚠️  Verification cancelled by user")
        sys.exit(130)
    except Exception as e:
        click.echo(f"\n\n❌ Verification failed: {e}")
        if verbose:
            logger.exception("Detailed error:")
        sys.exit(1)


@cli.command()
@click.argument('saidata_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--platforms', '-p',
    type=str,
    help='Comma-separated list of platforms to test (e.g., ubuntu:22.04,debian:12)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output with detailed progress'
)
@click.pass_context
def test(
    ctx: click.Context,
    saidata_file: Path,
    platforms: Optional[str],
    verbose: bool
) -> None:
    """Test existing saidata file by verifying against actual installations.
    
    This command loads an existing saidata file, extracts the software name,
    runs the verification workflow, and compares the results with the existing
    saidata to calculate a match confidence score.
    
    ARGUMENTS:
    
        SAIDATA_FILE: Path to existing saidata file to test
    
    EXAMPLES:
    
        # Test a saidata file
        saitest test software/nginx/default.yaml
        
        # Test with specific platforms
        saitest test software/apache/default.yaml --platforms ubuntu:22.04,debian:12
        
        # Verbose mode for detailed comparison
        saitest test software/redis/default.yaml --verbose
    """
    # Import here to avoid loading heavy dependencies at CLI startup
    import yaml
    from saitest.core.orchestrator import run_verification
    from pathlib import Path as PathLib
    
    # Configure logging based on verbose flag
    log_file = PathLib.home() / '.saitest' / 'logs' / f'test-{saidata_file.stem}-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'
    setup_logging(
        level=logging.INFO,
        log_file=log_file if verbose else None,
        verbose=verbose,
        quiet=False
    )
    
    # Check Docker availability
    if not check_docker_available():
        display_docker_installation_help()
        sys.exit(1)
    
    # Load existing saidata
    click.echo(f"\n📄 Loading saidata from: {saidata_file}")
    
    try:
        with open(saidata_file, 'r') as f:
            existing_saidata = yaml.safe_load(f)
    except Exception as e:
        click.echo(f"❌ Failed to load saidata file: {e}")
        sys.exit(1)
    
    # Extract software name from metadata
    metadata = existing_saidata.get('metadata', {})
    software = metadata.get('name')
    
    if not software:
        click.echo("❌ No software name found in saidata metadata")
        sys.exit(1)
    
    click.echo(f"🔍 Testing software: {software}")
    
    # Parse platforms if provided
    platform_list = None
    if platforms:
        platform_list = [p.strip() for p in platforms.split(',')]
        logger.info(f"Target platforms: {', '.join(platform_list)}")
    
    # Display start message
    if platform_list:
        click.echo(f"📦 Target platforms: {', '.join(platform_list)}")
    else:
        click.echo("📦 Platforms: Auto-select")
    click.echo()
    
    try:
        # Run verification workflow
        click.echo("⚙️  Running verification workflow...")
        
        result = asyncio.run(run_verification(
            software=software,
            platforms=platform_list,
            config={'input_saidata': existing_saidata}
        ))
        
        # Display results
        click.echo()
        click.echo("=" * 60)
        click.echo("📊 Test Results")
        click.echo("=" * 60)
        
        # Confidence score
        confidence = result.get('overall_confidence', 0.0)
        confidence_emoji = "✅" if confidence >= 0.7 else "⚠️" if confidence >= 0.5 else "❌"
        click.echo(f"{confidence_emoji} Overall Confidence: {confidence:.2%}")
        
        # Platform count
        platform_results = result.get('platform_results', [])
        click.echo(f"🖥️  Platforms Tested: {len(platform_results)}")
        
        # Show platform-provider combinations
        if platform_results and verbose:
            click.echo("\nTested combinations:")
            for pr in platform_results:
                status = "✓" if pr.success else "✗"
                click.echo(f"  {status} {pr.platform} with {pr.provider}")
        
        # Compare with existing saidata
        click.echo()
        click.echo("🔄 Comparison with existing saidata:")
        
        generated_saidata = result.get('generated_saidata', {})
        if generated_saidata:
            # Calculate match confidence
            match_score = calculate_match_confidence(existing_saidata, generated_saidata)
            match_emoji = "✅" if match_score >= 0.8 else "⚠️" if match_score >= 0.6 else "❌"
            click.echo(f"{match_emoji} Match Confidence: {match_score:.2%}")
            
            if verbose:
                # Show detailed comparison
                click.echo("\nDetailed comparison:")
                comparison = compare_saidata_details(existing_saidata, generated_saidata)
                for key, value in comparison.items():
                    click.echo(f"  {key}: {value}")
        else:
            click.echo("❌ No saidata generated for comparison")
        
        # Validation errors
        validation_errors = result.get('validation_errors', [])
        if validation_errors:
            click.echo(f"\n⚠️  Validation Errors: {len(validation_errors)}")
            if verbose:
                for error in validation_errors[:5]:  # Show first 5
                    click.echo(f"  - {error}")
        
        # Messages
        messages = result.get('messages', [])
        if messages and verbose:
            click.echo("\n📋 Workflow Messages:")
            for msg in messages:
                click.echo(f"  • {msg}")
        
        click.echo()
        click.echo("=" * 60)
        
        # Exit with appropriate code based on match confidence
        if generated_saidata:
            match_score = calculate_match_confidence(existing_saidata, generated_saidata)
            if match_score >= 0.8:
                click.echo("✅ Test passed - saidata matches verification results")
                sys.exit(0)
            elif match_score >= 0.6:
                click.echo("⚠️  Test passed with warnings - some differences detected")
                sys.exit(0)
            else:
                click.echo("❌ Test failed - significant differences detected")
                sys.exit(1)
        else:
            click.echo("❌ Test failed - no verification results generated")
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\n\n⚠️  Test cancelled by user")
        sys.exit(130)
    except Exception as e:
        click.echo(f"\n\n❌ Test failed: {e}")
        if verbose:
            logger.exception("Detailed error:")
        sys.exit(1)


def calculate_match_confidence(existing: Dict, generated: Dict) -> float:
    """Calculate confidence score for how well generated saidata matches existing.
    
    Args:
        existing: Existing saidata dictionary
        generated: Generated saidata dictionary (may include 'default' and 'overrides')
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    # Extract default saidata if generated has overrides structure
    if 'default' in generated:
        generated_default = generated['default']
    else:
        generated_default = generated
    
    # Compare key sections
    scores = []
    
    # Compare packages
    existing_packages = existing.get('packages', [])
    generated_packages = generated_default.get('packages', [])
    if existing_packages or generated_packages:
        package_score = compare_lists(
            [p.get('package_name', p.get('name')) for p in existing_packages],
            [p.get('package_name', p.get('name')) for p in generated_packages]
        )
        scores.append(package_score)
    
    # Compare services
    existing_services = existing.get('services', [])
    generated_services = generated_default.get('services', [])
    if existing_services or generated_services:
        service_score = compare_lists(
            [s.get('name') for s in existing_services],
            [s.get('name') for s in generated_services]
        )
        scores.append(service_score)
    
    # Compare files
    existing_files = existing.get('files', [])
    generated_files = generated_default.get('files', [])
    if existing_files or generated_files:
        file_score = compare_lists(
            [f.get('path') for f in existing_files],
            [f.get('path') for f in generated_files]
        )
        scores.append(file_score)
    
    # Compare commands
    existing_commands = existing.get('commands', [])
    generated_commands = generated_default.get('commands', [])
    if existing_commands or generated_commands:
        command_score = compare_lists(
            [c.get('name') for c in existing_commands],
            [c.get('name') for c in generated_commands]
        )
        scores.append(command_score)
    
    # Compare ports
    existing_ports = existing.get('ports', [])
    generated_ports = generated_default.get('ports', [])
    if existing_ports or generated_ports:
        port_score = compare_lists(
            [p.get('number') for p in existing_ports],
            [p.get('number') for p in generated_ports]
        )
        scores.append(port_score)
    
    # Return average score
    return sum(scores) / len(scores) if scores else 0.0


def compare_lists(list1: list, list2: list) -> float:
    """Compare two lists and return similarity score.
    
    Args:
        list1: First list
        list2: Second list
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not list1 and not list2:
        return 1.0
    
    if not list1 or not list2:
        return 0.0
    
    set1 = set(filter(None, list1))
    set2 = set(filter(None, list2))
    
    if not set1 and not set2:
        return 1.0
    
    if not set1 or not set2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0


def compare_saidata_details(existing: Dict, generated: Dict) -> Dict[str, str]:
    """Generate detailed comparison between existing and generated saidata.
    
    Args:
        existing: Existing saidata dictionary
        generated: Generated saidata dictionary
    
    Returns:
        Dictionary with comparison details
    """
    # Extract default saidata if generated has overrides structure
    if 'default' in generated:
        generated_default = generated['default']
    else:
        generated_default = generated
    
    details = {}
    
    # Packages
    existing_pkgs = set(p.get('package_name', p.get('name')) for p in existing.get('packages', []))
    generated_pkgs = set(p.get('package_name', p.get('name')) for p in generated_default.get('packages', []))
    details['Packages'] = f"{len(existing_pkgs & generated_pkgs)}/{len(existing_pkgs | generated_pkgs)} match"
    
    # Services
    existing_svcs = set(s.get('name') for s in existing.get('services', []))
    generated_svcs = set(s.get('name') for s in generated_default.get('services', []))
    details['Services'] = f"{len(existing_svcs & generated_svcs)}/{len(existing_svcs | generated_svcs)} match"
    
    # Files
    existing_files = set(f.get('path') for f in existing.get('files', []))
    generated_files = set(f.get('path') for f in generated_default.get('files', []))
    details['Files'] = f"{len(existing_files & generated_files)}/{len(existing_files | generated_files)} match"
    
    # Commands
    existing_cmds = set(c.get('name') for c in existing.get('commands', []))
    generated_cmds = set(c.get('name') for c in generated_default.get('commands', []))
    details['Commands'] = f"{len(existing_cmds & generated_cmds)}/{len(existing_cmds | generated_cmds)} match"
    
    # Ports
    existing_ports = set(p.get('number') for p in existing.get('ports', []))
    generated_ports = set(p.get('number') for p in generated_default.get('ports', []))
    details['Ports'] = f"{len(existing_ports & generated_ports)}/{len(existing_ports | generated_ports)} match"
    
    return details


def main() -> None:
    """Entry point for the saitest CLI."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
