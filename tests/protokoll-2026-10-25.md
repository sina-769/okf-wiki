<!-- Protokoll eines Nachbau-Tests. Erzeugt von tests/nachbau.sh im Container aus tests/Dockerfile. -->

# Nachbau-Protokoll 2026-10-25

**Ergebnis: 31 von 31 Pflichtschritten bestanden, 0 fehlgeschlagen; 1 optionaler Schritt übersprungen**
(echte Claude-Sitzung, braucht `CLAUDE_CODE_OAUTH_TOKEN`).

Wie der Lauf entstand:

- Umgebung: frischer Container `node:22-bookworm-slim` (Digest im Dockerfile) mit git, curl,
  Claude Code 2.1.291 (npm) und uv 0.12.7, Benutzer ohne `~/.claude`, ohne Python, ohne Login.
  OrbStack auf macOS (aarch64), Container mit `--cap-drop ALL`, `--security-opt no-new-privileges`,
  2 CPU, 2 GB.
- Aufruf, aus der Wurzel des Repos:

  ```bash
  docker build -t okf-wiki-nachbau -f plugins/okf-wiki/tests/Dockerfile plugins/okf-wiki/tests
  docker run --rm --cap-drop ALL --security-opt no-new-privileges \
    -v "$PWD:/src:ro" -v "$PWD/.nachbau:/out" okf-wiki-nachbau /src /out/lauf-$(date +%H%M%S)
  ```

- Der Container klont den Commit unten aus `/src` und installiert das Plugin aus dem Klon
  (`claude plugin marketplace add <klon>/plugins/okf-wiki`, `claude plugin install okf-wiki@okf-wiki`).
- Demo-Quellen über die GitHub-API, auf Commit gepinnt, per SHA-256 geprüft: OKF-v0.2-Spezifikation
  (Apache-2.0) und README von pi-llm-wiki (MIT). Sie liegen nur im Testordner, nicht im Repo.
- Die Hooks laufen mit genau den Befehlen aus `hooks/hooks.json`, mit gesetztem `CLAUDE_PLUGIN_ROOT` und
  `CLAUDE_PROJECT_DIR` und einem Ereignis-JSON auf stdin, wie Claude Code sie startet. Dass Claude Code die
  vier Hooks aus dem Plugin lädt, zeigt Schritt 4 (`claude plugin details`).
- Zusätzlich auf dem Mac (nicht protokolliert): derselbe Test mit leerem `HOME` und leerem uv-Cache,
  31 bestanden; und die Installation über einen zweiten Marketplace, der das Plugin aus einem
  Unterordner einbindet (`"source": "./plugins/okf-wiki"`); deren Plugin-Cache ist dateigleich mit dem
  Plugin-Ordner.

---


Beginn: 2026-10-25T08:17:12Z · Marketplace-Quelle: `/home/tester/checkout/plugins/okf-wiki` · Repo-Commit: `4993872f27afad6f0f21a79586523f0c829d6966`

## Umgebung

### 1. Werkzeuge und leere Ausgangslage

`08:17:12Z` · Exit 0 · bestanden

```text
$ 
uname -srm; echo "HOME=$HOME"
echo "claude $(claude --version)"; uv --version; git --version | head -1
command -v python3 >/dev/null && echo "python3: $(python3 --version)" || echo "python3: keins im PATH"
test ! -e "$HOME/.claude/plugins/installed_plugins.json" && echo "keine Plugins installiert"
test ! -e "$HOME/.claude/skills/okf-wiki" && echo "kein Skill-Ordner okf-wiki"
Linux 7.2.12-orbstack-00394-gbecdd6130068 aarch64
HOME=/home/tester
claude 2.1.291 (Claude Code)
uv 0.12.7 (aarch64-unknown-linux-musl)
git version 2.39.5
python3: keins im PATH
keine Plugins installiert
kein Skill-Ordner okf-wiki
```

## Installation

### 2. Marketplace hinzufügen

`08:17:12Z` · Exit 0 · bestanden

