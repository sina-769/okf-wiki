"""Gruppe 3: Reibung – Marker in Code, Kurz-SHA, Repo-Pfad je Datei, Stop-Hook mit Lint, Hook-Fehler als eine Zeile."""

import json

from .hilfe import WikiTest

SHA = "37a3d5e2ad727a043034103e01b23b75052f186c"
KONZEPT_MIT_CODE = """# Konzept

Offene Frage, als Kasten:

> [!todo] Noch zu klären.

Im Code zählt das nicht: `> [!todo]` und `> ⚠️ **Widerspruch:** X` sind nur Beispiele.

```markdown
> [!todo] Beispiel im Codeblock
> ⚠️ **Widerspruch:** Beispiel im Codeblock, siehe [Quelle](/sources/q1.md)
```
"""


class MarkerInCode(WikiTest):
    def setUp(self):
        super().setUp()
        self.quelle("q1")
        self.core("new", "concept", "k1", "--title", "Konzept", "--description", "Test", "--sources", "q1")
        self.core("body", "concepts/k1", "-", stdin=KONZEPT_MIT_CODE)

    def test_status_zaehlt_nur_echte_todos(self):
        todo = self.py("result = wiki.status()['todo']")
        quelle = self.text("sources/q1").count("[!todo]")
        self.assertEqual(todo, quelle + 1)
        self.assertIn(f"offene [!todo]: {quelle + 1}", self.core("status").stdout)

    def test_dashboard_offene_stellen_ohne_code(self):
        spots = self.py("result = wiki.reader_html()['concepts/k1']['open']")
        self.assertEqual([s["kind"] for s in spots], ["todo"])

    def test_lint_widerspruch_im_code_ist_keiner(self):
        self.assertNotIn("contradiction_one_sided", self.lint_codes("concepts/k1"))

    def test_echter_widerspruch_zaehlt_weiter(self):
        self.core("body", "concepts/k1", "-",
                  stdin="> ⚠️ **Widerspruch:** A sagt X, [Quelle q1](/sources/q1.md) sagt Y.\n")
        self.assertIn("contradiction_one_sided", self.lint_codes("concepts/k1"))
        spots = self.py("result = wiki.reader_html()['concepts/k1']['open']")
        self.assertEqual([s["kind"] for s in spots], ["contra"])


