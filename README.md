# cli-harness

A Claude Code skill that turns one CLI binary, already installed on your PATH, into a tested harness an agent can drive safely. A harness is a thin Click wrapper that shells out to the real binary, a test plan, tests that check real artifacts, and a generated SKILL.md.

It never clones, downloads or installs anything.

## Install

Plugin:

```
/plugin marketplace add wilsonwu-ai/cli-harness
/plugin install cli-harness
```

Or clone the repo and copy `skills/cli-harness` into `~/.claude/skills/`.

## Usage

```
/cli-harness sqlite3
```

The skill follows SOP.md, phases 0 to 6, and writes the result to `./harness-sqlite3/`. A finished example is in `examples/harness-sqlite3/`.

## What a harness contains

```
harness-<binary>/
  harness.json        binary, version, description, mutating command names
  cli.py              Click app rendered from the wrapper template, then extended
  TEST.md             test plan, written before code, with a "## Workflows" section
  tests/test_<binary>.py
  SKILL.md            generated from cli.py by gen_skill.py, never hand-written
```

## Safety model

- Installed binaries only. The binary is resolved with `shutil.which`; nothing is cloned, downloaded or pip-installed.
- Denylist. Binaries such as rm, dd, sudo, git, curl and ssh are refused before they are ever executed. Anything that moves money, deletes user data or touches credentials is refused too.
- Dry-run. Every mutating command has `--dry-run`, and agents run it first.
- Fail, not skip. A missing backend fails the tests; skip markers are rejected by the validator.
- Artifact-verified tests. Tests check file bytes, row counts and durations, never exit codes alone.
- No passthrough command, and errors always exit non-zero.

## Definition of done

`python3 skills/cli-harness/scripts/validate.py harness-<binary>` prints `Overall: PASS (9/9 checks)` and pytest is green. Nothing else counts.

## Credits

The methodology comes from HKUDS/CLI-Anything (Apache-2.0, https://github.com/HKUDS/CLI-Anything) and the paper arXiv 2606.03854. No upstream code was copied. See NOTICE.

Licensed under Apache-2.0. Copyright 2026 Wilson Wu.

Explainers: docs/eli5.html, docs/architecture.html
