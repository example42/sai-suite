#!/usr/bin/env python3
"""
Weekly Version Update Script for SAI Suite

This script updates/creates all versions for all software in the saidata directory
using locally present repositories. Designed to run as a weekly cronjob.

Features:
- Automatic discovery of saidata files
- Batch processing with parallel execution
- Comprehensive logging and reporting
- Email notifications (optional)
- Backup management with retention policy
- Progress tracking and statistics
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from saigen.cli.commands.refresh_versions import refresh_versions
from saigen.utils.config import get_config_manager


class VersionUpdateManager:
    """Manages weekly version updates for saidata files."""

    def __init__(
        self,
        saidata_dir: Path,
        backup_dir: Path,
        log_dir: Path,
        skip_default: bool = False,
        use_cache: bool = True,
        dry_run: bool = False,
        verbose: bool = False,
        parallel: bool = True,
        max_workers: int = 4,
    ):
        """Initialize version update manager.

        Args:
            saidata_dir: Path to saidata directory
            backup_dir: Path to backup directory
            log_dir: Path to log directory
            skip_default: Skip default.yaml files
            use_cache: Use cached repository data
            dry_run: Show what would be done without executing
            verbose: Enable verbose output
            parallel: Enable parallel processing
            max_workers: Maximum parallel workers
        """
        self.saidata_dir = saidata_dir
        self.backup_dir = backup_dir
        self.log_dir = log_dir
        self.skip_default = skip_default
        self.use_cache = use_cache
        self.dry_run = dry_run
        self.verbose = verbose
        self.parallel = parallel
        self.max_workers = max_workers

        # Statistics
        self.stats = {
            "total_dirs": 0,
            "processed_dirs": 0,
            "failed_dirs": 0,
            "skipped_dirs": 0,
            "total_updates": 0,
            "total_errors": 0,
            "start_time": None,
            "end_time": None,
        }

        # Results tracking
        self.results: List[Dict] = []

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging configuration."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"update_{timestamp}.log"

        # Configure logging
        log_format = "[%(asctime)s] %(levelname)s: %(message)s"
        log_level = logging.DEBUG if self.verbose else logging.INFO

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(log_format))

        # Configure root logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.log_file = log_file

    def discover_software_directories(self) -> List[Path]:
        """Discover all software directories containing saidata files.

        Returns:
            List of software directory paths
        """
        self.logger.info(f"Scanning for software directories in: {self.saidata_dir}")

        software_dirs = set()

        # Find all yaml files
        for yaml_file in self.saidata_dir.rglob("*.yaml"):
            try:
                # Check if it's a saidata file
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if data and "version" in data and "metadata" in data:
                    # This is a saidata file
                    software_dir = yaml_file.parent

                    # For OS-specific files, use parent directory
                    if software_dir.name in ["ubuntu", "debian", "centos", "fedora", "rocky"]:
                        software_dir = software_dir.parent

                    software_dirs.add(software_dir)

            except Exception as e:
                self.logger.debug(f"Skipping {yaml_file}: {e}")
                continue

        software_dirs_list = sorted(software_dirs)
        self.stats["total_dirs"] = len(software_dirs_list)
        self.logger.info(f"Found {len(software_dirs_list)} software directories")

        return software_dirs_list

    async def process_directory(self, software_dir: Path) -> Dict:
        """Process a single software directory.

        Args:
            software_dir: Path to software directory

        Returns:
            Dictionary with processing results
        """
        relative_path = software_dir.relative_to(self.saidata_dir)
        software_name = software_dir.name

        result = {
            "software": software_name,
            "path": str(relative_path),
            "success": False,
            "updates": 0,
            "errors": [],
            "warnings": [],
            "execution_time": 0.0,
        }

        self.logger.info(f"Processing: {relative_path}")

        try:
            # Create backup subdirectory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_subdir = self.backup_dir / timestamp / relative_path
            backup_subdir.mkdir(parents=True, exist_ok=True)

            # Build command arguments
            from click.testing import CliRunner
            from saigen.cli.main import cli

            runner = CliRunner()

            args = [
                "refresh-versions",
                str(software_dir),
                "--all-variants",
                f"--backup-dir={backup_subdir}",
            ]

            if self.skip_default:
                args.append("--skip-default")

            if not self.use_cache:
                args.append("--no-cache")

            if self.verbose:
                args.insert(0, "--verbose")

            if self.dry_run:
                args.insert(0, "--dry-run")

            # Execute command
            start_time = asyncio.get_event_loop().time()
            cli_result = runner.invoke(cli, args, catch_exceptions=False)
            execution_time = asyncio.get_event_loop().time() - start_time

            result["execution_time"] = execution_time

            if cli_result.exit_code == 0:
                result["success"] = True
                self.stats["processed_dirs"] += 1
                self.logger.info(f"✓ Successfully processed {relative_path}")

                # Parse output for update count (if available)
                if "updated" in cli_result.output.lower():
                    # Try to extract update count from output
                    import re

                    match = re.search(r"(\d+)\s+update", cli_result.output, re.IGNORECASE)
                    if match:
                        result["updates"] = int(match.group(1))
                        self.stats["total_updates"] += result["updates"]

            else:
                result["success"] = False
                result["errors"].append(f"Exit code: {cli_result.exit_code}")
                self.stats["failed_dirs"] += 1
                self.logger.error(f"✗ Failed to process {relative_path}")

                if cli_result.output:
                    self.logger.debug(f"Output: {cli_result.output}")

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))
            self.stats["failed_dirs"] += 1
            self.stats["total_errors"] += 1
            self.logger.error(f"✗ Error processing {relative_path}: {e}")

            if self.verbose:
                import traceback

                self.logger.debug(traceback.format_exc())

        return result

    async def process_all_directories(self, software_dirs: List[Path]):
        """Process all software directories.

        Args:
            software_dirs: List of software directory paths
        """
        if self.parallel and len(software_dirs) > 1:
            # Parallel processing
            self.logger.info(f"Processing {len(software_dirs)} directories in parallel (max workers: {self.max_workers})")

            # Create semaphore to limit concurrent tasks
            semaphore = asyncio.Semaphore(self.max_workers)

            async def process_with_semaphore(directory):
                async with semaphore:
                    return await self.process_directory(directory)

            # Process all directories
            tasks = [process_with_semaphore(d) for d in software_dirs]
            self.results = await asyncio.gather(*tasks)

        else:
            # Sequential processing
            self.logger.info(f"Processing {len(software_dirs)} directories sequentially")

            for software_dir in software_dirs:
                result = await self.process_directory(software_dir)
                self.results.append(result)

    def generate_summary(self) -> str:
        """Generate summary report.

        Returns:
            Summary report as string
        """
        duration = self.stats["end_time"] - self.stats["start_time"]

        summary = f"""
