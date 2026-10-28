<!-- Protokoll eines Nachbau-Tests. Erzeugt von tests/nachbau.sh im Container aus tests/Dockerfile. -->

# Nachbau-Protokoll 2026-10-28

**Ergebnis: 32 von 32 Schritten bestanden, 0 fehlgeschlagen, 0 übersprungen**, einschließlich der
echten Claude-Sitzung (`claude -p`, Schritt 32).

Wie der Lauf entstand:

- Getestet wurde Commit `3fdb7d7` des Repos claude-skills (okfw 0.2.0). Er unterscheidet sich in
  `plugins/okfw` nicht von `c3cb8e8` (okfw 0.2.0: Version und Änderungen); dazwischen änderte sich nur
  Material außerhalb des Plugins.
- Umgebung: frischer Container `node:22-bookworm-slim` (Digest im Dockerfile) mit git, curl,
  Claude Code 2.1.291 (npm) und uv 0.12.7, Benutzer ohne `~/.claude`, ohne Python, ohne Plugins.
  OrbStack auf macOS (aarch64), Container mit `--cap-drop ALL`, `--security-opt no-new-privileges`,
  ohne CPU- und Speichergrenze.
- Aufruf, aus der Wurzel des Repos; der Token für Schritt 32 kommt nur als Umgebungsvariable in den
  Container und steht nicht im Protokoll:

  ```bash
  docker build -t okfw-nachbau -f plugins/okfw/tests/Dockerfile plugins/okfw/tests
  docker run --rm --cap-drop ALL --security-opt no-new-privileges -e CLAUDE_CODE_OAUTH_TOKEN \
    -v "$PWD:/src:ro" -v "$PWD/plugins/okfw/.nachbau:/out" okfw-nachbau /src /out/lauf-0.2.0-claude
  ```

- Der Container klont `/src` noch einmal und installiert das Plugin aus diesem Klon
  (`claude plugin marketplace add <klon>/plugins/okfw`, `claude plugin install okfw@okfw`).
- Demo-Quellen über die GitHub-API, auf Commit gepinnt, per SHA-256 geprüft: OKF-v0.2-Spezifikation
  (Apache-2.0) und README von pi-llm-wiki (MIT). Sie liegen nur im Testordner, nicht im Repo.
- Die Hooks laufen in Schritt 24 bis 31 mit genau den Befehlen aus `hooks/hooks.json`, mit gesetztem
  `CLAUDE_PLUGIN_ROOT` und `CLAUDE_PROJECT_DIR` und einem Ereignis-JSON auf stdin, wie Claude Code sie
  startet. Schritt 32 zeigt es in einer echten Sitzung: Claude Code lädt die Hooks aus dem Plugin, der
  Guard lehnt den Write auf die Rohquelle ab, die Prüfsumme bleibt gleich.
- Ein Lauf kurz davor ohne Token bestand 31 von 31 Pflichtschritten und übersprang Schritt 32.

---


Beginn: 2026-10-28T05:26:12Z · Marketplace-Quelle: `/home/tester/checkout/plugins/okfw` · Repo-Commit: `3fdb7d79106140f69cf2919b0aff8a5fb5e39b2f`

## Umgebung

### 1. Werkzeuge und leere Ausgangslage

`05:26:12Z` · Exit 0 · bestanden

```text
$ 
uname -srm; echo "HOME=$HOME"
echo "claude $(claude --version)"; uv --version; git --version | head -1
command -v python3 >/dev/null && echo "python3: $(python3 --version)" || echo "python3: keins im PATH"
test ! -e "$HOME/.claude/plugins/installed_plugins.json" && echo "keine Plugins installiert"
test ! -e "$HOME/.claude/skills/okfw" && echo "kein Skill-Ordner okfw"
Linux 7.2.12-orbstack-00394-gbecdd6130068 aarch64
HOME=/home/tester
claude 2.1.291 (Claude Code)
uv 0.12.7 (aarch64-unknown-linux-musl)
git version 2.39.5
python3: keins im PATH
keine Plugins installiert
kein Skill-Ordner okfw
```

