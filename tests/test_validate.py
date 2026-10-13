import json
import re
import sys

import pytest

NAMES = ["harness_json", "cli_parses", "json_flag", "dry_run", "backend_call",
         "test_plan", "tests_exist", "no_skip", "skill_md_sync"]

CLI_SRC = '''import shutil
import subprocess

import click


@click.group()
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
def cli(as_json):
    """Root."""


@cli.command()
@click.argument("name")
@click.option("--dry-run", is_flag=True, help="Preview only.")
def create(name, dry_run):
    """Create a thing."""
    path = shutil.which("demo")
    subprocess.run([path, name])
'''

META = {"binary": "demo", "version": "1.0", "description": "Demo wrapper.", "mutating": ["create"]}
SKIPWORD = "pytest." + "skip"


@pytest.fixture
def val(SCRIPTS, load_module):
    return load_module(SCRIPTS / "validate.py")


@pytest.fixture
def harness(tmp_path, SCRIPTS, load_module):
    gs = load_module(SCRIPTS / "gen_skill.py")
    d = tmp_path / "harness-demo"
    (d / "tests").mkdir(parents=True)
    (d / "cli.py").write_text(CLI_SRC)
    (d / "harness.json").write_text(json.dumps(META))
    (d / "TEST.md").write_text("# Test plan: demo harness\n\n## Workflows\n1. x\n\n## Results\n")
    (d / "tests" / "test_x.py").write_text("def test_ok():\n    assert True\n")
    (d / "SKILL.md").write_text(gs.render_skill(META, gs.parse_cli(CLI_SRC)))
    return d


def _run(run_script, SCRIPTS, d, *extra):
    return run_script(SCRIPTS / "validate.py", d, *extra)


def test_check_names(val):
    assert val.CHECK_NAMES == NAMES


def test_valid_harness_passes(harness, SCRIPTS, run_script):
    p = _run(run_script, SCRIPTS, harness)
    assert p.returncode == 0, p.stdout + p.stderr
    assert p.stdout.strip().splitlines()[-1] == "Overall: PASS (9/9 checks)"
    for n in NAMES:
        assert f"[PASS] {n}:" in p.stdout


def test_json_schema(harness, SCRIPTS, run_script):
    p = _run(run_script, SCRIPTS, harness, "--json")
    assert p.returncode == 0, p.stderr
    d = json.loads(p.stdout)
    assert d["total"] == 9 and d["passed"] == 9 and d["overall"] == "PASS"
    assert [c["name"] for c in d["checks"]] == NAMES
    for c in d["checks"]:
        assert set(c) >= {"name", "passed", "detail"}
        assert c["passed"] is True


def test_run_checks_api(val, harness):
    res = val.run_checks(harness)
    assert [r["name"] for r in res] == NAMES
    assert all(r["passed"] for r in res)


def _sub(path, old, new):
    t = path.read_text()
    assert old in t
    path.write_text(t.replace(old, new))


def b_harness_json(d):
    j = json.loads((d / "harness.json").read_text())
    del j["version"]
    (d / "harness.json").write_text(json.dumps(j))


def b_cli_parses(d):
    (d / "cli.py").write_text(CLI_SRC + "\ndef broken(:\n")


def b_json_flag(d):
    _sub(d / "cli.py", '"--json", "as_json"', '"--verbose", "as_json"')


def b_dry_run(d):
    _sub(d / "cli.py", '"--dry-run"', '"--dry"')


def b_backend(d):
    _sub(d / "cli.py", "subprocess", "sproc")


def b_test_plan(d):
    _sub(d / "TEST.md", "## Workflows", "## Flows")


def b_tests_exist(d):
    (d / "tests" / "test_x.py").unlink()


def b_no_skip(d):
    (d / "tests" / "test_x.py").write_text(f"import pytest\n\ndef test_s():\n    {SKIPWORD}('x')\n")


def b_sync(d):
    with open(d / "SKILL.md", "a") as f:
        f.write("hand edit\n")


# (check, break fn, exact 8/9 expected?)
CASES = [
    ("harness_json", b_harness_json, False),
    ("cli_parses", b_cli_parses, False),
    ("json_flag", b_json_flag, False),
    ("dry_run", b_dry_run, False),
    ("backend_call", b_backend, False),
    ("test_plan", b_test_plan, True),
    ("tests_exist", b_tests_exist, True),
    ("no_skip", b_no_skip, True),
    ("skill_md_sync", b_sync, True),
]


@pytest.mark.parametrize("check,brk,exact", CASES, ids=[c[0] for c in CASES])
def test_break_one_check(harness, SCRIPTS, run_script, check, brk, exact):
    brk(harness)
    p = _run(run_script, SCRIPTS, harness)
    assert p.returncode == 1, p.stdout + p.stderr
    lines = p.stdout.strip().splitlines()
    assert f"[FAIL] {check}:" in p.stdout
    assert lines[-1].startswith("Overall: FAIL (")
    if exact:
        assert lines[-1] == "Overall: FAIL (8/9 checks)"
        assert sum(1 for l in lines if l.startswith("[FAIL]")) == 1
    j = json.loads(_run(run_script, SCRIPTS, harness, "--json").stdout)
    assert j["overall"] == "FAIL"
    by = {c["name"]: c for c in j["checks"]}
    assert by[check]["passed"] is False
    assert j["passed"] == sum(1 for c in j["checks"] if c["passed"])
