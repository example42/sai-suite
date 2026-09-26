"""Installed wheel behavior at the sai and saigen public interfaces."""

import json
import os
import shutil
import subprocess
import zipfile
from email.parser import Parser
from pathlib import Path


def test_built_wheels_validate_and_load_saidata_04(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    source = tmp_path / "source"
    source.mkdir()
    shutil.copytree(repo / "schemas", source / "schemas")
    for package in ("sai", "saigen"):
        shutil.copytree(
            repo / package,
            source / package,
            ignore=shutil.ignore_patterns("build", "*.egg-info", "__pycache__"),
        )
    wheels = tmp_path / "wheels"
    for package in ("sai", "saigen"):
        subprocess.run(
            ["uv", "build", "--sdist", "--out-dir", str(wheels), str(source / package)],
            check=True,
            capture_output=True,
            text=True,
            env=dict(os.environ, SETUPTOOLS_SCM_PRETEND_VERSION="0.1.0"),
        )
        sdist = next(wheels.glob(f"{package}-*.tar.gz"))
        subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(wheels), str(sdist)],
            check=True,
            capture_output=True,
            text=True,
            env=dict(os.environ, SETUPTOOLS_SCM_PRETEND_VERSION="0.1.0"),
        )

    environment = tmp_path / "environment"
    subprocess.run(["uv", "venv", str(environment)], check=True, capture_output=True, text=True)
    installed_python = environment / "bin" / "python"
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(installed_python),
            *[str(next(wheels.glob(f"{package}-*.whl"))) for package in ("saigen", "sai")],
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["uv", "pip", "check", "--python", str(installed_python)],
        check=True,
        capture_output=True,
        text=True,
    )
    for command in ("sai", "saigen"):
        help_result = subprocess.run(
            [str(environment / "bin" / command), "--help"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert help_result.returncode == 0, help_result.stderr + help_result.stdout
    for wheel in wheels.glob("*.whl"):
        with zipfile.ZipFile(wheel) as archive:
            assert all("/build/" not in name for name in archive.namelist())
            metadata_name = next(
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            )
            metadata = Parser().parsestr(archive.read(metadata_name).decode())
            assert metadata["License"] == "Apache-2.0"
            if wheel.name.startswith("sai-"):
                assert any(
                    requirement.startswith("saigen") and "extra ==" not in requirement
                    for requirement in metadata.get_all("Requires-Dist", [])
                )
            assert any(name.endswith(".dist-info/licenses/LICENSE") for name in archive.namelist())

    record = tmp_path / "software" / "ex" / "example" / "default.yaml"
    record.parent.mkdir(parents=True)
    record.write_text(
        'version: "0.4"\nmetadata:\n  name: example\n'
        "  evidence:\n    - kind: primary_source\n"
        "      source: https://example.org/docs\n"
        '      version: "1.0"\n      date: "2026-09-24"\n',
        encoding="utf-8",
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    origins = subprocess.run(
        [
            str(installed_python),
            "-c",
            "from importlib import import_module; "
            "print(import_module('sai.core.saidata_loader').__file__); "
            "print(import_module('saigen.cli.commands.validate').__file__)",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert origins.returncode == 0, origins.stderr
    assert all(path.startswith(str(environment)) for path in origins.stdout.splitlines())

    validated = subprocess.run(
        [str(installed_python), "-m", "saigen", "validate", str(record), "--format", "json"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert validated.returncode == 0, validated.stderr + validated.stdout
    assert json.loads(validated.stdout)["schema_version"] == "0.4"

    loaded = subprocess.run(
        [
            str(installed_python),
            "-c",
            "from sai.core.saidata_loader import SaidataLoader; "
            "from sai.models.config import SaiConfig; "
            "import sys; "
            "loaded = SaidataLoader(SaiConfig(saidata_paths=[sys.argv[1]], "
            "cache_enabled=False)).load_saidata('example'); "
            "print(loaded.metadata.evidence[0].kind)",
            str(tmp_path),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert loaded.returncode == 0, loaded.stderr + loaded.stdout
    assert loaded.stdout.strip() == "primary_source"
