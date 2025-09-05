"""Pytest configuration and fixtures for SAI tests."""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock
import pytest
import yaml

from sai.models.config import SaiConfig, LogLevel
from sai.models.saidata import SaiData, Metadata, Package, Service
from sai.models.provider_data import ProviderData, Provider, Action, ProviderType


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_config(temp_dir):
    """Create a sample SAI configuration."""
    return SaiConfig(
        log_level=LogLevel.INFO,
        cache_enabled=True,
        cache_directory=temp_dir / "cache",
        saidata_paths=[str(temp_dir / "saidata")],
        provider_paths=[str(temp_dir / "providers")],
        provider_priorities={"apt": 60, "brew": 70, "yum": 50}
    )


@pytest.fixture
def sample_saidata():
    """Create sample saidata for testing."""
    return SaiData(
        version="0.2",
        metadata=Metadata(
            name="nginx",
            display_name="Nginx Web Server",
            description="High-performance HTTP server and reverse proxy"
        ),
        packages=[
            Package(name="nginx", version=">=1.18.0")
        ],
        services=[
            Service(name="nginx", type="systemd", enabled=True)
        ]
    )


@pytest.fixture
def sample_provider_data():
    """Create sample provider data for testing."""
    return ProviderData(
        version="1.0",
        provider=Provider(
            name="apt",
            display_name="APT Package Manager",
            description="Debian/Ubuntu package manager",
            type=ProviderType.PACKAGE_MANAGER,
            platforms=["debian", "ubuntu"],
            capabilities=["install", "uninstall", "update", "search", "info"],
            executable="apt-get"
        ),
        actions={
            "install": Action(
                description="Install packages",
                template="apt-get install -y {{sai_package(saidata, 'apt')}}",
                requires_sudo=True,
                timeout=300
            ),
            "uninstall": Action(
                description="Remove packages",
                template="apt-get remove -y {{sai_package(saidata, 'apt')}}",
                requires_sudo=True,
                timeout=120
            ),
            "info": Action(
                description="Show package information",
                template="apt show {{sai_package(saidata, 'apt')}}",
                requires_sudo=False,
                timeout=30
            )
        }
    )


@pytest.fixture
def mock_provider(sample_provider_data):
    """Create a mock provider instance."""
    from sai.providers.base import BaseProvider
    
    provider = BaseProvider(sample_provider_data)
    
    # Mock system-dependent methods
    provider.is_available = Mock(return_value=True)
    provider.get_executable_path = Mock(return_value=Path("/usr/bin/apt-get"))
    provider.get_executable_version = Mock(return_value="apt 2.4.0")
    
    return provider


@pytest.fixture
def test_saidata_files(temp_dir):
    """Create test saidata files in temporary directory."""
    saidata_dir = temp_dir / "saidata"
    saidata_dir.mkdir(parents=True, exist_ok=True)
    
    # Create nginx saidata
    nginx_data = {
        "version": "0.2",
        "metadata": {
            "name": "nginx",
            "display_name": "Nginx Web Server",
            "description": "High-performance HTTP server"
        },
        "packages": [{"name": "nginx"}],
        "services": [{"name": "nginx", "type": "systemd"}],
        "providers": {
            "apt": {"packages": [{"name": "nginx"}]},
            "brew": {"packages": [{"name": "nginx"}]}
        }
    }
    
    nginx_file = saidata_dir / "nginx.yaml"
    with open(nginx_file, 'w') as f:
        yaml.dump(nginx_data, f)
    
    # Create git saidata
    git_data = {
        "version": "0.2",
        "metadata": {
            "name": "git",
            "display_name": "Git Version Control",
            "description": "Distributed version control system"
        },
        "packages": [{"name": "git"}],
        "providers": {
            "apt": {"packages": [{"name": "git"}]},
            "brew": {"packages": [{"name": "git"}]},
            "yum": {"packages": [{"name": "git"}]}
        }
    }
    
    git_file = saidata_dir / "git.yaml"
    with open(git_file, 'w') as f:
        yaml.dump(git_data, f)
    
    return {
        "nginx": nginx_file,
        "git": git_file,
        "directory": saidata_dir
    }


