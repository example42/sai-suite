"""Batch generation engine for processing multiple software packages."""

import asyncio
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..models.generation import (
    BatchGenerationRequest,
    BatchGenerationResult,
    GenerationRequest,
    GenerationResult,
    LLMProvider,
)
from .generation_engine import GenerationEngineError

logger = logging.getLogger(__name__)


class BatchProgressReporter:
    """Progress reporter for batch operations."""

    def __init__(self, total_items: int, verbose: bool = False):
        self.total_items = total_items
        self.completed = 0
        self.successful = 0
        self.failed = 0
        self.verbose = verbose
        self.start_time = time.time()
        self.last_report_time = time.time()

    def update(self, success: bool, software_name: str = "") -> None:
        """Update progress counters."""
        self.completed += 1
        if success:
            self.successful += 1
        else:
            self.failed += 1

        # Report progress every 5 seconds or on completion
        current_time = time.time()
        if (current_time - self.last_report_time > 5.0) or (self.completed == self.total_items):
            self._report_progress(software_name)
            self.last_report_time = current_time

    def _report_progress(self, current_software: str = "") -> None:
        """Report current progress."""
        elapsed = time.time() - self.start_time
        percentage = (self.completed / self.total_items) * 100

        if self.verbose:
            logger.info(
                f"Progress: {self.completed}/{self.total_items} ({percentage:.1f}%) - "
                f"Success: {self.successful}, Failed: {self.failed} - "
                f"Elapsed: {elapsed:.1f}s"
            )
            if current_software:
                logger.info(f"Processing: {current_software}")
        else:
            print(
                f"\rProgress: {self.completed}/{self.total_items} ({percentage:.1f}%)",
                end="",
                flush=True,
            )

    def get_summary(self) -> Dict[str, Any]:
        """Get final summary statistics."""
        elapsed = time.time() - self.start_time
        return {
            "total": self.total_items,
            "completed": self.completed,
            "successful": self.successful,
            "failed": self.failed,
            "elapsed_time": elapsed,
            "success_rate": (self.successful / self.completed) * 100 if self.completed > 0 else 0,
            "average_time_per_item": elapsed / self.completed if self.completed > 0 else 0,
        }