## Installation

### 2. Marketplace hinzufügen

`05:26:12Z` · Exit 0 · bestanden

```text
$ claude plugin marketplace add '/home/tester/checkout/plugins/okfw'
Adding marketplace…✔ Successfully added marketplace: okfw (declared in user settings)
```

### 3. Plugin installieren

`05:26:12Z` · Exit 0 · bestanden

```text
$ claude plugin install okfw@okfw
Installing plugin "okfw@okfw"...✔ Successfully installed plugin: okfw@okfw (scope: user)
```

### 4. Bestandteile des installierten Plugins

`05:26:12Z` · Exit 0 · bestanden

```text
$ claude plugin details okfw@okfw | sed -n '1,12p'
okfw 0.2.0
  Description: Wissens-Wikis im Open Knowledge Format v0.2 nach dem pi-llm-wiki-Muster, mit Belegpflicht, Lint, Hooks und HTML-Dashboard. Braucht uv.
  Source: okfw@okfw

Component inventory
  Skills (1)  okfw
  Agents (0)
  Hooks (4)  SessionStart, PreToolUse, PostToolUse, Stop  (harness-only — no model context cost)
  MCP servers (0)
  LSP servers (0)

Projected token cost
```

### 5. Installierte Dateien (Plugin-Cache)

`05:26:12Z` · Exit 0 · bestanden

```text
$ test -n '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0' && cd '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0' && find . -type f | sort && cat .claude-plugin/plugin.json
./.claude-plugin/marketplace.json
./.claude-plugin/plugin.json
./.gitignore
./CHANGELOG.md
./LICENSE
./NOTICE.md
./README.md
./docs/dashboard-lernpfad.png
./docs/dashboard-quellenkarte.png
./docs/dashboard-schichtengraph.png
./docs/dashboard-vorschau.png
./hooks/hooks.json
./skills/okfw/SKILL.md
./skills/okfw/docs/konfiguration.md
./skills/okfw/hooks/okf_hook.py
./skills/okfw/hooks/settings.example.json
./skills/okfw/local.example.md
./skills/okfw/okfw.py
./skills/okfw/profiles/default.toml
./skills/okfw/profiles/dokumentation.toml
./skills/okfw/templates/apa.csl
./skills/okfw/templates/dashboard.html
./skills/okfw/templates/fonts/OFL-IBM-Plex.txt
./skills/okfw/templates/fonts/OFL-JetBrains-Mono.txt
./skills/okfw/templates/fonts/README.md
./skills/okfw/templates/fonts/ibmplexsans-regular.woff2
./skills/okfw/templates/fonts/ibmplexsans-semibold.woff2
./skills/okfw/templates/fonts/ibmplexserif-regular.woff2
./skills/okfw/templates/fonts/jetbrainsmono-regular.woff2
./tests/Dockerfile
./tests/__init__.py
./tests/container-start.sh
./tests/hilfe.py
./tests/nachbau.sh
./tests/protokoll-2026-10-25.md
./tests/test_befehle.py
./tests/test_bestand.py
./tests/test_doku_code.py
./tests/test_reibung.py
./tests/test_schutz.py
… (gekürzt)
```

### 6. Manifest streng prüfen

`05:26:13Z` · Exit 0 · bestanden

```text
$ claude plugin validate --strict '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/.claude-plugin/plugin.json'
Validating plugin manifest: /home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/.claude-plugin/plugin.json

✔ Validation passed
```

## Demo-Wiki

### 7. Kern starten (uv holt Python ≥ 3.11, PyYAML, Markdown)

`05:26:19Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' --version
okfw 0.2.0
```

### 8. Python, das uv dafür nutzt

`05:26:20Z` · Exit 0 · bestanden

