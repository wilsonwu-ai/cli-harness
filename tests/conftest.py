"""Shared fixtures. Modules under test are loaded lazily inside tests, never at import time."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def REPO() -> Path:
    return _REPO


@pytest.fixture(scope="session")
def SKILL_DIR(REPO) -> Path:
    return REPO / "skills" / "cli-harness"


@pytest.fixture(scope="session")
def SCRIPTS(SKILL_DIR) -> Path:
    return SKILL_DIR / "scripts"


@pytest.fixture(scope="session")
def TEMPLATES(SKILL_DIR) -> Path:
    return SKILL_DIR / "templates"


@pytest.fixture
def load_module():
    """Return a function(path, name=None) importing a python file by path."""

    def _load(path, name=None):
        path = Path(path)
        name = name or ("t_" + path.parent.name.replace("-", "_") + "_" + path.stem.replace(".", "_"))
        spec = importlib.util.spec_from_file_location(name, str(path))
        assert spec is not None and spec.loader is not None, f"cannot load {path}"
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod

    return _load


@pytest.fixture
def run_script():
    """Return a function(script, *args, timeout=60, cwd=None) -> CompletedProcess."""

    def _run(script, *args, timeout=60, cwd=None):
        return subprocess.run(
            [sys.executable, str(script), *map(str, args)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

    return _run
