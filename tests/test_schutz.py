"""Gruppe 1: Schutzversprechen – stable nur durch Menschen, keine Symlinks als Rohquelle."""

import os

from .hilfe import WikiTest


class StableNurDurchMenschen(WikiTest):
    def setUp(self):
        super().setUp()
        self.quelle("q1")

    def test_verify_stable_ohne_human_wird_abgelehnt(self):
        done = self.core("verify", "sources/q1", "--by", "claude-code/claude-opus-5-5", "--status", "stable", ok=False)
        self.assertIn("human:", done.stderr)
        fm = self.fm("sources/q1")
        self.assertEqual(fm["status"], "draft")
        self.assertNotIn("verified", fm)

    def test_verify_stable_mit_human(self):
        self.core("verify", "sources/q1", "--by", "human:pruefer", "--status", "stable")
        fm = self.fm("sources/q1")
        self.assertEqual(fm["status"], "stable")
        self.assertEqual(fm["verified"][0]["by"], "human:pruefer")
        self.assertNotIn("stable_unverified", self.lint_codes("sources/q1"))

    def test_verify_ohne_status_durch_claude_bleibt_erlaubt(self):
        self.core("verify", "sources/q1", "--by", "claude-code/claude-opus-5-5", "--note", "Volltext geprüft")
        fm = self.fm("sources/q1")
        self.assertEqual(fm["status"], "draft")
        self.assertEqual(fm["verified"][0]["by"], "claude-code/claude-opus-5-5")

    def test_lint_stable_nur_mit_maschinenvermerk(self):
        self.core("verify", "sources/q1", "--by", "claude-code/claude-opus-5-5")
        self.py("wiki._write_frontmatter(wiki.page_path('sources/q1'), {'status': 'stable'})")
        self.assertIn("stable_unverified", self.lint_codes("sources/q1"))

    def test_lint_stable_ganz_ohne_vermerk(self):
        self.py("wiki._write_frontmatter(wiki.page_path('sources/q1'), {'status': 'stable'})")
        self.assertIn("stable_unverified", self.lint_codes("sources/q1"))


class KeineSymlinks(WikiTest):
    def test_symlink_wird_abgelehnt(self):
        echt = self.datei("echt.md")
        link = echt.with_name("verweis.md")
        os.symlink(echt, link)
        done = self.core("capture", "q-link", "--url", "https://example.org/x", "--file", str(link),
                         "--license", "MIT", ok=False)
        self.assertIn("Symlink", done.stderr)
        self.assertFalse((self.root / "raw" / "q-link").exists())

    def test_regulaere_datei_wird_erfasst(self):
        echt = self.datei("echt.md", "# Titel\n")
        self.core("capture", "q-echt", "--url", "https://example.org/x", "--file", str(echt), "--license", "MIT")
        kopie = self.root / "raw" / "q-echt" / "original" / "echt.md"
        self.assertEqual(kopie.read_text(encoding="utf-8"), "# Titel\n")
        self.assertEqual(kopie.stat().st_mode & 0o777, 0o444)
