import json
import re
import sys

import click
import pytest

FAKE = "definitely-not-a-real-binary-xyz"


@pytest.fixture
def render(TEMPLATES, tmp_path):
    def _r(binary, desc="A test wrapper."):
        src = (TEMPLATES / "wrapper_cli.py.tmpl").read_text()
        out = src.replace("{{BINARY}}", binary).replace("{{DESCRIPTION}}", desc)
        p = tmp_path / f"cli_{binary}.py"
        p.write_text(out)
        return p, out

    return _r


def test_two_placeholders(TEMPLATES):
    src = (TEMPLATES / "wrapper_cli.py.tmpl").read_text()
    assert set(re.findall(r"\{\{(\w+)\}\}", src)) == {"BINARY", "DESCRIPTION"}


def test_rendered_compiles(render):
    p, out = render("sqlite3")
    compile(out, str(p), "exec")
    assert 'BINARY = "sqlite3"' in out
    assert "{{" not in out


def test_version_sqlite3(render, run_script):
    p, _ = render("sqlite3")
    r = run_script(p, "--json", "version", timeout=30)
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["binary"] == "sqlite3"
    assert d["version"]


def test_missing_binary(render, run_script):
    p, _ = render(FAKE)
    r = run_script(p, "--json", "version", timeout=30)
    assert r.returncode != 0
    assert "not found on PATH" in r.stderr


def test_run_backend_dry_run(render, load_module):
    p, _ = render(FAKE)
    mod = load_module(p, "rendered_fake_cli")
    assert mod.BINARY == FAKE
    assert mod.run_backend(["x"], dry_run=True) == {"dry_run": True, "would_run": [FAKE, "x"]}
    with pytest.raises(click.ClickException) as ei:
        mod.run_backend(["x"])
    assert "not found on PATH" in ei.value.format_message()
    assert FAKE in ei.value.format_message()


def test_test_md_template(TEMPLATES):
    t = (TEMPLATES / "TEST.md.tmpl").read_text()
    for h in ["# Test plan: {{BINARY}} harness", "## Workflows", "## Artifact checks", "## Results"]:
        assert h in t