```text
$ uv python find && uv python list --only-installed
/home/tester/.local/share/uv/python/cpython-3.14-linux-aarch64-gnu/bin/python3.14
cpython-3.14.7-linux-aarch64-gnu    /home/tester/.local/share/uv/python/cpython-3.14-linux-aarch64-gnu/bin/python3.14
```

### 9. Wiki anlegen (Profil default)

`05:26:20Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' init --profile default && ls -a && cat wiki/.events.jsonl
angelegt: wiki.toml, Bundle wiki/ – Titel und Typen in wiki.toml anpassen
.
..
wiki
wiki.toml
{"ts": "2026-10-28T05:26:20Z", "kind": "init", "page": ".", "by": "claude-code/claude-opus-5-5", "detail": "Bundle angelegt (Profil default, okfw 0.2.0)"}
```

### 10. OKF-v0.2-Spezifikation über die GitHub-API holen (Apache-2.0)

`05:26:20Z` · Exit 0 · bestanden

```text
$ curl -sf -H 'Accept: application/vnd.github.raw' 'https://api.github.com/repos/GoogleCloudPlatform/knowledge-catalog/contents/okf/SPEC.md?ref=a8291a1a656669b8766fd4ff0f985505fb955e94' -o '$WORK/downloads/SPEC.md' && sha_ok 26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101 '$WORK/downloads/SPEC.md'
$WORK/downloads/SPEC.md: SHA-256 26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101 stimmt
```

### 11. README von pi-llm-wiki über die GitHub-API holen (MIT)

`05:26:21Z` · Exit 0 · bestanden

```text
$ curl -sf -H 'Accept: application/vnd.github.raw' 'https://api.github.com/repos/zosmaai/pi-llm-wiki/contents/README.md?ref=46bd677041ba01f0298e5afc22e6a8b592f5f835' -o '$WORK/downloads/README.md' && sha_ok cac7184ae31a6bd881e5362326200c899f8d58487134d28e1f11d5f0bc4466c8 '$WORK/downloads/README.md'
$WORK/downloads/README.md: SHA-256 cac7184ae31a6bd881e5362326200c899f8d58487134d28e1f11d5f0bc4466c8 stimmt
```

### 12. Quelle erfassen: okf-v0-2-spec

