"""Tests for template engine functionality."""

from unittest.mock import patch

import pytest

from sai.models.saidata import Metadata, Package, SaiData, Service
from sai.providers.template_engine import (
    TemplateContext,
    TemplateEngine,
    TemplateFunction,
    TemplateResolutionError,
)


class TestTemplateEngine:
    """Test TemplateEngine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TemplateEngine()

        # Create sample saidata
        self.saidata = SaiData(
            version="0.2",
            metadata=Metadata(
                name="nginx",
                display_name="Nginx Web Server",
                description="High-performance HTTP server",
            ),
            packages=[Package(name="nginx", version=">=1.18.0"), Package(name="nginx-extras")],
            services=[Service(name="nginx", type="systemd", enabled=True)],
        )

    def test_simple_template_resolution(self):
        """Test simple template variable resolution."""
        template = "Install {{saidata.metadata.name}}"

        result = self.engine.resolve_template(template, self.saidata)

        assert result == "Install nginx"

    def test_nested_attribute_resolution(self):
        """Test nested attribute resolution."""
        template = "{{saidata.metadata.display_name}} - {{saidata.metadata.description}}"

        result = self.engine.resolve_template(template, self.saidata)

        assert result == "Nginx Web Server - High-performance HTTP server"

    def test_array_expansion(self):
        """Test array expansion with wildcard."""
        template = "{{saidata.packages.*.name}}"

        result = self.engine.resolve_template(template, self.saidata)

        # Should expand to space-separated package names
        assert "nginx" in result
        assert "nginx-extras" in result

    def test_array_expansion_with_separator(self):
        """Test array expansion with custom separator."""
        template = "{{saidata.packages.*.name|join(',')}}"

        result = self.engine.resolve_template(template, self.saidata)

        assert "nginx,nginx-extras" in result or "nginx-extras,nginx" in result

    def test_conditional_template(self):
        """Test conditional template rendering."""
        template = "{% if saidata.services %}systemctl start {{saidata.services.0.name}}{% endif %}"

        result = self.engine.resolve_template(template, self.saidata)

        assert result == "systemctl start nginx"

    def test_loop_template(self):
        """Test loop template rendering."""
        template = "{% for package in saidata.packages %}{{package.name}} {% endfor %}"

        result = self.engine.resolve_template(template, self.saidata)

        assert "nginx" in result
        assert "nginx-extras" in result

    def test_template_with_filters(self):
        """Test template with Jinja2 filters."""
        template = "{{saidata.metadata.name|upper}}"

        result = self.engine.resolve_template(template, self.saidata)

        assert result == "NGINX"

    def test_template_with_default_value(self):
        """Test template with default value for missing attribute."""
        template = "{{saidata.metadata.version|default('latest')}}"

        result = self.engine.resolve_template(template, self.saidata)

        assert result == "latest"

    def test_custom_template_function(self):
        """Test custom template function."""

        # Register custom function
        def get_package_name(saidata, provider):
            if hasattr(saidata, "providers") and provider in saidata.providers:
                packages = saidata.providers[provider].get("packages", [])
                if packages:
                    return packages[0].get("name", saidata.metadata.name)
            return saidata.metadata.name

        self.engine.register_function("sai_package", get_package_name)

        # Add provider data to saidata
        self.saidata.providers = {"apt": {"packages": [{"name": "nginx-full"}]}}

        template = "{{sai_package(saidata, 'apt')}}"

        result = self.engine.resolve_template(template, self.saidata)

        assert result == "nginx-full"

    def test_template_resolution_error(self):
        """Test template resolution error handling."""
        template = "{{saidata.nonexistent.attribute}}"

        with pytest.raises(TemplateResolutionError) as exc_info:
            self.engine.resolve_template(template, self.saidata)

        assert "Template resolution failed" in str(exc_info.value)

    def test_invalid_template_syntax(self):
        """Test invalid template syntax handling."""
        template = "{{saidata.metadata.name"  # Missing closing braces

        with pytest.raises(TemplateResolutionError) as exc_info:
            self.engine.resolve_template(template, self.saidata)

        assert "Template syntax error" in str(exc_info.value)

    def test_template_with_variables(self):
        """Test template with additional variables."""
        template = "{{software_name}} version {{version}}"
        variables = {"software_name": "nginx", "version": "1.18.0"}

        result = self.engine.resolve_template(template, self.saidata, variables)

        assert result == "nginx version 1.18.0"

    def test_template_context_creation(self):
        """Test template context creation."""
        variables = {"custom_var": "value"}

        context = self.engine._create_context(self.saidata, variables)

        assert context["saidata"] == self.saidata
        assert context["custom_var"] == "value"
        # Should include built-in functions
        assert callable(context.get("sai_package"))
        assert callable(context.get("sai_service"))

    def test_builtin_sai_package_function(self):
        """Test built-in sai_package function."""
        # Add provider data
        self.saidata.providers = {
            "apt": {"packages": [{"name": "nginx-full"}]},
            "brew": {"packages": [{"name": "nginx"}]},
        }

        template_apt = "{{sai_package(saidata, 'apt')}}"
        template_brew = "{{sai_package(saidata, 'brew')}}"
        template_unknown = "{{sai_package(saidata, 'unknown')}}"

        result_apt = self.engine.resolve_template(template_apt, self.saidata)
        result_brew = self.engine.resolve_template(template_brew, self.saidata)
        result_unknown = self.engine.resolve_template(template_unknown, self.saidata)

        assert result_apt == "nginx-full"
        assert result_brew == "nginx"
        assert result_unknown == "nginx"  # Falls back to metadata name

    def test_builtin_sai_service_function(self):
        """Test built-in sai_service function."""
        template = "{{sai_service(saidata, 'systemd')}}"

        result = self.engine.resolve_template(template, self.saidata)

        assert result == "nginx"

    def test_template_with_complex_data(self):
        """Test template with complex nested data."""
        # Add complex provider data
        self.saidata.providers = {
            "apt": {
                "packages": [
                    {"name": "nginx-full", "version": ">=1.18.0"},
                    {"name": "nginx-common"},
                ],
                "config": {"sites_enabled": "/etc/nginx/sites-enabled", "conf_dir": "/etc/nginx"},
            }
        }

        template = "{{saidata.providers.apt.config.conf_dir}}/nginx.conf"

        result = self.engine.resolve_template(template, self.saidata)

        assert result == "/etc/nginx/nginx.conf"

    def test_template_with_environment_variables(self):
        """Test template with environment variables."""
        with patch.dict("os.environ", {"HOME": "/home/user", "USER": "testuser"}):
            template = "{{env.HOME}}/{{env.USER}}/config"

            result = self.engine.resolve_template(template, self.saidata)

            assert result == "/home/user/testuser/config"

    def test_template_caching(self):
        """Test template compilation caching."""
        template = "{{saidata.metadata.name}}"

        # First resolution should compile and cache
        result1 = self.engine.resolve_template(template, self.saidata)

        # Second resolution should use cached template
        result2 = self.engine.resolve_template(template, self.saidata)

        assert result1 == result2 == "nginx"

        # Check that template is cached
        assert template in self.engine._template_cache

    def test_template_cache_limit(self):
        """Test template cache size limit."""
        # Set small cache limit for testing
        self.engine._max_cache_size = 2

        templates = [
            "{{saidata.metadata.name}}",
            "{{saidata.metadata.display_name}}",
            "{{saidata.metadata.description}}",
        ]

        for template in templates:
            self.engine.resolve_template(template, self.saidata)

        # Cache should not exceed limit
        assert len(self.engine._template_cache) <= 2

    def test_template_with_missing_saidata(self):
        """Test template resolution with None saidata."""
        template = "{{saidata.metadata.name}}"

        with pytest.raises(TemplateResolutionError) as exc_info:
            self.engine.resolve_template(template, None)

        assert "saidata is required" in str(exc_info.value)

    def test_template_function_registration(self):
        """Test custom function registration."""

        def custom_function(value):
            return f"custom_{value}"

        self.engine.register_function("custom_func", custom_function)

        template = "{{custom_func('test')}}"

        result = self.engine.resolve_template(template, self.saidata)

        assert result == "custom_test"

    def test_template_function_override(self):
        """Test overriding built-in template functions."""

        def custom_sai_package(saidata, provider):
            return f"custom-{saidata.metadata.name}"

        self.engine.register_function("sai_package", custom_sai_package)

        template = "{{sai_package(saidata, 'apt')}}"

        result = self.engine.resolve_template(template, self.saidata)

        assert result == "custom-nginx"


class TestTemplateContext:
    """Test TemplateContext functionality."""

    def test_template_context_creation(self):
        """Test template context creation."""
        saidata = SaiData(version="0.2", metadata=Metadata(name="test"))
        variables = {"var1": "value1"}
        functions = {"func1": lambda x: x}

        context = TemplateContext(saidata, variables, functions)

        assert context.saidata == saidata
        assert context.variables == variables
        assert context.functions == functions

    def test_template_context_to_dict(self):
        """Test template context dictionary conversion."""
        saidata = SaiData(version="0.2", metadata=Metadata(name="test"))
        variables = {"var1": "value1"}
        functions = {"func1": lambda x: x}

        context = TemplateContext(saidata, variables, functions)
        context_dict = context.to_dict()

        assert context_dict["saidata"] == saidata
        assert context_dict["var1"] == "value1"
        assert context_dict["func1"] == functions["func1"]
        assert "env" in context_dict  # Environment variables should be included


class TestTemplateFunction:
    """Test TemplateFunction functionality."""

    def test_template_function_creation(self):
        """Test template function creation."""

        def test_func(arg1, arg2="default"):
            return f"{arg1}_{arg2}"

        template_func = TemplateFunction("test_func", test_func, "Test function")

        assert template_func.name == "test_func"
        assert template_func.function == test_func
        assert template_func.description == "Test function"

    def test_template_function_call(self):
        """Test template function calling."""

        def test_func(arg1, arg2="default"):
            return f"{arg1}_{arg2}"

        template_func = TemplateFunction("test_func", test_func)

        result1 = template_func("hello")
        result2 = template_func("hello", "world")

        assert result1 == "hello_default"
        assert result2 == "hello_world"


if __name__ == "__main__":
    pytest.main([__file__])
