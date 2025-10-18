"""Tests for template resolution engine."""


import pytest

from sai.models.provider_data import Action, Step
from sai.providers.template_engine import (
    ArrayExpansionFilter,
    SaidataContextBuilder,
    TemplateEngine,
    TemplateResolutionError,
)
from saigen.models.saidata import (
    Command,
    Directory,
    File,
    FileType,
    Metadata,
    Package,
    Port,
    Protocol,
    SaiData,
    Service,
    ServiceType,
    Urls,
)


class TestSaidataContextBuilder:
    """Test SaiData context building."""

    def test_build_basic_context(self):
        """Test building context from basic saidata."""
        metadata = Metadata(
            name="nginx",
            display_name="Nginx Web Server",
            description="High-performance web server",
            version="1.20.1",
            category="web",
            license="BSD-2-Clause",
        )

        saidata = SaiData(
            version="0.2",
            metadata=metadata,
        )

        builder = SaidataContextBuilder(saidata)
        context = builder.build_context()

        assert context["name"] == "nginx"
        assert context["version"] == "1.20.1"
        assert context["display_name"] == "Nginx Web Server"
        assert context["saidata"]["metadata"]["name"] == "nginx"
        assert context["metadata"]["description"] == "High-performance web server"

    def test_build_context_with_packages(self):
        """Test building context with packages."""
        metadata = Metadata(name="nginx", version="1.20.1")
        packages = [
            Package(name="nginx", package_name="nginx", version="1.20.1"),
            Package(name="nginx-common", package_name="nginx-common", alternatives=["nginx-core"]),
        ]

        saidata = SaiData(
            version="0.3",
            metadata=metadata,
            packages=packages,
        )

        builder = SaidataContextBuilder(saidata)
        context = builder.build_context()

        assert len(context["saidata"]["packages"]) == 2
        assert context["saidata"]["packages"][0]["name"] == "nginx"
        assert context["saidata"]["packages"][0]["package_name"] == "nginx"
        assert context["saidata"]["packages"][0]["version"] == "1.20.1"
        assert context["saidata"]["packages"][1]["name"] == "nginx-common"
        assert context["saidata"]["packages"][1]["alternatives"] == ["nginx-core"]

    def test_build_context_with_services(self):
        """Test building context with services."""
        metadata = Metadata(name="nginx")
        services = [
            Service(name="nginx", service_name="nginx", type=ServiceType.SYSTEMD, enabled=True),
        ]

        saidata = SaiData(
            version="0.2",
            metadata=metadata,
            services=services,
        )

        builder = SaidataContextBuilder(saidata)
        context = builder.build_context()

        assert len(context["saidata"]["services"]) == 1
        assert context["saidata"]["services"][0]["name"] == "nginx"
        assert context["saidata"]["services"][0]["service_name"] == "nginx"
        assert context["saidata"]["services"][0]["type"] == "systemd"
        assert context["saidata"]["services"][0]["enabled"] is True

    def test_build_context_with_files_and_directories(self):
        """Test building context with files and directories."""
        metadata = Metadata(name="nginx")
        files = [
            File(
                name="nginx.conf", path="/etc/nginx/nginx.conf", type=FileType.CONFIG, owner="root"
            ),
        ]
        directories = [
            Directory(name="nginx-conf", path="/etc/nginx", owner="root", mode="755"),
        ]

        saidata = SaiData(
            version="0.2",
            metadata=metadata,
            files=files,
            directories=directories,
        )

        builder = SaidataContextBuilder(saidata)
        context = builder.build_context()

        assert len(context["saidata"]["files"]) == 1
        assert context["saidata"]["files"][0]["path"] == "/etc/nginx/nginx.conf"
        assert context["saidata"]["files"][0]["type"] == "config"

        assert len(context["saidata"]["directories"]) == 1
        assert context["saidata"]["directories"][0]["path"] == "/etc/nginx"
        assert context["saidata"]["directories"][0]["mode"] == "755"

    def test_build_context_with_commands_and_ports(self):
        """Test building context with commands and ports."""
        metadata = Metadata(name="nginx")
        commands = [
            Command(name="nginx", path="/usr/sbin/nginx", aliases=["nginx-server"]),
        ]
        ports = [
            Port(port=80, protocol=Protocol.TCP, service="http"),
            Port(port=443, protocol=Protocol.TCP, service="https"),
        ]

        saidata = SaiData(
            version="0.2",
            metadata=metadata,
            commands=commands,
            ports=ports,
        )

        builder = SaidataContextBuilder(saidata)
        context = builder.build_context()

        assert len(context["saidata"]["commands"]) == 1
        assert context["saidata"]["commands"][0]["name"] == "nginx"
        assert context["saidata"]["commands"][0]["aliases"] == ["nginx-server"]

        assert len(context["saidata"]["ports"]) == 2
        assert context["saidata"]["ports"][0]["port"] == 80
        assert context["saidata"]["ports"][1]["port"] == 443

    def test_build_context_with_urls(self):
        """Test building context with URLs."""
        urls = Urls(
            website="https://nginx.org",
            documentation="https://nginx.org/en/docs/",
            source="https://github.com/nginx/nginx",
        )
        metadata = Metadata(name="nginx", urls=urls)

        saidata = SaiData(
            version="0.2",
            metadata=metadata,
        )

        builder = SaidataContextBuilder(saidata)
        context = builder.build_context()

        assert context["metadata"]["urls"]["website"] == "https://nginx.org"
        assert context["metadata"]["urls"]["documentation"] == "https://nginx.org/en/docs/"
        assert context["metadata"]["urls"]["source"] == "https://github.com/nginx/nginx"


