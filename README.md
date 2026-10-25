# okf-wiki

Claude-Code-Plugin für Wissens-Wikis im [Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/a8291a1a656669b8766fd4ff0f985505fb955e94/okf/SPEC.md)
(OKF), gepflegt nach dem LLM-Wiki-Muster von [pi-llm-wiki](https://github.com/zosmaai/pi-llm-wiki):
Markdown-Karten mit YAML-Frontmatter, unveränderliche Rohquellen, ein Ereignisstrom, generierte Indexe,
Belegpflicht für jede Sachaussage und ein HTML-Dashboard zum Lesen und Lernen.

- **Skill** `okf-wiki`: Arbeitsweise für Claude (Recall → Capture → Ingest → Retro → Lint), Beleg-,
  Lizenz- und Vertrauensregeln.
- **Kern** `skills/okf-wiki/okfwiki.py`: CLI und Python-Bibliothek (`init`, `capture`, `new`, `body`,
  `rebuild`, `lint`, `verify`, `lizenz`, `rechte`, `dashboard` …). Alles Projektspezifische steht in
  einer `wiki.toml` im Projekt; ohne `wiki.toml` schreibt der Kern nichts.
- **Hooks**: Status beim Sitzungsstart, Schreibschutz für Rohquellen, Ereignisstrom und generierte
  Dateien, Ereignisprotokoll bei Write/Edit, Rebuild beim Stop. Sie wirken nur in Projekten mit
  `wiki.toml`.
- **Dashboard**: eine einzelne HTML-Datei ohne Nachladen aus dem Netz (Netzgraph, Lernpfad, Glossar,
  offene Stellen, Leseansicht mit Belegen und Literatur nach APA 7).

Die Texte von Skill und Dokumentation sind deutsch.

## Voraussetzungen

| Was | Version im Nachbau-Test | Wozu |
|---|---|---|
| [Claude Code](https://code.claude.com/docs) | 2.1.291 | Plugin, Skill, Hooks |
| [uv](https://docs.astral.sh/uv/) | 0.12.7 | startet Kern und Hooks; holt Python ≥ 3.11 und die Pakete aus dem Skriptkopf (PEP 723) |
| Python | ≥ 3.11, von uv geholt, falls keins da ist | — |
| PyYAML ≥ 6.0, Markdown ≥ 3.5 | von uv beim ersten Start geholt | Frontmatter, Leseansicht |

Netz braucht der Kern beim ersten Start (PyPI, ggf. Python-Download durch uv) und sonst nur in Befehlen,
die dafür da sind: `new source --doi/--pmid/--arxiv` und `lizenz --fetch` (Crossref, PubMed, Europe PMC,
DataCite, OpenAlex, arXiv). Getestet unter macOS und Debian 12 (Container).

## Installation

```bash
claude plugin marketplace add <ordner-oder-repo>
claude plugin install okf-wiki@okf-wiki
```

`<ordner-oder-repo>` ist dieser Ordner (er enthält `.claude-plugin/marketplace.json`), ein Git-Klon davon
oder später das veröffentlichte Repo. Danach Claude Code neu starten (oder `/reload-plugins`).

Ohne Plugin geht es auch als Skill-Ordner: `skills/okf-wiki/` nach `~/.claude/skills/okf-wiki/` kopieren
und `skills/okf-wiki/hooks/settings.example.json` in die `.claude/settings.json` des Projekts übernehmen.
Nicht beides zugleich, sonst laufen die Hooks doppelt.

## Erste Schritte

Im Projektordner (Pfad zum Kern aus der Plugin-Installation):

```bash
OKF=$(ls -d ~/.claude/plugins/cache/okf-wiki/okf-wiki/*/skills/okf-wiki | tail -1)/okfwiki.py
uv run --quiet "$OKF" init --profile default        # wiki.toml und wiki/ anlegen
uv run --quiet "$OKF" capture <slug> --url URL --file PFAD --license NAME --license-url URL
uv run --quiet "$OKF" new source <slug> --title … --description … --access fulltext --set raw_packet=raw/<slug>
uv run --quiet "$OKF" rebuild && uv run --quiet "$OKF" lint
uv run --quiet "$OKF" dashboard                     # build/wiki-dashboard.html
```

Oder in Claude Code einfach um Wiki-Arbeit bitten; der Skill kennt die Befehle. Alle Befehle und
`wiki.toml`-Schlüssel: [skills/okf-wiki/docs/konfiguration.md](skills/okf-wiki/docs/konfiguration.md).

## Nachbau-Test

[tests/nachbau.sh](tests/nachbau.sh) installiert das Plugin in einer frischen Umgebung aus einem
Marketplace, legt ein Demo-Wiki aus zwei frei lizenzierten Quellen an (OKF-Spezifikation, Apache-2.0;
README von pi-llm-wiki, MIT; beide über die GitHub-API auf einen Commit gepinnt und per SHA-256
geprüft), erfasst sie, schreibt Karten, führt `rebuild`, `lint` und `dashboard` aus und ruft die Hooks
mit genau den Befehlen aus `hooks/hooks.json` auf. Jeder Schritt landet mit Befehl, Ausgabe und
Exit-Code in einem Protokoll.

```bash
docker build -t okf-wiki-nachbau -f tests/Dockerfile tests
docker run --rm -v "$PWD:/src:ro" -v "$PWD/.nachbau:/out" okf-wiki-nachbau /src /out/lauf-$(date +%H%M%S)
```

Letztes Protokoll: [tests/protokoll-2026-10-25.md](tests/protokoll-2026-10-25.md).

## Lizenz und Dank

Lizenz dieses Plugins: noch offen, wird vor der Veröffentlichung gewählt. Fremde Bestandteile und
Vorbilder mit ihren Lizenzen: [NOTICE.md](NOTICE.md).
