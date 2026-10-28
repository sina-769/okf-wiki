#!/usr/bin/env bash
# Nachbau-Test für das Claude-Code-Plugin okfw, für eine frische Umgebung (leerer Container oder leeres HOME).
#
#   nachbau.sh <marketplace-quelle> <ausgabeordner>
#
# <marketplace-quelle> ist alles, was `claude plugin marketplace add` versteht (Ordner mit
# .claude-plugin/marketplace.json, Git-URL, owner/repo). Der Test installiert das Plugin daraus, legt
# ein Demo-Wiki aus zwei frei lizenzierten Quellen an (OKF-v0.2-Spezifikation, Apache-2.0; README von
# pi-llm-wiki, MIT), erfasst beide als Rohquellen, schreibt Karten, führt rebuild, lint und dashboard aus,
# prüft die Freigabe (Ablehnung ohne Gegenprüfung, Rückfall nach body) und ruft die Hooks so auf, wie Claude Code sie aus hooks/hooks.json startet. Jeder Schritt steht mit
# Befehl, Ausgabe und Exit-Code in <ausgabeordner>/protokoll.md.
#
# Braucht: bash, git, curl, claude (Claude Code), uv. Netz: GitHub-API (Quellen), PyPI und die
# Python-Downloads von uv (beim ersten Start des Kerns). Kein Login bei Claude nötig; nur der optionale
# Schritt mit einer echten Claude-Sitzung braucht CLAUDE_CODE_OAUTH_TOKEN.
set -u

SRC=${1:?Marketplace-Quelle fehlt}
OUT=${2:?Ausgabeordner fehlt}
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
LOG="$OUT/protokoll.md"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/nachbau.XXXXXX") || { echo "kein Arbeitsordner" >&2; exit 2; }
DEMO="$WORK/demo-wiki"
DL="$WORK/downloads"
LEER="$WORK/ohne-wiki"
mkdir -p "$DEMO" "$DL" "$LEER"
N=0; OK=0; FAIL=0; SKIP=0

# Quellen, gepinnt auf Commit; SHA-256 der Dateien zum Abgleich
OKF_REPO=GoogleCloudPlatform/knowledge-catalog
OKF_COMMIT=a8291a1a656669b8766fd4ff0f985505fb955e94
OKF_PATH=okf/SPEC.md
OKF_SHA=26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101
PI_REPO=zosmaai/pi-llm-wiki
PI_COMMIT=46bd677041ba01f0298e5afc22e6a8b592f5f835
PI_PATH=README.md
PI_SHA=cac7184ae31a6bd881e5362326200c899f8d58487134d28e1f11d5f0bc4466c8
# Commit-Datum (GitHub-API, committer.date): OKF 2026-10-24, pi-llm-wiki 2026-10-09 → date der Quellenkarten

log() { printf '%s\n' "$*" >>"$LOG"; }
# sha_ok <sha256> <datei>: Prüfsumme vergleichen (GNU sha256sum oder shasum)
sha_of() { if sha256sum --version >/dev/null 2>&1; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }
sha_ok() { [ "$(sha_of "$2")" = "$1" ] && echo "$2: SHA-256 $1 stimmt"; }
export -f sha_of sha_ok

# step <titel> <befehl als Zeichenkette>: läuft in bash, Exit 0 = bestanden
step() {
  local title=$1 cmd=$2 out rc
  N=$((N + 1))
  out=$(cd "${CWD:-$WORK}" && bash -c "$cmd" 2>&1); rc=$?
  if [ $rc -eq 0 ]; then OK=$((OK + 1)); res="bestanden"; else FAIL=$((FAIL + 1)); res="**FEHLGESCHLAGEN**"; fi
  log "### $N. $title"
  log ""
  log "\`$(date -u +%H:%M:%SZ)\` · Exit $rc · $res"
  log ""
  log '```text'
  log "\$ ${cmd//$WORK/\$WORK}"
  printf '%s\n' "$out" | sed "s#$WORK#\$WORK#g" | head -n "${MAXLINES:-40}" >>"$LOG"
  [ "$(printf '%s\n' "$out" | wc -l)" -gt "${MAXLINES:-40}" ] && log "… (gekürzt)"
  log '```'
  log ""
  printf '%-4s %-20s %s\n' "$N." "$res" "$title"
}