@pytest.fixture
def test_provider_files(temp_dir):
    """Create test provider files in temporary directory."""
    provider_dir = temp_dir / "providers"
    provider_dir.mkdir(parents=True, exist_ok=True)
    
    # Create apt provider
    apt_data = {
        "version": "1.0",
        "provider": {
            "name": "apt",
            "display_name": "APT Package Manager",
            "type": "package_manager",
            "platforms": ["debian", "ubuntu"],
            "capabilities": ["install", "uninstall", "info"],
            "executable": "apt-get"
        },
        "actions": {
            "install": {
                "template": "apt-get install -y {{sai_package(saidata, 'apt')}}",
                "requires_sudo": True,
                "timeout": 300
            },
            "uninstall": {
                "template": "apt-get remove -y {{sai_package(saidata, 'apt')}}",
                "requires_sudo": True
            },
            "info": {
                "template": "apt show {{sai_package(saidata, 'apt')}}",
                "requires_sudo": False
            }
        }
    }
    
    apt_file = provider_dir / "apt.yaml"
    with open(apt_file, 'w') as f:
        yaml.dump(apt_data, f)
    
    # Create brew provider
    brew_data = {
        "version": "1.0",
        "provider": {
            "name": "brew",
            "display_name": "Homebrew Package Manager",
            "type": "package_manager",
            "platforms": ["darwin"],
            "capabilities": ["install", "uninstall", "info", "search"],
            "executable": "brew"
        },
        "actions": {
            "install": {
                "template": "brew install {{sai_package(saidata, 'brew')}}",
                "requires_sudo": False,
                "timeout": 600
            },
            "uninstall": {
                "template": "brew uninstall {{sai_package(saidata, 'brew')}}",
                "requires_sudo": False
            },
            "info": {
                "template": "brew info {{sai_package(saidata, 'brew')}}",
                "requires_sudo": False
            },
            "search": {
                "template": "brew search {{search_term}}",
                "requires_sudo": False
            }
        }
    }
    
    brew_file = provider_dir / "brew.yaml"
    with open(brew_file, 'w') as f:
        yaml.dump(brew_data, f)
    
    return {
        "apt": apt_file,
        "brew": brew_file,
        "directory": provider_dir
    }


@pytest.fixture
def mock_execution_result():
    """Create a mock execution result."""
    from sai.core.execution_engine import ExecutionResult, ExecutionStatus
    
    return ExecutionResult(
        success=True,
        status=ExecutionStatus.SUCCESS,
        message="Command executed successfully",
        provider_used="apt",
        action_name="install",
        commands_executed=["apt-get install -y nginx"],
        execution_time=2.5,
        dry_run=False,
        stdout="Package installed successfully",
        stderr="",
        exit_code=0
    )


@pytest.fixture
def mock_system_commands():
    """Mock system command utilities."""
    with pytest.mock.patch('sai.utils.system.is_executable_available', return_value=True), \
         pytest.mock.patch('sai.utils.system.check_executable_functionality', return_value=True), \
         pytest.mock.patch('sai.utils.system.get_executable_path', return_value=Path("/usr/bin/test")), \
         pytest.mock.patch('sai.utils.system.get_executable_version', return_value="test 1.0.0"):
        yield


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration between tests."""
    import logging
    
    # Store original state
    original_level = logging.root.level
    original_handlers = logging.root.handlers[:]
    
    yield
    
    # Reset to original state
    logging.root.setLevel(original_level)
    logging.root.handlers = original_handlers
    
    # Clear SAI and SAIGEN loggers
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        if logger_name.startswith(('sai', 'saigen')):
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.setLevel(logging.NOTSET)


# Saigen-specific fixtures
@pytest.fixture
def sample_saigen_config(temp_dir):
    """Create sample saigen configuration."""
    from saigen.models.config import SaigenConfig, LLMConfig
    
    return SaigenConfig(
        llm_providers={
            "openai": LLMConfig(
                api_key="test-key",
                model="gpt-3.5-turbo",
                max_tokens=2000,
                temperature=0.1
            )
        },
        output_directory=str(temp_dir / "output"),
        cache_directory=str(temp_dir / "cache"),
        generation={
            "retry_attempts": 2,
            "timeout": 60,
            "use_rag": True
        }
    )


@pytest.fixture
def mock_llm_response():
    """Create mock LLM response."""
    from saigen.llm.providers.base import LLMResponse
    
    return LLMResponse(
        content="""version: "0.2"
