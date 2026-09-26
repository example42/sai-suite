"""Public validation behavior for saidata 0.4 records."""

import json

from click.testing import CliRunner

from saigen.cli.commands.validate import validate


def test_validate_reports_the_04_schema_for_a_04_record(tmp_path):
    record = tmp_path / "example.yaml"
    record.write_text('version: "0.4"\nmetadata:\n  name: example\n', encoding="utf-8")

    result = CliRunner().invoke(validate, [str(record), "--format", "json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["schema_version"] == "0.4"


def test_validate_rejects_invalid_evidence(tmp_path):
    record = tmp_path / "example.yaml"
    record.write_text(
        'version: "0.4"\nmetadata:\n  name: example\n'
        "  evidence:\n    - kind: hearsay\n      source: https://example.org\n"
        '      version: "1.0"\n      date: "2026-09-24"\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(validate, [str(record), "--format", "json"])

    assert result.exit_code != 0


def test_validate_rejects_noassertion_as_a_license(tmp_path):
    record = tmp_path / "example.yaml"
    record.write_text(
        'version: "0.4"\nmetadata:\n  name: example\n'
        '  licenses:\n    - spdx_id: NOASSERTION\n      as_of_version: "1.0"\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(validate, [str(record), "--format", "json"])

    assert result.exit_code != 0


def test_validate_rejects_unknown_setting_change_effect(tmp_path):
    record = tmp_path / "example.yaml"
    record.write_text(
        'version: "0.4"\nmetadata:\n  name: example\n'
        "settings:\n  - key: max_clients\n    type: integer\n"
        "    scope: file\n    file: config\n    change_effect: reboot\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(validate, [str(record), "--format", "json"])

    assert result.exit_code != 0


def test_validate_rejects_unknown_flag_value_type(tmp_path):
    record = tmp_path / "example.yaml"
    record.write_text(
        'version: "0.4"\nmetadata:\n  name: example\n'
        "commands:\n  - name: examplectl\n    subcommands:\n"
        "      - name: status\n        flags:\n"
        "          - name: --verbose\n            value_type: mystery\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(validate, [str(record), "--format", "json"])

    assert result.exit_code != 0


def test_validate_requires_digest_for_kubernetes_manifest(tmp_path):
    record = tmp_path / "example.yaml"
    record.write_text(
        'version: "0.4"\nmetadata:\n  name: example\n'
        "providers:\n  kubernetes:\n    manifests:\n"
        "      - name: example\n        publisher: Example Project\n"
        '        version: "1.0"\n        source: https://example.org/manifest.yaml\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(validate, [str(record), "--format", "json"])

    assert result.exit_code != 0


def test_validate_rejects_evidence_inside_free_form_environment_map(tmp_path):
    record = tmp_path / "example.yaml"
    record.write_text(
        'version: "0.4"\nmetadata:\n  name: example\n'
        "sources:\n  - name: main\n    url: https://example.org/source.tar.gz\n"
        "    build_system: make\n    environment:\n"
        "      evidence:\n        - kind: primary_source\n"
        "          source: https://example.org/docs\n"
        '          version: "1.0"\n          date: "2026-09-24"\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(validate, [str(record), "--format", "json"])

    assert result.exit_code != 0


def test_advanced_validation_reports_the_04_schema(tmp_path):
    record = tmp_path / "example.yaml"
    record.write_text('version: "0.4"\nmetadata:\n  name: example\n', encoding="utf-8")

    result = CliRunner().invoke(validate, [str(record), "--advanced", "--no-repository-check"])

    assert result.exit_code == 0
    assert "Advanced Saidata 0.4 Schema Validation Report" in result.output
