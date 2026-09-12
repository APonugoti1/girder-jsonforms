import os
import subprocess
from pathlib import Path

from setuptools import Distribution
from setuptools.command.egg_info import manifest_maker


def _write_file(root, relative_path, content="test\n"):
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _build_sources(root):
    dist = Distribution(
        {"name": "girder-jsonforms", "version": "0.0.0", "license_files": ["LICENSE"]}
    )
    dist.script_name = "setup.py"
    dist.script_args = ["sdist"]

    cwd = Path.cwd()
    try:
        os.chdir(root)
        subprocess.run(["git", "init", "-q"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "add", "."], check=True)

        maker = manifest_maker(dist)
        maker.manifest = "SOURCES.txt"
        maker.ensure_finalized()
        maker.run()
        return set(Path("SOURCES.txt").read_text().splitlines())
    finally:
        os.chdir(cwd)


def test_manifest_includes_docs_and_toml_files():
    manifest = Path(__file__).resolve().parents[1] / "MANIFEST.in"
    lines = manifest.read_text().splitlines()

    assert "include README.md" in lines
    assert "include CLAUDE.md" in lines
    assert "include ruff.toml" in lines
    assert "recursive-include doc *.md" in lines
    assert "recursive-include test *.py" in lines


def test_manifest_uses_valid_exclude_directives():
    manifest = Path(__file__).resolve().parents[1] / "MANIFEST.in"
    lines = manifest.read_text().splitlines()

    assert "global-prune *.yaml" not in lines
    assert "exclude girder_jsonformst/tests" not in lines
    assert "exclude codecov.yml" in lines
    assert "exclude requirements-dev.txt" in lines
    assert "exclude tox.ini" in lines
    assert "include CLAUDE.md" in lines
    assert "include ruff.toml" in lines
    assert "recursive-include doc *.md" in lines
    assert "include *.md" not in lines
    assert "include *.toml" not in lines
    assert "include pyproject.toml" not in lines


def test_manifest_generates_expected_sources(tmp_path):
    manifest = Path(__file__).resolve().parents[1] / "MANIFEST.in"
    _write_file(tmp_path, "MANIFEST.in", manifest.read_text())
    _write_file(tmp_path, "setup.py", "")
    _write_file(tmp_path, "LICENSE")
    _write_file(tmp_path, "README.md")
    _write_file(tmp_path, "CLAUDE.md")
    _write_file(tmp_path, "ruff.toml")
    _write_file(tmp_path, "requirements-dev.txt")
    _write_file(tmp_path, "tox.ini")
    _write_file(tmp_path, "codecov.yml")
    _write_file(tmp_path, "example.yaml")
    _write_file(tmp_path, "doc/file-uploads.md")
    _write_file(tmp_path, "scripts/helper.py")
    _write_file(tmp_path, "test/test_manifest.py")
    _write_file(tmp_path, "girder_jsonforms/tests/test_legacy.py")
    _write_file(tmp_path, "girder_jsonforms/web_client/source.js")
    _write_file(
        tmp_path,
        "girder_jsonforms/web_client/dist/girder-plugin-jsonforms.umd.cjs",
    )
    _write_file(tmp_path, "girder_jsonforms/web_client/dist/style.css")

    sources = _build_sources(tmp_path)

    assert "README.md" in sources
    assert "CLAUDE.md" in sources
    assert "ruff.toml" in sources
    assert "doc/file-uploads.md" in sources
    assert "test/test_manifest.py" in sources
    assert "girder_jsonforms/web_client/dist/girder-plugin-jsonforms.umd.cjs" in sources
    assert "girder_jsonforms/web_client/dist/style.css" in sources

    assert "codecov.yml" not in sources
    assert "requirements-dev.txt" not in sources
    assert "tox.ini" not in sources
    assert "example.yaml" not in sources
    assert "scripts/helper.py" not in sources
    assert "girder_jsonforms/tests/test_legacy.py" not in sources
    assert "girder_jsonforms/web_client/source.js" not in sources
