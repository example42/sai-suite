#!/usr/bin/env python3
"""
SAI Release Automation Script

This script automates the release process for the SAI Software Management Suite.
It handles version bumping, changelog updates, git tagging, and PyPI publishing.
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import yaml


class ReleaseManager:
    """Manages the release process for SAI."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pyproject_path = project_root / "pyproject.toml"
        self.changelog_path = project_root / "CHANGELOG.md"
        
    def get_current_version(self) -> Optional[str]:
        """Get the current version from git tags."""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def bump_version(self, current_version: str, bump_type: str) -> str:
        """Bump version according to semantic versioning."""
        # Remove 'v' prefix if present
        version = current_version.lstrip('v')
        
        # Parse version
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$', version)
        if not match:
            raise ValueError(f"Invalid version format: {version}")
        
        major, minor, patch, pre = match.groups()
        major, minor, patch = int(major), int(minor), int(patch)
        
        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")
        
        return f"{major}.{minor}.{patch}"
    
    def update_changelog(self, version: str) -> None:
        """Update the changelog with the new version."""
        if not self.changelog_path.exists():
            print(f"Warning: Changelog not found at {self.changelog_path}")
            return
        
        content = self.changelog_path.read_text()
        
        # Replace [Unreleased] with version and date
        today = datetime.now().strftime("%Y-%m-%d")
        version_header = f"## [{version}] - {today}"
        
        # Find the unreleased section
        unreleased_pattern = r"## \[Unreleased\]"
        if not re.search(unreleased_pattern, content):
            print("Warning: No [Unreleased] section found in changelog")
            return
        
        # Replace [Unreleased] with version
        content = re.sub(unreleased_pattern, version_header, content)
        
        # Add new [Unreleased] section at the top
        unreleased_section = f"""## [Unreleased]

### Added

### Changed

### Fixed

### Security

{version_header}"""
        
        content = re.sub(
            rf"{re.escape(version_header)}",
            unreleased_section,
            content,
            count=1
        )
        
        self.changelog_path.write_text(content)
        print(f"Updated changelog for version {version}")
    
    def create_git_tag(self, version: str, message: str) -> None:
        """Create and push a git tag."""
        tag_name = f"v{version}"
        
        # Create annotated tag
        subprocess.run([
            "git", "tag", "-a", tag_name, "-m", message
        ], check=True)
        
        print(f"Created git tag: {tag_name}")
    
    def build_package(self) -> None:
        """Build the package for distribution."""
        print("Building package...")
        
        # Clean previous builds
        build_dir = self.project_root / "build"
        dist_dir = self.project_root / "dist"
        
        if build_dir.exists():
            subprocess.run(["rm", "-rf", str(build_dir)], check=True)
        if dist_dir.exists():
            subprocess.run(["rm", "-rf", str(dist_dir)], check=True)
        
        # Build package
        subprocess.run([
            sys.executable, "-m", "build"
        ], cwd=self.project_root, check=True)
        
        print("Package built successfully")
    
    def publish_to_pypi(self, test: bool = False) -> None:
        """Publish package to PyPI."""
        repository = "testpypi" if test else "pypi"
        print(f"Publishing to {'Test ' if test else ''}PyPI...")
        
        cmd = [sys.executable, "-m", "twine", "upload"]
        if test:
            cmd.extend(["--repository", "testpypi"])
        cmd.append("dist/*")
        
        subprocess.run(cmd, cwd=self.project_root, check=True)
        print(f"Published to {'Test ' if test else ''}PyPI successfully")
    
    def run_tests(self) -> bool:
        """Run the test suite."""
        print("Running tests...")
        try:
            subprocess.run([
                sys.executable, "-m", "pytest", "-v"
            ], cwd=self.project_root, check=True)
            print("All tests passed")
            return True
        except subprocess.CalledProcessError:
            print("Tests failed")
            return False
    
    def check_git_status(self) -> bool:
        """Check if git working directory is clean."""
        result = subprocess.run([
            "git", "status", "--porcelain"
        ], capture_output=True, text=True)
        
        if result.stdout.strip():
            print("Error: Git working directory is not clean")
            print("Please commit or stash your changes before releasing")
            return False
        
        return True
    
    def push_changes(self) -> None:
        """Push changes and tags to remote."""
        print("Pushing changes to remote...")
        subprocess.run(["git", "push"], check=True)
        subprocess.run(["git", "push", "--tags"], check=True)
        print("Changes pushed successfully")


def main():
    """Main entry point for the release script."""
    parser = argparse.ArgumentParser(description="SAI Release Automation")
    parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch"],
        help="Type of version bump"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Publish to Test PyPI instead of PyPI"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests"
    )
    parser.add_argument(
        "--skip-publish",
        action="store_true",
        help="Skip publishing to PyPI"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    release_manager = ReleaseManager(project_root)
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
    
    # Check git status
    if not args.dry_run and not release_manager.check_git_status():
        sys.exit(1)
    
    # Get current version
    current_version = release_manager.get_current_version()
    if not current_version:
        print("No previous version found, starting with 0.1.0")
        current_version = "0.0.0"
    
    # Calculate new version
    new_version = release_manager.bump_version(current_version, args.bump_type)
    print(f"Bumping version from {current_version} to {new_version}")
    
    if args.dry_run:
        print(f"Would update changelog for version {new_version}")
        print(f"Would create git tag v{new_version}")
        print("Would build package")
        if not args.skip_publish:
            print(f"Would publish to {'Test ' if args.test else ''}PyPI")
        return
    
    # Run tests
    if not args.skip_tests:
        if not release_manager.run_tests():
            print("Aborting release due to test failures")
            sys.exit(1)
    
    # Update changelog
    release_manager.update_changelog(new_version)
    
    # Commit changelog changes
    subprocess.run([
        "git", "add", str(release_manager.changelog_path)
    ], check=True)
    subprocess.run([
        "git", "commit", "-m", f"Update changelog for v{new_version}"
    ], check=True)
    
    # Create git tag
    tag_message = f"Release v{new_version}"
    release_manager.create_git_tag(new_version, tag_message)
    
    # Build package
    release_manager.build_package()
    
    # Publish to PyPI
    if not args.skip_publish:
        release_manager.publish_to_pypi(test=args.test)
    
    # Push changes
    release_manager.push_changes()
    
    print(f"\nRelease v{new_version} completed successfully!")
    print(f"Package available at: https://{'test.' if args.test else ''}pypi.org/project/sai/{new_version}/")


if __name__ == "__main__":
    main()