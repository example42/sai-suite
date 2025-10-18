"""Template resolution engine for SAI CLI tool."""

import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional, Union

from jinja2 import BaseLoader, Environment, StrictUndefined, TemplateSyntaxError, UndefinedError

from saigen.models.saidata import SaiData

from ..models.provider_data import Action

logger = logging.getLogger(__name__)


class TemplateResolutionError(Exception):
    """Exception raised when template resolution fails."""


class TemplateContext:
    """Template context container for organizing template variables and functions."""

    def __init__(
        self,
        saidata: SaiData,
        variables: Optional[Dict[str, Any]] = None,
        functions: Optional[Dict[str, Callable]] = None,
    ):
        """Initialize template context.

        Args:
            saidata: SaiData object
            variables: Additional template variables
            functions: Custom template functions
        """
        self.saidata = saidata
        self.variables = variables or {}
        self.functions = functions or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for Jinja2 template rendering.

        Returns:
            Dictionary containing all context variables and functions
        """
        context = {
            "saidata": self.saidata,
            "env": dict(os.environ),  # Environment variables
        }

        # Add custom variables
        context.update(self.variables)

        # Add custom functions
        context.update(self.functions)

        return context


class TemplateFunction:
    """Wrapper for template functions with metadata."""

    def __init__(self, name: str, function: Callable, description: str = ""):
        """Initialize template function.

        Args:
            name: Function name
            function: Callable function
            description: Function description
        """
        self.name = name
        self.function = function
        self.description = description

    def __call__(self, *args, **kwargs):
        """Call the wrapped function."""
        return self.function(*args, **kwargs)


class SaidataContextBuilder:
    """Builds template context from SaiData objects."""

    def __init__(self, saidata: SaiData):
        """Initialize context builder with saidata.

        Args:
            saidata: SaiData object to extract context from
        """
        self.saidata = saidata

    def build_context(self) -> Dict[str, Any]:
        """Build template context from saidata.

        Returns:
            Dictionary containing template variables
        """
        saidata_context = self._build_saidata_context()

        context = {
            "saidata": saidata_context,
            "metadata": self._build_metadata_context(),
        }

        # Add top-level convenience variables
        if self.saidata.metadata:
            context["name"] = self.saidata.metadata.name
            context["version"] = self.saidata.metadata.version
            context["display_name"] = (
                self.saidata.metadata.display_name or self.saidata.metadata.name
            )

        # Add top-level collections for easier access
        context.update(saidata_context)

        logger.debug(f"Built template context with keys: {list(context.keys())}")
        return context

    def _build_saidata_context(self) -> Dict[str, Any]:
        """Build the saidata section of the context."""
        context = {
            "metadata": self._build_metadata_context(),
        }

        # Add collections with array expansion support (always include as empty
        # lists if not present)
        context["packages"] = (
            [self._package_to_dict(pkg) for pkg in self.saidata.packages]
            if self.saidata.packages
            else []
        )
        context["services"] = (
            [self._service_to_dict(svc) for svc in self.saidata.services]
            if self.saidata.services
            else []
        )
        context["files"] = (
            [self._file_to_dict(file) for file in self.saidata.files] if self.saidata.files else []
        )
        context["directories"] = (
            [self._directory_to_dict(dir) for dir in self.saidata.directories]
            if self.saidata.directories
            else []
        )
        context["commands"] = (
            [self._command_to_dict(cmd) for cmd in self.saidata.commands]
            if self.saidata.commands
            else []
        )
        context["ports"] = (
            [self._port_to_dict(port) for port in self.saidata.ports] if self.saidata.ports else []
        )
        context["containers"] = (
            [self._container_to_dict(container) for container in self.saidata.containers]
            if self.saidata.containers
            else []
        )

        # Installation method collections
        context["sources"] = (
            [self._source_to_dict(src) for src in self.saidata.sources]
            if self.saidata.sources
            else []
        )
        context["binaries"] = (
            [self._binary_to_dict(bin) for bin in self.saidata.binaries]
            if self.saidata.binaries
            else []
        )
        context["scripts"] = (
            [self._script_to_dict(scr) for scr in self.saidata.scripts]
            if self.saidata.scripts
            else []
        )

        # Add providers section if it exists
        if hasattr(self.saidata, "providers") and self.saidata.providers:
            context["providers"] = self._build_providers_context()
            logger.debug(f"Added providers to context: {list(context['providers'].keys())}")
        else:
            context["providers"] = {}
            logger.debug("No providers found in saidata")

        return context

    def _build_metadata_context(self) -> Dict[str, Any]:
        """Build metadata context."""
        if not self.saidata.metadata:
            return {}

        metadata = self.saidata.metadata

        # Helper function to handle None values for Jinja2 default filter
        # Don't convert None to empty string - let Jinja2 handle it
        def safe_value(value):
            return value

        context = {
            "name": safe_value(metadata.name),
            "display_name": safe_value(metadata.display_name) or safe_value(metadata.name),
            "description": safe_value(metadata.description),
            "version": safe_value(metadata.version),
            "category": safe_value(metadata.category),
            "subcategory": safe_value(metadata.subcategory),
            "tags": metadata.tags or [],
            "license": safe_value(metadata.license),
            "language": safe_value(metadata.language),
            "maintainer": safe_value(metadata.maintainer),
        }

        # Add URLs if present
        if metadata.urls:
            context["urls"] = {
                "website": safe_value(metadata.urls.website),
                "documentation": safe_value(metadata.urls.documentation),
                "source": safe_value(metadata.urls.source),
                "issues": safe_value(metadata.urls.issues),
                "support": safe_value(metadata.urls.support),
                "download": safe_value(metadata.urls.download),
                "changelog": safe_value(metadata.urls.changelog),
                "license": safe_value(metadata.urls.license),
                "sbom": safe_value(metadata.urls.sbom),
                "icon": safe_value(metadata.urls.icon),
            }

        return context

    def _build_providers_context(self) -> Dict[str, Any]:
        """Build providers context from saidata."""
        if not hasattr(self.saidata, "providers") or not self.saidata.providers:
            return {}

        providers_context = {}

        # Handle different provider structures
        if hasattr(self.saidata.providers, "__dict__"):
            # If providers is an object with attributes
            for provider_name, provider_data in self.saidata.providers.__dict__.items():
                if provider_data is not None:
                    providers_context[provider_name] = self._provider_data_to_dict(provider_data)
        elif isinstance(self.saidata.providers, dict):
            # If providers is a dictionary
            for provider_name, provider_data in self.saidata.providers.items():
                if provider_data is not None:
                    providers_context[provider_name] = self._provider_data_to_dict(provider_data)

        return providers_context

    def _provider_data_to_dict(self, provider_data) -> Dict[str, Any]:
        """Convert provider data to dictionary."""
        if hasattr(provider_data, "__dict__"):
            # Convert object to dict
            result = {}
            for key, value in provider_data.__dict__.items():
                if isinstance(value, list):
                    result[key] = [self._convert_to_dict(item) for item in value]
                else:
                    result[key] = self._convert_to_dict(value)
            return result
        elif isinstance(provider_data, dict):
            return provider_data
        else:
            return {}

    def _convert_to_dict(self, obj) -> Any:
        """Convert object to dictionary if possible."""
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        else:
            return obj

    def _package_to_dict(self, package) -> Dict[str, Any]:
        """Convert Package model to dictionary."""
        return {
            "name": package.name,
            "package_name": package.package_name,
            "version": package.version,
            "alternatives": package.alternatives or [],
            "install_options": package.install_options,
            "repository": package.repository,
            "checksum": package.checksum,
            "signature": package.signature,
            "download_url": package.download_url,
        }

    def _service_to_dict(self, service) -> Dict[str, Any]:
        """Convert Service model to dictionary."""
        return {
            "name": service.name,
            "service_name": service.service_name or service.name,
            "type": service.type,
            "enabled": service.enabled,
            "config_files": service.config_files or [],
        }

    def _file_to_dict(self, file) -> Dict[str, Any]:
        """Convert File model to dictionary."""
        return {
            "name": file.name,
            "path": file.path,
            "type": file.type,
            "owner": file.owner,
            "group": file.group,
            "mode": file.mode,
            "backup": file.backup,
        }

    def _directory_to_dict(self, directory) -> Dict[str, Any]:
        """Convert Directory model to dictionary."""
        return {
            "name": directory.name,
            "path": directory.path,
            "owner": directory.owner,
            "group": directory.group,
            "mode": directory.mode,
            "recursive": directory.recursive,
        }

    def _command_to_dict(self, command) -> Dict[str, Any]:
        """Convert Command model to dictionary."""
        return {
            "name": command.name,
            "path": command.path,
            "arguments": command.arguments or [],
            "aliases": command.aliases or [],
            "shell_completion": command.shell_completion,
            "man_page": command.man_page,
        }

    def _port_to_dict(self, port) -> Dict[str, Any]:
        """Convert Port model to dictionary."""
        return {
            "port": port.port,
            "protocol": port.protocol,
            "service": port.service,
            "description": port.description,
        }

    def _container_to_dict(self, container) -> Dict[str, Any]:
        """Convert Container model to dictionary."""
        return {
            "name": container.name,
            "image": container.image,
            "tag": container.tag,
            "registry": container.registry,
            "platform": container.platform,
            "ports": container.ports or [],
            "volumes": container.volumes or [],
            "environment": container.environment or {},
            "networks": container.networks or [],
            "labels": container.labels or {},
        }

    def _source_to_dict(self, source) -> Dict[str, Any]:
        """Convert Source model to dictionary."""
        return {
            "name": source.name,
            "url": source.url,
            "version": source.version,
            "build_system": source.build_system,
            "build_dir": source.build_dir,
            "source_dir": source.source_dir,
            "install_prefix": source.install_prefix,
            "configure_args": source.configure_args or [],
            "build_args": source.build_args or [],
            "install_args": source.install_args or [],
            "prerequisites": source.prerequisites or [],
            "environment": source.environment or {},
            "checksum": source.checksum,
            "custom_commands": (
                source.custom_commands.__dict__ if source.custom_commands else {}
            ),
        }

    def _binary_to_dict(self, binary) -> Dict[str, Any]:
        """Convert Binary model to dictionary."""
        return {
            "name": binary.name,
            "url": binary.url,
            "version": binary.version,
            "architecture": binary.architecture,
            "platform": binary.platform,
            "checksum": binary.checksum,
            "install_path": binary.install_path,
            "executable": binary.executable,
            "archive": binary.archive.__dict__ if binary.archive else {},
            "permissions": binary.permissions,
            "custom_commands": (
                binary.custom_commands.__dict__ if binary.custom_commands else {}
            ),
        }

    def _script_to_dict(self, script) -> Dict[str, Any]:
        """Convert Script model to dictionary."""
        return {
            "name": script.name,
            "url": script.url,
            "version": script.version,
            "interpreter": script.interpreter,
            "checksum": script.checksum,
            "arguments": script.arguments or [],
            "environment": script.environment or {},
            "working_dir": script.working_dir,
            "timeout": script.timeout,
            "custom_commands": (
                script.custom_commands.__dict__ if script.custom_commands else {}
            ),
        }


class ArrayExpansionFilter:
    """Custom Jinja2 filter for array expansion syntax."""

    @staticmethod
    def expand_array_syntax(template_str: str, context: Dict[str, Any]) -> str:
        """Expand array syntax like {{saidata.packages.*.name}} before Jinja2 processing.

        Args:
            template_str: Template string with potential array syntax
            context: Template context dictionary

        Returns:
            Template string with array syntax expanded to Jinja2 loops
        """
        # Pattern to match array expansion syntax: {{path.*.field|filter}}
        array_pattern = r"\{\{\s*([^}]+\.\*\.[^}|]+)(\|[^}]+)?\s*\}\}"

        def replace_array_syntax(match):
            full_path = match.group(1).strip()
            filters = match.group(2) or ""

            # Split the path: saidata.packages.*.name -> ['saidata', 'packages', '*', 'name']
            parts = full_path.split(".")

            if "*" not in parts:
                return match.group(0)  # No array expansion needed

            star_index = parts.index("*")
            if star_index == 0 or star_index == len(parts) - 1:
                logger.warning(f"Invalid array syntax: {full_path}")
                return match.group(0)

            # Build the path components
            array_path = ".".join(parts[:star_index])
            field_path = ".".join(parts[star_index + 1 :])

            # Generate Jinja2 loop syntax with proper filter handling
            if filters:
                # Handle filters like |join(',')
                if "join(" in filters:
                    # Extract separator from join filter
                    join_match = re.search(r'join\([\'"]([^\'"]*)[\'"]?\)', filters)
                    if join_match:
                        sep = join_match.group(1)
                        jinja_loop = (
                            f"{{{{ {array_path} | map(attribute='{field_path}') | "
                            f"join('{sep}') }}}}"
                        )
                    else:
                        jinja_loop = (
                            f"{{{{ {array_path} | map(attribute='{field_path}') | join(' ') }}}}"
                        )
                else:
                    jinja_loop = f"{{{{ {array_path} | map(attribute='{field_path}'){filters} }}}}"
            else:
                jinja_loop = f"{{{{ {array_path} | map(attribute='{field_path}') | join(' ') }}}}"

            logger.debug(f"Expanded array syntax '{full_path}{filters}' to '{jinja_loop}'")
            return jinja_loop

        expanded = re.sub(array_pattern, replace_array_syntax, template_str)
        return expanded


class TemplateEngine:
    """Template resolution engine using Jinja2."""

    def __init__(self):
        """Initialize the template engine."""
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=False,  # We're dealing with shell commands, not HTML
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,  # Raise errors for undefined variables
        )

        # Template cache for performance
        self._template_cache = {}
        self._max_cache_size = 100

        # Custom functions registry
        self._custom_functions = {}

        # Add custom filters
        self.env.filters["expand_arrays"] = self._expand_arrays_filter
        self.env.filters["sai_lookup"] = self._sai_lookup_filter

        # Override default filter to handle None values properly
        def default_filter(value, default_value="", boolean=False):
            """Custom default filter that treats None as undefined."""
            if value is None or (boolean and not value):
                return default_value
            return value

        self.env.filters["default"] = default_filter

        # Add global functions for easier template access
        self.env.globals["sai_packages"] = self._sai_packages_global
        self.env.globals["sai_package"] = self._sai_package_global
        self.env.globals["sai_service"] = self._sai_service_global
        self.env.globals["sai_file"] = self._sai_file_global
        self.env.globals["sai_port"] = self._sai_port_global
        self.env.globals["sai_command"] = self._sai_command_global

        # Installation method functions
        self.env.globals["sai_source"] = self._sai_source_global
        self.env.globals["sai_binary"] = self._sai_binary_global
        self.env.globals["sai_script"] = self._sai_script_global

        logger.debug("Template engine initialized")

    def register_function(self, name: str, function: Callable) -> None:
        """Register a custom template function.

        Args:
            name: Function name to use in templates
            function: Callable function
        """
        self._custom_functions[name] = function
        self.env.globals[name] = function
        logger.debug(f"Registered custom template function: {name}")

    def _create_context(
        self, saidata: SaiData, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create template context from saidata and variables.

        Args:
            saidata: SaiData object
            variables: Additional variables

        Returns:
            Template context dictionary
        """
        if saidata is None:
            raise TemplateResolutionError("saidata is required for template resolution")

        # Build context from saidata
        context_builder = SaidataContextBuilder(saidata)
        context = context_builder.build_context()

        # Add the raw saidata object for direct access
        context["saidata"] = saidata

        # Add environment variables
        context["env"] = dict(os.environ)

        # Add custom variables
        if variables:
            context.update(variables)

        # Add custom functions
        context.update(self._custom_functions)

        # Add built-in global functions that use the current context
        def sai_packages_wrapper(saidata_obj, provider_name=None):
            return self._sai_packages_global(context, provider_name)

        def sai_package_wrapper(saidata_obj, index_or_wildcard=0, field="package_name", provider_name=None):
            return self._sai_package_global(context, index_or_wildcard, field, provider_name)

        def sai_service_wrapper(saidata_obj, provider_name=None, index=0, field="name"):
            return self._sai_service_global(context, provider_name, index, field)

        def sai_file_wrapper(saidata_obj, index=0, field="path"):
            return self._sai_file_global(context, index, field)

        def sai_port_wrapper(saidata_obj, index=0, field="port"):
            return self._sai_port_global(context, index, field)

        def sai_command_wrapper(saidata_obj, index=0, field="path"):
            return self._sai_command_global(context, index, field)

        # Installation method function wrappers
        def sai_source_wrapper(saidata_obj, index=0, field="url", provider_name=None):
            return self._sai_source_global(context, index, field, provider_name)

        def sai_binary_wrapper(saidata_obj, index=0, field="url", provider_name=None):
            return self._sai_binary_global(context, index, field, provider_name)

        def sai_script_wrapper(saidata_obj, index=0, field="url", provider_name=None):
            return self._sai_script_global(context, index, field, provider_name)

        # Only add built-in functions if they haven't been overridden by custom functions
        if "sai_packages" not in context:
            context["sai_packages"] = sai_packages_wrapper
        if "sai_package" not in context:
            context["sai_package"] = sai_package_wrapper
        if "sai_service" not in context:
            context["sai_service"] = sai_service_wrapper
        if "sai_file" not in context:
            context["sai_file"] = sai_file_wrapper
        if "sai_port" not in context:
            context["sai_port"] = sai_port_wrapper
        if "sai_command" not in context:
            context["sai_command"] = sai_command_wrapper
        if "sai_source" not in context:
            context["sai_source"] = sai_source_wrapper
        if "sai_binary" not in context:
            context["sai_binary"] = sai_binary_wrapper
        if "sai_script" not in context:
            context["sai_script"] = sai_script_wrapper

        return context

    def resolve_template(
        self,
        template_str: str,
        saidata: SaiData,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Resolve template string with saidata context.

        Args:
            template_str: Template string to resolve
            saidata: SaiData object for context
            additional_context: Additional template variables

        Returns:
            Resolved template string

        Raises:
            TemplateResolutionError: If template resolution fails
        """
        try:
            # Check cache first
            if template_str in self._template_cache:
                template = self._template_cache[template_str]
            else:
                # Expand array syntax before Jinja2 processing
                expanded_template = ArrayExpansionFilter.expand_array_syntax(template_str, {})

                # Create and cache template
                try:
                    template = self.env.from_string(expanded_template)
                except TemplateSyntaxError as e:
                    raise TemplateResolutionError(f"Template syntax error in '{template_str}': {e}")

                # Cache management
                if len(self._template_cache) >= self._max_cache_size:
                    # Remove oldest entry (simple FIFO)
                    oldest_key = next(iter(self._template_cache))
                    del self._template_cache[oldest_key]

                self._template_cache[template_str] = template

            # Create context
            context = self._create_context(saidata, additional_context)

            # Render template
            result = template.render(context)

            logger.debug(f"Resolved template: '{template_str}' -> '{result}'")
            return result.strip()

        except TemplateResolutionError:
            raise
        except (TemplateSyntaxError, UndefinedError) as e:
            error_msg = f"Template resolution failed for '{template_str}': {e}"
            logger.error(error_msg)
            raise TemplateResolutionError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error resolving template '{template_str}': {e}"
            logger.error(error_msg)
            raise TemplateResolutionError(error_msg) from e

    def resolve_action_template(
        self, action: Action, saidata: SaiData, additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Resolve all template strings in an action.

        Args:
            action: Action object with potential templates
            saidata: SaiData object for context
            additional_context: Additional template variables

        Returns:
            Dictionary with resolved template values

        Raises:
            TemplateResolutionError: If any template resolution fails
        """
        resolved = {}

        try:
            # Resolve main command/template
            if action.template:
                resolved["command"] = self.resolve_template(
                    action.template, saidata, additional_context
                )
            elif action.command:
                resolved["command"] = self.resolve_template(
                    action.command, saidata, additional_context
                )

            # Resolve script if present
            if action.script:
                resolved["script"] = self.resolve_template(
                    action.script, saidata, additional_context
                )

            # Resolve rollback command if present
            if action.rollback:
                resolved["rollback"] = self.resolve_template(
                    action.rollback, saidata, additional_context
                )

            # Resolve variables if present
            if action.variables:
                resolved["variables"] = {}
                for key, value in action.variables.items():
                    resolved["variables"][key] = self.resolve_template(
                        value, saidata, additional_context
                    )

            # Resolve step commands if present
            if action.steps:
                resolved["steps"] = []
                for step in action.steps:
                    step_resolved = {
                        "name": step.name,
                        "command": self.resolve_template(step.command, saidata, additional_context),
                        "condition": step.condition,
                        "ignore_failure": step.ignore_failure,
                        "timeout": step.timeout,
                    }

                    # Resolve condition if it's a template
                    if step.condition:
                        step_resolved["condition"] = self.resolve_template(
                            step.condition, saidata, additional_context
                        )

                    resolved["steps"].append(step_resolved)

            logger.debug(f"Resolved action templates: {list(resolved.keys())}")
            return resolved

        except Exception as e:
            error_msg = f"Failed to resolve action templates: {e}"
            logger.error(error_msg)
            raise TemplateResolutionError(error_msg) from e

    def _expand_arrays_filter(self, value: List[Dict[str, Any]], field: str) -> List[str]:
        """Jinja2 filter to extract field values from array of objects.

        Args:
            value: List of dictionaries
            field: Field name to extract

        Returns:
            List of field values
        """
        if not isinstance(value, list):
            return []

        result = []
        for item in value:
            if isinstance(item, dict) and field in item:
                result.append(str(item[field]))

        return result

    def _sai_lookup_filter(
        self,
        saidata_context: Dict[str, Any],
        resource_type: str,
        field: str = "name",
        index: int = 0,
        provider_name: str = None,
    ) -> str:
        """Smart lookup filter for saidata resources with provider-specific fallbacks.

        This filter implements the standard SAI lookup pattern:
        1. Try provider-specific resource (if provider_name specified)
        2. Fall back to general resource array
        3. Ultimate fallback to metadata.name

        Args:
            saidata_context: The saidata context dictionary
            resource_type: Type of resource ('packages', 'services', 'files', etc.)
            field: Field to extract (default: 'name')
            index: Index for single item lookup (default: 0)
            provider_name: Provider name for provider-specific lookup

        Returns:
            Resolved value or empty string if not found

        Examples:
            {{saidata | sai_lookup('packages', 'name')}} -> all package names
            {{saidata | sai_lookup('packages', 'name', 0, 'brew')}} -> first package name with brew fallback
            {{saidata | sai_lookup('services', 'service_name', 0)}} -> first service name
            {{saidata | sai_lookup('files', 'path', 0)}} -> first file path
        """
        try:
            # Helper function to extract field from resource
            def extract_field(resource, field_name):
                if isinstance(resource, dict):
                    return str(resource.get(field_name, ""))
                elif hasattr(resource, field_name):
                    value = getattr(resource, field_name, "")
                    return str(value) if value is not None else ""
                return ""

            # Helper function to get names from resource list
            def get_resource_names(resources, field_name, single_index=None):
                if not resources:
                    return ""

                if single_index is not None and single_index >= 0:
                    # Return single item
                    if len(resources) > single_index:
                        return extract_field(resources[single_index], field_name)
                    return ""
                else:
                    # Return all items joined with space
                    names = []
                    for resource in resources:
                        name = extract_field(resource, field_name)
                        if name:
                            names.append(name)
                    return " ".join(names)

            # 1. Try provider-specific resource first
            if provider_name and "providers" in saidata_context:
                providers = saidata_context["providers"]
                if isinstance(providers, dict) and provider_name in providers:
                    provider_data = providers[provider_name]
                    if isinstance(provider_data, dict) and resource_type in provider_data:
                        provider_resources = provider_data[resource_type]
                        if provider_resources:
                            result = get_resource_names(
                                provider_resources, field, index if index >= 0 else None
                            )
                            if result:
                                logger.debug(f"Found provider-specific {resource_type}: {result}")
                                return result

            # 2. Fall back to general resource array
            if resource_type in saidata_context:
                general_resources = saidata_context[resource_type]
                if general_resources:
                    result = get_resource_names(
                        general_resources, field, index if index >= 0 else None
                    )
                    if result:
                        return result

            # 3. Ultimate fallback to metadata.name for 'name' field
            if field == "name" and "metadata" in saidata_context:
                metadata = saidata_context["metadata"]
                if isinstance(metadata, dict) and "name" in metadata:
                    return str(metadata["name"])

            # 4. Return empty string if nothing found
            return ""

        except Exception as e:
            logger.warning(f"Error in sai_lookup filter: {e}")
            return ""

    def _sai_packages_global(
        self, saidata_context: Dict[str, Any], provider_name: str = None
    ) -> str:
        """Global function to get all package names with provider fallback.

        Usage: {{sai_packages(saidata, 'brew')}} or {{sai_packages(saidata)}}
        """
        # Handle case where saidata_context is the actual SaiData object
        if hasattr(saidata_context, "metadata"):
            # Convert SaiData to context
            context_builder = SaidataContextBuilder(saidata_context)
            saidata_context = context_builder.build_context()

        return self._sai_lookup_filter(saidata_context, "packages", "name", -1, provider_name)

    def _sai_package_global(
        self,
        saidata_context: Dict[str, Any],
        index_or_wildcard: Union[int, str] = 0,
        field: str = "package_name",
        provider_name: Optional[str] = None,
    ) -> str:
        """Global function to get package field with provider fallback.

        Args:
            saidata_context: The saidata context dictionary
            index_or_wildcard: Index (int) or '*' for all packages
            field: Field to extract ('name', 'package_name', 'version', etc.)
            provider_name: Provider name for provider-specific lookup

        Returns:
            Package field value(s) as string

        Usage:
            {{sai_package(saidata, 0, 'package_name', 'apt')}}  # First package name for apt
            {{sai_package(saidata, '*', 'package_name', 'apt')}} # All package names for apt
            {{sai_package(saidata, 0, 'name')}}                  # Logical name
            {{sai_package(saidata, 0)}}                          # First package_name (default)
        """
        # Handle case where saidata_context is the actual SaiData object
        if hasattr(saidata_context, "metadata"):
            # Convert SaiData to context
            context_builder = SaidataContextBuilder(saidata_context)
            saidata_context = context_builder.build_context()

        # Determine if we want all packages or a single one
        if index_or_wildcard == "*":
            index = -1  # Signal to return all
        else:
            index = int(index_or_wildcard)

        return self._sai_lookup_filter(saidata_context, "packages", field, index, provider_name)

    def _sai_service_global(
        self,
        saidata_context: Dict[str, Any],
        provider_name: str = None,
        index: int = 0,
        field: str = "name",
    ) -> str:
        """Global function to get service information.

        Usage: {{sai_service(saidata)}} or {{sai_service(saidata, 'systemd', 0, 'service_name')}}
        """
        # Handle case where saidata_context is the actual SaiData object
        if hasattr(saidata_context, "metadata"):
            # Convert SaiData to context
            context_builder = SaidataContextBuilder(saidata_context)
            saidata_context = context_builder.build_context()

        # For backward compatibility, if provider_name is an int, it's actually the index
        if isinstance(provider_name, int):
            index = provider_name
            provider_name = None

        return self._sai_lookup_filter(saidata_context, "services", field, index, provider_name)

    def _sai_file_global(
        self, saidata_context: Dict[str, Any], index: int = 0, field: str = "path"
    ) -> str:
        """Global function to get file information.

        Usage: {{sai_file(saidata)}} or {{sai_file(saidata, 0, 'path')}}
        """
        return self._sai_lookup_filter(saidata_context, "files", field, index)

    def _sai_port_global(
        self, saidata_context: Dict[str, Any], index: int = 0, field: str = "port"
    ) -> str:
        """Global function to get port information.

        Usage: {{sai_port(saidata)}} or {{sai_port(saidata, 0, 'port')}}
        """
        return self._sai_lookup_filter(saidata_context, "ports", field, index)

    def _sai_command_global(
        self, saidata_context: Dict[str, Any], index: int = 0, field: str = "path"
    ) -> str:
        """Global function to get command information.

        Args:
            saidata_context: Saidata context dictionary
            index: Index of command to retrieve (default: 0)
            field: Field to extract (default: 'path')

        Returns:
            Command field value as string

        Usage: {{sai_command(saidata)}} or {{sai_command(saidata, 0, 'path')}}
        """
        return self._sai_lookup_filter(saidata_context, "commands", field, index)

    def _sai_source_global(
        self,
        saidata_context: Dict[str, Any],
        index: int = 0,
        field: str = "url",
        provider_name: Optional[str] = None,
    ) -> str:
        """Global function to get source configuration field.

        Args:
            saidata_context: The saidata context dictionary
            index: Index of source to retrieve
            field: Field to extract ('name', 'url', 'version', 'build_system', etc.)
            provider_name: Provider name for provider-specific lookup

        Returns:
            Source field value as string

        Usage:
            {{sai_source(saidata, 0, 'url')}}           # First source URL
            {{sai_source(saidata, 0, 'version')}}       # First source version
            {{sai_source(saidata, 0, 'url', 'source')}} # Provider-specific source URL
        """
        if hasattr(saidata_context, "metadata"):
            context_builder = SaidataContextBuilder(saidata_context)
            saidata_context = context_builder.build_context()

        return self._sai_lookup_filter(saidata_context, "sources", field, index, provider_name)

    def _sai_binary_global(
        self,
        saidata_context: Dict[str, Any],
        index: int = 0,
        field: str = "url",
        provider_name: Optional[str] = None,
    ) -> str:
        """Global function to get binary configuration field.

        Args:
            saidata_context: The saidata context dictionary
            index: Index of binary to retrieve
            field: Field to extract ('name', 'url', 'version', 'platform', etc.)
            provider_name: Provider name for provider-specific lookup

        Returns:
            Binary field value as string

        Usage:
            {{sai_binary(saidata, 0, 'url')}}            # First binary URL
            {{sai_binary(saidata, 0, 'platform')}}       # First binary platform
            {{sai_binary(saidata, 0, 'url', 'binary')}}  # Provider-specific binary URL
        """
        if hasattr(saidata_context, "metadata"):
            context_builder = SaidataContextBuilder(saidata_context)
            saidata_context = context_builder.build_context()

        return self._sai_lookup_filter(saidata_context, "binaries", field, index, provider_name)

    def _sai_script_global(
        self,
        saidata_context: Dict[str, Any],
        index: int = 0,
        field: str = "url",
        provider_name: Optional[str] = None,
    ) -> str:
        """Global function to get script configuration field.

        Args:
            saidata_context: The saidata context dictionary
            index: Index of script to retrieve
            field: Field to extract ('name', 'url', 'interpreter', etc.)
            provider_name: Provider name for provider-specific lookup

        Returns:
            Script field value as string

        Usage:
            {{sai_script(saidata, 0, 'url')}}            # First script URL
            {{sai_script(saidata, 0, 'interpreter')}}    # First script interpreter
            {{sai_script(saidata, 0, 'url', 'script')}}  # Provider-specific script URL
        """
        if hasattr(saidata_context, "metadata"):
            context_builder = SaidataContextBuilder(saidata_context)
            saidata_context = context_builder.build_context()

        return self._sai_lookup_filter(saidata_context, "scripts", field, index, provider_name)