`05:26:21Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' capture okf-v0-2-spec   --url 'https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/a8291a1a656669b8766fd4ff0f985505fb955e94/okf/SPEC.md' --file '$WORK/downloads/SPEC.md' --commit a8291a1a656669b8766fd4ff0f985505fb955e94   --license Apache-2.0 --license-url https://www.apache.org/licenses/LICENSE-2.0 --note 'OKF v0.2, Spezifikation'   && cat raw/okf-v0-2-spec/manifest.json
erfasst: raw/okf-v0-2-spec (1 Datei(en))
{
  "id": "okf-v0-2-spec",
  "url": "https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/a8291a1a656669b8766fd4ff0f985505fb955e94/okf/SPEC.md",
  "retrieved_at": "2026-10-28T05:26:21Z",
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

`05:26:21Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' capture pi-llm-wiki   --url 'https://github.com/zosmaai/pi-llm-wiki/blob/46bd677041ba01f0298e5afc22e6a8b592f5f835/README.md' --file '$WORK/downloads/README.md' --commit 46bd677041ba01f0298e5afc22e6a8b592f5f835   --license MIT --license-url 'https://github.com/zosmaai/pi-llm-wiki/blob/46bd677041ba01f0298e5afc22e6a8b592f5f835/LICENSE' --note 'pi-llm-wiki, README'   && ls -l raw/pi-llm-wiki/original
erfasst: raw/pi-llm-wiki (1 Datei(en))
total 32
-r--r--r-- 1 tester tester 28856 Oct 28 05:26 README.md
```

### 14. Quellenkarte anlegen: okf-v0-2-spec

`05:26:21Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' new source okf-v0-2-spec   --title 'Open Knowledge Format (OKF), Version 0.2'   --description 'Spezifikation eines Formats für Wissensbündel aus Markdown-Dateien mit YAML-Frontmatter.'   --access fulltext --resource 'https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/a8291a1a656669b8766fd4ff0f985505fb955e94/okf/SPEC.md'   --set raw_packet=raw/okf-v0-2-spec --set format=specification --set date=2026-10-24 --fundweg person   --set 'license={name: Apache-2.0, url: "https://www.apache.org/licenses/LICENSE-2.0"}'
angelegt: wiki/sources/okf-v0-2-spec.md
```

### 15. Quellenkarte anlegen: pi-llm-wiki

`05:26:21Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' new source pi-llm-wiki   --title 'pi-llm-wiki (README)'   --description 'Erweiterung und MCP-Server für ein selbstgepflegtes LLM-Wiki nach dem Muster von Andrej Karpathy.'   --access fulltext --resource 'https://github.com/zosmaai/pi-llm-wiki/blob/46bd677041ba01f0298e5afc22e6a8b592f5f835/README.md'   --set raw_packet=raw/pi-llm-wiki --set format=documentation --set date=2026-10-09 --fundweg person   --set 'license={name: MIT, url: "https://github.com/zosmaai/pi-llm-wiki/blob/46bd677041ba01f0298e5afc22e6a8b592f5f835/LICENSE"}'
angelegt: wiki/sources/pi-llm-wiki.md
```

### 16. Konzeptkarte anlegen, die beide Quellen nutzt

`05:26:21Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' new concept llm-wiki-im-okf   --title 'LLM-Wiki im Open Knowledge Format'   --description 'Wie das LLM-Wiki-Muster und das Open Knowledge Format zusammenpassen.' --sources okf-v0-2-spec,pi-llm-wiki   --set domain=wissensorganisation --set 'aliases=[LLM Wiki, Open Knowledge Format Wiki]'
angelegt: wiki/concepts/llm-wiki-im-okf.md
```

### 17. Seiteninhalte setzen (body)

`05:26:22Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' body sources/okf-v0-2-spec '$WORK/okf.md'   && uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' body sources/pi-llm-wiki '$WORK/pi.md'   && uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' body concepts/llm-wiki-im-okf '$WORK/konzept.md' && cat wiki/concepts/llm-wiki-im-okf.md
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
aliases: [LLM Wiki, Open Knowledge Format Wiki]
generated: {by: claude-code/claude-opus-5-5, at: '2026-10-28T05:26:22Z'}
---

# LLM-Wiki im Open Knowledge Format

pi-llm-wiki folgt dem LLM-Wiki-Muster von Andrej Karpathy und erfasst Quellen unveränderlich.[^pi-llm-wiki]
Das Open Knowledge Format verlangt im Frontmatter nur `type`, alles Weitere ist Profil.[^okf-v0-2-spec]

Quellen: [OKF v0.2](/sources/okf-v0-2-spec.md) und [pi-llm-wiki](/sources/pi-llm-wiki.md).

[^okf-v0-2-spec]: [Open Knowledge Format (OKF), Version 0.2](/sources/okf-v0-2-spec.md)
[^pi-llm-wiki]: [pi-llm-wiki (README)](/sources/pi-llm-wiki.md)
```

### 18. rebuild

`05:26:22Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' rebuild && cat wiki/index.md
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

`05:26:22Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' rebuild --check

```

### 20. lint (0 Fehler verlangt)

`05:26:22Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' lint; rc=$?; uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' lint --json | grep -c '"severity": "error"' | sed 's/^/Fehler: /'; exit $rc

3 Seiten · 0 Fehler · 0 Warnungen · 0 Hinweise
Fehler: 0
```

### 21. status

`05:26:22Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' status
Bundle: wiki (3 Seiten)
Seiten nach Typ: concept 1, source 2
draft: 3 · veraltet: 0 · offene [!todo]: 0
Vertrauen: unverified 3
Rohquellen ohne Karte: keine
Fundweg der Quellen: Von der Person 2 (Modellvorschlag 0 %)
Ereignisse: 9, zuletzt 2026-10-28T05:26:22Z (wiki/.events.jsonl)
```