```text
$ claude plugin marketplace add '/home/tester/checkout/plugins/okf-wiki'
Adding marketplace…✔ Successfully added marketplace: okf-wiki (declared in user settings)
```

### 3. Plugin installieren

`08:17:13Z` · Exit 0 · bestanden

```text
$ claude plugin install okf-wiki@okf-wiki
Installing plugin "okf-wiki@okf-wiki"...✔ Successfully installed plugin: okf-wiki@okf-wiki (scope: user)
```

### 4. Bestandteile des installierten Plugins

`08:17:13Z` · Exit 0 · bestanden

```text
$ claude plugin details okf-wiki@okf-wiki | sed -n '1,12p'
okf-wiki 0.1.0
  Description: Wissens-Wikis im Open Knowledge Format v0.2 nach dem pi-llm-wiki-Muster, mit Belegpflicht, Lint, Hooks und HTML-Dashboard. Braucht uv.
  Source: okf-wiki@okf-wiki

Component inventory
  Skills (1)  okf-wiki
  Agents (0)
  Hooks (4)  SessionStart, PreToolUse, PostToolUse, Stop  (harness-only — no model context cost)
  MCP servers (0)
  LSP servers (0)

Projected token cost
```

### 5. Installierte Dateien (Plugin-Cache)

`08:17:13Z` · Exit 0 · bestanden

```text
$ test -n '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0' && cd '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0' && find . -type f | sort && cat .claude-plugin/plugin.json
./.claude-plugin/marketplace.json
./.claude-plugin/plugin.json
./NOTICE.md
./README.md
./hooks/hooks.json
./skills/okf-wiki/SKILL.md
./skills/okf-wiki/docs/konfiguration.md
./skills/okf-wiki/hooks/okf_hook.py
./skills/okf-wiki/hooks/settings.example.json
./skills/okf-wiki/okfwiki.py
./skills/okf-wiki/profiles/default.toml
./skills/okf-wiki/templates/apa.csl
./skills/okf-wiki/templates/dashboard.html
./skills/okf-wiki/templates/fonts/OFL-IBM-Plex.txt
./skills/okf-wiki/templates/fonts/OFL-JetBrains-Mono.txt
./skills/okf-wiki/templates/fonts/README.md
./skills/okf-wiki/templates/fonts/ibmplexsans-regular.woff2
./skills/okf-wiki/templates/fonts/ibmplexsans-semibold.woff2
./skills/okf-wiki/templates/fonts/ibmplexserif-regular.woff2
./skills/okf-wiki/templates/fonts/jetbrainsmono-regular.woff2
./tests/Dockerfile
./tests/container-start.sh
./tests/nachbau.sh
./tests/protokoll-2026-10-25.md
{
  "name": "okf-wiki",
  "version": "0.1.0",
  "description": "Wissens-Wikis im Open Knowledge Format v0.2 nach dem pi-llm-wiki-Muster: Quellen unveränderlich erfassen, Karten mit Belegpflicht anlegen, Indexe und Log generieren, Lint, Prüfvermerke, Lizenz- und Nutzungsrechte je Quelle, APA/CSL/RIS-Export und ein HTML-Dashboard (Netz, Lernpfad, Glossar, offene Stellen, Leseansicht). Skill plus Hooks (Status, Schreibschutz, Ereignisprotokoll, Rebuild); braucht uv.",
  "author": {
    "name": "sina-769",
    "url": "https://github.com/sina-769"
  },
  "keywords": ["wiki", "knowledge-base", "okf", "open-knowledge-format", "llm-wiki", "citations", "provenance", "dashboard"]
}
```

### 6. Manifest streng prüfen

`08:17:13Z` · Exit 0 · bestanden

```text
$ claude plugin validate --strict '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/.claude-plugin/plugin.json'
Validating plugin manifest: /home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/.claude-plugin/plugin.json

✔ Validation passed
```

## Demo-Wiki

### 7. Kern starten (uv holt Python ≥ 3.11, PyYAML, Markdown)

`08:17:16Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' --version
okf-wiki 0.1.0
```

### 8. Python, das uv dafür nutzt

