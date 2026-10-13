import json
import shutil
import time
import uuid

import pytest

CONTRACT_DENY = ["rm", "rmdir", "dd", "mkfs", "diskutil", "shred", "srm", "sudo", "su", "kill",
                 "killall", "launchctl", "security", "git", "gh", "curl", "wget", "ssh", "scp"]


@pytest.fixture
def probe_mod(SCRIPTS, load_module):
    return load_module(SCRIPTS / "probe.py")


def test_probe_sqlite3(probe_mod):
    t = time.monotonic()
    r = probe_mod.probe("sqlite3")
    assert time.monotonic() - t < 15
    assert r["path"] == shutil.which("sqlite3")
    assert r["path"]
    assert r["version"]
    assert r["help"]
    assert r["denylisted"] is False
    assert r["deny_reason"] is None
    assert r["binary"] == "sqlite3"
    assert "help_flag_used" in r


def test_probe_cli_ok(SCRIPTS, run_script):
    p = run_script(SCRIPTS / "probe.py", "sqlite3", timeout=30)
    assert p.returncode == 0, p.stderr
    d = json.loads(p.stdout)
    assert d["binary"] == "sqlite3"
    assert d["denylisted"] is False


def test_probe_not_found(SCRIPTS, run_script):
    name = "nope-" + uuid.uuid4().hex
    p = run_script(SCRIPTS / "probe.py", name)
    assert p.returncode == 2
    d = json.loads(p.stdout)
    assert d["error"] == "not_found"
    assert d["binary"] == name


@pytest.mark.parametrize("name", ["rm", "/bin/rm"])
def test_probe_denylisted_cli(SCRIPTS, run_script, name):
    p = run_script(SCRIPTS / "probe.py", name)
    assert p.returncode == 3
    d = json.loads(p.stdout)
    assert d["error"] == "denylisted"
    assert d["deny_reason"]


def test_probe_denylisted_api(probe_mod):
    r = probe_mod.probe("/bin/rm")
    assert r["error"] == "denylisted"
    assert r["deny_reason"]


def test_denylist_contents(probe_mod):
    assert isinstance(probe_mod.DENYLIST, frozenset)
    missing = [n for n in CONTRACT_DENY if n not in probe_mod.DENYLIST]
    assert not missing, missing


def test_resolve(probe_mod):
    assert probe_mod.resolve("sqlite3") == shutil.which("sqlite3")
    assert probe_mod.resolve("nope-" + uuid.uuid4().hex) is None


def test_probe_not_found_api(probe_mod):
    r = probe_mod.probe("nope-" + uuid.uuid4().hex)
    assert r["error"] == "not_found"
