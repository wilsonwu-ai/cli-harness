"""Probe an installed binary: resolve it on PATH, refuse dangerous ones, capture version and help text."""
import argparse
import json
import os
import shutil
import subprocess
import sys

DENYLIST = frozenset({
    "rm", "rmdir", "dd", "mkfs", "diskutil", "shred", "srm", "sudo", "su", "kill", "killall",
    "launchctl", "security", "git", "gh", "curl", "wget", "ssh", "scp",
})
VERSION_FLAGS = ("--version", "-version", "-V")
HELP_FLAGS = ("--help", "-help", "-h")
HELP_LIMIT = 20000


def resolve(binary):
    return shutil.which(binary)


def _run(path, flag, timeout):
    try:
        p = subprocess.run([path, flag], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, errors="replace", timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return ""
    return p.stdout.strip()


def probe(binary, timeout=10):
    name = os.path.basename(binary)
    if name in DENYLIST:
        return {"error": "denylisted", "binary": binary,
                "deny_reason": f"'{name}' is on the denylist: it can delete data, move money or touch credentials"}
    path = resolve(binary)
    if path is None:
        return {"error": "not_found", "binary": binary}
    version = None
    for flag in VERSION_FLAGS:
        out = _run(path, flag, timeout)
        if out:
            version = next(line.strip() for line in out.splitlines() if line.strip())
            break
    help_text, used = "", None
    for flag in HELP_FLAGS:
        out = _run(path, flag, timeout)
        if out:
            help_text, used = out[:HELP_LIMIT], flag
            break
    return {"binary": binary, "path": path, "version": version, "help": help_text,
            "help_flag_used": used, "denylisted": False, "deny_reason": None}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("binary")
    ap.add_argument("--timeout", type=float, default=10)
    args = ap.parse_args(argv)
    result = probe(args.binary, args.timeout)
    print(json.dumps(result))
    return {"not_found": 2, "denylisted": 3}.get(result.get("error"), 0)


if __name__ == "__main__":
    sys.exit(main())
