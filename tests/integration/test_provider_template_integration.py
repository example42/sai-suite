"""Tests for BaseProvider template integration."""


import pytest

from sai.models.provider_data import Action, Provider, ProviderData, ProviderType, Step
from sai.providers.base import BaseProvider
from sai.providers.template_engine import TemplateResolutionError
from saigen.models.saidata import Metadata, Package, SaiData, Service, ServiceType


class TestProviderTemplateIntegration:
    """Test BaseProvider integration with template engine."""

    def create_test_provider_data(self) -> ProviderData:
        """Create test provider data."""
        provider = Provider(
            name="apt",
            display_name="APT Package Manager",
            description="Debian/Ubuntu package manager",
            type=ProviderType.PACKAGE_MANAGER,
            platforms=["debian", "ubuntu"],
            capabilities=["install", "uninstall", "start", "stop"],
            executable="apt-get",
        )

        actions = {
            "install": Action(
                description="Install packages",
                template="apt-get install -y {{saidata.packages.*.name}}",
                timeout=300,
                rollback="apt-get remove -y {{saidata.packages.*.name}}",
            ),
            "uninstall": Action(
                description="Remove packages",
                template="apt-get remove -y {{saidata.packages.*.name}}",
                timeout=180,
            ),
            "start": Action(
                description="Start services",
                steps=[
                    Step(
                        name="Start service",
                        command="systemctl start {{saidata.services.*.service_name}}",
                    ),
                    Step(
                        name="Enable service",
                        command="systemctl enable {{saidata.services.*.service_name}}",
                    ),
                ],
            ),
        }

        return ProviderData(
            version="1.0",
            provider=provider,
            actions=actions,
        )

    def create_test_saidata(self) -> SaiData:
        """Create test saidata."""
        metadata = Metadata(
            name="nginx",
            display_name="Nginx Web Server",
            version="1.20.1",
        )

        packages = [
            Package(name="nginx", version="1.20.1"),
            Package(name="nginx-common"),
        ]

        services = [
            Service(name="nginx", service_name="nginx", type=ServiceType.SYSTEMD),
        ]

        return SaiData(
            version="0.2",
            metadata=metadata,
            packages=packages,
            services=services,
        )

    def test_provider_initialization_with_template_engine(self):
        """Test that provider initializes with template engine."""
        provider_data = self.create_test_provider_data()
        provider = BaseProvider(provider_data)

        assert provider.template_engine is not None
        assert hasattr(provider, "resolve_action_templates")
        assert hasattr(provider, "resolve_template")

    def test_resolve_action_templates_install(self):
        """Test resolving install action templates."""
        provider_data = self.create_test_provider_data()
        provider = BaseProvider(provider_data)
        saidata = self.create_test_saidata()

        result = provider.resolve_action_templates("install", saidata)

        assert "command" in result
        assert result["command"] == "apt-get install -y nginx nginx-common"
        assert "rollback" in result
        assert result["rollback"] == "apt-get remove -y nginx nginx-common"

    def test_resolve_action_templates_with_steps(self):
        """Test resolving action templates with steps."""
        provider_data = self.create_test_provider_data()
        provider = BaseProvider(provider_data)
        saidata = self.create_test_saidata()

        result = provider.resolve_action_templates("start", saidata)

        assert "steps" in result
        assert len(result["steps"]) == 2
        assert result["steps"][0]["command"] == "systemctl start nginx"
        assert result["steps"][1]["command"] == "systemctl enable nginx"

    def test_resolve_action_templates_with_additional_context(self):
        """Test resolving templates with additional context."""
        provider_data = self.create_test_provider_data()
        provider = BaseProvider(provider_data)
        saidata = self.create_test_saidata()

        # Add custom action with additional context variables
        provider_data.actions["custom"] = Action(
            description="Custom action",
            template="install {{name}} to {{install_dir}} with {{options}}",
        )

        additional_context = {
            "install_dir": "/opt/nginx",
            "options": "--with-ssl",
        }

        result = provider.resolve_action_templates("custom", saidata, additional_context)

        assert result["command"] == "install nginx to /opt/nginx with --with-ssl"

    def test_resolve_single_template(self):
        """Test resolving a single template string."""
        provider_data = self.create_test_provider_data()
        provider = BaseProvider(provider_data)
        saidata = self.create_test_saidata()

        result = provider.resolve_template(
            "systemctl status {{saidata.services.*.service_name}}", saidata
        )

        assert result == "systemctl status nginx"

    def test_resolve_template_with_additional_context(self):
        """Test resolving template with additional context."""
        provider_data = self.create_test_provider_data()
        provider = BaseProvider(provider_data)
        saidata = self.create_test_saidata()

        additional_context = {"port": 80, "config_file": "/etc/nginx/nginx.conf"}

        result = provider.resolve_template(
            "Configure {{name}} on port {{port}} using {{config_file}}", saidata, additional_context
        )

        assert result == "Configure nginx on port 80 using /etc/nginx/nginx.conf"

    def test_unsupported_action_error(self):
        """Test error handling for unsupported actions."""
        provider_data = self.create_test_provider_data()
        provider = BaseProvider(provider_data)
        saidata = self.create_test_saidata()

        with pytest.raises(ValueError, match="Action 'nonexistent' not supported"):
            provider.resolve_action_templates("nonexistent", saidata)

    def test_template_resolution_error_handling(self):
        """Test error handling for template resolution failures."""
        provider_data = self.create_test_provider_data()
        provider = BaseProvider(provider_data)
        saidata = self.create_test_saidata()

        # Add action with invalid template
        provider_data.actions["invalid"] = Action(
            description="Invalid action",
            template="install {{undefined_variable}}",
        )

        with pytest.raises(TemplateResolutionError):
            provider.resolve_action_templates("invalid", saidata)

    def test_get_action_method(self):
        """Test getting action definitions."""
        provider_data = self.create_test_provider_data()
        provider = BaseProvider(provider_data)

        # Test existing action
        action = provider.get_action("install")
        assert action is not None
        assert action.description == "Install packages"
        assert action.template == "apt-get install -y {{saidata.packages.*.name}}"

        # Test non-existent action
        action = provider.get_action("nonexistent")
        assert action is None

    def test_complex_template_scenario(self):
        """Test complex template resolution scenario."""
        provider_data = self.create_test_provider_data()
        provider = BaseProvider(provider_data)

        # Create more complex saidata
        metadata = Metadata(name="postgresql", version="13.7")
        packages = [
            Package(name="postgresql-13", version="13.7"),
            Package(name="postgresql-client-13"),
            Package(name="postgresql-contrib-13"),
        ]
        services = [
            Service(name="postgresql", service_name="postgresql", type=ServiceType.SYSTEMD),
        ]

        saidata = SaiData(
            version="0.2",
            metadata=metadata,
            packages=packages,
            services=services,
        )

        # Add complex action
        provider_data.actions["complex_install"] = Action(
            description="Complex installation",
            steps=[
                Step(
                    name="Update package cache",
                    command="apt-get update",
                ),
                Step(
                    name="Install packages",
                    command="apt-get install -y {{saidata.packages.*.name}}",
                ),
                Step(
                    name="Initialize database",
                    command="sudo -u postgres initdb -D /var/lib/postgresql/{{version}}/main",
                ),
                Step(
                    name="Start and enable service",
                    command="systemctl start {{saidata.services.*.service_name}} && systemctl enable {{saidata.services.*.service_name}}",
                ),
            ],
            variables={
                "data_dir": "/var/lib/postgresql/{{version}}/main",
                "config_file": "/etc/postgresql/{{version}}/main/postgresql.conf",
            },
        )

        result = provider.resolve_action_templates("complex_install", saidata)

        assert len(result["steps"]) == 4
        assert result["steps"][0]["command"] == "apt-get update"
        assert (
            result["steps"][1]["command"]
            == "apt-get install -y postgresql-13 postgresql-client-13 postgresql-contrib-13"
        )
        assert (
            result["steps"][2]["command"]
            == "sudo -u postgres initdb -D /var/lib/postgresql/13.7/main"
        )
        assert (
            result["steps"][3]["command"]
            == "systemctl start postgresql && systemctl enable postgresql"
        )

        assert result["variables"]["data_dir"] == "/var/lib/postgresql/13.7/main"
        assert result["variables"]["config_file"] == "/etc/postgresql/13.7/main/postgresql.conf"


if __name__ == "__main__":
    pytest.main([__file__])
