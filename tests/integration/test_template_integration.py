"""Integration tests for template engine with realistic scenarios."""

import pytest
from sai.providers.template_engine import TemplateEngine
from sai.models.provider_data import Action, Step
from saigen.models.saidata import (
    SaiData,
    Metadata,
    Package,
    Service,
    ServiceType,
)


class TestTemplateIntegration:
    """Test template engine with realistic provider scenarios."""
    
    def test_nginx_install_template(self):
        """Test template resolution for nginx installation."""
        # Create realistic nginx saidata
        metadata = Metadata(
            name="nginx",
            display_name="Nginx Web Server",
            version="1.20.1",
            category="web",
        )
        
        packages = [
            Package(name="nginx", version="1.20.1"),
            Package(name="nginx-common"),
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
        
        # Test simple package installation template
        engine = TemplateEngine()
        
        # Test array expansion for package names
        result = engine.resolve_template(
            "apt-get install -y {{saidata.packages.*.name}}",
            saidata
        )
        assert result == "apt-get install -y nginx nginx-common"
        
        # Test service management
        result = engine.resolve_template(
            "systemctl enable {{saidata.services.*.service_name}}",
            saidata
        )
        assert result == "systemctl enable nginx"
        
        # Test metadata access
        result = engine.resolve_template(
            "Installing {{display_name}} ({{name}}) version {{version}}",
            saidata
        )
        assert result == "Installing Nginx Web Server (nginx) version 1.20.1"
    
    def test_multi_step_action_resolution(self):
        """Test resolving multi-step actions."""
        metadata = Metadata(name="postgresql", version="13.7")
        packages = [
            Package(name="postgresql-13"),
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
        
        # Create a multi-step action
        steps = [
            Step(
                name="Install packages",
                command="apt-get install -y {{saidata.packages.*.name}}",
            ),
            Step(
                name="Initialize database",
                command="sudo -u postgres initdb -D /var/lib/postgresql/{{version}}/main",
            ),
            Step(
                name="Start service",
                command="systemctl start {{saidata.services.*.service_name}}",
            ),
            Step(
                name="Enable service",
                command="systemctl enable {{saidata.services.*.service_name}}",
            ),
        ]
        
        action = Action(
            description="Install and configure PostgreSQL",
            steps=steps,
            timeout=600,
        )
        
        engine = TemplateEngine()
        result = engine.resolve_action_template(action, saidata)
        
        assert len(result['steps']) == 4
        assert result['steps'][0]['command'] == "apt-get install -y postgresql-13 postgresql-client-13 postgresql-contrib-13"
        assert result['steps'][1]['command'] == "sudo -u postgres initdb -D /var/lib/postgresql/13.7/main"
        assert result['steps'][2]['command'] == "systemctl start postgresql"
        assert result['steps'][3]['command'] == "systemctl enable postgresql"
    
    def test_conditional_template_resolution(self):
        """Test template resolution with conditionals."""
        metadata = Metadata(name="redis", version="6.2.7")
        packages = [Package(name="redis-server")]
        
        saidata = SaiData(
            version="0.2",
            metadata=metadata,
            packages=packages,
        )
        
        # Template with conditional logic
        template = """
        {%- if version -%}
        apt-get install -y {{saidata.packages.*.name}}={{version}}*
        {%- else -%}
        apt-get install -y {{saidata.packages.*.name}}
        {%- endif -%}
        """
        
        engine = TemplateEngine()
        result = engine.resolve_template(template, saidata)
        
        assert result == "apt-get install -y redis-server=6.2.7*"
        
        # Test without version
        saidata.metadata.version = None
        result = engine.resolve_template(template, saidata)
        assert result == "apt-get install -y redis-server"
    
    def test_docker_container_template(self):
        """Test template resolution for Docker containers."""
        from saigen.models.saidata import Container
        
        metadata = Metadata(name="nginx", version="1.20.1")
        containers = [
            Container(
                name="nginx-web",
                image="nginx",
                tag="1.20.1-alpine",
                ports=["80:80", "443:443"],
                volumes=["/etc/nginx:/etc/nginx:ro"],
                environment={"NGINX_HOST": "localhost"},
            )
        ]
        
        saidata = SaiData(
            version="0.2",
            metadata=metadata,
            containers=containers,
        )
        
        # Docker run template
        template = """
        docker run -d --name {{saidata.containers.0.name}} \
        {%- for port in saidata.containers.0.ports %}
        -p {{port}} \
        {%- endfor %}
        {%- for volume in saidata.containers.0.volumes %}
        -v {{volume}} \
        {%- endfor %}
        {%- for key, value in saidata.containers.0.environment.items() %}
        -e {{key}}={{value}} \
        {%- endfor %}
        {{saidata.containers.0.image}}:{{saidata.containers.0.tag}}
        """
        
        engine = TemplateEngine()
        result = engine.resolve_template(template, saidata)
        
        # Normalize whitespace for comparison
        normalized_result = ' '.join(result.split())
        expected = "docker run -d --name nginx-web -p 80:80 -p 443:443 -v /etc/nginx:/etc/nginx:ro -e NGINX_HOST=localhost nginx:1.20.1-alpine"
        
        assert normalized_result == expected
    
    def test_complex_package_array_expansion(self):
        """Test complex array expansion scenarios."""
        metadata = Metadata(name="lamp-stack")
        packages = [
            Package(name="apache2", version="2.4.41"),
            Package(name="mysql-server", version="8.0.28"),
            Package(name="php", version="7.4.3"),
            Package(name="php-mysql"),
            Package(name="libapache2-mod-php"),
        ]
        
        saidata = SaiData(
            version="0.2",
            metadata=metadata,
            packages=packages,
        )
        
        engine = TemplateEngine()
        
        # Test package names expansion
        result = engine.resolve_template(
            "apt-get install -y {{saidata.packages.*.name}}",
            saidata
        )
        assert result == "apt-get install -y apache2 mysql-server php php-mysql libapache2-mod-php"
        
        # Test filtering packages with versions
        template = """
        {%- for pkg in saidata.packages -%}
        {%- if pkg.version -%}
        {{pkg.name}}={{pkg.version}} {% endif -%}
        {%- endfor -%}
        """
        
        result = engine.resolve_template(template, saidata)
        normalized_result = result.strip()
        assert normalized_result == "apache2=2.4.41 mysql-server=8.0.28 php=7.4.3"
    
    def test_template_with_additional_context(self):
        """Test template resolution with additional context variables."""
        metadata = Metadata(name="custom-app", version="1.0.0")
        saidata = SaiData(version="0.2", metadata=metadata)
        
        additional_context = {
            'install_prefix': '/opt/custom-app',
            'user': 'appuser',
            'group': 'appgroup',
            'config_file': 'app.conf',
        }
        
        template = """
        mkdir -p {{install_prefix}}/bin {{install_prefix}}/etc {{install_prefix}}/var/log &&
        chown -R {{user}}:{{group}} {{install_prefix}} &&
        cp {{config_file}} {{install_prefix}}/etc/ &&
        echo "Installed {{display_name}} to {{install_prefix}}"
        """
        
        engine = TemplateEngine()
        result = engine.resolve_template(template, saidata, additional_context)
        
        expected_parts = [
            "mkdir -p /opt/custom-app/bin /opt/custom-app/etc /opt/custom-app/var/log",
            "chown -R appuser:appgroup /opt/custom-app",
            "cp app.conf /opt/custom-app/etc/",
            "echo \"Installed custom-app to /opt/custom-app\""
        ]
        
        for part in expected_parts:
            assert part in result
    
    def test_error_handling_with_realistic_templates(self):
        """Test error handling with realistic but problematic templates."""
        from sai.providers.template_engine import TemplateResolutionError
        
        metadata = Metadata(name="test-app")
        saidata = SaiData(version="0.2", metadata=metadata)
        
        engine = TemplateEngine()
        
        # Test undefined variable in realistic context
        with pytest.raises(TemplateResolutionError):
            engine.resolve_template(
                "systemctl start {{undefined_variable}}",
                saidata
            )
        
        # Test malformed template
        with pytest.raises(TemplateResolutionError):
            engine.resolve_template(
                "install {{saidata.packages.*.name",  # Missing closing brace
                saidata
            )


if __name__ == "__main__":
    pytest.main([__file__])