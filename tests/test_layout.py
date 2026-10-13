import json
import re


def _read(p):
    assert p.exists(), f"missing {p}"
    return p.read_text(encoding="utf-8")


def test_plugin_json(REPO):
    d = json.loads(_read(REPO / ".claude-plugin" / "plugin.json"))
    assert d["name"] == "cli-harness"
    assert d["version"] == "0.1.0"
    assert d["license"] == "Apache-2.0"
    assert d["author"]["name"] == "Wilson Wu"
    assert d["author"]["url"] == "https://github.com/wilsonwu-ai"
    assert d["homepage"] == "https://github.com/wilsonwu-ai/cli-harness"


def test_marketplace_json(REPO):
    d = json.loads(_read(REPO / ".claude-plugin" / "marketplace.json"))
    assert d["name"] == "cli-harness"
    assert "owner" in d and d["owner"]
    plugin = d["plugins"][0]
    assert plugin["name"] == "cli-harness"
    assert plugin["source"] == "./"
    assert plugin["description"]


def _frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert m, "SKILL.md must start with YAML frontmatter"
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, m.group(2)


def test_skill_md(SKILL_DIR):
    fm, body = _frontmatter(_read(SKILL_DIR / "SKILL.md"))
    assert fm.get("name") == "cli-harness"
    assert fm.get("description")
    assert "SOP.md" in body


def test_sop_md(SKILL_DIR):
    text = _read(SKILL_DIR / "SOP.md")
    for n in range(0, 7):
        assert re.search(rf"(?i)phase\s*{n}\b|^#+\s*{n}[\.\):\s]|^\s*{n}\.\s", text, re.M), f"phase {n} missing"
    assert "Overall: PASS (9/9 checks)" in text


def test_license(REPO):
    assert "Apache License" in _read(REPO / "LICENSE")


def test_notice(REPO):
    text = _read(REPO / "NOTICE")
    assert "HKUDS" in text
    assert "2606.03854" in text


def test_gotchas(SKILL_DIR):
    assert _read(SKILL_DIR / "GOTCHAS.md").strip()