metadata:
  name: "test-software"
  display_name: "Test Software"
  description: "A test software package"
  category: "development"

providers:
  apt:
    packages:
      - name: "test-software"
        version: "latest"
""",
        tokens_used=150,
        cost_estimate=0.003,
        model_used="gpt-3.5-turbo",
        finish_reason="stop"
    )


@pytest.fixture
def sample_generation_request():
    """Create sample generation request."""
    from saigen.models.generation import GenerationRequest, LLMProvider
    
    return GenerationRequest(
        software_name="nginx",
        target_providers=["apt", "brew"],
        llm_provider=LLMProvider.OPENAI,
        use_rag=True
    )


@pytest.fixture
def sample_repository_packages():
    """Create sample repository packages."""
    from saigen.models.repository import RepositoryPackage
    
    return [
        RepositoryPackage(
            name="nginx",
            version="1.20.1",
            description="High-performance HTTP server and reverse proxy",
            repository_name="apt",
            platform="linux",
            category="web-server",
            tags=["http", "server", "proxy"],
            homepage="https://nginx.org",
            maintainer="nginx team"
        ),
        RepositoryPackage(
            name="nginx",
            version="1.21.0",
            description="HTTP and reverse proxy server",
            repository_name="brew",
            platform="macos",
            category="web-server",
            tags=["http", "server"],
            homepage="https://nginx.org"
        )
    ]


@pytest.fixture
def mock_generation_engine():
    """Create mock generation engine."""
    from unittest.mock import Mock, AsyncMock
    from saigen.models.generation import GenerationResult
    from saigen.models.saidata import SaiData, Metadata
    
    engine = Mock()
    
    async def mock_generate(request):
        return GenerationResult(
            success=True,
            saidata=SaiData(
                version="0.2",
                metadata=Metadata(name=request.software_name)
            ),
            validation_errors=[],
            warnings=[],
            generation_time=1.0,
            llm_provider_used="openai",
            tokens_used=100,
            cost_estimate=0.001
        )
    
    engine.generate_saidata = mock_generate
    engine.get_available_providers.return_value = ["openai"]
    engine.get_provider_info.return_value = {
        "name": "openai",
        "model": "gpt-3.5-turbo",
        "available": True
    }
    
    return engine


@pytest.fixture
def isolated_filesystem():
    """Create an isolated filesystem for tests."""
    import os
    import tempfile
    
    original_cwd = os.getcwd()
    temp_dir = tempfile.mkdtemp()
    
    try:
        os.chdir(temp_dir)
        yield Path(temp_dir)
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)


# Test markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_system: mark test as requiring system dependencies"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance benchmark"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "llm_integration: mark test as requiring LLM API access"
    )


# Skip markers for CI/CD
def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers."""
    import pytest
    
    # Skip integration tests if --no-integration flag is used
    if config.getoption("--no-integration", default=False):
        skip_integration = pytest.mark.skip(reason="Integration tests disabled")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
    
    # Skip system tests if --no-system flag is used
    if config.getoption("--no-system", default=False):
        skip_system = pytest.mark.skip(reason="System tests disabled")
        for item in items:
            if "requires_system" in item.keywords:
                item.add_marker(skip_system)
    
    # Skip performance tests if --no-performance flag is used
    if config.getoption("--no-performance", default=False):
        skip_performance = pytest.mark.skip(reason="Performance tests disabled")
        for item in items:
            if "performance" in item.keywords:
                item.add_marker(skip_performance)
    
    # Skip LLM tests if --no-llm flag is used
    if config.getoption("--no-llm", default=False):
        skip_llm = pytest.mark.skip(reason="LLM integration tests disabled")
        for item in items:
            if "llm_integration" in item.keywords:
                item.add_marker(skip_llm)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--no-integration",
        action="store_true",
        default=False,
        help="Skip integration tests"
    )
    parser.addoption(
        "--no-system",
        action="store_true",
        default=False,
        help="Skip tests that require system dependencies"
    )
    parser.addoption(
        "--no-performance",
        action="store_true",
        default=False,
        help="Skip performance tests"
    )
    parser.addoption(
        "--no-llm",
        action="store_true",
        default=False,
        help="Skip tests that require LLM API access"
    )