class SoftwareListParser:
    """Parser for software list files with category filtering."""

    @staticmethod
    def parse_file(file_path: Path, category_filter: Optional[str] = None) -> List[str]:
        """Parse software list file and optionally filter by category.

        Args:
            file_path: Path to software list file
            category_filter: Optional category filter (regex pattern)

        Returns:
            List of software names
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Software list file not found: {file_path}")

        software_list = []
        current_category = None
        include_section = True

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    # Check for category headers in comments
                    if line.startswith("##"):
                        current_category = line[2:].strip()
                        # Apply category filter if specified
                        if category_filter:
                            include_section = bool(
                                re.search(category_filter, current_category, re.IGNORECASE)
                            )
                        else:
                            include_section = True
                    continue

                # Add software name if in included section
                if include_section:
                    # Remove inline comments
                    software_name = line.split("#")[0].strip()
                    if software_name:
                        software_list.append(software_name)

        return software_list

    @staticmethod
    def parse_string(content: str, category_filter: Optional[str] = None) -> List[str]:
        """Parse software list from string content.

        Args:
            content: Software list content
            category_filter: Optional category filter (regex pattern)

        Returns:
            List of software names
        """
        software_list = []
        current_category = None
        include_section = True

        for line in content.split("\n"):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                # Check for category headers in comments
                if line.startswith("##"):
                    current_category = line[2:].strip()
                    # Apply category filter if specified
                    if category_filter:
                        include_section = bool(
                            re.search(category_filter, current_category, re.IGNORECASE)
                        )
                    else:
                        include_section = True
                continue

            # Add software name if in included section
            if include_section:
                # Remove inline comments
                software_name = line.split("#")[0].strip()
                if software_name:
                    software_list.append(software_name)

        return software_list

    @staticmethod
    def validate_software_names(software_list: List[str]) -> List[str]:
        """Validate and sanitize software names.

        Args:
            software_list: List of software names to validate

        Returns:
            List of valid software names
        """
        valid_names = []
        name_pattern = re.compile(r"^[a-zA-Z0-9._-]+$")

        for name in software_list:
            if name_pattern.match(name):
                valid_names.append(name)
            else:
                logger.warning(f"Skipping invalid software name: {name}")

        return valid_names


class BatchGenerationEngine:
    """Engine for batch processing of saidata generation."""

    def __init__(self, generation_engine_or_config, generation_engine=None):
        # Handle backward compatibility - if first arg is dict, it's config
        if isinstance(generation_engine_or_config, dict):
            config = generation_engine_or_config
            self.generation_engine = generation_engine
            batch_config = config.get("batch", {})
            self.max_concurrent = batch_config.get("max_concurrent", 3)
            self.retry_attempts = batch_config.get("retry_attempts", 2)
            self.timeout = batch_config.get("timeout", 300)
            max_workers = self.max_concurrent
        else:
            # New style - first arg is generation engine
            self.generation_engine = generation_engine_or_config
            self.max_concurrent = 3
            self.retry_attempts = 2
            self.timeout = 300
            max_workers = 3

        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def generate_batch(
        self,
        request: BatchGenerationRequest,
        progress_callback: Optional[Callable[[str, bool], None]] = None,
    ) -> BatchGenerationResult:
        """Generate saidata for multiple software packages.

        Args:
            request: Batch generation request
            progress_callback: Optional callback for progress updates

        Returns:
            BatchGenerationResult with aggregated results
        """
        start_time = time.time()

        # Validate software list
        if not request.software_list:
            raise GenerationEngineError("Software list cannot be empty")

        # Sanitize software names
        valid_software = SoftwareListParser.validate_software_names(request.software_list)
        if not valid_software:
            raise GenerationEngineError("No valid software names found in list")

        # Filter out existing files if force is not set
        software_to_process = valid_software
        skipped_count = 0
        if not request.force and request.output_directory:
            software_to_process = []
            for software_name in valid_software:
                output_path = self._get_output_path(software_name, request.output_directory)
                if output_path and output_path.exists():
                    logger.info(f"Skipping existing file: {output_path}")
                    skipped_count += 1
                else:
                    software_to_process.append(software_name)
            
            if skipped_count > 0:
                logger.info(f"Skipped {skipped_count} existing files (use --force to regenerate)")
        
        if not software_to_process:
            logger.info("No software packages to process (all files exist)")
            return BatchGenerationResult(
                total_requested=len(valid_software),
                successful=0,
                failed=0,
                results=[],
                failed_software=[],
                total_time=time.time() - start_time,
                average_time_per_item=0.0,
            )

        logger.info(f"Starting batch generation for {len(software_to_process)} software packages")

        # Initialize progress reporter
        progress_reporter = BatchProgressReporter(
            total_items=len(software_to_process), verbose=logger.isEnabledFor(logging.DEBUG)
        )

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(request.max_concurrent)

        # Track results
        results: List[GenerationResult] = []
        failed_software: List[str] = []

        async def process_software(software_name: str) -> GenerationResult:
            """Process a single software package."""
            async with semaphore:
                try:
                    # Create individual generation request
                    gen_request = GenerationRequest(
                        software_name=software_name,
                        target_providers=request.target_providers,
                        llm_provider=request.llm_provider,
                        use_rag=request.use_rag,
                        output_path=self._get_output_path(software_name, request.output_directory),
                    )

                    # Generate saidata
                    result = await self.generation_engine.generate_saidata(gen_request)

                    # Save to file if successful and output directory specified
                    if result.success and result.saidata and request.output_directory:
                        output_path = self._get_output_path(software_name, request.output_directory)
                        # Get model name from the result
                        model_name = self.generation_engine._get_model_name(result.llm_provider_used)
                        await self.generation_engine.save_saidata(
                            result.saidata, output_path, model_name=model_name
                        )

                    # Update progress
                    progress_reporter.update(result.success, software_name)
                    if progress_callback:
                        progress_callback(software_name, result.success)

                    return result

                except Exception as e:
                    logger.error(f"Failed to process {software_name}: {e}")

                    # Create error result
                    error_result = GenerationResult(
                        success=False,
                        saidata=None,
                        validation_errors=[],
                        warnings=[f"Generation failed: {str(e)}"],
                        generation_time=0.0,
                        llm_provider_used=request.llm_provider
                        if isinstance(request.llm_provider, str)
                        else request.llm_provider.value,
                        repository_sources_used=[],
                    )

                    progress_reporter.update(False, software_name)
                    if progress_callback:
                        progress_callback(software_name, False)

                    return error_result

        # Process all software packages concurrently
        tasks = [process_software(software) for software in software_to_process]

        if request.continue_on_error:
            # Use gather with return_exceptions=True to continue on errors
            task_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(task_results):
                if isinstance(result, Exception):
                    logger.error(f"Task failed for {software_to_process[i]}: {result}")
                    failed_software.append(software_to_process[i])
                    # Create error result
                    error_result = GenerationResult(
                        success=False,
                        saidata=None,
                        validation_errors=[],
                        warnings=[f"Task failed: {str(result)}"],
                        generation_time=0.0,
                        llm_provider_used=request.llm_provider
                        if isinstance(request.llm_provider, str)
                        else request.llm_provider.value,
                        repository_sources_used=[],
                    )
                    results.append(error_result)
                else:
                    results.append(result)
                    if not result.success:
                        failed_software.append(software_to_process[i])
        else:
            # Stop on first error
            try:
                results = await asyncio.gather(*tasks)
                for i, result in enumerate(results):
                    if not result.success:
                        failed_software.append(software_to_process[i])
                        # Stop on first failure when continue_on_error=False
                        logger.error(
                            f"Batch processing stopped due to failure: {software_to_process[i]}"
                        )
                        raise GenerationEngineError(
                            f"Batch processing failed: {software_to_process[i]} generation failed"
                        )
            except GenerationEngineError:
                # Re-raise our own exceptions
                raise
            except Exception as e:
                logger.error(f"Batch processing stopped due to error: {e}")
                raise GenerationEngineError(f"Batch processing failed: {e}")

        # Calculate final statistics
        total_time = time.time() - start_time
        successful_count = sum(1 for r in results if r.success)
        failed_count = len(results) - successful_count

        # Print final progress if not verbose
        if not logger.isEnabledFor(logging.DEBUG):
            print()  # New line after progress indicator

        logger.info(
            f"Batch generation completed: {successful_count} successful, {failed_count} failed"
        )

        return BatchGenerationResult(
            total_requested=len(valid_software),
            successful=successful_count,
            failed=failed_count,
            results=results,
            failed_software=failed_software,
            total_time=total_time,
            average_time_per_item=total_time / len(results) if results else 0.0,
        )

    def _get_output_path(
        self, software_name: str, output_directory: Optional[Path]
    ) -> Optional[Path]:
        """Get output path for a software package using hierarchical structure.

        Creates paths following the structure:
        {first_two_letters}/{software_name}/default.yaml

        Args:
            software_name: Name of the software
            output_directory: Base output directory

        Returns:
            Full hierarchical output path or None if no output directory specified
        """
        if not output_directory:
            return None

        from ..utils.path_utils import get_hierarchical_output_path

        return get_hierarchical_output_path(software_name, output_directory)

    async def generate_from_file(
        self,
        file_path: Path,
        target_providers: List[str],
        llm_provider: LLMProvider = LLMProvider.OPENAI,
        output_directory: Optional[Path] = None,
        max_concurrent: int = 3,
        continue_on_error: bool = True,
        category_filter: Optional[str] = None,
        use_rag: bool = True,
        force: bool = False,
        progress_callback: Optional[Callable[[str, bool], None]] = None,
    ) -> BatchGenerationResult:
        """Generate saidata from a software list file.

        Args:
            file_path: Path to software list file
            target_providers: List of target providers
            llm_provider: LLM provider to use
            output_directory: Directory to save generated files
            max_concurrent: Maximum concurrent generations
            continue_on_error: Whether to continue on individual failures
            category_filter: Optional category filter regex
            use_rag: Whether to use RAG for enhanced generation
            force: Whether to overwrite existing files
            progress_callback: Optional progress callback

        Returns:
            BatchGenerationResult with results
        """
        # Parse software list from file
        software_list = SoftwareListParser.parse_file(file_path, category_filter)

        if not software_list:
            raise GenerationEngineError(f"No software found in file: {file_path}")

        logger.info(f"Parsed {len(software_list)} software packages from {file_path}")
        if category_filter:
            logger.info(f"Applied category filter: {category_filter}")

        # Create batch request
        request = BatchGenerationRequest(
            software_list=software_list,
            target_providers=target_providers,
            llm_provider=llm_provider,
            output_directory=output_directory,
            max_concurrent=max_concurrent,
            continue_on_error=continue_on_error,
            category_filter=category_filter,
            use_rag=use_rag,
            force=force,
        )

        return await self.generate_batch(request, progress_callback)

    async def generate_from_list(
        self,
        software_names: List[str],
        target_providers: List[str],
        llm_provider: LLMProvider = LLMProvider.OPENAI,
        output_directory: Optional[Path] = None,
        max_concurrent: int = 3,
        continue_on_error: bool = True,
        use_rag: bool = True,
        force: bool = False,
        progress_callback: Optional[Callable[[str, bool], None]] = None,
    ) -> BatchGenerationResult:
        """Generate saidata from a list of software names.

        Args:
            software_names: List of software names
            target_providers: List of target providers
            llm_provider: LLM provider to use
            output_directory: Directory to save generated files
            max_concurrent: Maximum concurrent generations
            continue_on_error: Whether to continue on individual failures
            use_rag: Whether to use RAG for enhanced generation
            force: Whether to overwrite existing files
            progress_callback: Optional progress callback

        Returns:
            BatchGenerationResult with results
        """
        if not software_names:
            raise GenerationEngineError("Software names list cannot be empty")

        # Create batch request
        request = BatchGenerationRequest(
            software_list=software_names,
            target_providers=target_providers,
            llm_provider=llm_provider,
            output_directory=output_directory,
            max_concurrent=max_concurrent,
            continue_on_error=continue_on_error,
            use_rag=use_rag,
            force=force,
        )

        return await self.generate_batch(request, progress_callback)

    def get_statistics_summary(self, result: BatchGenerationResult) -> str:
        """Get formatted statistics summary.

        Args:
            result: Batch generation result

        Returns:
            Formatted statistics string
        """
        success_rate = (
            (result.successful / result.total_requested) * 100 if result.total_requested > 0 else 0
        )

        summary = f"""
