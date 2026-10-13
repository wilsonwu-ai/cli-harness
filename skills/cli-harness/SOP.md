# SOP: building a harness

Follow the phases in order. Do not skip a phase and do not reorder them. Set `S` to the skill directory (`${CLAUDE_PLUGIN_ROOT}/skills/cli-harness` or `~/.claude/skills/cli-harness`) and `B` to the binary name. Read GOTCHAS.md first.

## Phase 0: Refuse checks

```
python3 $S/scripts/probe.py $B > /tmp/probe.json; echo "exit=$?"
```

- Exit 2 (`not_found`): stop. Tell the user the binary is not on PATH. Do not install it.
- Exit 3 (`denylisted`): stop. Tell the user the `deny_reason`. Do not run the binary.
- Also refuse, even when probe exits 0, any binary that moves money, deletes user data or touches credentials.

## Phase 1: Probe

Read the `help` field of the probe output (and `version`). Decide the command surface: at most 6 commands for v1. For each, record whether it mutates (writes files, changes state, deletes). Read-only commands need no `--dry-run`. Write the mutating names down; they go into `harness.json`.

## Phase 2: Plan

```
mkdir -p harness-$B/tests
sed "s/{{BINARY}}/$B/g" $S/templates/TEST.md.tmpl > harness-$B/TEST.md
```

Fill in `## Workflows` (numbered, realistic, each with the artifact check that proves it worked) and `## Artifact checks`. Write this BEFORE any code.

## Phase 3: Build

Render the wrapper:

```
python3 - <<PY
from pathlib import Path
s = Path("$S/templates/wrapper_cli.py.tmpl").read_text()
s = s.replace("{{BINARY}}", "$B").replace("{{DESCRIPTION}}", "<one line>")
Path("harness-$B/cli.py").write_text(s)
PY
```

Then:

- Write `harness-$B/harness.json`: `{"binary": "...", "version": "...", "description": "...", "mutating": [...]}`.
- Add commands to cli.py with `@cli.command(...)`, each calling `run_backend([...])`. Call the real binary; never reimplement it.
- Every mutating command gets a `--dry-run` option and passes `dry_run=` to `run_backend`.
- No passthrough "raw" command. Errors exit non-zero. Never swallow stderr.
- Keep the `--json` group option and `emit()`.

## Phase 4: Test

Write `harness-$B/tests/test_$B.py` from TEST.md. Rules:

- Verify artifacts, never exit codes alone: file magic bytes, row counts, ffprobe durations, file sizes.
- A missing backend must FAIL. Never use `pytest.skip`, `mark.skip`, `skipif` or `importorskip`.
- Use `tmp_path` for all files.

```
cd harness-$B && python3 -m pytest tests -q
```

Paste the pytest summary line into TEST.md under `## Results`.

## Phase 5: Document

```
python3 $S/scripts/gen_skill.py harness-$B
```

Never hand-edit the generated SKILL.md. Change cli.py or harness.json and regenerate. `gen_skill.py harness-$B --check` verifies it is current.

## Phase 6: Done

```
python3 $S/scripts/validate.py harness-$B
python3 -m pytest harness-$B/tests -q
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