### 22. dashboard

`05:26:22Z` · Exit 0 · bestanden

```text
$ uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' dashboard && ls -l build/wiki-dashboard.html   && echo "Seiten im Dashboard: $(grep -o 'llm-wiki-im-okf' build/wiki-dashboard.html | wc -l) Treffer für llm-wiki-im-okf"   && ! grep -Eo '<(script|img|iframe)[^>]+src=.https?://|<link[^>]+href=.https?://|url\(.?https?://' build/wiki-dashboard.html   && echo 'lädt nichts aus dem Netz nach (kein script/img/iframe/link/url() auf http)'
Dashboard: $WORK/demo-wiki/build/wiki-dashboard.html
-rw-r--r-- 1 tester tester 499589 Oct 28 05:26 build/wiki-dashboard.html
Seiten im Dashboard: 11 Treffer für llm-wiki-im-okf
lädt nichts aus dem Netz nach (kein script/img/iframe/link/url() auf http)
```

### 23. Rohquelle bleibt unverändert (SHA-256)

`05:26:22Z` · Exit 0 · bestanden

```text
$ sha_ok 26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101 raw/okf-v0-2-spec/original/SPEC.md   && sha_ok cac7184ae31a6bd881e5362326200c899f8d58487134d28e1f11d5f0bc4466c8 raw/pi-llm-wiki/original/README.md
raw/okf-v0-2-spec/original/SPEC.md: SHA-256 26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101 stimmt
raw/pi-llm-wiki/original/README.md: SHA-256 cac7184ae31a6bd881e5362326200c899f8d58487134d28e1f11d5f0bc4466c8 stimmt
```

## Hooks, wie Claude Code sie aus dem Plugin startet

### 24. hooks.json: Befehle

`05:26:22Z` · Exit 0 · bestanden

```text
$ grep -o '"command": *".*"' '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/hooks/hooks.json' | sed 's/^"command": *//'
"uv run --quiet --script \"${CLAUDE_PLUGIN_ROOT}/skills/okfw/hooks/okf_hook.py\" session-start 2>/dev/null || echo '{\"systemMessage\": \"okfw: Hook session-start ließ sich nicht starten (uv run --script)\"}'"
"uv run --quiet --script \"${CLAUDE_PLUGIN_ROOT}/skills/okfw/hooks/okf_hook.py\" guard"
"uv run --quiet --script \"${CLAUDE_PLUGIN_ROOT}/skills/okfw/hooks/okf_hook.py\" post-edit 2>/dev/null || echo '{\"systemMessage\": \"okfw: Hook post-edit ließ sich nicht starten (uv run --script)\"}'"
"uv run --quiet --script \"${CLAUDE_PLUGIN_ROOT}/skills/okfw/hooks/okf_hook.py\" stop 2>/dev/null || echo '{\"systemMessage\": \"okfw: Hook stop ließ sich nicht starten (uv run --script)\"}'"
```

### 25. SessionStart im Demo-Wiki: Status als Kontext

`05:26:23Z` · Exit 0 · bestanden

```text
$ out=$(CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0 CLAUDE_PROJECT_DIR=$WORK/demo-wiki bash -c $'uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}/skills/okfw/hooks/okf_hook.py" session-start 2>/dev/null || echo \'{"systemMessage": "okfw: Hook session-start lie\303\237 sich nicht starten (uv run --script)"}\'' <<< \{\"hook_event_name\":\"SessionStart\"\,\"source\":\"startup\"\}); echo "$out"; grep -q 'OKF-v0.2-Wiki unter' <<< "$out"
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "OKF-v0.2-Wiki unter $WORK/demo-wiki/wiki: 3 Seiten (concept 1, source 2), davon 3 draft, 0 veraltet, 0 offene [!todo]. Letztes Ereignis: 2026-10-28T05:26:22Z. Vor inhaltlicher Arbeit wiki/index.md lesen und im Wiki suchen. Nicht direkt bearbeiten: wiki/.events.jsonl, wiki/**/index.md, wiki/log.md, raw/**, build/wiki-dashboard.html. Werkzeug: uv run --quiet /home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py (new, capture, verify, lint vor Abschluss)."}}
```