class TestArrayExpansionFilter:
    """Test array expansion functionality."""

    def test_expand_simple_array_syntax(self):
        """Test expanding simple array syntax."""
        template = "install {{saidata.packages.*.name}}"
        context = {
            "saidata": {
                "packages": [
                    {"name": "nginx"},
                    {"name": "nginx-common"},
                ]
            }
        }

        result = ArrayExpansionFilter.expand_array_syntax(template, context)
        expected = "install {{ saidata.packages | map(attribute='name') | join(' ') }}"
        assert result == expected

    def test_expand_nested_field_syntax(self):
        """Test expanding nested field syntax."""
        template = "systemctl status {{saidata.services.*.service_name}}"
        context = {}

        result = ArrayExpansionFilter.expand_array_syntax(template, context)
        expected = (
            "systemctl status {{ saidata.services | map(attribute='service_name') | join(' ') }}"
        )
        assert result == expected

    def test_no_expansion_needed(self):
        """Test template without array syntax."""
        template = "install {{saidata.metadata.name}}"
        context = {}

        result = ArrayExpansionFilter.expand_array_syntax(template, context)
        assert result == template

    def test_multiple_array_expansions(self):
        """Test template with multiple array expansions."""
        template = "install {{saidata.packages.*.name}} && systemctl enable {{saidata.services.*.service_name}}"
        context = {}

        result = ArrayExpansionFilter.expand_array_syntax(template, context)
        expected = "install {{ saidata.packages | map(attribute='name') | join(' ') }} && systemctl enable {{ saidata.services | map(attribute='service_name') | join(' ') }}"
        assert result == expected

    def test_invalid_array_syntax(self):
        """Test handling of invalid array syntax."""
        template = "install {{*.packages.name}}"  # Star at beginning
        context = {}

        result = ArrayExpansionFilter.expand_array_syntax(template, context)
        assert result == template  # Should remain unchanged


