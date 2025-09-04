"""Core execution engine for SAI CLI tool."""

import logging
import subprocess
import shlex
import os
import signal
import tempfile
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from ..models.saidata import SaiData
from ..models.provider_data import Action, Step
from ..providers.base import BaseProvider
from ..utils.system import get_system_info
from ..utils.logging import get_logger
from ..utils.errors import (
    ExecutionError, ProviderSelectionError, CommandExecutionError,
    PermissionError, UnsafeCommandError, CommandInjectionError
)
from ..utils.execution_tracker import get_execution_tracker, ExecutionStatus


logger = get_logger(__name__)


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    DRY_RUN = "dry_run"


@dataclass
class ExecutionResult:
    """Result of an action execution."""
    success: bool
    status: ExecutionStatus
    message: str
    provider_used: str
    action_name: str
    commands_executed: List[str]
    execution_time: float
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error_details: Optional[str] = None
    dry_run: bool = False


@dataclass
class ExecutionContext:
    """Context for action execution."""
    action: str
    software: str
    saidata: SaiData
    provider: Optional[str] = None
    dry_run: bool = False
    verbose: bool = False
    timeout: Optional[int] = None
    additional_context: Optional[Dict[str, Any]] = None


# Remove old exception classes - now using centralized error hierarchy


class ExecutionEngine:
    """Core execution engine that coordinates provider selection and action execution."""
    
    def __init__(self, providers: List[BaseProvider], config: Optional[Any] = None):
        """Initialize the execution engine.
        
        Args:
            providers: List of available providers
            config: SAI configuration object
        """
        self.providers = providers
        self.available_providers = [p for p in providers if p.is_available()]
        self.config = config
        self.execution_tracker = get_execution_tracker(config)
        
        logger.info(f"ExecutionEngine initialized with {len(self.providers)} providers "
                   f"({len(self.available_providers)} available)")
    
    def execute_action(self, context: ExecutionContext) -> ExecutionResult:
        """Execute an action using the most appropriate provider.
        
        Args:
            context: Execution context with action details
            
        Returns:
            ExecutionResult with execution details
            
        Raises:
            ProviderSelectionError: If no suitable provider is found
            ExecutionError: If execution fails
        """
        execution_id = None
        start_time = self._get_current_time()
        
        try:
            # Select the best provider for this action
            selected_provider = self._select_provider(context)
            
            # Start execution tracking
            execution_id = self.execution_tracker.start_execution(
                action=context.action,
                software=context.software,
                provider=selected_provider.name,
                dry_run=context.dry_run,
                verbose=context.verbose,
                timeout=context.timeout,
                additional_context={
                    'saidata_version': getattr(context.saidata, 'version', None) if context.saidata else None
                }
            )
            
            logger.info(f"Executing action '{context.action}' for '{context.software}' "
                       f"using provider '{selected_provider.name}' (ID: {execution_id})")
            
            # Get the action definition
            action = selected_provider.get_action(context.action)
            if not action:
                raise ExecutionError(
                    f"Action '{context.action}' not found in provider '{selected_provider.name}'",
                    action=context.action,
                    provider=selected_provider.name
                )
            
            # Execute the action
            if context.dry_run:
                result = self._dry_run_action(selected_provider, action, context, execution_id)
            else:
                result = self._execute_action(selected_provider, action, context, execution_id)
            
            # Calculate execution time
            result.execution_time = self._get_current_time() - start_time
            
            # Finish execution tracking
            final_result = self.execution_tracker.finish_execution(
                execution_id=execution_id,
                success=result.success,
                message=result.message,
                error_details=result.error_details
            )
            
            logger.info(f"Action execution completed: {result.status} in {result.execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = self._get_current_time() - start_time
            
            # Handle execution tracking cleanup
            if execution_id:
                try:
                    self.execution_tracker.finish_execution(
                        execution_id=execution_id,
                        success=False,
                        message=f"Execution failed: {e}",
                        error_details=str(e)
                    )
                except Exception as tracking_error:
                    logger.error(f"Failed to update execution tracking: {tracking_error}")
            
            # Log error with context
            logger.error(f"Action execution failed: {e}", extra={
                'action': context.action,
                'software': context.software,
                'execution_time': execution_time,
                'dry_run': context.dry_run
            }, exc_info=True)
            
            # Re-raise SAI errors as-is, wrap others
            if isinstance(e, (ProviderSelectionError, ExecutionError)):
                raise
            else:
                raise ExecutionError(
                    f"Unexpected error during execution: {e}",
                    action=context.action,
                    software=context.software,
                    error_code="EXECUTION_UNEXPECTED_ERROR"
                ) from e
    
    def _select_provider(self, context: ExecutionContext) -> BaseProvider:
        """Select the most appropriate provider for the action.
        
        Args:
            context: Execution context
            
        Returns:
            Selected provider
            
        Raises:
            ProviderSelectionError: If no suitable provider is found
        """
        # If specific provider is requested, use it
        if context.provider:
            for provider in self.available_providers:
                if provider.name == context.provider:
                    if provider.has_action(context.action):
                        logger.debug(f"Using requested provider '{context.provider}'")
                        return provider
                    else:
                        raise ProviderSelectionError(
                            f"Provider '{context.provider}' does not support action '{context.action}'"
                        )
            
            raise ProviderSelectionError(f"Requested provider '{context.provider}' not available")
        
        # Find providers that support the action
        suitable_providers = [
            p for p in self.available_providers 
            if p.has_action(context.action)
        ]
        
        if not suitable_providers:
            available_actions = set()
            for p in self.available_providers:
                available_actions.update(p.get_supported_actions())
            
            raise ProviderSelectionError(
                f"No available provider supports action '{context.action}'. "
                f"Available actions: {sorted(available_actions)}"
            )
        
        # Sort by priority (higher priority first)
        suitable_providers.sort(key=lambda p: p.get_priority(), reverse=True)
        
        selected = suitable_providers[0]
        logger.debug(f"Selected provider '{selected.name}' (priority: {selected.get_priority()}) "
                    f"from {len(suitable_providers)} suitable providers")
        
        return selected
    
    def _dry_run_action(self, provider: BaseProvider, action: Action, 
                       context: ExecutionContext, execution_id: Optional[str] = None) -> ExecutionResult:
        """Perform a dry run of the action (show what would be executed).
        
        Args:
            provider: Selected provider
            action: Action to execute
            context: Execution context
            
        Returns:
            ExecutionResult with dry run information
        """
        try:
            # Resolve templates to see what commands would be executed
            resolved = provider.resolve_action_templates(
                context.action, context.saidata, context.additional_context
            )
            
            commands = []
            message_parts = [f"DRY RUN: Would execute action '{context.action}' using provider '{provider.name}'"]
            
            # Collect commands that would be executed
            if 'command' in resolved:
                commands.append(resolved['command'])
                message_parts.append(f"Command: {resolved['command']}")
            
            if 'script' in resolved:
                commands.append(resolved['script'])
                message_parts.append(f"Script: {resolved['script']}")
            
            if 'steps' in resolved:
                for i, step in enumerate(resolved['steps']):
                    step_cmd = step['command']
                    commands.append(step_cmd)
                    step_name = step.get('name', f'Step {i+1}')
                    message_parts.append(f"{step_name}: {step_cmd}")
            
            # Add execution details
            if action.requires_root:
                message_parts.append("Note: This action requires root privileges")
            
            if action.timeout != 300:  # Non-default timeout
                message_parts.append(f"Timeout: {action.timeout}s")
            
            message = "\n".join(message_parts)
            
            return ExecutionResult(
                success=True,
                status=ExecutionStatus.DRY_RUN,
                message=message,
                provider_used=provider.name,
                action_name=context.action,
                commands_executed=commands,
                execution_time=0.0,
                dry_run=True
            )
            
        except Exception as e:
            error_msg = f"Dry run failed: {e}"
            logger.error(error_msg)
            
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.FAILURE,
                message=error_msg,
                provider_used=provider.name,
                action_name=context.action,
                commands_executed=[],
                execution_time=0.0,
                error_details=str(e),
                dry_run=True
            )
    
    def _execute_action(self, provider: BaseProvider, action: Action,
                       context: ExecutionContext, execution_id: Optional[str] = None) -> ExecutionResult:
        """Execute the action using the selected provider.
        
        Args:
            provider: Selected provider
            action: Action to execute
            context: Execution context
            
        Returns:
            ExecutionResult with execution details
        """
        try:
            # Resolve templates
            resolved = provider.resolve_action_templates(
                context.action, context.saidata, context.additional_context
            )
            
            commands_executed = []
            
            # Execute based on action type
            if action.steps:
                # Multi-step execution
                result = self._execute_steps(resolved['steps'], action, commands_executed, context, execution_id)
            elif 'command' in resolved:
                # Single command execution
                result = self._execute_command(resolved['command'], action, commands_executed, context, execution_id)
            elif 'script' in resolved:
                # Script execution
                result = self._execute_script(resolved['script'], action, commands_executed, context, execution_id)
            else:
                raise ExecutionError("No executable command, script, or steps found in action")
            
            # Update result with provider and action info
            result.provider_used = provider.name
            result.action_name = context.action
            result.commands_executed = commands_executed
            
            return result
            
        except Exception as e:
            error_msg = f"Action execution failed: {e}"
            logger.error(error_msg)
            
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.FAILURE,
                message=error_msg,
                provider_used=provider.name,
                action_name=context.action,
                commands_executed=[],
                execution_time=0.0,
                error_details=str(e)
            )
    
    def _execute_command(self, command: str, action: Action, commands_executed: List[str],
                        context: ExecutionContext, execution_id: Optional[str] = None) -> ExecutionResult:
        """Execute a single command.
        
        Args:
            command: Command to execute
            action: Action configuration
            commands_executed: List to track executed commands
            context: Execution context
            
        Returns:
            ExecutionResult with execution details
        """
        commands_executed.append(command)
        
        # Parse command safely
        try:
            cmd_args = shlex.split(command)
        except ValueError as e:
            raise ExecutionError(f"Invalid command syntax: {e}")
        
        if not cmd_args:
            raise ExecutionError("Empty command")
        
        # Execute with security constraints
        cmd_start_time = self._get_current_time()
        result = self._run_secure_command(
            cmd_args, 
            timeout=context.timeout or action.timeout,
            requires_root=action.requires_root,
            verbose=context.verbose
        )
        cmd_execution_time = self._get_current_time() - cmd_start_time
        
        # Track command execution if execution_id is provided
        if execution_id and self.execution_tracker:
            self.execution_tracker.add_command_result(
                execution_id=execution_id,
                command=command,
                exit_code=result.get('exit_code', -1),
                stdout=result.get('stdout', ''),
                stderr=result.get('stderr', ''),
                execution_time=cmd_execution_time
            )
        
        if result['success']:
            return ExecutionResult(
                success=True,
                status=ExecutionStatus.SUCCESS,
                message=f"Command executed successfully: {command}",
                provider_used="",  # Will be set by caller
                action_name=context.action,
                commands_executed=[],  # Will be set by caller
                execution_time=0.0,  # Will be set by caller
                exit_code=result['exit_code'],
                stdout=result['stdout'],
                stderr=result['stderr']
            )
        else:
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.FAILURE,
                message=f"Command failed: {command}",
                provider_used="",  # Will be set by caller
                action_name=context.action,
                commands_executed=[],  # Will be set by caller
                execution_time=0.0,  # Will be set by caller
                exit_code=result['exit_code'],
                stdout=result['stdout'],
                stderr=result['stderr'],
                error_details=result.get('error')
            )
    
    def _execute_steps(self, steps: List[Dict], action: Action, commands_executed: List[str],
                      context: ExecutionContext, execution_id: Optional[str] = None) -> ExecutionResult:
        """Execute multiple steps in sequence.
        
        Args:
            steps: List of resolved steps
            action: Action configuration
            commands_executed: List to track executed commands
            context: Execution context
            
        Returns:
            ExecutionResult with execution details
        """
        for i, step in enumerate(steps):
            step_name = step.get('name', f'Step {i+1}')
            command = step['command']
            ignore_failure = step.get('ignore_failure', False)
            step_timeout = step.get('timeout') or context.timeout or action.timeout
            
            logger.debug(f"Executing {step_name}: {command}")
            
            # Check condition if present
            condition = step.get('condition')
            if condition and not self._evaluate_condition(condition):
                logger.debug(f"Skipping {step_name} due to condition: {condition}")
                continue
            
            commands_executed.append(command)
            
            # Parse and execute command
            try:
                cmd_args = shlex.split(command)
            except ValueError as e:
                if not ignore_failure:
                    raise ExecutionError(f"Invalid command syntax in {step_name}: {e}")
                logger.warning(f"Invalid command syntax in {step_name}, ignoring: {e}")
                continue
            
            step_start_time = self._get_current_time()
            result = self._run_secure_command(
                cmd_args,
                timeout=step_timeout,
                requires_root=action.requires_root,
                verbose=context.verbose
            )
            step_execution_time = self._get_current_time() - step_start_time
            
            # Track command execution if execution_id is provided
            if execution_id and self.execution_tracker:
                self.execution_tracker.add_command_result(
                    execution_id=execution_id,
                    command=command,
                    exit_code=result.get('exit_code', -1),
                    stdout=result.get('stdout', ''),
                    stderr=result.get('stderr', ''),
                    execution_time=step_execution_time
                )
            
            if not result['success'] and not ignore_failure:
                return ExecutionResult(
                    success=False,
                    status=ExecutionStatus.FAILURE,
                    message=f"Step failed: {step_name}",
                    provider_used="",  # Will be set by caller
                    action_name=context.action,
                    commands_executed=[],  # Will be set by caller
                    execution_time=0.0,  # Will be set by caller
                    exit_code=result['exit_code'],
                    stdout=result['stdout'],
                    stderr=result['stderr'],
                    error_details=result.get('error')
                )
            elif not result['success']:
                logger.warning(f"Step failed but ignoring: {step_name}")
        
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.SUCCESS,
            message=f"All steps completed successfully ({len(steps)} steps)",
            provider_used="",  # Will be set by caller
            action_name=context.action,
            commands_executed=[],  # Will be set by caller
            execution_time=0.0  # Will be set by caller
        )
    
    def _execute_script(self, script: str, action: Action, commands_executed: List[str],
                       context: ExecutionContext, execution_id: Optional[str] = None) -> ExecutionResult:
        """Execute a script.
        
        Args:
            script: Script content to execute
            action: Action configuration
            commands_executed: List to track executed commands
            context: Execution context
            
        Returns:
            ExecutionResult with execution details
        """
        commands_executed.append(f"<script: {len(script)} characters>")
        
        # For now, treat script as a shell command
        # In the future, this could be enhanced to support different script types
        script_start_time = self._get_current_time()
        result = self._run_secure_command(
            ['/bin/sh', '-c', script],
            timeout=context.timeout or action.timeout,
            requires_root=action.requires_root,
            verbose=context.verbose
        )
        script_execution_time = self._get_current_time() - script_start_time
        
        # Track script execution if execution_id is provided
        if execution_id and self.execution_tracker:
            self.execution_tracker.add_command_result(
                execution_id=execution_id,
                command=f"<script: {len(script)} characters>",
                exit_code=result.get('exit_code', -1),
                stdout=result.get('stdout', ''),
                stderr=result.get('stderr', ''),
                execution_time=script_execution_time
            )
        
        if result['success']:
            return ExecutionResult(
                success=True,
                status=ExecutionStatus.SUCCESS,
                message="Script executed successfully",
                provider_used="",  # Will be set by caller
                action_name=context.action,
                commands_executed=[],  # Will be set by caller
                execution_time=0.0,  # Will be set by caller
                exit_code=result['exit_code'],
                stdout=result['stdout'],
                stderr=result['stderr']
            )
        else:
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.FAILURE,
                message="Script execution failed",
                provider_used="",  # Will be set by caller
                action_name=context.action,
                commands_executed=[],  # Will be set by caller
                execution_time=0.0,  # Will be set by caller
                exit_code=result['exit_code'],
                stdout=result['stdout'],
                stderr=result['stderr'],
                error_details=result.get('error')
            )
    
    def _run_secure_command(self, cmd_args: List[str], timeout: int, requires_root: bool,
                           verbose: bool) -> Dict[str, Any]:
        """Run a command with enhanced security constraints.
        
        Args:
            cmd_args: Command arguments
            timeout: Timeout in seconds
            requires_root: Whether command requires root privileges
            verbose: Whether to log verbose output
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Enhanced security validation
            validation_result = self._validate_command_security(cmd_args, requires_root)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'exit_code': -1,
                    'stdout': '',
                    'stderr': ''
                }
            
            # Apply security sanitization
            sanitized_args = self._sanitize_command_args(cmd_args)
            
            # Handle root requirement with enhanced sudo handling
            final_args = self._handle_privilege_escalation(sanitized_args, requires_root)
            
            if verbose:
                # Log sanitized command for security
                safe_cmd = ' '.join(arg if not self._is_sensitive_arg(arg) else '[REDACTED]' for arg in final_args)
                logger.info(f"Executing: {safe_cmd}")
            
            # Execute with enhanced security constraints
            process = subprocess.Popen(
                final_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,  # Never use shell=True for security
                env=self._get_secure_environment(),
                preexec_fn=self._get_preexec_fn(),
                cwd=None,  # Don't inherit current working directory
                start_new_session=True if os.name != 'nt' else False
            )
            
            return self._handle_process_execution(process, timeout, verbose)
                
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {
                'success': False,
                'error': str(e),
                'exit_code': -1,
                'stdout': '',
                'stderr': ''
            }
    
    def _get_current_time(self) -> float:
        """Get current time in seconds since epoch.
        
        Returns:
            Current time as float
        """
        import time
        return time.time()
    
    def _validate_command_security(self, cmd_args: List[str], requires_root: bool) -> Dict[str, Any]:
        """Validate command arguments for security issues.
        
        Args:
            cmd_args: Command arguments to validate
            requires_root: Whether command requires root privileges
            
        Returns:
            Dictionary with validation result
        """
        if not cmd_args:
            return {'valid': False, 'error': 'Empty command'}
        
        if not all(isinstance(arg, str) for arg in cmd_args):
            return {'valid': False, 'error': 'Invalid command argument types'}
        
        # Check for dangerous characters and patterns
        dangerous_patterns = [
            '&&', '||', ';', '|', '>', '<', '`', '$(',
            '$(', '${', '\n', '\r', '\0'
        ]
        
        for arg in cmd_args:
            # Check for null bytes and control characters
            if '\0' in arg or any(ord(c) < 32 and c not in '\t\n\r' for c in arg):
                return {'valid': False, 'error': f'Invalid characters in argument: {arg[:50]}...'}
            
            # Check for command injection patterns
            for pattern in dangerous_patterns:
                if pattern in arg:
                    return {'valid': False, 'error': f'Potentially dangerous pattern "{pattern}" in argument'}
        
        # Validate executable path
        executable = cmd_args[0]
        if not self._is_safe_executable(executable):
            return {'valid': False, 'error': f'Unsafe executable: {executable}'}
        
        # Additional validation for root commands
        if requires_root:
            if not self._is_safe_root_command(cmd_args):
                return {'valid': False, 'error': 'Command not safe for root execution'}
        
        return {'valid': True}
    
    def _sanitize_command_args(self, cmd_args: List[str]) -> List[str]:
        """Sanitize command arguments.
        
        Args:
            cmd_args: Command arguments to sanitize
            
        Returns:
            Sanitized command arguments
        """
        sanitized = []
        for arg in cmd_args:
            # Remove any null bytes
            sanitized_arg = arg.replace('\0', '')
            
            # Limit argument length to prevent buffer overflow attacks
            if len(sanitized_arg) > 4096:
                logger.warning(f"Truncating overly long argument: {sanitized_arg[:50]}...")
                sanitized_arg = sanitized_arg[:4096]
            
            sanitized.append(sanitized_arg)
        
        return sanitized
    
    def _handle_privilege_escalation(self, cmd_args: List[str], requires_root: bool) -> List[str]:
        """Handle privilege escalation with enhanced sudo support.
        
        Args:
            cmd_args: Command arguments
            requires_root: Whether command requires root privileges
            
        Returns:
            Command arguments with privilege escalation if needed
        """
        if not requires_root:
            return cmd_args
        
        # Check if already running as root
        if os.name != 'nt' and os.geteuid() == 0:
            logger.debug("Already running as root")
            return cmd_args
        
        # On Windows, we can't easily escalate privileges
        if os.name == 'nt':
            logger.warning("Root privileges requested on Windows - command may fail")
            return cmd_args
        
        # Use sudo with security options
        sudo_args = [
            'sudo',
            '-n',  # Non-interactive mode
            '--'   # End of sudo options
        ]
        
        logger.debug("Command requires root, using sudo with security options")
        return sudo_args + cmd_args
    
    def _is_safe_executable(self, executable: str) -> bool:
        """Check if an executable is safe to run.
        
        Args:
            executable: Executable path or name
            
        Returns:
            True if executable is considered safe
        """
        # Block obviously dangerous executables
        dangerous_executables = {
            'rm', 'rmdir', 'del', 'format', 'fdisk',
            'dd', 'mkfs', 'parted', 'gparted',
            'shutdown', 'reboot', 'halt', 'poweroff',
            'su', 'sudo', 'passwd', 'chpasswd',
            'chmod', 'chown', 'chgrp',
            'iptables', 'ufw', 'firewall-cmd'
        }
        
        # Extract just the executable name
        exec_name = os.path.basename(executable)
        
        # Allow if it's a known package manager or system tool
        safe_executables = {
            'apt', 'apt-get', 'yum', 'dnf', 'zypper', 'pacman',
            'brew', 'pip', 'npm', 'cargo', 'gem', 'go',
            'docker', 'podman', 'systemctl', 'service',
            'which', 'whereis', 'ls', 'cat', 'echo',
            'grep', 'find', 'ps', 'top', 'htop'
        }
        
        if exec_name in safe_executables:
            return True
        
        if exec_name in dangerous_executables:
            logger.warning(f"Blocking potentially dangerous executable: {exec_name}")
            return False
        
        # Allow executables in standard system paths
        if '/' in executable:
            safe_paths = [
                '/usr/bin/', '/usr/local/bin/', '/bin/', '/sbin/',
                '/usr/sbin/', '/usr/local/sbin/', '/opt/homebrew/bin/'
            ]
            return any(executable.startswith(path) for path in safe_paths)
        
        # For relative executables, they should be in PATH
        return True
    
    def _is_safe_root_command(self, cmd_args: List[str]) -> bool:
        """Check if a command is safe to run with root privileges.
        
        Args:
            cmd_args: Command arguments
            
        Returns:
            True if command is safe for root execution
        """
        if not cmd_args:
            return False
        
        executable = os.path.basename(cmd_args[0])
        
        # Allow common package management operations with root
        safe_root_commands = {
            'apt', 'apt-get', 'yum', 'dnf', 'zypper', 'pacman',
            'systemctl', 'service', 'brew'
        }
        
        if executable in safe_root_commands:
            return True
        
        # Block dangerous root operations
        dangerous_root_patterns = [
            'rm -rf /', 'rm -rf /*', 'format', 'fdisk',
            'mkfs', 'dd if=', 'dd of='
        ]
        
        cmd_str = ' '.join(cmd_args)
        for pattern in dangerous_root_patterns:
            if pattern in cmd_str:
                logger.error(f"Blocking dangerous root command pattern: {pattern}")
                return False
        
        return True
    
    def _is_sensitive_arg(self, arg: str) -> bool:
        """Check if an argument contains sensitive information.
        
        Args:
            arg: Argument to check
            
        Returns:
            True if argument is sensitive
        """
        sensitive_patterns = [
            'password', 'passwd', 'secret', 'key', 'token',
            'auth', 'credential', 'private'
        ]
        
        arg_lower = arg.lower()
        return any(pattern in arg_lower for pattern in sensitive_patterns)
    
    def _get_preexec_fn(self):
        """Get preexec function for subprocess security.
        
        Returns:
            Preexec function or None
        """
        if os.name == 'nt':
            return None
        
        def preexec():
            try:
                # Create new process group (only if not already a session leader)
                try:
                    os.setsid()
                except OSError:
                    # Already a session leader or permission denied, skip
                    pass
                
                # Set resource limits if available
                try:
                    import resource
                    # Limit CPU time to prevent runaway processes (more generous)
                    resource.setrlimit(resource.RLIMIT_CPU, (1800, 1800))  # 30 minutes
                    # Limit memory usage (more generous)
                    resource.setrlimit(resource.RLIMIT_AS, (4*1024*1024*1024, 4*1024*1024*1024))  # 4GB
                except (ImportError, OSError, ValueError):
                    # Resource limits not available or invalid on this system
                    pass
            except Exception:
                # If anything fails in preexec, just continue without security restrictions
                # This prevents the subprocess from failing to start
                pass
        
        return preexec
    
    def _handle_process_execution(self, process: subprocess.Popen, timeout: int, 
                                verbose: bool) -> Dict[str, Any]:
        """Handle process execution with timeout and cleanup.
        
        Args:
            process: Process to handle
            timeout: Timeout in seconds
            verbose: Whether to log verbose output
            
        Returns:
            Dictionary with execution results
        """
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            exit_code = process.returncode
            
            if verbose and stdout:
                logger.info(f"STDOUT: {stdout}")
            if verbose and stderr:
                logger.info(f"STDERR: {stderr}")
            
            return {
                'success': exit_code == 0,
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': stderr
            }
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out after {timeout} seconds, terminating...")
            
            # Graceful termination first
            self._terminate_process_group(process, signal.SIGTERM)
            
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if still running
                logger.warning("Process didn't terminate gracefully, force killing...")
                self._terminate_process_group(process, signal.SIGKILL)
                stdout, stderr = process.communicate()
            
            return {
                'success': False,
                'error': f'Command timed out after {timeout} seconds',
                'exit_code': -1,
                'stdout': stdout or '',
                'stderr': stderr or ''
            }
    
    def _terminate_process_group(self, process: subprocess.Popen, sig: int):
        """Terminate process group safely.
        
        Args:
            process: Process to terminate
            sig: Signal to send
        """
        try:
            if os.name != 'nt':
                # Kill the entire process group
                os.killpg(os.getpgid(process.pid), sig)
            else:
                # On Windows, just terminate the process
                if sig == signal.SIGTERM:
                    process.terminate()
                else:
                    process.kill()
        except (OSError, ProcessLookupError):
            # Process already terminated
            pass
    
    def _get_secure_environment(self) -> Dict[str, str]:
        """Get a secure environment for command execution.
        
        Returns:
            Dictionary with secure environment variables
        """
        # Start with minimal environment to prevent environment variable injection
        secure_env = {
            'PATH': self._get_secure_path(),
            'LANG': 'C',
            'LC_ALL': 'C',  # Ensure consistent locale
        }
        
        # Add essential variables only if they exist and are safe
        safe_vars = ['HOME', 'USER', 'USERNAME', 'LOGNAME']
        for var in safe_vars:
            value = os.environ.get(var)
            if value and self._is_safe_env_value(value):
                secure_env[var] = value
        
        # Add system-specific variables
        system_info = get_system_info()
        if system_info['platform'] == 'darwin':
            tmpdir = os.environ.get('TMPDIR', '/tmp')
            if self._is_safe_env_value(tmpdir):
                secure_env['TMPDIR'] = tmpdir
        elif system_info['platform'] == 'windows':
            win_vars = {
                'SYSTEMROOT': os.environ.get('SYSTEMROOT', 'C:\\Windows'),
                'TEMP': os.environ.get('TEMP', tempfile.gettempdir()),
                'TMP': os.environ.get('TMP', tempfile.gettempdir()),
                'COMSPEC': os.environ.get('COMSPEC', 'C:\\Windows\\System32\\cmd.exe'),
            }
            for var, value in win_vars.items():
                if value and self._is_safe_env_value(value):
                    secure_env[var] = value
        else:  # Linux and other Unix-like systems
            secure_env['TMPDIR'] = '/tmp'
        
        # Remove any potentially dangerous environment variables
        dangerous_vars = [
            'LD_PRELOAD', 'LD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES',
            'DYLD_LIBRARY_PATH', 'PYTHONPATH', 'PERL5LIB', 'RUBYLIB'
        ]
        for var in dangerous_vars:
            secure_env.pop(var, None)
        
        return secure_env
    
    def _get_secure_path(self) -> str:
        """Get a secure PATH environment variable.
        
        Returns:
            Secure PATH string
        """
        # Define safe system paths
        safe_paths = []
        
        system_info = get_system_info()
        if system_info['platform'] == 'windows':
            safe_paths = [
                'C:\\Windows\\System32',
                'C:\\Windows',
                'C:\\Program Files\\Git\\bin',
                'C:\\ProgramData\\chocolatey\\bin',
            ]
        elif system_info['platform'] == 'darwin':
            safe_paths = [
                '/usr/bin',
                '/bin',
                '/usr/sbin',
                '/sbin',
                '/usr/local/bin',
                '/opt/homebrew/bin',
                '/opt/homebrew/sbin',
            ]
        else:  # Linux and other Unix-like
            safe_paths = [
                '/usr/bin',
                '/bin',
                '/usr/sbin',
                '/sbin',
                '/usr/local/bin',
                '/usr/local/sbin',
            ]
        
        # Filter existing paths
        existing_paths = [path for path in safe_paths if os.path.isdir(path)]
        
        # Add current PATH entries that are safe
        current_path = os.environ.get('PATH', '')
        if current_path:
            for path in current_path.split(os.pathsep):
                if path and self._is_safe_path_entry(path) and path not in existing_paths:
                    existing_paths.append(path)
        
        return os.pathsep.join(existing_paths)
    
    def _is_safe_env_value(self, value: str) -> bool:
        """Check if an environment variable value is safe.
        
        Args:
            value: Environment variable value
            
        Returns:
            True if value is safe
        """
        if not value:
            return False
        
        # Check for dangerous characters
        dangerous_chars = ['\0', '\n', '\r', ';', '&', '|', '`', '$']
        if any(char in value for char in dangerous_chars):
            return False
        
        # Limit length to prevent buffer overflow
        if len(value) > 4096:
            return False
        
        return True
    
    def _is_safe_path_entry(self, path: str) -> bool:
        """Check if a PATH entry is safe.
        
        Args:
            path: Path entry to check
            
        Returns:
            True if path is safe
        """
        if not path or not self._is_safe_env_value(path):
            return False
        
        # Block obviously dangerous paths
        dangerous_paths = [
            '/tmp', '/var/tmp', '/dev/shm',
            '.',  # Current directory
            '',   # Empty path
        ]
        
        if path in dangerous_paths:
            return False
        
        # Block paths that don't exist or aren't directories
        if not os.path.isdir(path):
            return False
        
        # Block world-writable directories (security risk)
        try:
            stat_info = os.stat(path)
            if stat_info.st_mode & 0o002:  # World writable
                logger.warning(f"Blocking world-writable path: {path}")
                return False
        except OSError:
            return False
        
        return True
    
    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition string.
        
        Args:
            condition: Condition to evaluate
            
        Returns:
            True if condition is met, False otherwise
        """
        # For now, implement basic condition evaluation
        # This could be enhanced to support more complex conditions
        
        # Simple boolean conditions
        if condition.lower() in ('true', '1', 'yes'):
            return True
        elif condition.lower() in ('false', '0', 'no'):
            return False
        
        # File existence checks
        if condition.startswith('file_exists:'):
            file_path = condition[12:].strip()
            return os.path.exists(file_path)
        
        # Command success checks
        if condition.startswith('command_success:'):
            command = condition[16:].strip()
            try:
                result = subprocess.run(
                    shlex.split(command),
                    capture_output=True,
                    timeout=10,
                    shell=False
                )
                return result.returncode == 0
            except Exception:
                return False
        
        # Default to False for unknown conditions
        logger.warning(f"Unknown condition type: {condition}")
        return False
    
    def _get_current_time(self) -> float:
        """Get current time in seconds.
        
        Returns:
            Current time as float
        """
        import time
        return time.time()
    
    def get_available_providers(self) -> List[BaseProvider]:
        """Get list of available providers.
        
        Returns:
            List of available providers
        """
        return self.available_providers.copy()
    
    def get_provider_by_name(self, name: str) -> Optional[BaseProvider]:
        """Get provider by name.
        
        Args:
            name: Provider name
            
        Returns:
            Provider if found, None otherwise
        """
        for provider in self.providers:
            if provider.name == name:
                return provider
        return None
    
    def get_supported_actions(self) -> Dict[str, List[str]]:
        """Get all supported actions by provider.
        
        Returns:
            Dictionary mapping provider names to their supported actions
        """
        result = {}
        for provider in self.available_providers:
            result[provider.name] = provider.get_supported_actions()
        return result