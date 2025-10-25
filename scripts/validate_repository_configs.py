#!/usr/bin/env python3
"""
Repository Configuration Validation Script

This script validates all repository configurations in saigen/repositories/configs/
against the requirements specified in the provider-version-refresh-enhancement spec.

Validates:
- Repository configuration structure
- Endpoint URLs (both bulk and API)
- Parsing configurations
- version_mapping fields
- API rate limiting and authentication
- EOL repository metadata
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiohttp
import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from saigen.models.repository import RepositoryInfo


class RepositoryConfigValidator:
    """Validates repository configurations."""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.results = {
            'total_repos': 0,
            'valid_repos': 0,
            'invalid_repos': 0,
            'warnings': [],
            'errors': [],
            'endpoint_tests': [],
            'eol_repos': []
        }
    
    def validate_all(self) -> Dict:
        """Validate all repository configuration files."""
        print("=" * 80)
        print("Repository Configuration Validation")
        print("=" * 80)
        print()
        
        config_files = sorted(self.config_dir.glob("*.yaml"))
        print(f"Found {len(config_files)} configuration files\n")
        
        for config_file in config_files:
            if config_file.name == "README.md":
                continue
            print(f"Validating {config_file.name}...")
            self._validate_config_file(config_file)
            print()
        
        return self.results
    
    def _validate_config_file(self, config_file: Path) -> None:
        """Validate a single configuration file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or 'repositories' not in config_data:
                self._add_error(config_file.name, "Missing 'repositories' key")
                return
            
            for repo_config in config_data['repositories']:
                self._validate_repository(config_file.name, repo_config)
        
        except yaml.YAMLError as e:
            self._add_error(config_file.name, f"YAML parsing error: {e}")
        except Exception as e:
            self._add_error(config_file.name, f"Unexpected error: {e}")
    
    def _validate_repository(self, file_name: str, repo_config: Dict) -> None:
        """Validate a single repository configuration."""
        self.results['total_repos'] += 1
        repo_name = repo_config.get('name', 'UNKNOWN')
        
        print(f"  - {repo_name}")
        
        # Required fields validation
        required_fields = ['name', 'type', 'platform', 'endpoints', 'parsing']
        missing_fields = [f for f in required_fields if f not in repo_config]
        
        if missing_fields:
            self._add_error(repo_name, f"Missing required fields: {', '.join(missing_fields)}")
            self.results['invalid_repos'] += 1
            return
        
        # Validate version_mapping
        self._validate_version_mapping(repo_name, repo_config)
        
        # Validate endpoints
        self._validate_endpoints(repo_name, repo_config)
        
        # Validate parsing configuration
        self._validate_parsing(repo_name, repo_config)
        
        # Validate query_type
        self._validate_query_type(repo_name, repo_config)
        
        # Validate EOL status
        self._validate_eol_status(repo_name, repo_config)
        
        # Validate rate limiting for API repos
        self._validate_rate_limiting(repo_name, repo_config)
        
        # Validate authentication
        self._validate_authentication(repo_name, repo_config)
        
        self.results['valid_repos'] += 1
    
    def _validate_version_mapping(self, repo_name: str, repo_config: Dict) -> None:
        """Validate version_mapping field."""
        version_mapping = repo_config.get('version_mapping')
        
        if version_mapping is None:
            self._add_warning(repo_name, "No version_mapping defined (OS-specific queries not supported)")
            return
        
        if not isinstance(version_mapping, dict):
            self._add_error(repo_name, "version_mapping must be a dictionary")
            return
        
        if len(version_mapping) == 0:
            self._add_warning(repo_name, "version_mapping is empty")
            return
        
        # Validate each mapping entry
        for version, codename in version_mapping.items():
            if not isinstance(version, str) or not isinstance(codename, str):
                self._add_error(repo_name, f"version_mapping entry {version}:{codename} must be string:string")
                continue
            
            # Validate version format (should be numeric with dots)
            if not version.replace('.', '').isdigit():
                self._add_warning(repo_name, f"version_mapping key '{version}' should be numeric (e.g., '22.04', '11')")
            
            # Validate codename format (lowercase alphanumeric with hyphens)
            if not codename.replace('-', '').replace('_', '').isalnum() or codename != codename.lower():
                self._add_warning(repo_name, f"version_mapping value '{codename}' should be lowercase alphanumeric")
        
        print(f"    ✓ version_mapping: {len(version_mapping)} mapping(s)")
    
    def _validate_endpoints(self, repo_name: str, repo_config: Dict) -> None:
        """Validate endpoint URLs."""
        endpoints = repo_config.get('endpoints', {})
        
        if not endpoints:
            self._add_error(repo_name, "No endpoints defined")
            return
        
        # Check for required endpoint types
        query_type = repo_config.get('query_type', 'bulk_download')
        
        if query_type == 'bulk_download':
            if 'packages' not in endpoints:
                self._add_error(repo_name, "bulk_download repos must have 'packages' endpoint")
        elif query_type == 'api':
            if 'search' not in endpoints and 'info' not in endpoints:
                self._add_error(repo_name, "API repos must have 'search' or 'info' endpoint")
        
        # Validate URL format
        for endpoint_type, url in endpoints.items():
            if not url:
                self._add_warning(repo_name, f"Empty {endpoint_type} endpoint")
                continue
            
            # Check if URL is valid
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                self._add_error(repo_name, f"Invalid {endpoint_type} URL: {url}")
            elif parsed.scheme not in ['http', 'https']:
                self._add_warning(repo_name, f"{endpoint_type} URL uses {parsed.scheme} (prefer https)")
        
        print(f"    ✓ endpoints: {len(endpoints)} endpoint(s)")
    
    def _validate_parsing(self, repo_name: str, repo_config: Dict) -> None:
        """Validate parsing configuration."""
        parsing = repo_config.get('parsing', {})
        
        if not parsing:
            self._add_error(repo_name, "No parsing configuration defined")
            return
        
        # Check for required parsing fields
        if 'format' not in parsing:
            self._add_error(repo_name, "parsing.format is required")
        
        if 'fields' not in parsing:
            self._add_warning(repo_name, "parsing.fields not defined")
        else:
            fields = parsing['fields']
            required_fields = ['name', 'version']
            missing = [f for f in required_fields if f not in fields]
            if missing:
                self._add_error(repo_name, f"parsing.fields missing: {', '.join(missing)}")
        
        print(f"    ✓ parsing: format={parsing.get('format')}")
    
    def _validate_query_type(self, repo_name: str, repo_config: Dict) -> None:
        """Validate query_type field."""
        query_type = repo_config.get('query_type', 'bulk_download')
        
        valid_types = ['bulk_download', 'api']
        if query_type not in valid_types:
            self._add_error(repo_name, f"query_type must be one of: {', '.join(valid_types)}")
        else:
            print(f"    ✓ query_type: {query_type}")
    
    def _validate_eol_status(self, repo_name: str, repo_config: Dict) -> None:
        """Validate EOL status."""
        eol = repo_config.get('eol', False)
        
        if not isinstance(eol, bool):
            self._add_error(repo_name, "eol must be a boolean")
        elif eol:
            self.results['eol_repos'].append(repo_name)
            print(f"    ⚠ EOL: true (end-of-life repository)")
    
    def _validate_rate_limiting(self, repo_name: str, repo_config: Dict) -> None:
        """Validate rate limiting configuration for API repos."""
        query_type = repo_config.get('query_type', 'bulk_download')
        
        if query_type == 'api':
            limits = repo_config.get('limits', {})
            
            if not limits:
                self._add_warning(repo_name, "API repo should have rate limiting configuration")
                return
            
            # Check for recommended limit fields
            recommended = ['requests_per_minute', 'concurrent_requests', 'timeout_seconds']
            missing = [f for f in recommended if f not in limits]
            
            if missing:
                self._add_warning(repo_name, f"API repo missing recommended limits: {', '.join(missing)}")
            else:
                print(f"    ✓ rate limiting: {limits.get('requests_per_minute')} req/min, "
                      f"{limits.get('concurrent_requests')} concurrent")
    
    def _validate_authentication(self, repo_name: str, repo_config: Dict) -> None:
        """Validate authentication configuration."""
        auth = repo_config.get('auth')
        
        if auth:
            if 'type' not in auth:
                self._add_error(repo_name, "auth.type is required when auth is defined")
            else:
                print(f"    ✓ authentication: {auth['type']}")
    
    def _add_error(self, repo_name: str, message: str) -> None:
        """Add an error to results."""
        error_msg = f"[ERROR] {repo_name}: {message}"
        self.results['errors'].append(error_msg)
        print(f"    ✗ {message}")
    
    def _add_warning(self, repo_name: str, message: str) -> None:
        """Add a warning to results."""
        warning_msg = f"[WARNING] {repo_name}: {message}"
        self.results['warnings'].append(warning_msg)
        print(f"    ⚠ {message}")


