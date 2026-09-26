"""Public loading behavior for saidata 0.4 records."""

import pytest
import yaml

from sai.core.saidata_loader import SaidataLoader, ValidationError
from sai.models.config import SaiConfig


def test_loader_preserves_04_reference_fields_and_evidence(tmp_path):
    record_path = tmp_path / "software" / "ex" / "example" / "default.yaml"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(
        yaml.safe_dump(
            {
                "version": "0.4",
                "metadata": {
                    "name": "example",
                    "identifiers": {"purl": "pkg:generic/example"},
                    "licenses": [{"spdx_id": "Apache-2.0", "as_of_version": "1.0"}],
                    "evidence": [
                        {
                            "kind": "primary_source",
                            "source": "https://example.org/docs/1.0",
                            "version": "1.0",
                            "date": "2026-09-24",
                        }
                    ],
                },
                "files": [{"name": "config", "path": "/etc/example.conf"}],
                "settings": [
                    {
                        "key": "max_clients",
                        "type": "integer",
                        "scope": "file",
                        "file": "config",
                        "defaults": [{"value": 100, "as_of_version": "1.0"}],
                    }
                ],
                "commands": [
                    {
                        "name": "examplectl",
                        "subcommands": [{"name": "status", "flags": [{"name": "--verbose"}]}],
                    }
                ],
                "providers": {
                    "kubernetes": {
                        "manifests": [
                            {
                                "name": "example",
                                "publisher": "Example Project",
                                "version": "1.0",
                                "source": "https://example.org/manifest.yaml",
                                "digest": "sha256:" + "a" * 64,
                            }
                        ]
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    loader = SaidataLoader(SaiConfig(saidata_paths=[str(tmp_path)], cache_enabled=False))
    loaded = loader.load_saidata("example")
    serialized = loaded.model_dump(exclude_none=True)

    assert serialized["metadata"]["identifiers"]["purl"] == "pkg:generic/example"
    assert serialized["metadata"]["licenses"][0]["spdx_id"] == "Apache-2.0"
    assert serialized["metadata"]["evidence"][0]["kind"] == "primary_source"
    assert serialized["settings"][0]["defaults"][0]["value"] == 100
    assert serialized["commands"][0]["subcommands"][0]["flags"][0]["name"] == "--verbose"
    assert serialized["providers"]["kubernetes"]["manifests"][0]["publisher"] == "Example Project"


def test_loader_rejects_invalid_04_license(tmp_path):
    record_path = tmp_path / "software" / "ex" / "example" / "default.yaml"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(
        'version: "0.4"\nmetadata:\n  name: example\n'
        '  licenses:\n    - spdx_id: NOASSERTION\n      as_of_version: "1.0"\n',
        encoding="utf-8",
    )
    loader = SaidataLoader(SaiConfig(saidata_paths=[str(tmp_path)], cache_enabled=False))

    with pytest.raises(ValidationError, match="NOASSERTION"):
        loader.load_saidata("example")
