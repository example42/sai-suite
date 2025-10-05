#!/usr/bin/env python3

from pathlib import Path

import click


@click.command()
@click.argument("files", nargs=-1)
@click.option("--directory", "-d", help="Directory to process")
def test_validate(files, directory):
    """Test validation command."""
    print(f"Files: {files}")
    print(f"Directory: {directory}")

    if directory:
        directory_path = Path(directory)
        yaml_files = list(directory_path.glob("*.yaml"))
        print(f"Found {len(yaml_files)} files")


if __name__ == "__main__":
    test_validate()