class EndpointTester:
    """Tests repository endpoints for connectivity."""
    
    def __init__(self, config_dir: Path, timeout: int = 10):
        self.config_dir = config_dir
        self.timeout = timeout
        self.results = []
    
    async def test_all_endpoints(self) -> List[Dict]:
        """Test all repository endpoints."""
        print("\n" + "=" * 80)
        print("Endpoint Connectivity Tests")
        print("=" * 80)
        print()
        
        config_files = sorted(self.config_dir.glob("*.yaml"))
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            for config_file in config_files:
                if config_file.name == "README.md":
                    continue
                
                print(f"Testing endpoints in {config_file.name}...")
                await self._test_config_file(session, config_file)
                print()
        
        return self.results
    
    async def _test_config_file(self, session: aiohttp.ClientSession, config_file: Path) -> None:
        """Test endpoints in a configuration file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or 'repositories' not in config_data:
                return
            
            for repo_config in config_data['repositories']:
                await self._test_repository_endpoints(session, repo_config)
        
        except Exception as e:
            print(f"  Error loading {config_file.name}: {e}")
    
    async def _test_repository_endpoints(self, session: aiohttp.ClientSession, repo_config: Dict) -> None:
        """Test endpoints for a single repository."""
        repo_name = repo_config.get('name', 'UNKNOWN')
        endpoints = repo_config.get('endpoints', {})
        
        if not endpoints:
            return
        
        print(f"  - {repo_name}")
        
        # Test each endpoint
        for endpoint_type, url_template in endpoints.items():
            # Skip if URL has placeholders that need substitution
            if '{arch}' in url_template or '{query}' in url_template or '{package}' in url_template:
                # Try to substitute with reasonable defaults
                url = url_template.replace('{arch}', 'amd64')
                url = url.replace('{query}', 'test')
                url = url.replace('{package}', 'test')
            else:
                url = url_template
            
            result = await self._test_endpoint(session, repo_name, endpoint_type, url)
            self.results.append(result)
    
    async def _test_endpoint(self, session: aiohttp.ClientSession, repo_name: str, 
                            endpoint_type: str, url: str) -> Dict:
        """Test a single endpoint."""
        result = {
            'repo': repo_name,
            'endpoint_type': endpoint_type,
            'url': url,
            'status': 'unknown',
            'status_code': None,
            'response_time': None,
            'error': None
        }
        
        try:
            start_time = time.time()
            async with session.head(url, allow_redirects=True) as response:
                result['status_code'] = response.status
                result['response_time'] = time.time() - start_time
                
                if response.status == 200:
                    result['status'] = 'success'
                    print(f"    ✓ {endpoint_type}: {response.status} ({result['response_time']:.2f}s)")
                elif response.status in [301, 302, 307, 308]:
                    result['status'] = 'redirect'
                    print(f"    ⚠ {endpoint_type}: {response.status} (redirect)")
                elif response.status == 403:
                    result['status'] = 'forbidden'
                    print(f"    ⚠ {endpoint_type}: 403 (may require authentication)")
                elif response.status == 404:
                    result['status'] = 'not_found'
                    print(f"    ✗ {endpoint_type}: 404 (not found)")
                else:
                    result['status'] = 'error'
                    print(f"    ✗ {endpoint_type}: {response.status}")
        
        except asyncio.TimeoutError:
            result['status'] = 'timeout'
            result['error'] = 'Request timeout'
            print(f"    ✗ {endpoint_type}: timeout")
        except aiohttp.ClientError as e:
            result['status'] = 'error'
            result['error'] = str(e)
            print(f"    ✗ {endpoint_type}: {type(e).__name__}")
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            print(f"    ✗ {endpoint_type}: {e}")
        
        return result


def print_summary(validation_results: Dict, endpoint_results: List[Dict]) -> None:
    """Print validation summary."""
    print("\n" + "=" * 80)
    print("Validation Summary")
    print("=" * 80)
    print()
    
    # Repository validation summary
    print(f"Total repositories: {validation_results['total_repos']}")
    print(f"Valid repositories: {validation_results['valid_repos']}")
    print(f"Invalid repositories: {validation_results['invalid_repos']}")
    print(f"EOL repositories: {len(validation_results['eol_repos'])}")
    print()
    
    # Errors
    if validation_results['errors']:
        print(f"Errors ({len(validation_results['errors'])}):")
        for error in validation_results['errors']:
            print(f"  {error}")
        print()
    
    # Warnings
    if validation_results['warnings']:
        print(f"Warnings ({len(validation_results['warnings'])}):")
        for warning in validation_results['warnings'][:10]:  # Show first 10
            print(f"  {warning}")
        if len(validation_results['warnings']) > 10:
            print(f"  ... and {len(validation_results['warnings']) - 10} more")
        print()
    
    # EOL repositories
    if validation_results['eol_repos']:
        print(f"EOL Repositories ({len(validation_results['eol_repos'])}):")
        for repo in validation_results['eol_repos']:
            print(f"  - {repo}")
        print()
    
    # Endpoint test summary
    if endpoint_results:
        success_count = sum(1 for r in endpoint_results if r['status'] == 'success')
        error_count = sum(1 for r in endpoint_results if r['status'] in ['error', 'not_found', 'timeout'])
        warning_count = sum(1 for r in endpoint_results if r['status'] in ['redirect', 'forbidden'])
        
        print(f"Endpoint Tests:")
        print(f"  Total: {len(endpoint_results)}")
        print(f"  Success: {success_count}")
        print(f"  Warnings: {warning_count}")
        print(f"  Errors: {error_count}")
        print()
        
        # Show failed endpoints
        failed = [r for r in endpoint_results if r['status'] in ['error', 'not_found', 'timeout']]
        if failed:
            print(f"Failed Endpoints ({len(failed)}):")
            for result in failed[:10]:  # Show first 10
                print(f"  - {result['repo']} ({result['endpoint_type']}): {result['status']}")
                if result['error']:
                    print(f"    Error: {result['error']}")
            if len(failed) > 10:
                print(f"  ... and {len(failed) - 10} more")
            print()


async def main():
    """Main validation function."""
    # Get config directory
    script_dir = Path(__file__).parent
    config_dir = script_dir.parent / "saigen" / "repositories" / "configs"
    
    if not config_dir.exists():
        print(f"Error: Config directory not found: {config_dir}")
        sys.exit(1)
    
    # Run validation
    validator = RepositoryConfigValidator(config_dir)
    validation_results = validator.validate_all()
    
    # Run endpoint tests
    tester = EndpointTester(config_dir, timeout=10)
    endpoint_results = await tester.test_all_endpoints()
    
    # Print summary
    print_summary(validation_results, endpoint_results)
    
    # Save results to JSON
    output_file = script_dir / "repository_validation_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'validation': validation_results,
            'endpoint_tests': endpoint_results
        }, f, indent=2)
    
    print(f"Results saved to: {output_file}")
    
    # Exit with error code if there are errors
    if validation_results['errors'] or validation_results['invalid_repos'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
