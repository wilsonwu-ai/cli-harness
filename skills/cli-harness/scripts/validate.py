"""Run the nine cli-harness acceptance checks against a harness directory."""
import argparse
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gen_skill  # noqa: E402

CHECK_NAMES = ["harness_json", "cli_parses", "json_flag", "dry_run", "backend_call",
               "test_plan", "tests_exist", "no_skip", "skill_md_sync"]
SKIP_TOKENS = ("pytest.skip", "mark.skip", "skipif", "importorskip")
META_KEYS = ("binary", "version", "description", "mutating")


def _load_meta(d):
    p = d / "harness.json"
    if not p.is_file():
        return None, "harness.json missing"
    try:
        meta = json.loads(p.read_text())
    except ValueError as e:
        return None, f"harness.json invalid JSON: {e}"
    if not isinstance(meta, dict):
        return None, "harness.json is not an object"
    missing = [k for k in META_KEYS if k not in meta]
    if missing:
        return None, "harness.json missing keys: " + ", ".join(missing)
    if not isinstance(meta["mutating"], list):
        return None, "harness.json 'mutating' is not a list"
    return meta, "harness.json valid"


def _load_parsed(d):
    p = d / "cli.py"
    if not p.is_file():
        return None, None, "cli.py missing"
    src = p.read_text()
    try:
        return src, gen_skill.parse_cli(src), "cli.py parses"
    except SyntaxError as e:
        return None, None, f"cli.py syntax error: {e}"


def run_checks(harness_dir):
    d = Path(harness_dir)
    meta, meta_msg = _load_meta(d)
    src, parsed, parse_msg = _load_parsed(d)
    results = {}

    def rec(name, ok, detail):
        results[name] = {"name": name, "passed": bool(ok), "detail": detail}

    rec("harness_json", meta is not None, meta_msg)
    rec("cli_parses", parsed is not None, parse_msg)

    if parsed is None:
        rec("json_flag", False, parse_msg)
    else:
        ok = any(o["flag"] == "--json" for o in parsed["group_options"])
        rec("json_flag", ok, "group has --json option" if ok else "click group has no --json option")

    if meta is None or parsed is None:
        rec("dry_run", False, "needs valid harness.json and cli.py")
    else:
        cmds = {c["name"]: c for c in parsed["commands"]}
        bad = [m for m in meta["mutating"]
               if m not in cmds or not any(o["flag"] == "--dry-run" for o in cmds[m]["options"])]
        rec("dry_run", not bad,
            "all mutating commands have --dry-run" if not bad else "missing --dry-run or command: " + ", ".join(bad))

    if src is None:
        rec("backend_call", False, parse_msg)
    else:
        miss = [t for t in ("shutil.which", "subprocess") if t not in src]
        rec("backend_call", not miss, "calls the real binary" if not miss else "cli.py lacks: " + ", ".join(miss))

    tm = d / "TEST.md"
    has_plan = tm.is_file() and any(l.startswith("## Workflows") for l in tm.read_text().splitlines())
    rec("test_plan", has_plan, "TEST.md has ## Workflows" if has_plan else "TEST.md missing or has no '## Workflows' line")

    tests = sorted((d / "tests").glob("test_*.py")) if (d / "tests").is_dir() else []
    rec("tests_exist", bool(tests), f"{len(tests)} test file(s)" if tests else "no tests/test_*.py")

    all_py = sorted((d / "tests").glob("*.py")) if (d / "tests").is_dir() else []
    offenders = [f.name for f in all_py if any(t in f.read_text() for t in SKIP_TOKENS)]
    rec("no_skip", not offenders, "no skips in tests" if not offenders else "skip found in: " + ", ".join(offenders))

    sk = d / "SKILL.md"
    if meta is None or parsed is None:
        rec("skill_md_sync", False, "needs valid harness.json and cli.py")
    elif not sk.is_file():
        rec("skill_md_sync", False, "SKILL.md missing")
    else:
        ok = sk.read_text() == gen_skill.render_skill(meta, parsed)
        rec("skill_md_sync", ok, "SKILL.md matches cli.py" if ok else "SKILL.md is stale; rerun gen_skill.py")

    return [results[n] for n in CHECK_NAMES]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("harness_dir")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args(argv)
    checks = run_checks(args.harness_dir)
    passed = sum(c["passed"] for c in checks)
    total = len(checks)
    overall = "PASS" if passed == total else "FAIL"
    if args.as_json:
        print(json.dumps({"checks": checks, "passed": passed, "total": total, "overall": overall}))
    else:
        for c in checks:
            print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['name']}: {c['detail']}")
        print(f"Overall: PASS ({total}/{total} checks)" if overall == "PASS" else f"Overall: FAIL ({passed}/{total} checks)")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