skip() {
  N=$((N + 1)); SKIP=$((SKIP + 1))
  log "### $N. $1"; log ""; log "übersprungen: $2"; log ""
  printf '%-4s %-20s %s\n' "$N." "übersprungen" "$1"
}

: >"$LOG"
log "# Nachbau-Test okfw"
log ""
log "Beginn: $(date -u +%Y-%m-%dT%H:%M:%SZ) · Marketplace-Quelle: \`$SRC\`${REPO_COMMIT:+ · Repo-Commit: \`$REPO_COMMIT\`}"
log ""
log "## Umgebung"
log ""

step "Werkzeuge und leere Ausgangslage" '
uname -srm; echo "HOME=$HOME"
echo "claude $(claude --version)"; uv --version; git --version | head -1
command -v python3 >/dev/null && echo "python3: $(python3 --version)" || echo "python3: keins im PATH"
test ! -e "$HOME/.claude/plugins/installed_plugins.json" && echo "keine Plugins installiert"
test ! -e "$HOME/.claude/skills/okfw" && echo "kein Skill-Ordner okfw"'

log "## Installation"
log ""
step "Marketplace hinzufügen" "claude plugin marketplace add '$SRC'"
step "Plugin installieren" "claude plugin install okfw@okfw"
step "Bestandteile des installierten Plugins" "claude plugin details okfw@okfw | sed -n '1,12p'"
P=$(grep -o '"installPath": *"[^"]*okfw[^"]*"' "$HOME/.claude/plugins/installed_plugins.json" 2>/dev/null \
  | head -1 | sed 's/.*: *"//; s/"$//')
K="$P/skills/okfw/okfw.py"
H="$P/skills/okfw/hooks/okf_hook.py"
step "Installierte Dateien (Plugin-Cache)" "test -n '$P' && cd '$P' && find . -type f | sort && cat .claude-plugin/plugin.json"
step "Manifest streng prüfen" "claude plugin validate --strict '$P/.claude-plugin/plugin.json'"

log "## Demo-Wiki"
log ""
CWD=$DEMO
step "Kern starten (uv holt Python ≥ 3.11, PyYAML, Markdown)" "uv run --quiet '$K' --version"
step "Python, das uv dafür nutzt" "uv python find && uv python list --only-installed"
step "Wiki anlegen (Profil default)" "uv run --quiet '$K' init --profile default && ls -a && cat wiki/.events.jsonl"

fetch() { # fetch <repo> <commit> <pfad> <ziel> <sha256>
  echo "curl -sf -H 'Accept: application/vnd.github.raw' 'https://api.github.com/repos/$1/contents/$3?ref=$2' -o '$4' && sha_ok $5 '$4'"
}
step "OKF-v0.2-Spezifikation über die GitHub-API holen (Apache-2.0)" "$(fetch $OKF_REPO $OKF_COMMIT $OKF_PATH "$DL/SPEC.md" $OKF_SHA)"
step "README von pi-llm-wiki über die GitHub-API holen (MIT)" "$(fetch $PI_REPO $PI_COMMIT $PI_PATH "$DL/README.md" $PI_SHA)"
step "Quelle erfassen: okf-v0-2-spec" "uv run --quiet '$K' capture okf-v0-2-spec \
  --url 'https://github.com/$OKF_REPO/blob/$OKF_COMMIT/$OKF_PATH' --file '$DL/SPEC.md' --commit $OKF_COMMIT \
  --license Apache-2.0 --license-url https://www.apache.org/licenses/LICENSE-2.0 --note 'OKF v0.2, Spezifikation' \
  && cat raw/okf-v0-2-spec/manifest.json"
step "Quelle erfassen: pi-llm-wiki" "uv run --quiet '$K' capture pi-llm-wiki \
  --url 'https://github.com/$PI_REPO/blob/$PI_COMMIT/$PI_PATH' --file '$DL/README.md' --commit $PI_COMMIT \
  --license MIT --license-url 'https://github.com/$PI_REPO/blob/$PI_COMMIT/LICENSE' --note 'pi-llm-wiki, README' \
  && ls -l raw/pi-llm-wiki/original"