`08:17:16Z` · Exit 0 · bestanden

```text
$ uv python find && uv python list --only-installed
/home/tester/.local/share/uv/python/cpython-3.14-linux-aarch64-gnu/bin/python3.14
cpython-3.14.7-linux-aarch64-gnu    /home/tester/.local/share/uv/python/cpython-3.14-linux-aarch64-gnu/bin/python3.14
```

### 9. Wiki anlegen (Profil default)

`08:17:16Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' init --profile default && ls -a && cat wiki/.events.jsonl
angelegt: wiki.toml, Bundle wiki/ – Titel und Typen in wiki.toml anpassen
.
..
wiki
wiki.toml
{"ts": "2026-10-25T08:17:16Z", "kind": "init", "page": ".", "by": "claude-code/claude-opus-5-5", "detail": "Bundle angelegt (Profil default, okf-wiki 0.1.0)"}
```

### 10. OKF-v0.2-Spezifikation über die GitHub-API holen (Apache-2.0)

`08:17:17Z` · Exit 0 · bestanden

```text
$ curl -sf -H 'Accept: application/vnd.github.raw' 'https://api.github.com/repos/GoogleCloudPlatform/knowledge-catalog/contents/okf/SPEC.md?ref=a8291a1a656669b8766fd4ff0f985505fb955e94' -o '$WORK/downloads/SPEC.md' && sha_ok 26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101 '$WORK/downloads/SPEC.md'
$WORK/downloads/SPEC.md: SHA-256 26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101 stimmt
```

### 11. README von pi-llm-wiki über die GitHub-API holen (MIT)

`08:17:17Z` · Exit 0 · bestanden

```text
$ curl -sf -H 'Accept: application/vnd.github.raw' 'https://api.github.com/repos/zosmaai/pi-llm-wiki/contents/README.md?ref=46bd677041ba01f0298e5afc22e6a8b592f5f835' -o '$WORK/downloads/README.md' && sha_ok cac7184ae31a6bd881e5362326200c899f8d58487134d28e1f11d5f0bc4466c8 '$WORK/downloads/README.md'
$WORK/downloads/README.md: SHA-256 cac7184ae31a6bd881e5362326200c899f8d58487134d28e1f11d5f0bc4466c8 stimmt
```

### 12. Quelle erfassen: okf-v0-2-spec

`08:17:17Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' capture okf-v0-2-spec   --url 'https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/a8291a1a656669b8766fd4ff0f985505fb955e94/okf/SPEC.md' --file '$WORK/downloads/SPEC.md' --commit a8291a1a656669b8766fd4ff0f985505fb955e94   --license Apache-2.0 --license-url https://www.apache.org/licenses/LICENSE-2.0 --note 'OKF v0.2, Spezifikation'   && cat raw/okf-v0-2-spec/manifest.json
erfasst: raw/okf-v0-2-spec (1 Datei(en))
{
  "id": "okf-v0-2-spec",
  "url": "https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/a8291a1a656669b8766fd4ff0f985505fb955e94/okf/SPEC.md",
  "retrieved_at": "2026-10-25T08:17:17Z",
  "retrieved_by": "claude-code/claude-opus-5-5",
  "commit": "a8291a1a656669b8766fd4ff0f985505fb955e94",
  "license": {
    "name": "Apache-2.0",
    "url": "https://www.apache.org/licenses/LICENSE-2.0"
  },
  "note": "OKF v0.2, Spezifikation",
  "files": [
    {
      "path": "original/SPEC.md",
      "sha256": "26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101",
      "bytes": 37748,
      "source_path": null
    }
  ]
}
```

### 13. Quelle erfassen: pi-llm-wiki

`08:17:17Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' capture pi-llm-wiki   --url 'https://github.com/zosmaai/pi-llm-wiki/blob/46bd677041ba01f0298e5afc22e6a8b592f5f835/README.md' --file '$WORK/downloads/README.md' --commit 46bd677041ba01f0298e5afc22e6a8b592f5f835   --license MIT --license-url 'https://github.com/zosmaai/pi-llm-wiki/blob/46bd677041ba01f0298e5afc22e6a8b592f5f835/LICENSE' --note 'pi-llm-wiki, README'   && ls -l raw/pi-llm-wiki/original
erfasst: raw/pi-llm-wiki (1 Datei(en))
total 32
-r--r--r-- 1 tester tester 28856 Oct 25 08:17 README.md
```

