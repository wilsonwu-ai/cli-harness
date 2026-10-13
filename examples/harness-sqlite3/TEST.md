# Test plan: sqlite3 harness

## Workflows

1. Build a database: `create-table` makes `people(id INTEGER PRIMARY KEY, name TEXT, age INTEGER)` in a new .db, then `insert` adds three rows. Artifact check: opened with Python's sqlite3 module, the file starts with the 16 bytes `SQLite format 3\x00`, `people` exists in sqlite_master, and `SELECT count(*)` is 3.
2. Inspect: `tables` and `schema` on that db. Artifact check: the JSON from `tables` equals the table names read independently via Python sqlite3; the `schema` DDL equals the `sql` column read via Python sqlite3.
3. Query: `query` runs a SELECT with a WHERE clause. Artifact check: returned rows equal rows fetched independently via Python sqlite3. A write statement through `query` fails (read-only) and the row count is unchanged.
4. Dry run: `create-table --dry-run` and `insert --dry-run` on a db. Artifact check: output reports `dry_run` and the argv, the db file is not created (or its bytes/row count are unchanged if it exists).
5. Errors: inserting into a missing table, querying a missing db, and a missing binary. Artifact check: non-zero exit, and querying a missing db does not create the file. With PATH emptied, the CLI fails (never skips).

## Artifact checks

- Database file starts with the magic bytes `SQLite format 3\x00`.
- Row counts and values read via Python sqlite3 equal what was inserted, including a value containing a single quote.
- `tables`/`schema`/`query` output equals independent Python sqlite3 reads.
- A missing sqlite3 must FAIL the tests, never skip them.
- Every mutating command (create-table, insert) is exercised with --dry-run and the target is confirmed unchanged.

## Results

`7 passed`