step "Quellenkarte anlegen: okf-v0-2-spec" "uv run --quiet '$K' new source okf-v0-2-spec \
  --title 'Open Knowledge Format (OKF), Version 0.2' \
  --description 'Spezifikation eines Formats für Wissensbündel aus Markdown-Dateien mit YAML-Frontmatter.' \
  --access fulltext --resource 'https://github.com/$OKF_REPO/blob/$OKF_COMMIT/$OKF_PATH' \
  --set raw_packet=raw/okf-v0-2-spec --set format=specification --set date=2026-10-24 --fundweg person \
  --set 'license={name: Apache-2.0, url: \"https://www.apache.org/licenses/LICENSE-2.0\"}'"
step "Quellenkarte anlegen: pi-llm-wiki" "uv run --quiet '$K' new source pi-llm-wiki \
  --title 'pi-llm-wiki (README)' \
  --description 'Erweiterung und MCP-Server für ein selbstgepflegtes LLM-Wiki nach dem Muster von Andrej Karpathy.' \
  --access fulltext --resource 'https://github.com/$PI_REPO/blob/$PI_COMMIT/$PI_PATH' \
  --set raw_packet=raw/pi-llm-wiki --set format=documentation --set date=2026-10-09 --fundweg person \
  --set 'license={name: MIT, url: \"https://github.com/$PI_REPO/blob/$PI_COMMIT/LICENSE\"}'"
step "Konzeptkarte anlegen, die beide Quellen nutzt" "uv run --quiet '$K' new concept llm-wiki-im-okf \
  --title 'LLM-Wiki im Open Knowledge Format' \
  --description 'Wie das LLM-Wiki-Muster und das Open Knowledge Format zusammenpassen.' --sources okf-v0-2-spec,pi-llm-wiki \
  --set domain=wissensorganisation --set 'aliases=[LLM Wiki, Open Knowledge Format Wiki]'"

cat >"$WORK/okf.md" <<'EOF'
# Open Knowledge Format (OKF), Version 0.2

## Kurzreferat

Die Spezifikation beschreibt Bündel aus Markdown-Dokumenten mit YAML-Frontmatter.

## Kernaussagen

- `type` ist der einzige stets verlangte Schlüssel im Frontmatter (§ 4, Z. 187).
- Verbraucher müssen kaputte Links tolerieren (§ 6, Z. 464).

## Relevanz

Format des Demo-Wikis.

## Verbindungen

- [LLM-Wiki im Open Knowledge Format](/concepts/llm-wiki-im-okf.md)

## Zugang

Volltext als Rohquelle `raw/okf-v0-2-spec`, Lizenz Apache-2.0.
EOF
cat >"$WORK/pi.md" <<'EOF'
# pi-llm-wiki (README)

## Kurzreferat

Das README beschreibt ein Wiki, das ein Sprachmodell selbst pflegt.

## Kernaussagen

- Das Paket folgt dem LLM-Wiki-Muster von Andrej Karpathy (Z. 23).
- Quellen werden unveränderlich erfasst (Z. 119).

## Relevanz

Muster, nach dem okfw arbeitet.

## Verbindungen

- [LLM-Wiki im Open Knowledge Format](/concepts/llm-wiki-im-okf.md)

## Zugang

Volltext als Rohquelle `raw/pi-llm-wiki`, Lizenz MIT.
EOF
cat >"$WORK/konzept.md" <<'EOF'
# LLM-Wiki im Open Knowledge Format

pi-llm-wiki folgt dem LLM-Wiki-Muster von Andrej Karpathy und erfasst Quellen unveränderlich.[^pi-llm-wiki]
Das Open Knowledge Format verlangt im Frontmatter nur `type`, alles Weitere ist Profil.[^okf-v0-2-spec]

Quellen: [OKF v0.2](/sources/okf-v0-2-spec.md) und [pi-llm-wiki](/sources/pi-llm-wiki.md).

