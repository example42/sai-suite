"""Action executor for running multiple SAI actions."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from ..core.execution_engine import ExecutionContext, ExecutionEngine, ExecutionResult
from ..core.saidata_loader import SaidataLoader, SaidataNotFoundError
from ..models.actions import ActionConfig, ActionFile, ActionItem
from ..models.saidata import Metadata, SaiData
from ..utils.logging import get_logger


@dataclass
class ActionExecutionResult:
    """Result of executing a single action."""

    action_type: str
    software: str
    success: bool
    result: Optional[ExecutionResult] = None
    error: Optional[str] = None


@dataclass
class ActionFileExecutionResult:
    """Result of executing an entire action file."""

    success: bool
    total_actions: int
    successful_actions: int
    failed_actions: int
    results: List[ActionExecutionResult]
    execution_time: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_actions == 0:
            return 100.0
        return (self.successful_actions / self.total_actions) * 100.0


class ActionExecutor:
    """Executes actions from action files."""

    def __init__(self, execution_engine: ExecutionEngine, saidata_loader: SaidataLoader):
        """Initialize the action executor.

        Args:
            execution_engine: Engine for executing individual actions
            saidata_loader: Loader for saidata files
        """
        self.execution_engine = execution_engine
        self.saidata_loader = saidata_loader
        self.logger = get_logger(__name__)

    def execute_action_file(
        self, action_file: ActionFile, global_config: Optional[Dict[str, Any]] = None
    ) -> ActionFileExecutionResult:
        """Execute all actions in an action file.

        Args:
            action_file: The action file to execute
            global_config: Global configuration overrides

        Returns:
            ActionFileExecutionResult: Results of execution
        """
        import time

        start_time = time.time()

        # Get effective configuration
        config = action_file.get_effective_config(global_config)

        # Get all actions to execute
        all_actions = action_file.actions.get_all_actions()

        if not all_actions:
            return ActionFileExecutionResult(
                success=True,
                total_actions=0,
                successful_actions=0,
                failed_actions=0,
                results=[],
                execution_time=time.time() - start_time,
            )

        self.logger.info(f"Executing {len(all_actions)} actions")

        # Execute actions
        if config.parallel:
            results = self._execute_actions_parallel(all_actions, config)
        else:
            results = self._execute_actions_sequential(all_actions, config)

        # Calculate summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        overall_success = failed == 0 or (config.continue_on_error and successful > 0)

        execution_time = time.time() - start_time

        return ActionFileExecutionResult(
            success=overall_success,
            total_actions=len(results),
            successful_actions=successful,
            failed_actions=failed,
            results=results,
            execution_time=execution_time,
        )

    def _execute_actions_sequential(
        self, actions: List[tuple[str, Union[str, ActionItem]]], config: ActionConfig
    ) -> List[ActionExecutionResult]:
        """Execute actions sequentially."""
        results = []

        for action_type, item in actions:
            result = self._execute_single_action(action_type, item, config)
            results.append(result)

            # Stop on first failure if not continuing on error
            if not result.success and not config.continue_on_error:
                self.logger.error(f"Action failed, stopping execution: {result.error}")
                break

        return results

    def _execute_actions_parallel(
        self, actions: List[tuple[str, Union[str, ActionItem]]], config: ActionConfig
    ) -> List[ActionExecutionResult]:
        """Execute actions in parallel."""
        results = []

        # Group actions by type to maintain some ordering
        action_groups = {}
        for action_type, item in actions:
            if action_type not in action_groups:
                action_groups[action_type] = []
            action_groups[action_type].append(item)

        # Execute each group in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []

            for action_type, items in action_groups.items():
                for item in items:
                    future = executor.submit(self._execute_single_action, action_type, item, config)
                    futures.append(future)

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)

                    # Log failures immediately
                    if not result.success:
                        self.logger.error(f"Action failed: {result.error}")

                        # If not continuing on error, cancel remaining futures
                        if not config.continue_on_error:
                            for f in futures:
                                f.cancel()
                            break

                except Exception as e:
                    self.logger.error(f"Unexpected error in parallel execution: {e}")

        return results

    def _execute_single_action(
        self, action_type: str, item: Union[str, ActionItem, Dict[str, Any]], config: ActionConfig
    ) -> ActionExecutionResult:
        """Execute a single action.

        Args:
            action_type: Type of action (install, uninstall, etc.)
            item: Action item (string, dict, or ActionItem object)
            config: Action configuration

        Returns:
            ActionExecutionResult: Result of the action
        """
        # Normalize item to ActionItem
        if isinstance(item, str):
            action_item = ActionItem(name=item)
        elif isinstance(item, dict):
            action_item = ActionItem(**item)
        else:
            action_item = item

        software = action_item.name

        try:
            # Load saidata for the software
            saidata = self._load_saidata_for_software(software)

            # Get extra parameters from the action item
            extra_params = (
                action_item.get_extra_params() if hasattr(action_item, "get_extra_params") else {}
            )

            # Create execution context with extra parameters
            execution_context = ExecutionContext(
                action=action_type,
                software=software,
                saidata=saidata,
                provider=action_item.provider or config.provider,
                dry_run=config.dry_run,
                verbose=config.verbose,
                quiet=config.quiet,
                timeout=action_item.timeout or config.timeout,
                additional_context=extra_params if extra_params else None,
            )

            # Execute the action
            result = self.execution_engine.execute_action(execution_context)

            return ActionExecutionResult(
                action_type=action_type, software=software, success=result.success, result=result
            )

        except Exception as e:
            error_msg = f"Failed to execute {action_type} for {software}: {e}"
            self.logger.error(error_msg)

            return ActionExecutionResult(
                action_type=action_type, software=software, success=False, error=error_msg
            )

    def _load_saidata_for_software(self, software: str) -> SaiData:
        """Load saidata for software, creating minimal saidata if not found.

        Args:
            software: Software name

        Returns:
            SaiData: Loaded or minimal saidata
        """
        try:
            return self.saidata_loader.load_saidata(software)
        except SaidataNotFoundError:
            # Create minimal saidata
            self.logger.debug(f"No saidata found for '{software}', using minimal saidata")
            return SaiData(version="0.2", metadata=Metadata(name=software))