### 26. SessionStart ohne wiki.toml: keine Ausgabe

`05:26:23Z` · Exit 0 · bestanden

```text
$ out=$(CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0 CLAUDE_PROJECT_DIR=$WORK/ohne-wiki bash -c $'uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}/skills/okfw/hooks/okf_hook.py" session-start 2>/dev/null || echo \'{"systemMessage": "okfw: Hook session-start lie\303\237 sich nicht starten (uv run --script)"}\'' <<< \{\"hook_event_name\":\"SessionStart\"\,\"source\":\"startup\"\}); test -z "$out" && echo 'leer'
leer
```

### 27. PreToolUse: Write auf Rohquelle wird abgelehnt

`05:26:23Z` · Exit 0 · bestanden

```text
$ out=$(CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0 CLAUDE_PROJECT_DIR=$WORK/demo-wiki bash -c uv\ run\ --quiet\ --script\ \"\$\{CLAUDE_PLUGIN_ROOT\}/skills/okfw/hooks/okf_hook.py\"\ guard <<< \{\"hook_event_name\":\"PreToolUse\"\,\"tool_name\":\"Write\"\,\"cwd\":\"$WORK/demo-wiki\"\,\"tool_input\":\{\"file_path\":\"$WORK/demo-wiki/raw/okf-v0-2-spec/original/SPEC.md\"\,\"content\":\"x\"\}\}); echo "$out"; grep -q '"permissionDecision": "deny"' <<< "$out"
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Geschützte Wiki-Datei: raw/okf-v0-2-spec/original/SPEC.md ist eine unveränderliche Rohquelle. Neue Quellen mit `uv run --quiet /home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py capture`, neue Fassung als <slug>-v2."}}
```

### 28. PreToolUse: Write auf wiki/index.md wird abgelehnt

`05:26:23Z` · Exit 0 · bestanden

```text
$ out=$(CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0 CLAUDE_PROJECT_DIR=$WORK/demo-wiki bash -c uv\ run\ --quiet\ --script\ \"\$\{CLAUDE_PLUGIN_ROOT\}/skills/okfw/hooks/okf_hook.py\"\ guard <<< \{\"hook_event_name\":\"PreToolUse\"\,\"tool_name\":\"Write\"\,\"cwd\":\"$WORK/demo-wiki\"\,\"tool_input\":\{\"file_path\":\"$WORK/demo-wiki/wiki/index.md\"\,\"content\":\"x\"\}\}); echo "$out"; grep -q '"permissionDecision": "deny"' <<< "$out"
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Geschützte Wiki-Datei: wiki/index.md ist generiert. Inhalte in den Seiten ändern, dann `uv run --quiet /home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py rebuild`."}}
```

### 29. PreToolUse: Edit einer Karte ist erlaubt

`05:26:23Z` · Exit 0 · bestanden

```text
$ out=$(CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0 CLAUDE_PROJECT_DIR=$WORK/demo-wiki bash -c uv\ run\ --quiet\ --script\ \"\$\{CLAUDE_PLUGIN_ROOT\}/skills/okfw/hooks/okf_hook.py\"\ guard <<< \{\"hook_event_name\":\"PreToolUse\"\,\"tool_name\":\"Edit\"\,\"cwd\":\"$WORK/demo-wiki\"\,\"tool_input\":\{\"file_path\":\"$WORK/demo-wiki/wiki/concepts/llm-wiki-im-okf.md\"\}\}); test -z "$out" && echo 'keine Einwände'
keine Einwände
```

### 30. PostToolUse: Edit einer Karte landet im Ereignisstrom

