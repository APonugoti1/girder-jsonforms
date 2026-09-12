from pathlib import Path


def test_manifest_includes_docs_and_toml_files():
    manifest = Path(__file__).resolve().parents[1] / "MANIFEST.in"
    lines = manifest.read_text().splitlines()

    assert "include *.md" in lines
    assert "include *.toml" in lines
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