class TestTemplateEngine:
    """Test template resolution engine."""

    def test_resolve_simple_template(self):
        """Test resolving simple template."""
        metadata = Metadata(name="nginx", version="1.20.1")
        saidata = SaiData(version="0.2", metadata=metadata)

        engine = TemplateEngine()
        result = engine.resolve_template("install {{name}}", saidata)

        assert result == "install nginx"

    def test_resolve_metadata_template(self):
        """Test resolving metadata template."""
        metadata = Metadata(
            name="nginx",
            display_name="Nginx Web Server",
            version="1.20.1",
        )
        saidata = SaiData(version="0.2", metadata=metadata)

        engine = TemplateEngine()
        result = engine.resolve_template("Installing {{display_name}} version {{version}}", saidata)

        assert result == "Installing Nginx Web Server version 1.20.1"

    def test_resolve_package_array_template(self):
        """Test resolving template with package array expansion."""
        metadata = Metadata(name="nginx")
        packages = [
            Package(name="nginx", package_name="nginx"),
            Package(name="nginx-common", package_name="nginx-common"),
        ]
        saidata = SaiData(version="0.3", metadata=metadata, packages=packages)

        engine = TemplateEngine()
        result = engine.resolve_template("apt-get install {{saidata.packages.*.name}}", saidata)

        assert result == "apt-get install nginx nginx-common"

    def test_resolve_service_array_template(self):
        """Test resolving template with service array expansion."""
        metadata = Metadata(name="nginx")
        services = [
            Service(name="nginx", service_name="nginx"),
            Service(name="nginx-proxy", service_name="nginx-proxy"),
        ]
        saidata = SaiData(version="0.2", metadata=metadata, services=services)

        engine = TemplateEngine()
        result = engine.resolve_template(
            "systemctl enable {{saidata.services.*.service_name}}", saidata
        )

        assert result == "systemctl enable nginx nginx-proxy"

    def test_resolve_with_additional_context(self):
        """Test resolving template with additional context."""
        metadata = Metadata(name="nginx")
        saidata = SaiData(version="0.2", metadata=metadata)

        additional_context = {
            "custom_var": "custom_value",
            "install_dir": "/opt/nginx",
        }

        engine = TemplateEngine()
        result = engine.resolve_template(
            "install {{name}} to {{install_dir}} with {{custom_var}}", saidata, additional_context
        )

        assert result == "install nginx to /opt/nginx with custom_value"

    def test_resolve_action_template(self):
        """Test resolving action templates."""
        metadata = Metadata(name="nginx")
        packages = [Package(name="nginx", package_name="nginx")]
        saidata = SaiData(version="0.3", metadata=metadata, packages=packages)

        action = Action(
            description="Install nginx",
            template="apt-get install -y {{saidata.packages.*.name}}",
            rollback="apt-get remove -y {{saidata.packages.*.name}}",
            variables={
                "config_path": "/etc/{{name}}/{{name}}.conf",
                "service_name": "{{name}}",
            },
        )

        engine = TemplateEngine()
        result = engine.resolve_action_template(action, saidata)

        assert result["command"] == "apt-get install -y nginx"
        assert result["rollback"] == "apt-get remove -y nginx"
        assert result["variables"]["config_path"] == "/etc/nginx/nginx.conf"
        assert result["variables"]["service_name"] == "nginx"

    def test_resolve_action_with_steps(self):
        """Test resolving action with steps."""
        metadata = Metadata(name="nginx")
        saidata = SaiData(version="0.2", metadata=metadata)

        steps = [
            Step(
                name="Install package",
                command="apt-get install -y {{name}}",
            ),
            Step(
                name="Start service",
                command="systemctl start {{name}}",
                condition="{{name}} == 'nginx'",
            ),
        ]

        action = Action(
            description="Install and start nginx",
            steps=steps,
        )

        engine = TemplateEngine()
        result = engine.resolve_action_template(action, saidata)

        assert len(result["steps"]) == 2
        assert result["steps"][0]["command"] == "apt-get install -y nginx"
        assert result["steps"][1]["command"] == "systemctl start nginx"
        assert result["steps"][1]["condition"] == "nginx == 'nginx'"

    def test_template_resolution_error(self):
        """Test template resolution error handling."""
        metadata = Metadata(name="nginx")
        saidata = SaiData(version="0.2", metadata=metadata)

        engine = TemplateEngine()

        # Test undefined variable
        with pytest.raises(TemplateResolutionError):
            engine.resolve_template("install {{undefined_var}}", saidata)

        # Test syntax error
        with pytest.raises(TemplateResolutionError):
            engine.resolve_template("install {{name", saidata)  # Missing closing brace

    def test_empty_arrays_handling(self):
        """Test handling of empty arrays in templates."""
        metadata = Metadata(name="nginx")
        saidata = SaiData(version="0.2", metadata=metadata)  # No packages

        engine = TemplateEngine()
        result = engine.resolve_template("install {{saidata.packages.*.name}}", saidata)

        # Should handle missing packages gracefully
        assert result == "install"

    def test_complex_template_with_conditionals(self):
        """Test complex template with Jinja2 conditionals."""
        metadata = Metadata(name="nginx", version="1.20.1")
        packages = [Package(name="nginx", package_name="nginx")]
        saidata = SaiData(version="0.3", metadata=metadata, packages=packages)

        template = """
        {%- if version -%}
        apt-get install -y {{saidata.packages.*.name}}={{version}}
        {%- else -%}
        apt-get install -y {{saidata.packages.*.name}}
        {%- endif -%}
        """

        engine = TemplateEngine()
        result = engine.resolve_template(template, saidata)

        assert result == "apt-get install -y nginx=1.20.1"

    def test_whitespace_handling(self):
        """Test proper whitespace handling in templates."""
        metadata = Metadata(name="nginx")
        packages = [Package(name="nginx", package_name="nginx"), Package(name="nginx-common", package_name="nginx-common")]
        saidata = SaiData(version="0.3", metadata=metadata, packages=packages)

        engine = TemplateEngine()
        result = engine.resolve_template("  install {{saidata.packages.*.name}}  ", saidata)

        # Should strip leading/trailing whitespace
        assert result == "install nginx nginx-common"


if __name__ == "__main__":
    pytest.main([__file__])