Batch Generation Summary:
========================
Total Requested: {result.total_requested}
Successful: {result.successful}
Failed: {result.failed}
Success Rate: {success_rate:.1f}%
Total Time: {result.total_time:.2f}s
Average Time per Item: {result.average_time_per_item:.2f}s
"""

        if result.failed_software:
            summary += f"\nFailed Software:\n"
            for software in result.failed_software[:10]:  # Show first 10
                summary += f"  - {software}\n"
            if len(result.failed_software) > 10:
                summary += f"  ... and {len(result.failed_software) - 10} more\n"

        return summary

    async def cleanup(self) -> None:
        """Cleanup batch engine resources."""
        self.executor.shutdown(wait=True)

    async def process_batch(self, software_list, **kwargs):
        """Backward compatibility method for process_batch."""
        from ..models.generation import BatchGenerationRequest, LLMProvider

        # Convert old-style arguments to new BatchGenerationRequest
        request = BatchGenerationRequest(
            software_list=software_list,
            target_providers=kwargs.get("target_providers", []),
            llm_provider=kwargs.get("llm_provider", LLMProvider.OPENAI),
            use_rag=kwargs.get("use_rag", True),
            output_directory=kwargs.get("output_directory"),
            max_concurrent=kwargs.get("max_concurrent", self.max_concurrent),
            continue_on_error=kwargs.get("continue_on_error", True),
            category_filter=kwargs.get("category_filter"),
            force=kwargs.get("force", False),
        )

        return await self.generate_batch(request, kwargs.get("progress_callback"))


# Backward compatibility alias for tests
BatchEngine = BatchGenerationEngine