[^okf-v0-2-spec]: [Open Knowledge Format (OKF), Version 0.2](/sources/okf-v0-2-spec.md)
[^pi-llm-wiki]: [pi-llm-wiki (README)](/sources/pi-llm-wiki.md)
EOF
step "Seiteninhalte setzen (body)" "uv run --quiet '$K' body sources/okf-v0-2-spec '$WORK/okf.md' \
  && uv run --quiet '$K' body sources/pi-llm-wiki '$WORK/pi.md' \
  && uv run --quiet '$K' body concepts/llm-wiki-im-okf '$WORK/konzept.md' && cat wiki/concepts/llm-wiki-im-okf.md"

step "rebuild" "uv run --quiet '$K' rebuild && cat wiki/index.md"
step "rebuild --check (nichts mehr zu tun)" "uv run --quiet '$K' rebuild --check"
step "lint (0 Fehler verlangt)" "uv run --quiet '$K' lint; rc=\$?; uv run --quiet '$K' lint --json | grep -c '\"severity\": \"error\"' | sed 's/^/Fehler: /'; exit \$rc"
step "status" "uv run --quiet '$K' status"
step "dashboard" "uv run --quiet '$K' dashboard && ls -l build/wiki-dashboard.html \
  && echo \"Seiten im Dashboard: \$(grep -o 'llm-wiki-im-okf' build/wiki-dashboard.html | wc -l) Treffer für llm-wiki-im-okf\" \
  && ! grep -Eo '<(script|img|iframe)[^>]+src=.https?://|<link[^>]+href=.https?://|url\\(.?https?://' build/wiki-dashboard.html \
  && echo 'lädt nichts aus dem Netz nach (kein script/img/iframe/link/url() auf http)'"
step "Rohquelle bleibt unverändert (SHA-256)" "sha_ok $OKF_SHA raw/okf-v0-2-spec/original/SPEC.md \
  && sha_ok $PI_SHA raw/pi-llm-wiki/original/README.md"

log "## Freigabe"
log ""
KARTE=wiki/concepts/llm-wiki-im-okf.md
step "Freigabe ohne Gegenprüfung wird abgelehnt" "out=\$(uv run --quiet '$K' verify concepts/llm-wiki-im-okf \
  --by human:nachbau --status stable 2>&1); rc=\$?; echo \"\$out\"; echo \"Exit \$rc\"; test \$rc -ne 0 \
  && grep -q 'keine Gegenprüfung' <<< \"\$out\" && grep '^status:' $KARTE && grep -q '^status: draft' $KARTE"
step "Freigabe nach Gegenprüfung, Rückfall nach body (stable → draft)" "uv run --quiet '$K' verify concepts/llm-wiki-im-okf \
  --by claude-code/nachbau --note 'Gegenprüfung im Nachbau' \
  && uv run --quiet '$K' verify concepts/llm-wiki-im-okf --by human:nachbau --status stable --note 'Charge Nachbau' \
  && grep -q '^status: stable' $KARTE && grep -c 'body_sha256' $KARTE | sed 's/^/Vermerke mit Prüfwert: /' \
  && { cat '$WORK/konzept.md'; echo; echo 'Ein Satz nach der Freigabe.'; } | uv run --quiet '$K' body concepts/llm-wiki-im-okf - \
  && grep '^status:' $KARTE && grep -q '^status: draft' $KARTE \
  && uv run --quiet '$K' lint --json | grep -o '\"code\": \"verified_outdated\"' \
  && uv run --quiet '$K' status | grep -E '^(Vertrauen|Freigaben):'"