### 14. Quellenkarte anlegen: okf-v0-2-spec

`08:17:17Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' new source okf-v0-2-spec   --title 'Open Knowledge Format (OKF), Version 0.2'   --description 'Spezifikation eines Formats für Wissensbündel aus Markdown-Dateien mit YAML-Frontmatter.'   --access fulltext --resource 'https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/a8291a1a656669b8766fd4ff0f985505fb955e94/okf/SPEC.md'   --set raw_packet=raw/okf-v0-2-spec --set format=specification --set date=2026-10-24 --fundweg person   --set 'license={name: Apache-2.0, url: "https://www.apache.org/licenses/LICENSE-2.0"}'
angelegt: wiki/sources/okf-v0-2-spec.md
```

### 15. Quellenkarte anlegen: pi-llm-wiki

`08:17:17Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' new source pi-llm-wiki   --title 'pi-llm-wiki (README)'   --description 'Erweiterung und MCP-Server für ein selbstgepflegtes LLM-Wiki nach dem Muster von Andrej Karpathy.'   --access fulltext --resource 'https://github.com/zosmaai/pi-llm-wiki/blob/46bd677041ba01f0298e5afc22e6a8b592f5f835/README.md'   --set raw_packet=raw/pi-llm-wiki --set format=documentation --set date=2026-10-09 --fundweg person   --set 'license={name: MIT, url: "https://github.com/zosmaai/pi-llm-wiki/blob/46bd677041ba01f0298e5afc22e6a8b592f5f835/LICENSE"}'
angelegt: wiki/sources/pi-llm-wiki.md
```

### 16. Konzeptkarte anlegen, die beide Quellen nutzt

`08:17:17Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' new concept llm-wiki-im-okf   --title 'LLM-Wiki im Open Knowledge Format'   --description 'Wie das LLM-Wiki-Muster und das Open Knowledge Format zusammenpassen.' --sources okf-v0-2-spec,pi-llm-wiki   --set domain=wissensorganisation --set 'aliases=[LLM Wiki, OKF-Wiki]'
angelegt: wiki/concepts/llm-wiki-im-okf.md
```

### 17. Seiteninhalte setzen (body)

`08:17:18Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' body sources/okf-v0-2-spec '$WORK/okf.md'   && uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' body sources/pi-llm-wiki '$WORK/pi.md'   && uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' body concepts/llm-wiki-im-okf '$WORK/konzept.md' && cat wiki/concepts/llm-wiki-im-okf.md
aktualisiert: wiki/sources/okf-v0-2-spec.md
aktualisiert: wiki/sources/pi-llm-wiki.md
aktualisiert: wiki/concepts/llm-wiki-im-okf.md
---
type: concept
title: LLM-Wiki im Open Knowledge Format
description: Wie das LLM-Wiki-Muster und das Open Knowledge Format zusammenpassen.
status: draft
tags: []
sources:
- {id: okf-v0-2-spec, resource: /sources/okf-v0-2-spec.md}
- {id: pi-llm-wiki, resource: /sources/pi-llm-wiki.md}
domain: wissensorganisation
aliases: [LLM Wiki, OKF-Wiki]
generated: {by: claude-code/claude-opus-5-5, at: '2026-10-25T08:17:17Z'}
---

# LLM-Wiki im Open Knowledge Format

pi-llm-wiki folgt dem LLM-Wiki-Muster von Andrej Karpathy und erfasst Quellen unveränderlich.[^pi-llm-wiki]
Das Open Knowledge Format verlangt im Frontmatter nur `type`, alles Weitere ist Profil.[^okf-v0-2-spec]

Quellen: [OKF v0.2](/sources/okf-v0-2-spec.md) und [pi-llm-wiki](/sources/pi-llm-wiki.md).

[^okf-v0-2-spec]: [Open Knowledge Format (OKF), Version 0.2](/sources/okf-v0-2-spec.md)
[^pi-llm-wiki]: [pi-llm-wiki (README)](/sources/pi-llm-wiki.md)
```

