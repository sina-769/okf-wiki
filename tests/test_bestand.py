"""Bisheriges Verhalten, das bleiben soll: der Ablauf aus nachbau.sh, offline und ohne Claude Code."""

import json

from .hilfe import WikiTest

SHA = "a8291a1a656669b8766fd4ff0f985505fb955e94"
KONZEPT = """# LLM-Wiki im Open Knowledge Format

Das Format verlangt im Frontmatter nur `type`.[^spec] Das Muster pflegt Quellen unveränderlich.[^readme]

Quellen: [Spezifikation](/sources/spec.md) und [README](/sources/readme.md).

[^spec]: [Spezifikation](/sources/spec.md), Abschn. 4
[^readme]: [README](/sources/readme.md)
"""


class Ablauf(WikiTest):
    def setUp(self):
        super().setUp()
        for slug, lic in (("spec", "Apache-2.0"), ("readme", "MIT")):
            datei = self.datei(f"{slug}.md", f"# {slug}\n")
            self.core("capture", slug, "--url", f"https://example.org/{slug}", "--file", str(datei),
                      "--commit", SHA, "--license", lic)
            self.core("new", "source", slug, "--title", slug.capitalize(), "--description", "Testquelle",
                      "--access", "fulltext", "--resource", f"https://example.org/{slug}", "--fundweg", "person",
                      "--set", f"raw_packet=raw/{slug}", "--set", "date=2026-10-24")
        self.core("new", "concept", "llm-wiki", "--title", "LLM-Wiki im Open Knowledge Format",
                  "--description", "Wie Muster und Format zusammenpassen.", "--sources", "spec,readme")
        self.core("body", "concepts/llm-wiki", "-", stdin=KONZEPT)
        for slug in ("spec", "readme"):
            self.core("body", f"sources/{slug}", "-", stdin=f"# {slug}\n\n## Kurzreferat\n\nText.\n\n## Kernaussagen\n\n"
                      f"- Aussage (Z. 1).\n\n## Relevanz\n\nTest.\n\n## Verbindungen\n\n"
                      f"- [LLM-Wiki](/concepts/llm-wiki.md)\n\n## Zugang\n\nRohquelle.\n")
        self.core("rebuild")

    def test_lint_rebuild_status_dashboard(self):
        out = json.loads(self.core("lint", "--json").stdout)
        self.assertEqual(out["counts"].get("error", 0), 0, out["findings"])
        self.core("rebuild", "--check")
        status = self.core("status").stdout
        self.assertIn("Seiten nach Typ: concept 1, source 2", status)
        self.assertIn("Fundweg der Quellen: Von der Person 2", status)
        self.core("dashboard")
        html = (self.root / "build" / "wiki-dashboard.html").read_text(encoding="utf-8")
        self.assertIn("llm-wiki", html)
        self.assertNotRegex(html, r"<(script|img|iframe)[^>]+src=.https?://")

    def test_rohquelle_bleibt_unveraendert(self):
        manifest = json.loads((self.root / "raw" / "spec" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["commit"], SHA)
        self.assertEqual(manifest["license"], {"name": "Apache-2.0", "url": None})
        self.assertEqual(manifest["files"][0]["source_path"], None)
        self.core("capture", "spec", "--url", "https://example.org", "--file", str(self.datei("neu.md")), ok=False)

    def test_hooks(self):
        start = json.loads(self.hook("session-start", {"hook_event_name": "SessionStart", "source": "startup"}).stdout)
        self.assertIn("OKF-v0.2-Wiki unter", start["hookSpecificOutput"]["additionalContext"])
        for target in ("raw/spec/original/spec.md", "wiki/index.md", "wiki/.events.jsonl", "build/wiki-dashboard.html"):
            done = self.hook("guard", {"hook_event_name": "PreToolUse", "tool_name": "Write", "cwd": str(self.root),
                                       "tool_input": {"file_path": str(self.root / target), "content": "x"}})
            self.assertIn('"permissionDecision": "deny"', done.stdout, target)
        karte = str(self.root / "wiki" / "concepts" / "llm-wiki.md")
        done = self.hook("guard", {"hook_event_name": "PreToolUse", "tool_name": "Edit", "cwd": str(self.root),
                                   "tool_input": {"file_path": karte}})
        self.assertEqual(done.stdout, "")
        events = self.root / "wiki" / ".events.jsonl"
        vorher = len(events.read_text(encoding="utf-8").splitlines())
        self.hook("post-edit", {"hook_event_name": "PostToolUse", "tool_name": "Edit", "cwd": str(self.root),
                                "tool_input": {"file_path": karte}})
        zeilen = events.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(zeilen), vorher + 1)
        self.assertEqual(json.loads(zeilen[-1])["by"], "process:claude-code-hook")
        self.assertEqual(self.hook("stop", {"hook_event_name": "Stop"}).stdout, "")
        self.core("rebuild", "--check")
