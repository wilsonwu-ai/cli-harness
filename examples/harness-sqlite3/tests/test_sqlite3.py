"""Artifact-verifying tests for the sqlite3 harness. A missing sqlite3 FAILS."""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

CLI = Path(__file__).resolve().parent.parent / "cli.py"
MAGIC = b"SQLite format 3\x00"


def run(*args, env=None):
    proc = subprocess.run([sys.executable, str(CLI), "--json", *map(str, args)],
                          capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
    return proc


def ok(*args):
    proc = run(*args)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def py_rows(db, sql):
    con = sqlite3.connect(str(db))
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def build(tmp_path):
    db = tmp_path / "people.db"
    ok("create-table", db, "people", "--column", "id INTEGER PRIMARY KEY",
       "--column", "name TEXT", "--column", "age INTEGER")
    for name, age in [("Ada", 36), ("Grace", 45), ("O'Brien", 29)]:
        ok("insert", db, "people", "--set", f"name={name}", "--set", f"age={age}")
    return db


def test_backend_present():
    assert shutil.which("sqlite3"), "sqlite3 must be installed; this is a failure, not a skip"


def test_build_database_artifacts(tmp_path):
    db = build(tmp_path)
    assert db.read_bytes()[:16] == MAGIC
    assert py_rows(db, "SELECT name FROM sqlite_master WHERE type='table'") == [("people",)]
    assert py_rows(db, "SELECT count(*) FROM people") == [(3,)]
    assert py_rows(db, "SELECT name, age FROM people ORDER BY id") == [("Ada", 36), ("Grace", 45), ("O'Brien", 29)]
    assert py_rows(db, "SELECT typeof(age) FROM people LIMIT 1") == [("integer",)]


def test_tables_and_schema_match_independent_reads(tmp_path):
    db = build(tmp_path)
    ok("create-table", db, "notes", "--column", "body TEXT")
    expected = [r[0] for r in py_rows(db, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    assert ok("tables", db)["tables"] == expected == ["notes", "people"]
    ddl = py_rows(db, "SELECT sql FROM sqlite_master WHERE name='people'")[0][0]
    assert ok("schema", db, "people")["schema"] == [{"name": "people", "sql": ddl}]
    assert len(ok("schema", db)["schema"]) == 2


def test_query_matches_python_and_is_read_only(tmp_path):
    db = build(tmp_path)
    rows = ok("query", db, "SELECT name, age FROM people WHERE age > 30 ORDER BY age")["rows"]
    assert [(r["name"], r["age"]) for r in rows] == py_rows(db, "SELECT name, age FROM people WHERE age > 30 ORDER BY age")
    assert ok("query", db, "SELECT * FROM people WHERE 0")["rows"] == []
    before = db.read_bytes()
    bad = run("query", db, "DELETE FROM people")
    assert bad.returncode != 0
    assert db.read_bytes() == before
    assert py_rows(db, "SELECT count(*) FROM people") == [(3,)]


def test_dry_run_changes_nothing(tmp_path):
    db = tmp_path / "dry.db"
    out = ok("create-table", db, "t", "--column", "x TEXT", "--dry-run")
    assert out["dry_run"] is True and out["would_run"][0] == "sqlite3"
    assert not db.exists()
    ok("create-table", db, "t", "--column", "x TEXT")
    before = db.read_bytes()
    out = ok("insert", db, "t", "--set", "x=a", "--dry-run")
    assert out["dry_run"] is True
    assert db.read_bytes() == before
    assert py_rows(db, "SELECT count(*) FROM t") == [(0,)]


def test_errors_exit_nonzero(tmp_path):
    db = build(tmp_path)
    assert run("insert", db, "missing_table", "--set", "x=1").returncode != 0
    assert py_rows(db, "SELECT count(*) FROM people") == [(3,)]
    assert run("create-table", db, "people", "--column", "id INTEGER").returncode != 0  # already exists
    assert run("insert", db, "people; DROP TABLE people", "--set", "x=1").returncode != 0
    assert py_rows(db, "SELECT count(*) FROM people") == [(3,)]
    gone = tmp_path / "nope.db"
    assert run("query", gone, "SELECT 1").returncode != 0
    assert not gone.exists()


def test_missing_binary_fails(tmp_path):
    empty = tmp_path / "emptybin"
    empty.mkdir()
    env = {**os.environ, "PATH": str(empty)}
    db = tmp_path / "x.db"
    db.write_bytes(MAGIC)  # exists, so click's exists check passes and we reach the backend
    proc = run("tables", db, env=env)
    assert proc.returncode != 0
    assert "not found on PATH" in proc.stderr
    proc = run("create-table", tmp_path / "y.db", "t", "--column", "x TEXT", env=env)
    assert proc.returncode != 0
    assert not (tmp_path / "y.db").exists()