Weekly Version Update Summary
{'=' * 60}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Duration: {duration:.2f} seconds
Saidata Directory: {self.saidata_dir}

Results:
--------
Total Directories: {self.stats['total_dirs']}
Successfully Processed: {self.stats['processed_dirs']}
Failed: {self.stats['failed_dirs']}
Skipped: {self.stats['skipped_dirs']}
Total Updates: {self.stats['total_updates']}
Total Errors: {self.stats['total_errors']}

Configuration:
--------------
Skip Default: {self.skip_default}
Use Cache: {self.use_cache}
Dry Run: {self.dry_run}
Verbose: {self.verbose}
Parallel: {self.parallel}
Max Workers: {self.max_workers}

Details:
--------
Log File: {self.log_file}
Backup Directory: {self.backup_dir}
"""

        # Add failed directories if any
        if self.stats["failed_dirs"] > 0:
            summary += "\nFailed Directories:\n"
            for result in self.results:
                if not result["success"]:
                    summary += f"  - {result['path']}\n"
                    for error in result["errors"]:
                        summary += f"    Error: {error}\n"

        return summary

    def save_summary(self):
        """Save summary report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.log_dir / f"summary_{timestamp}.txt"

        summary = self.generate_summary()

        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)

        self.logger.info(f"Summary saved to: {summary_file}")

        # Also save JSON results
        json_file = self.log_dir / f"results_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(
                {"stats": self.stats, "results": self.results}, f, indent=2, default=str
            )

        self.logger.info(f"Results saved to: {json_file}")

    def cleanup_old_backups(self, retention_days: int = 30):
        """Clean up old backup directories.

        Args:
            retention_days: Number of days to retain backups
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would clean up backups older than {retention_days} days")
            return

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        removed_count = 0

        for backup_subdir in self.backup_dir.iterdir():
            if backup_subdir.is_dir():
                try:
                    # Parse timestamp from directory name
                    dir_timestamp = datetime.strptime(backup_subdir.name, "%Y%m%d_%H%M%S")

                    if dir_timestamp < cutoff_date:
                        import shutil

                        shutil.rmtree(backup_subdir)
                        removed_count += 1
                        self.logger.debug(f"Removed old backup: {backup_subdir}")

                except (ValueError, OSError) as e:
                    self.logger.debug(f"Skipping {backup_subdir}: {e}")

        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} old backup directories")

    async def run(self, cleanup_backups: bool = True, retention_days: int = 30):
        """Run the version update process.

        Args:
            cleanup_backups: Whether to clean up old backups
            retention_days: Number of days to retain backups
        """
        self.stats["start_time"] = asyncio.get_event_loop().time()

        self.logger.info("=" * 60)
        self.logger.info("Weekly Version Update Started")
        self.logger.info("=" * 60)

        # Discover software directories
        software_dirs = self.discover_software_directories()

        if not software_dirs:
            self.logger.warning("No software directories found")
            return

        # Process all directories
        await self.process_all_directories(software_dirs)

        self.stats["end_time"] = asyncio.get_event_loop().time()

        # Generate and save summary
        self.logger.info("=" * 60)
        self.logger.info("Weekly Version Update Completed")
        self.logger.info("=" * 60)
        self.logger.info(self.generate_summary())

        self.save_summary()

        # Cleanup old backups
        if cleanup_backups:
            self.cleanup_old_backups(retention_days)

        # Exit with appropriate code
        if self.stats["failed_dirs"] > 0:
            self.logger.warning("⚠ Some directories failed to process")
            sys.exit(1)
        else:
            self.logger.info("✓ All directories processed successfully")
            sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Weekly version update script for SAI Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--saidata-dir",
        type=Path,
        default=Path.home() / "saidata",
        help="Path to saidata directory (default: ~/saidata)",
    )

    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path.home() / "saidata-backups",
        help="Path to backup directory (default: ~/saidata-backups)",
    )

    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path.home() / "logs" / "saidata-updates",
        help="Path to log directory (default: ~/logs/saidata-updates)",
    )

    parser.add_argument(
        "--skip-default", action="store_true", help="Skip default.yaml files"
    )

    parser.add_argument(
        "--no-cache", action="store_true", help="Don't use cached repository data"
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without executing"
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    parser.add_argument(
        "--sequential", action="store_true", help="Disable parallel processing"
    )

    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum parallel workers (default: 4)",
    )

    parser.add_argument(
        "--no-cleanup", action="store_true", help="Don't clean up old backups"
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Backup retention in days (default: 30)",
    )

    args = parser.parse_args()

    # Validate saidata directory
    if not args.saidata_dir.exists():
        print(f"Error: Saidata directory not found: {args.saidata_dir}")
        sys.exit(1)

    # Create manager
    manager = VersionUpdateManager(
        saidata_dir=args.saidata_dir,
        backup_dir=args.backup_dir,
        log_dir=args.log_dir,
        skip_default=args.skip_default,
        use_cache=not args.no_cache,
        dry_run=args.dry_run,
        verbose=args.verbose,
        parallel=not args.sequential,
        max_workers=args.max_workers,
    )

    # Run update process
    asyncio.run(manager.run(cleanup_backups=not args.no_cleanup, retention_days=args.retention_days))


if __name__ == "__main__":
    main()
