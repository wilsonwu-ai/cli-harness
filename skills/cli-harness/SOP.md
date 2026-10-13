# SOP: building a harness

Follow the phases in order. Do not skip a phase and do not reorder them. Read GOTCHAS.md first.

Run everything from the directory that should contain `harness-<binary>`; create it if needed. Each shell call is a fresh shell, so start every shell block with `S=... B=...`. `S` is the skill directory (`${CLAUDE_PLUGIN_ROOT}/skills/cli-harness` or `~/.claude/skills/cli-harness`; if neither path exists, use the directory containing this SKILL.md). `B` is the binary name. Set `PYTHONDONTWRITEBYTECODE=1` in the same line so no `__pycache__` is left behind.

## Phase 0: Refuse checks

```
S=... B=...
python3 $S/scripts/probe.py $B > "${TMPDIR:-/tmp}/probe.json"; echo "exit=$?"
```

On exit 0 the JSON has the keys `binary`, `path`, `version`, `help`, `help_flag_used`, `denylisted`, `deny_reason`. On exit 2 or 3 it is an error object: `{"error":"not_found","binary":...}` or `{"error":"denylisted","binary":...,"deny_reason":...}`.

- Exit 2 (`not_found`): stop. Tell the user the binary is not on PATH. Do not install it.
- Exit 3 (`denylisted`): stop. Tell the user the `deny_reason`. Do not run the binary.
- Also refuse, even when probe exits 0, any binary that moves money, deletes user data or touches credentials.

## Phase 1: Probe

Read the `help` field of the probe output (and `version`). Decide the command surface: at most 6 commands for v1. For each, record whether it mutates (writes files, changes state, deletes). Read-only commands need no `--dry-run`. Write the mutating names down; they go into `harness.json`. The cap of 6 commands INCLUDES the built-in `version` command, so you add at most 5.

## Phase 2: Plan

```
S=... B=...
mkdir -p harness-$B/tests
sed "s/{{BINARY}}/$B/g" $S/templates/TEST.md.tmpl > harness-$B/TEST.md
```

Fill in `## Workflows` (numbered, realistic, each with the artifact check that proves it worked) and `## Artifact checks`. Write this BEFORE any code.

## Phase 3: Build

Render the wrapper:

```
S=... B=...
python3 - <<PY
from pathlib import Path
s = Path("$S/templates/wrapper_cli.py.tmpl").read_text()
s = s.replace("{{BINARY}}", "$B").replace("{{DESCRIPTION}}", "<one line>")
Path("harness-$B/cli.py").write_text(s)
PY
```

Then:

- Write `harness-$B/harness.json`: `{"binary": "...", "version": "...", "description": "...", "mutating": [...]}`. `version` is the short version string (for example `3.45.3`). `mutating` uses the CLI command names (hyphenated, for example `create-table`), not function names.
- Add commands to cli.py with `@cli.command(...)`, each calling `run_backend([...])`. Call the real binary; never reimplement it.
- Every mutating command gets a `--dry-run` option and must call `run_backend(..., dry_run=dry_run)`. validate checks this syntactically.
- No passthrough "raw" command. Errors exit non-zero. Never swallow stderr.
- Keep the `--json` group option and `emit()`.

## Phase 4: Test

Write `harness-$B/tests/test_$B.py` from TEST.md. Rules:

- Verify artifacts, never exit codes alone: file magic bytes, row counts, ffprobe durations, file sizes.
- A missing backend must FAIL. Never use `pytest.skip`, `mark.skip`, `skipif` or `importorskip`.
- Use `tmp_path` for all files.
- Missing-binary test recipe: run the CLI in a subprocess with `env={"PATH": ""}` and `sys.executable` as the interpreter (so Python itself still resolves), then assert a non-zero exit and "not found on PATH" in stderr.

```
S=... B=...
cd harness-$B && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests -q
```

Paste the pytest count into TEST.md under `## Results` as "N passed", without the timing. Keep the fixed rule bullets in TEST.md (under "## Rules (do not edit)").

## Phase 5: Document

```
S=... B=...
python3 $S/scripts/gen_skill.py harness-$B
```

Never hand-edit the generated SKILL.md. Change cli.py or harness.json and regenerate. `gen_skill.py harness-$B --check` verifies it is current.

## Phase 6: Done

```
S=... B=...
PYTHONDONTWRITEBYTECODE=1 python3 $S/scripts/validate.py harness-$B
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider harness-$B/tests -q
```

Done means BOTH: validate prints the line below AND pytest is green. Nothing else counts.

```
Overall: PASS (9/9 checks)
```

## Safety rules

- Installed binaries only. Resolve with `shutil.which`. Never clone, download or pip-install.
- Respect the denylist (rm, dd, sudo, git, curl, ssh and the rest in probe.py). Never run a denylisted binary.
- Never wrap a binary that moves money, deletes user data or touches credentials, even if it is not on the denylist.
- Mutating commands support `--dry-run`, and you run it first.
- No passthrough command. Failures exit non-zero. A missing binary fails, it does not skip.
