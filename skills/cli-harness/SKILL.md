---
name: cli-harness
description: Wrap ONE command-line binary that is ALREADY INSTALLED on PATH (for example sqlite3 or ffmpeg) into a tested, agent-ready harness with a Click wrapper, artifact-verified tests and a generated SKILL.md. Invoke as /cli-harness <binary>. Not for building new CLIs from source, not for installing software, not for web apps or APIs.
---

# cli-harness

Read SOP.md in this directory before doing anything. Do not improvise.

## Invocation

`/cli-harness <binary>` where `<binary>` is a name already on PATH, such as `sqlite3`.

## Scope

This skill turns one installed executable into a harness at `./harness-<binary>/`: a thin Click wrapper that shells out to the real binary, a test plan written before code, tests that verify real artifacts, and a SKILL.md generated from the code. It never clones, downloads or pip-installs anything, and it refuses binaries on the denylist or ones that move money, delete user data or touch credentials. Done means `validate.py` prints `Overall: PASS (9/9 checks)` and pytest is green.

## Paths

Paths are relative to this skill directory. When installed as a plugin the directory is `${CLAUDE_PLUGIN_ROOT}/skills/cli-harness`. When copied by hand it is `~/.claude/skills/cli-harness`. If neither path exists, use the directory containing this SKILL.md.

- `scripts/probe.py` : resolve and probe the binary (exit 2 not found, exit 3 denylisted)
- `scripts/gen_skill.py` : generate the harness SKILL.md from cli.py
- `scripts/validate.py` : the 9-check gate
- `templates/wrapper_cli.py.tmpl` : Click wrapper, placeholders `{{BINARY}}` and `{{DESCRIPTION}}`
- `templates/TEST.md.tmpl` : test plan, placeholder `{{BINARY}}`
- `GOTCHAS.md` : macOS quirks, read before probing