### 18. rebuild

`08:17:18Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' rebuild && cat wiki/index.md
Projektionen neu erzeugt: 4 Datei(en) geändert
---
okf_version: "0.2"
---

# Wiki – zuerst lesen

# Bereiche

* [Synthesen](syntheses/) - Querschnitt über mehrere Quellen (0 Seiten)
* [Analysen](analyses/) - Dauerhafte Antworten und Prüfaufträge (0 Seiten)
* [Konzepte](concepts/) - Begriffe, Mechanismen und Konventionen (1 Seiten)
* [Entitäten](entities/) - Organisationen, Projekte, Datenquellen, Personen (0 Seiten)
* [Quellen](sources/) - Je eine Karte pro Quelle (2 Seiten)
```

### 19. rebuild --check (nichts mehr zu tun)

`08:17:18Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' rebuild --check

```

### 20. lint (0 Fehler verlangt)

`08:17:18Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' lint; rc=$?; uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' lint --json | grep -c '"severity": "error"' | sed 's/^/Fehler: /'; exit $rc

3 Seiten · 0 Fehler · 0 Warnungen · 0 Hinweise
Fehler: 0
```

### 21. status

`08:17:18Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' status
Bundle: wiki (3 Seiten)
Seiten nach Typ: concept 1, source 2
draft: 3 · veraltet: 0 · offene [!todo]: 0
Vertrauen: unverified 3
Rohquellen ohne Karte: keine
Fundweg der Quellen: Von der Person 2 (Modellvorschlag 0 %)
Ereignisse: 9, zuletzt 2026-10-25T08:17:18Z (wiki/.events.jsonl)
```

### 22. dashboard

`08:17:18Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' dashboard && ls -l build/wiki-dashboard.html   && echo "Seiten im Dashboard: $(grep -o 'llm-wiki-im-okf' build/wiki-dashboard.html | wc -l) Treffer für llm-wiki-im-okf"   && ! grep -Eo '<(script|img|iframe)[^>]+src=.https?://|<link[^>]+href=.https?://|url\(.?https?://' build/wiki-dashboard.html   && echo 'lädt nichts aus dem Netz nach (kein script/img/iframe/link/url() auf http)'
Dashboard: $WORK/demo-wiki/build/wiki-dashboard.html
-rw-r--r-- 1 tester tester 498862 Oct 25 08:17 build/wiki-dashboard.html
Seiten im Dashboard: 11 Treffer für llm-wiki-im-okf
lädt nichts aus dem Netz nach (kein script/img/iframe/link/url() auf http)
```

### 23. Rohquelle bleibt unverändert (SHA-256)

`08:17:18Z` · Exit 0 · bestanden

```text
$ sha_ok 26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101 raw/okf-v0-2-spec/original/SPEC.md   && sha_ok cac7184ae31a6bd881e5362326200c899f8d58487134d28e1f11d5f0bc4466c8 raw/pi-llm-wiki/original/README.md
raw/okf-v0-2-spec/original/SPEC.md: SHA-256 26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101 stimmt
raw/pi-llm-wiki/original/README.md: SHA-256 cac7184ae31a6bd881e5362326200c899f8d58487134d28e1f11d5f0bc4466c8 stimmt
```

## Hooks, wie Claude Code sie aus dem Plugin startet

### 24. hooks.json: Befehle

`08:17:18Z` · Exit 0 · bestanden

```text
$ grep -o '"command": *".*"' '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/hooks/hooks.json' | sed 's/^"command": *//'
"uv run --quiet --script \"${CLAUDE_PLUGIN_ROOT}/skills/okf-wiki/hooks/okf_hook.py\" session-start 2>/dev/null || true"
"uv run --quiet --script \"${CLAUDE_PLUGIN_ROOT}/skills/okf-wiki/hooks/okf_hook.py\" guard"
"uv run --quiet --script \"${CLAUDE_PLUGIN_ROOT}/skills/okf-wiki/hooks/okf_hook.py\" post-edit 2>/dev/null || true"
"uv run --quiet --script \"${CLAUDE_PLUGIN_ROOT}/skills/okf-wiki/hooks/okf_hook.py\" stop 2>/dev/null || true"
```

