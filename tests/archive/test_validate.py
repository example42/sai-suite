#!/usr/bin/env python3

from pathlib import Path

import yaml

from sai.core.saidata_loader import SaidataLoader
from sai.utils.config import get_config


def test_directory_validation():
    directory = Path("saidata")

    # Find files
    yaml_files = list(directory.glob("*.yaml"))
    print(f"Found {len(yaml_files)} files")

    # Load config and saidata loader
    config = get_config()
    saidata_loader = SaidataLoader(config)

    # Validate each file
    for file_path in yaml_files:
        print(f"Validating {file_path}")
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)

            validation_result = saidata_loader.validate_saidata(data)
            print(f"  Valid: {validation_result.valid}")
            print(f"  Errors: {len(validation_result.errors)}")
            print(f"  Warnings: {len(validation_result.warnings)}")

        except Exception as e:
            print(f"  Error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    test_directory_validation()