log "## Hooks, wie Claude Code sie aus dem Plugin startet"
log ""
CWD=$WORK
cmd_of() { grep -o '"command": *".*'"$1"'.*"' "$P/hooks/hooks.json" | head -1 | sed 's/^"command": *"//; s/"$//; s/\\"/"/g'; }
hook() { # hook <unterbefehl> <projekt> <json>
  printf 'CLAUDE_PLUGIN_ROOT=%q CLAUDE_PROJECT_DIR=%q bash -c %q <<< %q' "$P" "$2" "$(cmd_of "$1")" "$3"
}
step "hooks.json: Befehle" "grep -o '\"command\": *\".*\"' '$P/hooks/hooks.json' | sed 's/^\"command\": *//'"
step "SessionStart im Demo-Wiki: Status als Kontext" "out=\$($(hook session-start "$DEMO" '{"hook_event_name":"SessionStart","source":"startup"}')); echo \"\$out\"; grep -q 'OKF-v0.2-Wiki unter' <<< \"\$out\""
step "SessionStart ohne wiki.toml: keine Ausgabe" "out=\$($(hook session-start "$LEER" '{"hook_event_name":"SessionStart","source":"startup"}')); test -z \"\$out\" && echo 'leer'"
step "PreToolUse: Write auf Rohquelle wird abgelehnt" "out=\$($(hook guard "$DEMO" "{\"hook_event_name\":\"PreToolUse\",\"tool_name\":\"Write\",\"cwd\":\"$DEMO\",\"tool_input\":{\"file_path\":\"$DEMO/raw/okf-v0-2-spec/original/SPEC.md\",\"content\":\"x\"}}")); echo \"\$out\"; grep -q '\"permissionDecision\": \"deny\"' <<< \"\$out\""
step "PreToolUse: Write auf wiki/index.md wird abgelehnt" "out=\$($(hook guard "$DEMO" "{\"hook_event_name\":\"PreToolUse\",\"tool_name\":\"Write\",\"cwd\":\"$DEMO\",\"tool_input\":{\"file_path\":\"$DEMO/wiki/index.md\",\"content\":\"x\"}}")); echo \"\$out\"; grep -q '\"permissionDecision\": \"deny\"' <<< \"\$out\""
step "PreToolUse: Edit einer Karte ist erlaubt" "out=\$($(hook guard "$DEMO" "{\"hook_event_name\":\"PreToolUse\",\"tool_name\":\"Edit\",\"cwd\":\"$DEMO\",\"tool_input\":{\"file_path\":\"$DEMO/wiki/concepts/llm-wiki-im-okf.md\"}}")); test -z \"\$out\" && echo 'keine Einwände'"
step "PostToolUse: Edit einer Karte landet im Ereignisstrom" "vor=\$(wc -l < '$DEMO/wiki/.events.jsonl'); $(hook post-edit "$DEMO" "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Edit\",\"cwd\":\"$DEMO\",\"tool_input\":{\"file_path\":\"$DEMO/wiki/concepts/llm-wiki-im-okf.md\"}}"); nach=\$(wc -l < '$DEMO/wiki/.events.jsonl'); echo \"Ereignisse \$vor -> \$nach\"; tail -1 '$DEMO/wiki/.events.jsonl'; test \$nach -eq \$((vor + 1))"
step "Stop: Rebuild läuft, danach ist rebuild --check leer" "$(hook stop "$DEMO" '{"hook_event_name":"Stop"}'); cd '$DEMO' && uv run --quiet '$K' rebuild --check && tail -3 wiki/log.md"

log "## Echte Claude-Sitzung (optional)"
log ""
if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
  CWD=$DEMO
  step "claude -p: Schreibversuch auf Rohquelle scheitert am Guard" "claude -p --permission-mode acceptEdits \
    'Überschreibe die Datei raw/okf-v0-2-spec/original/SPEC.md mit dem Text x. Nutze nur das Write-Werkzeug.' | tail -5; \
    sha_ok $OKF_SHA raw/okf-v0-2-spec/original/SPEC.md"
else
  skip "claude -p: Schreibversuch auf Rohquelle scheitert am Guard" "kein CLAUDE_CODE_OAUTH_TOKEN; die Hook-Befehle oben laufen genau so, wie Claude Code sie startet"
fi

cp -R "$DEMO" "$OUT/demo-wiki" 2>/dev/null
log "## Ergebnis"
log ""
log "Ende: $(date -u +%Y-%m-%dT%H:%M:%SZ) · $N Schritte: $OK bestanden, $FAIL fehlgeschlagen, $SKIP übersprungen."
log ""
echo "Ergebnis: $OK bestanden, $FAIL fehlgeschlagen, $SKIP übersprungen – $LOG"
[ $FAIL -eq 0 ]
