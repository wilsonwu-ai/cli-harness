"""Create, fill and query SQLite databases through the sqlite3 binary."""
import json
import re
import shutil
import subprocess

import click

BINARY = "sqlite3"


def run_backend(args: list[str], input: str | None = None, dry_run=False, timeout: float = 60) -> dict:
    """Run the real binary. Never swallows failures."""
    # A dry run intentionally skips the PATH check so plans can be previewed anywhere.
    if dry_run:
        return {"dry_run": True, "would_run": [BINARY, *args]}
    path = shutil.which(BINARY)
    if path is None:
        raise click.ClickException(f"{BINARY} not found on PATH")
    try:
        proc = subprocess.run(
            [path, *args],
            input=input,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL if input is None else None,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise click.ClickException(f"{BINARY} timed out after {timeout} seconds")
    if proc.returncode != 0:
        message = proc.stderr.strip()
        if message.startswith("Error: "):
            message = message[len("Error: "):]
        raise click.ClickException(message or f"{BINARY} exited with {proc.returncode}")
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def emit(ctx, data: dict):
    """Print data as JSON in --json mode, else as readable lines."""
    if ctx.obj and ctx.obj.get("json"):
        click.echo(json.dumps(data))
    else:
        for key, value in data.items():
            shown = json.dumps(value) if isinstance(value, (list, dict)) else value
            click.echo(f"{key}: {shown}")


@click.group()
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output.")
@click.pass_context
def cli(ctx, as_json):
    """Create, fill and query SQLite databases through the sqlite3 binary."""
    ctx.obj = {"json": as_json}


@cli.command()
@click.pass_context
def version(ctx):
    """Show the backend binary version."""
    last_error = None
    for flag in ("--version", "-version"):
        try:
            result = run_backend([flag])
        except click.ClickException as exc:
            if "not found on PATH" in exc.format_message():
                raise
            last_error = exc
            continue
        lines = [ln.strip() for ln in (result["stdout"] + result["stderr"]).splitlines() if ln.strip()]
        if lines:
            emit(ctx, {"binary": BINARY, "version": lines[0]})
            return
    raise last_error or click.ClickException(f"could not read {BINARY} version")


IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ident(name: str) -> str:
    if not IDENT.match(name):
        raise click.ClickException(f"invalid identifier: {name!r}")
    return name


def _lit(value: str) -> str:
    """Quote a value as an SQL string literal."""
    return "'" + value.replace("'", "''") + "'"


def _rows(stdout: str) -> list:
    """sqlite3 -json prints nothing at all for zero rows."""
    return json.loads(stdout) if stdout.strip() else []


@cli.command("create-table")
@click.argument("db", type=click.Path(dir_okay=False))
@click.argument("table")
@click.option("--column", "columns", multiple=True, required=True,
              help='Column definition, repeatable, e.g. --column "id INTEGER PRIMARY KEY".')
@click.option("--dry-run", is_flag=True, help="Show the sqlite3 call without running it.")
@click.pass_context
def create_table(ctx, db, table, columns, dry_run):
    """Create a table (and the database file if it does not exist)."""
    sql = f"CREATE TABLE {_ident(table)} ({', '.join(columns)});"
    result = run_backend([db, sql], dry_run=dry_run)
    emit(ctx, result if dry_run else {"db": db, "table": table, "created": True})


@cli.command()
@click.argument("db", type=click.Path(dir_okay=False))
@click.argument("table")
@click.option("--set", "pairs", multiple=True, required=True,
              help="COLUMN=VALUE, repeatable. Values are inserted as quoted text and coerced by column affinity.")
@click.option("--dry-run", is_flag=True, help="Show the sqlite3 call without running it.")
@click.pass_context
def insert(ctx, db, table, pairs, dry_run):
    """Insert one row into an existing table."""
    cols, vals = [], []
    for pair in pairs:
        col, sep, val = pair.partition("=")
        if not sep:
            raise click.ClickException(f"--set expects COLUMN=VALUE, got {pair!r}")
        cols.append(_ident(col))
        vals.append(_lit(val))
    sql = f"INSERT INTO {_ident(table)} ({', '.join(cols)}) VALUES ({', '.join(vals)});"
    result = run_backend([db, sql], dry_run=dry_run)
    emit(ctx, result if dry_run else {"db": db, "table": table, "inserted": 1})


@cli.command()
@click.argument("db", type=click.Path(exists=True, dir_okay=False))
@click.argument("sql")
@click.pass_context
def query(ctx, db, sql):
    """Run a read-only SQL query and return the rows."""
    result = run_backend(["-readonly", "-json", db, sql])
    emit(ctx, {"rows": _rows(result["stdout"])})


@cli.command()
@click.argument("db", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def tables(ctx, db):
    """List user tables in the database."""
    sql = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
    result = run_backend(["-readonly", "-json", db, sql])
    emit(ctx, {"tables": [r["name"] for r in _rows(result["stdout"])]})


@cli.command()
@click.argument("db", type=click.Path(exists=True, dir_okay=False))
@click.argument("table", required=False)
@click.pass_context
def schema(ctx, db, table):
    """Show CREATE statements, for one table or for all."""
    sql = "SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL"
    if table:
        sql += f" AND tbl_name={_lit(table)}"
    result = run_backend(["-readonly", "-json", db, sql + " ORDER BY name;"])
    emit(ctx, {"schema": _rows(result["stdout"])})


if __name__ == "__main__":
    cli()