`05:26:23Z` · Exit 0 · bestanden

```text
$ vor=$(wc -l < '$WORK/demo-wiki/wiki/.events.jsonl'); CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0 CLAUDE_PROJECT_DIR=$WORK/demo-wiki bash -c $'uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}/skills/okfw/hooks/okf_hook.py" post-edit 2>/dev/null || echo \'{"systemMessage": "okfw: Hook post-edit lie\303\237 sich nicht starten (uv run --script)"}\'' <<< \{\"hook_event_name\":\"PostToolUse\"\,\"tool_name\":\"Edit\"\,\"cwd\":\"$WORK/demo-wiki\"\,\"tool_input\":\{\"file_path\":\"$WORK/demo-wiki/wiki/concepts/llm-wiki-im-okf.md\"\}\}; nach=$(wc -l < '$WORK/demo-wiki/wiki/.events.jsonl'); echo "Ereignisse $vor -> $nach"; tail -1 '$WORK/demo-wiki/wiki/.events.jsonl'; test $nach -eq $((vor + 1))
Ereignisse 9 -> 10
{"ts": "2026-10-28T05:26:23Z", "kind": "edit", "page": "concepts/llm-wiki-im-okf", "by": "process:claude-code-hook", "detail": ""}
```

### 31. Stop: Rebuild läuft, danach ist rebuild --check leer

`05:26:23Z` · Exit 0 · bestanden

```text
$ CLAUDE_PLUGIN_ROOT=/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0 CLAUDE_PROJECT_DIR=$WORK/demo-wiki bash -c $'uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}/skills/okfw/hooks/okf_hook.py" stop 2>/dev/null || echo \'{"systemMessage": "okfw: Hook stop lie\303\237 sich nicht starten (uv run --script)"}\'' <<< \{\"hook_event_name\":\"Stop\"\}; cd '$WORK/demo-wiki' && uv run --quiet '/home/tester/.claude/plugins/cache/okfw/okfw/0.2.0/skills/okfw/okfw.py' rebuild --check && tail -3 wiki/log.md
* **Quelle erfasst**: `raw/pi-llm-wiki` – pi-llm-wiki, README
* **Quelle erfasst**: `raw/okf-v0-2-spec` – OKF v0.2, Spezifikation
* **Initialisierung**: `.` – Bundle angelegt (Profil default, okfw 0.2.0)
```

## Echte Claude-Sitzung (optional)

### 32. claude -p: Schreibversuch auf Rohquelle scheitert am Guard

`05:26:31Z` · Exit 0 · bestanden

```text
$ claude -p --permission-mode acceptEdits     'Überschreibe die Datei raw/okf-v0-2-spec/original/SPEC.md mit dem Text x. Nutze nur das Write-Werkzeug.' | tail -5;     sha_ok 26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101 raw/okf-v0-2-spec/original/SPEC.md
Den Hook habe ich nicht umgangen, auch nicht mit Bash oder einem anderen Werkzeug. Du hattest ausdrücklich nur Write erlaubt, und der Schutz gehört zur Wiki-Konfiguration.

Zwei Wege führen weiter:
- **Neue Fassung anlegen:** Der Hook empfiehlt, die Quelle mit `uv run --quiet /home/tester/checkout/plugins/okfw/skills/okfw/okfw.py capture` zu erfassen. Die neue Fassung bekommt den Slug `okf-v0-2-spec-v2`. Das Original bleibt dabei erhalten.
- **Schutz aufheben:** Wenn du das Original wirklich ersetzen willst, musst du den Hook selbst lockern oder ausschalten. Sag mir dann Bescheid, dann schreibe ich "x" in die Datei.
raw/okf-v0-2-spec/original/SPEC.md: SHA-256 26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101 stimmt
```

## Ergebnis

Ende: 2026-10-28T05:26:31Z · 32 Schritte: 32 bestanden, 0 fehlgeschlagen, 0 übersprungen.