### 25. SessionStart im Demo-Wiki: Status als Kontext

`08:17:18Z` · Exit 0 · bestanden

```text
$ out=$(CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0 CLAUDE_PROJECT_DIR=$WORK/demo-wiki bash -c uv\ run\ --quiet\ --script\ \"\$\{CLAUDE_PLUGIN_ROOT\}/skills/okf-wiki/hooks/okf_hook.py\"\ session-start\ 2\>/dev/null\ \|\|\ true <<< \{\"hook_event_name\":\"SessionStart\"\,\"source\":\"startup\"\}); echo "$out"; grep -q 'OKF-v0.2-Wiki unter' <<< "$out"
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "OKF-v0.2-Wiki unter $WORK/demo-wiki/wiki: 3 Seiten (concept 1, source 2), davon 3 draft, 0 veraltet, 0 offene [!todo]. Letztes Ereignis: 2026-10-25T08:17:18Z. Vor inhaltlicher Arbeit wiki/index.md lesen und im Wiki suchen. Nicht direkt bearbeiten: wiki/.events.jsonl, wiki/**/index.md, wiki/log.md, raw/**, build/wiki-dashboard.html. Werkzeug: uv run --quiet /home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py (new, capture, verify, lint vor Abschluss)."}}
```

### 26. SessionStart ohne wiki.toml: keine Ausgabe

`08:17:18Z` · Exit 0 · bestanden

```text
$ out=$(CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0 CLAUDE_PROJECT_DIR=$WORK/ohne-wiki bash -c uv\ run\ --quiet\ --script\ \"\$\{CLAUDE_PLUGIN_ROOT\}/skills/okf-wiki/hooks/okf_hook.py\"\ session-start\ 2\>/dev/null\ \|\|\ true <<< \{\"hook_event_name\":\"SessionStart\"\,\"source\":\"startup\"\}); test -z "$out" && echo 'leer'
leer
```

### 27. PreToolUse: Write auf Rohquelle wird abgelehnt

`08:17:18Z` · Exit 0 · bestanden

```text
$ out=$(CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0 CLAUDE_PROJECT_DIR=$WORK/demo-wiki bash -c uv\ run\ --quiet\ --script\ \"\$\{CLAUDE_PLUGIN_ROOT\}/skills/okf-wiki/hooks/okf_hook.py\"\ guard <<< \{\"hook_event_name\":\"PreToolUse\"\,\"tool_name\":\"Write\"\,\"cwd\":\"$WORK/demo-wiki\"\,\"tool_input\":\{\"file_path\":\"$WORK/demo-wiki/raw/okf-v0-2-spec/original/SPEC.md\"\,\"content\":\"x\"\}\}); echo "$out"; grep -q '"permissionDecision": "deny"' <<< "$out"
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Geschützte Wiki-Datei: raw/okf-v0-2-spec/original/SPEC.md ist eine unveränderliche Rohquelle. Neue Quellen mit `uv run --quiet /home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py capture`, neue Fassung als <slug>-v2."}}
```

### 28. PreToolUse: Write auf wiki/index.md wird abgelehnt

`08:17:18Z` · Exit 0 · bestanden

```text
$ out=$(CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0 CLAUDE_PROJECT_DIR=$WORK/demo-wiki bash -c uv\ run\ --quiet\ --script\ \"\$\{CLAUDE_PLUGIN_ROOT\}/skills/okf-wiki/hooks/okf_hook.py\"\ guard <<< \{\"hook_event_name\":\"PreToolUse\"\,\"tool_name\":\"Write\"\,\"cwd\":\"$WORK/demo-wiki\"\,\"tool_input\":\{\"file_path\":\"$WORK/demo-wiki/wiki/index.md\"\,\"content\":\"x\"\}\}); echo "$out"; grep -q '"permissionDecision": "deny"' <<< "$out"
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Geschützte Wiki-Datei: wiki/index.md ist generiert. Inhalte in den Seiten ändern, dann `uv run --quiet /home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py rebuild`."}}
```

