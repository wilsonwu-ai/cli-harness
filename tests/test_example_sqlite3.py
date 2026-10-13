import sys
import subprocess

import pytest


@pytest.fixture
def ex(REPO):
    d = REPO / "examples" / "harness-sqlite3"
    assert d.is_dir(), f"missing {d}"
    return d


def test_validate_passes(ex, SCRIPTS, run_script):
    p = run_script(SCRIPTS / "validate.py", ex)
    assert p.returncode == 0, p.stdout + p.stderr
    assert p.stdout.strip().splitlines()[-1] == "Overall: PASS (9/9 checks)"


def test_skill_md_fresh(ex, SCRIPTS, run_script):
    p = run_script(SCRIPTS / "gen_skill.py", ex, "--check")
    assert p.returncode == 0, p.stdout + p.stderr


def test_example_pytest_green(ex):
    p = subprocess.run([sys.executable, "-m", "pytest", str(ex / "tests"), "-q"],
                       capture_output=True, text=True, timeout=180)
    assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-1000:]