class CaptureKomfort(WikiTest):
    def test_kurz_sha_warnt(self):
        datei = self.datei("a.md")
        done = self.core("capture", "q1", "--url", "https://example.org", "--file", str(datei), "--license", "MIT",
                         "--commit", SHA[:7])
        self.assertIn("kein voller Commit-SHA", done.stderr)
        manifest = json.loads((self.root / "raw" / "q1" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["commit"], SHA[:7])

    def test_voller_sha_ohne_warnung(self):
        datei = self.datei("a.md")
        done = self.core("capture", "q1", "--url", "https://example.org", "--file", str(datei), "--license", "MIT",
                         "--commit", SHA)
        self.assertNotIn("Achtung", done.stderr)

    def test_repo_pfad_je_datei(self):
        a, b, c = self.datei("hooks.json"), self.datei("okf_hook.py"), self.datei("README.md")
        self.core("capture", "q1", "--url", "https://example.org", "--license", "MIT", "--source-path", "README.md",
                  "--file", f"{a}=hooks/hooks.json", "--file", f"{b}=skills/okfw/hooks/okf_hook.py", "--file", str(c))
        manifest = json.loads((self.root / "raw" / "q1" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual([(f["path"], f["source_path"]) for f in manifest["files"]],
                         [("original/hooks.json", "hooks/hooks.json"),
                          ("original/okf_hook.py", "skills/okfw/hooks/okf_hook.py"),
                          ("original/README.md", "README.md")])

    def test_datei_mit_gleichheitszeichen_im_namen(self):
        datei = self.datei("a=b.md")
        self.core("capture", "q1", "--url", "https://example.org", "--license", "MIT", "--file", str(datei))
        self.assertTrue((self.root / "raw" / "q1" / "original" / "a=b.md").exists())


class StopHook(WikiTest):
    def test_lint_fehler_als_eine_zeile(self):
        self.core("new", "concept", "k1", "--title", "Konzept", "--description", "Test")
        self.core("body", "concepts/k1", "-", stdin="Aussage ohne Quelle.[^fehlt]\n\n[^fehlt]: irgendwo\n")
        done = self.hook("stop", {"hook_event_name": "Stop"})
        self.assertEqual(done.returncode, 0, done.stderr)
        out = json.loads(done.stdout)
        self.assertNotIn("decision", out)
        self.assertIn("Fehler", out["systemMessage"])
        self.assertIn("footnote_unsourced", out["systemMessage"])
        self.assertEqual(len(done.stdout.strip().splitlines()), 1)
        self.core("rebuild", "--check")   # Rebuild ist trotzdem gelaufen

    def test_sauberes_wiki_still(self):
        done = self.hook("stop", {"hook_event_name": "Stop"})
        self.assertEqual((done.returncode, done.stdout), (0, ""))


class HookFehlerSichtbar(WikiTest):
    def test_requires_core_beim_sitzungsstart(self):
        toml = self.root / "wiki.toml"
        toml.write_text(toml.read_text(encoding="utf-8").replace('requires_core = "0.1"', 'requires_core = "9.0"'),
                        encoding="utf-8")
        done = self.hook("session-start", {"hook_event_name": "SessionStart", "source": "startup"})
        self.assertEqual(done.returncode, 0)
        out = json.loads(done.stdout)
        self.assertIn("verlangt okfw 9.0", out["systemMessage"])
        self.assertIn("verlangt okfw 9.0", out["hookSpecificOutput"]["additionalContext"])

    def test_requires_core_beim_stop(self):
        toml = self.root / "wiki.toml"
        toml.write_text(toml.read_text(encoding="utf-8").replace('requires_core = "0.1"', 'requires_core = "9.0"'),
                        encoding="utf-8")
        out = json.loads(self.hook("stop", {"hook_event_name": "Stop"}).stdout)
        self.assertIn("verlangt okfw 9.0", out["systemMessage"])

    def test_kaputte_wiki_toml_im_guard(self):
        (self.root / "wiki.toml").write_text("[wiki\n", encoding="utf-8")
        target = self.root / "raw" / "x" / "original" / "a.md"
        done = self.hook("guard", {"hook_event_name": "PreToolUse", "tool_name": "Write", "cwd": str(self.root),
                                   "tool_input": {"file_path": str(target), "content": "x"}})
        self.assertEqual(done.returncode, 0)
        out = json.loads(done.stdout)
        self.assertIn("nicht lesbar", out["systemMessage"])
        self.assertNotIn("hookSpecificOutput", out)

    def test_kaputte_wiki_toml_beim_sitzungsstart(self):
        (self.root / "wiki.toml").write_text("[wiki\n", encoding="utf-8")
        out = json.loads(self.hook("session-start", {"hook_event_name": "SessionStart"}).stdout)
        self.assertIn("nicht lesbar", out["systemMessage"])

    def test_ohne_wiki_toml_still(self):
        leer = self.base / "ohne-wiki"
        leer.mkdir()
        for name in ("session-start", "stop"):
            done = self.hook(name, {"hook_event_name": "Stop"}, project=leer)
            self.assertEqual((done.returncode, done.stdout), (0, ""), name)

    def test_kern_direkt_ohne_wiki_toml_still(self):
        # so ruft settings.example.json den Kern auf (Skill-Ordner-Variante)
        leer = self.base / "ohne-wiki"
        leer.mkdir()
        for args in (("status", "--hook"), ("rebuild", "--hook"), ("rebuild", "--quiet")):
            done = self.core(*args, root=leer)
            self.assertEqual(done.stdout, "", args)