### 29. PreToolUse: Edit einer Karte ist erlaubt

`08:17:18Z` · Exit 0 · bestanden

```text
$ out=$(CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0 CLAUDE_PROJECT_DIR=$WORK/demo-wiki bash -c uv\ run\ --quiet\ --script\ \"\$\{CLAUDE_PLUGIN_ROOT\}/skills/okf-wiki/hooks/okf_hook.py\"\ guard <<< \{\"hook_event_name\":\"PreToolUse\"\,\"tool_name\":\"Edit\"\,\"cwd\":\"$WORK/demo-wiki\"\,\"tool_input\":\{\"file_path\":\"$WORK/demo-wiki/wiki/concepts/llm-wiki-im-okf.md\"\}\}); test -z "$out" && echo 'keine Einwände'
keine Einwände
```

### 30. PostToolUse: Edit einer Karte landet im Ereignisstrom

`08:17:18Z` · Exit 0 · bestanden

```text
$ vor=$(wc -l < '$WORK/demo-wiki/wiki/.events.jsonl'); CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0 CLAUDE_PROJECT_DIR=$WORK/demo-wiki bash -c uv\ run\ --quiet\ --script\ \"\$\{CLAUDE_PLUGIN_ROOT\}/skills/okf-wiki/hooks/okf_hook.py\"\ post-edit\ 2\>/dev/null\ \|\|\ true <<< \{\"hook_event_name\":\"PostToolUse\"\,\"tool_name\":\"Edit\"\,\"cwd\":\"$WORK/demo-wiki\"\,\"tool_input\":\{\"file_path\":\"$WORK/demo-wiki/wiki/concepts/llm-wiki-im-okf.md\"\}\}; nach=$(wc -l < '$WORK/demo-wiki/wiki/.events.jsonl'); echo "Ereignisse $vor -> $nach"; tail -1 '$WORK/demo-wiki/wiki/.events.jsonl'; test $nach -eq $((vor + 1))
Ereignisse 9 -> 10
{"ts": "2026-10-25T08:17:18Z", "kind": "edit", "page": "concepts/llm-wiki-im-okf", "by": "process:claude-code-hook", "detail": ""}
```

### 31. Stop: Rebuild läuft, danach ist rebuild --check leer

`08:17:18Z` · Exit 0 · bestanden

```text
$ CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0 CLAUDE_PROJECT_DIR=$WORK/demo-wiki bash -c uv\ run\ --quiet\ --script\ \"\$\{CLAUDE_PLUGIN_ROOT\}/skills/okf-wiki/hooks/okf_hook.py\"\ stop\ 2\>/dev/null\ \|\|\ true <<< \{\"hook_event_name\":\"Stop\"\}; cd '$WORK/demo-wiki' && uv run --quiet '/home/tester/.claude/plugins/cache/okf-wiki/okf-wiki/0.1.0/skills/okf-wiki/okfwiki.py' rebuild --check && tail -3 wiki/log.md
* **Quelle erfasst**: `raw/pi-llm-wiki` – pi-llm-wiki, README
* **Quelle erfasst**: `raw/okf-v0-2-spec` – OKF v0.2, Spezifikation
* **Initialisierung**: `.` – Bundle angelegt (Profil default, okf-wiki 0.1.0)
```

## Echte Claude-Sitzung (optional)

### 32. claude -p: Schreibversuch auf Rohquelle scheitert am Guard

übersprungen: kein CLAUDE_CODE_OAUTH_TOKEN; die Hook-Befehle oben laufen genau so, wie Claude Code sie startet

## Ergebnis

Ende: 2026-10-25T08:17:18Z · 32 Schritte: 31 bestanden, 0 fehlgeschlagen, 1 übersprungen.

