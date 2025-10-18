"""Execution result tracking and reporting for SAI CLI tool."""

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.config import SaiConfig
from .logging import get_logger


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    DRY_RUN = "dry_run"


@dataclass
class CommandResult:
    """Result of a single command execution."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    timestamp: str
    success: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ExecutionMetrics:
    """Metrics for execution tracking."""

    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    commands_executed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    def update_from_result(self, result: "ExecutionResult") -> None:
        """Update metrics from an execution result."""
        self.total_executions += 1
        if result.success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1

        self.total_execution_time += result.execution_time
        self.average_execution_time = self.total_execution_time / self.total_executions
        self.commands_executed += len(result.commands)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ExecutionResult:
    """Comprehensive execution result with tracking information."""

    # Basic execution info
    execution_id: str
    action: str
    software: str
    provider: str
    status: ExecutionStatus
    success: bool

    # Timing information
    start_time: str
    end_time: Optional[str]
    execution_time: float

    # Execution details
    commands: List[CommandResult]
    message: str
    error_details: Optional[str] = None

    # Context information
    dry_run: bool = False
    verbose: bool = False
    timeout: Optional[int] = None
    user: Optional[str] = None
    hostname: Optional[str] = None
    working_directory: Optional[str] = None

    # Additional metadata
    saidata_version: Optional[str] = None
    provider_version: Optional[str] = None
    cli_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result_dict = asdict(self)
        # Convert CommandResult objects to dictionaries
        result_dict["commands"] = [
            cmd.to_dict() if hasattr(cmd, "to_dict") else cmd for cmd in self.commands
        ]
        return result_dict

    def get_summary(self) -> str:
        """Get a human-readable summary of the execution."""
        status_emoji = "✓" if self.success else "✗"
        duration = f"{self.execution_time:.2f}s"

        summary = f"{status_emoji} {self.action} {self.software} using {self.provider} ({duration})"

        if self.commands:
            summary += f" - {len(self.commands)} command(s) executed"

        if self.dry_run:
            summary += " [DRY RUN]"

        return summary

    def get_detailed_report(self) -> str:
        """Get a detailed report of the execution."""
        lines = [
            f"Execution Report",
            f"================",
            f"ID: {self.execution_id}",
            f"Action: {self.action}",
            f"Software: {self.software}",
            f"Provider: {self.provider}",
            f"Status: {self.status.value}",
            f"Success: {self.success}",
            f"Start Time: {self.start_time}",
            f"End Time: {self.end_time or 'N/A'}",
            f"Duration: {self.execution_time:.2f}s",
            f"Dry Run: {self.dry_run}",
            "",
        ]

        if self.message:
            lines.extend([f"Message:", f"  {self.message}", ""])

        if self.error_details:
            lines.extend([f"Error Details:", f"  {self.error_details}", ""])

        if self.commands:
            lines.extend([f"Commands Executed ({len(self.commands)}):", ""])

            for i, cmd in enumerate(self.commands, 1):
                status = "✓" if cmd.success else "✗"
                lines.extend(
                    [
                        f"  {i}. {status} {cmd.command}",
                        f"     Exit Code: {cmd.exit_code}",
                        f"     Duration: {cmd.execution_time:.3f}s",
                        f"     Timestamp: {cmd.timestamp}",
                    ]
                )

                if cmd.stdout and len(cmd.stdout.strip()) > 0:
                    stdout_preview = cmd.stdout.strip()[:200]
                    if len(cmd.stdout.strip()) > 200:
                        stdout_preview += "..."
                    lines.append(f"     Output: {stdout_preview}")

                if cmd.stderr and len(cmd.stderr.strip()) > 0:
                    stderr_preview = cmd.stderr.strip()[:200]
                    if len(cmd.stderr.strip()) > 200:
                        stderr_preview += "..."
                    lines.append(f"     Error: {stderr_preview}")

                lines.append("")

        return "\n".join(lines)


class ExecutionTracker:
    """Tracks and manages execution results with persistence and reporting."""

    def __init__(self, config: Optional[SaiConfig] = None):
        """Initialize the execution tracker.

        Args:
            config: SAI configuration object
        """
        self.config = config or SaiConfig()
        self.logger = get_logger(__name__, self.config)

        # Setup tracking directory
        self.tracking_dir = self.config.cache_directory / "executions"
        self.tracking_dir.mkdir(parents=True, exist_ok=True)

        # Metrics tracking
        self.metrics = ExecutionMetrics()
        self._load_metrics()

        # Current executions
        self._current_executions: Dict[str, ExecutionResult] = {}

    def start_execution(
        self,
        action: str,
        software: str,
        provider: str,
        dry_run: bool = False,
        verbose: bool = False,
        timeout: Optional[int] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start tracking a new execution.

        Args:
            action: Action being executed
            software: Software being acted upon
            provider: Provider being used
            dry_run: Whether this is a dry run
            verbose: Whether verbose mode is enabled
            timeout: Execution timeout in seconds
            additional_context: Additional context information

        Returns:
            Unique execution ID
        """
        import getpass
        import socket
        import uuid

        execution_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc).isoformat()

        # Gather context information
        context = additional_context or {}

        try:
            user = getpass.getuser()
        except Exception:
            user = None

        try:
            hostname = socket.gethostname()
        except Exception:
            hostname = None

        try:
            working_directory = str(Path.cwd())
        except Exception:
            working_directory = None

        # Create execution result
        execution_result = ExecutionResult(
            execution_id=execution_id,
            action=action,
            software=software,
            provider=provider,
            status=ExecutionStatus.RUNNING,
            success=False,
            start_time=start_time,
            end_time=None,
            execution_time=0.0,
            commands=[],
            message="Execution started",
            dry_run=dry_run,
            verbose=verbose,
            timeout=timeout,
            user=user,
            hostname=hostname,
            working_directory=working_directory,
            **context,
        )

        # Store current execution
        self._current_executions[execution_id] = execution_result

        # Log execution start
        self.logger.log_execution_start(
            action,
            software,
            provider,
            {"execution_id": execution_id, "dry_run": dry_run, "timeout": timeout},
        )

        return execution_id

    def add_command_result(
        self,
        execution_id: str,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        execution_time: float,
    ) -> None:
        """Add a command result to an execution.

        Args:
            execution_id: Execution ID
            command: Command that was executed
            exit_code: Exit code of the command
            stdout: Standard output
            stderr: Standard error
            execution_time: Time taken to execute the command
        """
        if execution_id not in self._current_executions:
            self.logger.warning(f"Unknown execution ID: {execution_id}")
            return

        command_result = CommandResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            execution_time=execution_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
            success=exit_code == 0,
        )

        self._current_executions[execution_id].commands.append(command_result)

        # Log command execution
        self.logger.log_command_execution(command, exit_code, execution_time, stdout, stderr)

    def finish_execution(
        self, execution_id: str, success: bool, message: str, error_details: Optional[str] = None
    ) -> ExecutionResult:
        """Finish tracking an execution.

        Args:
            execution_id: Execution ID
            success: Whether execution was successful
            message: Final execution message
            error_details: Error details if execution failed

        Returns:
            Final execution result
        """
        if execution_id not in self._current_executions:
            raise ValueError(f"Unknown execution ID: {execution_id}")

        execution_result = self._current_executions[execution_id]

        # Update execution result
        execution_result.end_time = datetime.now(timezone.utc).isoformat()
        execution_result.success = success
        execution_result.message = message
        execution_result.error_details = error_details

        # Calculate total execution time
        start_dt = datetime.fromisoformat(execution_result.start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(execution_result.end_time.replace("Z", "+00:00"))
        execution_result.execution_time = (end_dt - start_dt).total_seconds()

        # Set final status
        if execution_result.dry_run:
            execution_result.status = ExecutionStatus.DRY_RUN
        elif success:
            execution_result.status = ExecutionStatus.SUCCESS
        else:
            execution_result.status = ExecutionStatus.FAILURE

        # Log execution end
        self.logger.log_execution_end(
            execution_result.action,
            execution_result.software,
            execution_result.provider,
            success,
            execution_result.execution_time,
            {
                "execution_id": execution_id,
                "commands_executed": len(execution_result.commands),
                "dry_run": execution_result.dry_run,
            },
        )

        # Update metrics
        self.metrics.update_from_result(execution_result)

        # Persist execution result
        self._save_execution_result(execution_result)

        # Save updated metrics
        self._save_metrics()

        # Remove from current executions
        del self._current_executions[execution_id]

        return execution_result

    def cancel_execution(
        self, execution_id: str, reason: str = "Cancelled by user"
    ) -> ExecutionResult:
        """Cancel a running execution.

        Args:
            execution_id: Execution ID
            reason: Cancellation reason

        Returns:
            Final execution result
        """
        if execution_id not in self._current_executions:
            raise ValueError(f"Unknown execution ID: {execution_id}")

        execution_result = self._current_executions[execution_id]
        execution_result.status = ExecutionStatus.CANCELLED
        execution_result.success = False
        execution_result.message = reason
        execution_result.end_time = datetime.now(timezone.utc).isoformat()

        # Calculate execution time up to cancellation
        start_dt = datetime.fromisoformat(execution_result.start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(execution_result.end_time.replace("Z", "+00:00"))
        execution_result.execution_time = (end_dt - start_dt).total_seconds()

        # Log cancellation
        self.logger.warning(f"Execution cancelled: {execution_id} - {reason}")

        # Persist execution result
        self._save_execution_result(execution_result)

        # Remove from current executions
        del self._current_executions[execution_id]

        return execution_result

    def get_execution_history(
        self,
        limit: Optional[int] = None,
        action_filter: Optional[str] = None,
        software_filter: Optional[str] = None,
        provider_filter: Optional[str] = None,
        success_only: bool = False,
    ) -> List[ExecutionResult]:
        """Get execution history with optional filtering.

        Args:
            limit: Maximum number of results to return
            action_filter: Filter by action name
            software_filter: Filter by software name
            provider_filter: Filter by provider name
            success_only: Only return successful executions

        Returns:
            List of execution results
        """
        results = []

        # Get all execution files
        execution_files = list(self.tracking_dir.glob("execution_*.json"))
        execution_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        for file_path in execution_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Reconstruct ExecutionResult
                execution_result = self._dict_to_execution_result(data)

                # Apply filters
                if action_filter and execution_result.action != action_filter:
                    continue

                if software_filter and execution_result.software != software_filter:
                    continue

                if provider_filter and execution_result.provider != provider_filter:
                    continue

                if success_only and not execution_result.success:
                    continue

                results.append(execution_result)

                # Apply limit
                if limit and len(results) >= limit:
                    break

            except Exception as e:
                self.logger.warning(f"Failed to load execution result from {file_path}: {e}")
                continue

        return results

    def get_metrics(self) -> ExecutionMetrics:
        """Get current execution metrics.

        Returns:
            Current execution metrics
        """
        return self.metrics

    def clear_history(self, older_than_days: Optional[int] = None) -> int:
        """Clear execution history.

        Args:
            older_than_days: Only clear executions older than this many days

        Returns:
            Number of executions cleared
        """
        cleared_count = 0
        cutoff_time = None

        if older_than_days:
            cutoff_time = time.time() - (older_than_days * 24 * 60 * 60)

        execution_files = list(self.tracking_dir.glob("execution_*.json"))

        for file_path in execution_files:
            try:
                if cutoff_time and file_path.stat().st_mtime > cutoff_time:
                    continue

                file_path.unlink()
                cleared_count += 1

            except Exception as e:
                self.logger.warning(f"Failed to delete execution file {file_path}: {e}")

        self.logger.info(f"Cleared {cleared_count} execution records")
        return cleared_count

    def _save_execution_result(self, execution_result: ExecutionResult) -> None:
        """Save execution result to disk.

        Args:
            execution_result: Execution result to save
        """
        try:
            file_path = self.tracking_dir / f"execution_{execution_result.execution_id}.json"

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(execution_result.to_dict(), f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to save execution result: {e}")

    def _load_metrics(self) -> None:
        """Load metrics from disk."""
        metrics_file = self.tracking_dir / "metrics.json"

        try:
            if metrics_file.exists():
                with open(metrics_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.metrics = ExecutionMetrics(**data)
        except Exception as e:
            self.logger.warning(f"Failed to load metrics: {e}")
            self.metrics = ExecutionMetrics()

    def _save_metrics(self) -> None:
        """Save metrics to disk."""
        metrics_file = self.tracking_dir / "metrics.json"

        try:
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(self.metrics.to_dict(), f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")

    def _dict_to_execution_result(self, data: Dict[str, Any]) -> ExecutionResult:
        """Convert dictionary to ExecutionResult.

        Args:
            data: Dictionary data

        Returns:
            ExecutionResult object
        """
        # Convert command dictionaries back to CommandResult objects
        commands = []
        for cmd_data in data.get("commands", []):
            if isinstance(cmd_data, dict):
                commands.append(CommandResult(**cmd_data))
            else:
                commands.append(cmd_data)

        data["commands"] = commands
        data["status"] = ExecutionStatus(data["status"])

        return ExecutionResult(**data)


# Global execution tracker instance
_execution_tracker: Optional[ExecutionTracker] = None


def get_execution_tracker(config: Optional[SaiConfig] = None) -> ExecutionTracker:
    """Get the global execution tracker instance.

    Args:
        config: SAI configuration object

    Returns:
        ExecutionTracker instance
    """
    global _execution_tracker

    if _execution_tracker is None:
        _execution_tracker = ExecutionTracker(config)

    return _execution_tracker
