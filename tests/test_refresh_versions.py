"""Tests for refresh-versions command."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from saigen.cli.main import cli
from saigen.models.saidata import SaiData, Metadata, Package
import yaml


@pytest.fixture
def sample_saidata_file(tmp_path):
    """Create a sample saidata file for testing."""
    saidata_path = tmp_path / "test-nginx.yaml"
    
    saidata_content = {
        'version': '0.3',
        'metadata': {
            'name': 'nginx',
            'display_name': 'Nginx',
            'description': 'HTTP server',
            'version': '1.20.0'
        },
        'packages': [
            {
                'name': 'nginx',
                'package_name': 'nginx',
                'version': '1.20.0'
            }
        ],
        'providers': {
            'apt': {
                'packages': [
                    {
                        'name': 'nginx',
                        'package_name': 'nginx',
                        'version': '1.20.0'
                    }
                ]
            }
        }
    }
    
    with open(saidata_path, 'w') as f:
        yaml.dump(saidata_content, f)
    
    return saidata_path


def test_refresh_versions_help():
    """Test that refresh-versions command shows help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['refresh-versions', '--help'])
    
    assert result.exit_code == 0
    assert 'Refresh package versions' in result.output
    assert '--check-only' in result.output
    assert '--providers' in result.output


def test_refresh_versions_dry_run(sample_saidata_file):
    """Test refresh-versions in dry-run mode."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        '--dry-run',
        'refresh-versions',
        str(sample_saidata_file)
    ])
    
    assert result.exit_code == 0
    assert '[DRY RUN]' in result.output
    assert 'Would refresh versions' in result.output


def test_refresh_versions_check_only(sample_saidata_file):
    """Test refresh-versions in check-only mode."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        'refresh-versions',
        '--check-only',
        str(sample_saidata_file)
    ])
    
    # Should complete without error
    assert result.exit_code == 0
    assert 'Check Results' in result.output


def test_refresh_versions_with_backup(sample_saidata_file, tmp_path):
    """Test that backup is created."""
    runner = CliRunner()
    
    # Run with backup enabled (default)
    result = runner.invoke(cli, [
        'refresh-versions',
        '--check-only',  # Use check-only to avoid actual updates
        str(sample_saidata_file)
    ])
    
    assert result.exit_code == 0


def test_refresh_versions_invalid_file():
    """Test refresh-versions with non-existent file."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        'refresh-versions',
        'nonexistent.yaml'
    ])
    
    assert result.exit_code != 0


def test_refresh_versions_providers_filter(sample_saidata_file):
    """Test refresh-versions with provider filter."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        'refresh-versions',
        '--check-only',
        '--providers', 'apt',
        str(sample_saidata_file)
    ])
    
    assert result.exit_code == 0


def test_collect_packages_from_saidata():
    """Test package collection from saidata."""
    from saigen.cli.commands.refresh_versions import _collect_packages_from_saidata
    
    # Create a sample saidata
    saidata = SaiData(
        version='0.3',
        metadata=Metadata(name='test'),
        packages=[
            Package(name='pkg1', package_name='pkg1', version='1.0.0')
        ]
    )
    
    packages = _collect_packages_from_saidata(saidata, None)
    
    assert len(packages) == 1
    assert packages[0]['package_name'] == 'pkg1'
    assert packages[0]['current_version'] == '1.0.0'


def test_collect_packages_with_provider_filter():
    """Test package collection with provider filter."""
    from saigen.cli.commands.refresh_versions import _collect_packages_from_saidata
    from saigen.models.saidata import ProviderConfig
    
    # Create saidata with multiple providers
    saidata = SaiData(
        version='0.3',
        metadata=Metadata(name='test'),
        providers={
            'apt': ProviderConfig(
                packages=[Package(name='pkg1', package_name='pkg1', version='1.0.0')]
            ),
            'brew': ProviderConfig(
                packages=[Package(name='pkg2', package_name='pkg2', version='2.0.0')]
            )
        }
    )
    
    # Filter for apt only
    packages = _collect_packages_from_saidata(saidata, ['apt'])
    
    assert len(packages) == 1
    assert packages[0]['provider'] == 'apt'
    assert packages[0]['package_name'] == 'pkg1'


def test_load_saidata(sample_saidata_file):
    """Test loading saidata from file."""
    from saigen.cli.commands.refresh_versions import _load_saidata
    
    saidata = _load_saidata(sample_saidata_file)
    
    assert saidata.metadata.name == 'nginx'
    assert len(saidata.packages) == 1
    assert saidata.packages[0].version == '1.20.0'


def test_load_saidata_with_python_tags(tmp_path):
    """Test loading saidata with Python object tags (legacy format)."""
    from saigen.cli.commands.refresh_versions import _load_saidata
    
    # Create a file with Python object tags (like old generated files)
    saidata_path = tmp_path / "legacy.yaml"
    content = """version: '0.3'
metadata:
  name: test
  description: Test
services:
  - name: test-service
    service_name: test
    type: !!python/object/apply:saigen.models.saidata.ServiceType
      - systemd
    enabled: true
packages:
  - name: test
    package_name: test
    version: 1.0.0
"""
    with open(saidata_path, 'w') as f:
        f.write(content)
    
    # Should load successfully despite Python tags
    saidata = _load_saidata(saidata_path)
    
    assert saidata.metadata.name == 'test'
    assert len(saidata.packages) == 1
    assert saidata.services[0].type == 'systemd'


def test_save_saidata(tmp_path):
    """Test saving saidata to file."""
    from saigen.cli.commands.refresh_versions import _save_saidata
    
    saidata = SaiData(
        version='0.3',
        metadata=Metadata(name='test', description='Test package'),
        packages=[
            Package(name='pkg1', package_name='pkg1', version='1.0.0')
        ]
    )
    
    output_path = tmp_path / "output.yaml"
    _save_saidata(saidata, output_path)
    
    assert output_path.exists()
    
    # Verify it can be loaded back
    with open(output_path) as f:
        data = yaml.safe_load(f)
    
    assert data['metadata']['name'] == 'test'
    assert data['packages'][0]['version'] == '1.0.0'


def test_backup_path_generation(tmp_path):
    """Test backup path generation."""
    from saigen.cli.commands.refresh_versions import _get_backup_path
    
    original = tmp_path / "test.yaml"
    backup = _get_backup_path(original)
    
    assert backup.parent == original.parent
    assert backup.stem.startswith('test.backup.')
    assert backup.suffix == '.yaml'


def test_backup_path_with_custom_dir(tmp_path):
    """Test backup path with custom directory."""
    from saigen.cli.commands.refresh_versions import _get_backup_path
    
    original = tmp_path / "test.yaml"
    backup_dir = tmp_path / "backups"
    backup = _get_backup_path(original, backup_dir)
    
    assert backup.parent == backup_dir
    assert backup.stem.startswith('test.backup.')
