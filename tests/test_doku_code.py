"""Gruppe 4: Stellen, an denen Doku und Code auseinanderlagen und der Code nachgezogen wurde."""

import json
import shutil
import unittest

from .hilfe import SKILL, WikiTest

SICHTBARKEIT = """
[visibility]
field = "sichtbarkeit"
default = "oeffentlich"
hidden = ["intern"]

[export.csl]
path = "build/references.json"
"""


class GuardWieProtectedPaths(WikiTest):
    def setUp(self):
        super().setUp()
        toml = self.root / "wiki.toml"
        text = toml.read_text(encoding="utf-8").replace("protected = []", 'protected = ["notizen/**"]')
        toml.write_text(text + SICHTBARKEIT, encoding="utf-8")

    def test_jeder_geschuetzte_pfad_wird_abgelehnt(self):
        patterns = self.py("result = okfw.protected_paths(wiki)")
        self.assertIn("build/wiki-dashboard-oeffentlich.html", patterns)
        for pattern in patterns:
            sample = self.root / pattern.replace("**", "x/y")
            done = self.hook("guard", {"hook_event_name": "PreToolUse", "tool_name": "Write", "cwd": str(self.root),
                                       "tool_input": {"file_path": str(sample), "content": "x"}})
            self.assertIn('"permissionDecision": "deny"', done.stdout, pattern)

    def test_eigenes_public_path(self):
        with (self.root / "wiki.toml").open("a", encoding="utf-8") as f:
            f.write('\n[dashboard]\npublic_path = "site/wiki.html"\n')
        self.assertIn("site/wiki.html", self.py("result = okfw.protected_paths(wiki)"))
        done = self.hook("guard", {"hook_event_name": "PreToolUse", "tool_name": "Edit", "cwd": str(self.root),
                                   "tool_input": {"file_path": str(self.root / "site" / "wiki.html")}})
        self.assertIn('"permissionDecision": "deny"', done.stdout)


class OeffentlichOhneAblageort(WikiTest):
    def test_stored_nur_in_normaler_ausgabe(self):
        with (self.root / "wiki.toml").open("a", encoding="utf-8") as f:
            f.write(SICHTBARKEIT)
        datei = self.datei("a.md")
        self.core("capture", "q1", "--url", "https://example.org", "--file", str(datei), "--license", "MIT")
        self.core("new", "source", "q1", "--title", "Q1", "--description", "D", "--access", "fulltext",
                  "--resource", "https://example.org", "--set", "raw_packet=raw/q1")
        stored = self.py("""
nodes = lambda w: {n['id']: n['stored'] for n in w.dashboard_data()['nodes']}
result = [nodes(wiki)['sources/q1'], nodes(wiki.public_view())['sources/q1']]""")
        self.assertEqual(stored[0], [{"path": "raw/q1", "tracked": False}])
        self.assertEqual(stored[1], [])


class ApaAlsStandard(WikiTest):
    ITEM = {"id": "x", "type": "book", "title": "Ein Titel", "author": [{"family": "Muster", "given": "Max"}],
            "issued": {"date-parts": [[2024]]}}

    def test_stil_ohne_angabe_ist_apa(self):
        self.assertEqual(self.py("result = str(wiki.csl_style())"), str(SKILL / "templates" / "apa.csl"))

    def test_eigener_stil_geht_vor(self):
        with (self.root / "wiki.toml").open("a", encoding="utf-8") as f:
            f.write('\n[export.csl]\nstyle = "stil/eigen.csl"\n')
        self.assertEqual(self.py("result = str(wiki.csl_style())"), str(self.root / "stil" / "eigen.csl"))

    @unittest.skipIf(shutil.which("pandoc") is None, "pandoc fehlt")
    def test_render_apa_formatiert_nach_apa(self):
        out = self.py(f"result = wiki.render_apa([{json.dumps(self.ITEM)}])")
        self.assertIn("Muster, M. (2024)", out)


class ZeilenAlsFundstelle(WikiTest):
    def test_z_landet_im_beleg(self):
        self.quelle("q1", extra=("--set", "date=2026-10-25"))
        self.core("new", "concept", "k1", "--title", "Konzept", "--description", "D", "--sources", "q1")
        self.core("sources", "concepts/k1", "--add", "q1-z120=q1")
        self.core("body", "concepts/k1", "-", stdin="Erste Aussage.[^q1-z120]\n\n"
                  "[^q1-z120]: [Quelle q1](/sources/q1.md), Z. 120–135\n")
        html = self.py("result = wiki.reader_html()['concepts/k1']['html']")
        self.assertRegex(html, r"class=\"cite-ref\".*?, 2026, Z\. 120–135</a>")
        refs = self.py("result = [r['key'] for r in wiki.reader_html()['concepts/k1']['refs']]")
        self.assertEqual(refs, ["q1"])


class ProfilDokumentation(WikiTest):
    profile = "dokumentation"

    def test_specification_und_dataset_erlaubt(self):
        for slug, fmt in (("spec", "specification"), ("daten", "dataset")):
            datei = self.datei(f"{slug}.md")
            self.core("capture", slug, "--url", "https://example.org", "--file", str(datei), "--license", "MIT")
            self.core("new", "source", slug, "--title", slug, "--description", "D", "--access", "fulltext",
                      "--resource", "https://example.org", "--set", f"raw_packet=raw/{slug}", "--set", f"format={fmt}")
            self.assertNotIn("enum_invalid", self.lint_codes(f"sources/{slug}"))
        self.core("new", "source", "falsch", "--title", "F", "--description", "D", "--access", "citation",
                  "--set", "format=video")
        self.assertIn("enum_invalid", self.lint_codes("sources/falsch"))
