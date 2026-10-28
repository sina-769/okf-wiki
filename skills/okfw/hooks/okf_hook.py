# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Claude-Code-Hooks für okfw, nur Standardbibliothek (läuft bei jedem Write/Edit).

  okf_hook.py guard          PreToolUse: blockiert Schreibzugriffe auf Rohquellen, Ereignisstrom und Projektionen
                             sowie Edit/Write, die auf einer Wiki-Seite status oder verified ändern
  okf_hook.py post-edit      PostToolUse: hat ein Write/Edit den Körper einer Wiki-Seite geändert, zieht
                             `okfw.py body --nachziehen` generated nach (stable wie bei body); sonst nur ein Ereignis
  okf_hook.py session-start  SessionStart: `okfw.py status --hook`, nur wenn das Projekt eine wiki.toml hat
  okf_hook.py stop           Stop: `okfw.py rebuild --hook` (Rebuild, Lint-Fehler als eine Zeile), nur mit wiki.toml

Guard und Ereignisprotokoll suchen die wiki.toml aufwärts ab der Zieldatei, session-start und stop
im Projektordner ($CLAUDE_PROJECT_DIR); ohne wiki.toml tut der Hook nichts. So kostet das Plugin in
Projekten ohne Wiki keinen Start des Kerns. Bedienfehler (kaputte wiki.toml, falsches requires_core,
fehlendes uv, Zeitüberschreitung) melden die Hooks als eine Zeile (`systemMessage`), blockieren aber nichts. Braucht Python ≥ 3.11 (tomllib); im Plugin startet es
deshalb über `uv run --script`.
Entspricht Guard und Ereignisprotokoll aus dem Claude-Code-Plugin von pi-llm-wiki.
"""

import datetime as dt
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

RESERVED = ("index.md", "log.md")
TRUST_KEYS = ("status", "verified")   # ändert nur okfw.py verify (und body: stable → draft), über Bash
FRONTMATTER_RE = re.compile(r"---[ \t]*\n(.*?)^---[ \t]*$", re.S | re.M)
CORE = Path(__file__).resolve().parent.parent / "okfw.py"


class ConfigError(Exception):
    """wiki.toml vorhanden, aber nicht lesbar."""


def notice(text: str) -> None:
    """Eine Zeile für die Person (Claude Code zeigt systemMessage an), ohne etwas zu blockieren."""
    print(json.dumps({"systemMessage": one_line(f"okfw: {text}")}, ensure_ascii=False))


def one_line(text: str) -> str:
    return " ".join(str(text).split())


def find_config(path: Path):
    for directory in path.parents:
        candidate = directory / "wiki.toml"
        if candidate.is_file():
            return candidate
    return None


def load(path: Path):
    config = find_config(path)
    if config is None:
        return None
    try:
        with config.open("rb") as f:
            cfg = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"{config} nicht lesbar ({exc})") from exc
    root = config.parent.resolve()
    wiki = cfg.get("wiki", {})
    paths = cfg.get("paths", {})
    bundle_rel = wiki.get("bundle", "wiki")
    return {
        "root": root,
        "bundle": (root / bundle_rel).resolve(),
        "events": (root / (paths.get("events") or f"{bundle_rel}/.events.jsonl")).resolve(),
        "raw": (root / paths["raw"]).resolve() if paths.get("raw") else None,
        "exports": {(root / p).resolve() for p in generated_outputs(cfg)},
        "protected": list(paths.get("protected", [])),
    }


def generated_outputs(cfg: dict) -> list[str]:
    """Exporte und Dashboards wie protected_paths() im Kern: [export.*] path, [dashboard] path und, mit
    [visibility] field, das öffentliche Dashboard ([dashboard] public_path oder <path>-oeffentlich daneben)."""
    out = [v["path"] for v in cfg.get("export", {}).values() if isinstance(v, dict) and v.get("path")]
    dashboard = cfg.get("dashboard", {})
    path = dashboard.get("path") or "build/wiki-dashboard.html"
    out.append(path)
    if cfg.get("visibility", {}).get("field"):
        public = Path(path)
        out.append(dashboard.get("public_path") or str(public.with_name(f"{public.stem}-oeffentlich{public.suffix}")))
    return out


def target_path(event: dict):
    tool_input = event.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not target:
        return None
    path = Path(target)
    if not path.is_absolute():
        path = Path(event.get("cwd") or ".") / path
    return path.resolve()


def reason_for(ctx: dict, path: Path):
    tool = f"uv run --quiet {CORE}"
    try:
        rel = path.relative_to(ctx["root"]).as_posix()
    except ValueError:
        return None
    if path == ctx["events"]:
        return f"{rel} ist der Append-only-Ereignisstrom. Ereignisse mit `{tool} event` oder `verify` schreiben."
    if ctx["raw"] and path.is_relative_to(ctx["raw"]):
        return f"{rel} ist eine unveränderliche Rohquelle. Neue Quellen mit `{tool} capture`, neue Fassung als <slug>-v2."
    if path in ctx["exports"]:
        return f"{rel} ist ein generierter Export. Die Quellenkarten ändern, dann `{tool} rebuild`."
    if path.is_relative_to(ctx["bundle"]) and path.name in RESERVED:
        return f"{rel} ist generiert. Inhalte in den Seiten ändern, dann `{tool} rebuild`."
    for pattern in ctx["protected"]:
        if fnmatch.fnmatch(rel, pattern):
            return f"{rel} ist laut wiki.toml geschützt ({pattern})."
    return None


def trust_blocks(text: str) -> dict:
    """Top-Level-Schlüssel status und verified im Frontmatter als Text, ohne PyYAML: Schlüsselzeile und
    eingerückte Folgezeilen, Leerzeilen und Leerraum am Zeilenende ohne Bedeutung."""
    m = FRONTMATTER_RE.match(text)
    lines = m.group(1).splitlines() if m else []
    blocks, i = {}, 0
    while i < len(lines):
        key = re.match(r"([A-Za-z_][\w-]*)\s*:", lines[i])
        i += 1
        if not key or key.group(1) not in TRUST_KEYS:
            continue
        block = [lines[i - 1].rstrip()]
        while i < len(lines) and (lines[i].startswith((" ", "\t", "- ")) or lines[i].strip() in ("", "-")):
            if lines[i].strip():
                block.append(lines[i].rstrip())
            i += 1
        blocks[key.group(1)] = "\n".join(block)
    return blocks


def new_text(event: dict, path: Path):
    """Inhalt der Datei nach Write, Edit oder MultiEdit; None, wenn er sich nicht bestimmen lässt."""
    tool, tool_input = event.get("tool_name"), event.get("tool_input") or {}
    if tool == "Write":
        return tool_input.get("content")
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    edits = tool_input.get("edits") if tool == "MultiEdit" else [tool_input] if tool == "Edit" else None
    for edit in edits or []:
        old, new = edit.get("old_string"), edit.get("new_string")
        if not isinstance(old, str) or not isinstance(new, str) or not old:
            continue
        text = text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)
    return text if edits is not None else None


def trust_reason(ctx: dict, path: Path, event: dict):
    """Ändert ein Edit oder Write auf einer Wiki-Seite status oder verified? Eine neue Seite darf status: draft tragen."""
    if path.suffix != ".md" or path.name in RESERVED or not path.is_relative_to(ctx["bundle"]):
        return None
    if any(part.startswith(".") for part in path.relative_to(ctx["bundle"]).parts):
        return None
    after = new_text(event, path)
    if after is None:
        return None
    before = trust_blocks(path.read_text(encoding="utf-8", errors="replace")) if path.is_file() else {}
    after = trust_blocks(after)
    if not path.is_file() and re.fullmatch(r"status:\s*[\"']?draft[\"']?", after.get("status", "status: draft")):
        after.pop("status", None)
    changed = [k for k in TRUST_KEYS if before.get(k) != after.get(k)]
    if not changed:
        return None
    rel = path.relative_to(ctx["root"]).as_posix()
    return (f"{rel}: {' und '.join(changed)} ändert nur `uv run --quiet {CORE} verify <seite> --by …` "
            "(Prüfvermerk mit Prüfwert; Freigabe nur durch einen Menschen). Den Rest der Seite mit Edit oder `body` "
            "ändern und status/verified so lassen, wie sie stehen.")


def guard(event: dict) -> None:
    path = target_path(event)
    try:
        ctx = load(path) if path else None
    except ConfigError as exc:
        notice(f"Guard ohne Wirkung, {exc}; Rohquellen und Projektionen sind bis zur Korrektur nicht geschützt.")
        return
    reason = reason_for(ctx, path) if ctx else None
    if ctx and not reason:
        trust = trust_reason(ctx, path, event)
        if trust:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Vertrauensfelder der Wiki-Seite: {trust}",
            }}, ensure_ascii=False))
            return
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"Geschützte Wiki-Datei: {reason}",
        }}, ensure_ascii=False))


def body_of(text: str) -> str:
    """Körper ohne Frontmatter, normalisiert wie body_sha256 im Kern (LF, ohne Leerzeilen an Anfang und Ende)."""
    m = FRONTMATTER_RE.match(text)
    body = text[m.end():] if m else text
    return body.replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def text_before(event: dict):
    """Dateiinhalt vor dem Werkzeug aus der Antwort von Claude Code; "" für eine neue Datei, None unbekannt."""
    response = event.get("tool_response")
    if not isinstance(response, dict):
        return None
    if isinstance(response.get("originalFile"), str):
        return response["originalFile"]
    return "" if response.get("type") == "create" else None


def pull_generated(ctx: dict, page: str, tool: str) -> bool:
    """Körper geändert: generated über den Kern nachziehen (Akteur aus [wiki] actor, stable wie bei body).
    Der Kern schreibt das Ereignis update; False, wenn er nicht lief (dann bleibt es beim Ereignis des Hooks)."""
    try:
        done = run_core(ctx["root"], "body", page, "--nachziehen", "--detail", f"{tool} über Claude Code", timeout=15)
    except subprocess.TimeoutExpired:
        notice(f"generated von {page} nach 15 s nicht nachgezogen; `body {page} --nachziehen` von Hand.")
        return False
    if done is None:
        notice(f"uv fehlt im PATH, generated von {page} nicht nachgezogen.")
        return False
    if done.returncode != 0:
        notice(core_failed(f"generated von {page} nachziehen", done))
        return False
    lines = done.stdout.strip().splitlines()
    out = {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": one_line(
        f"okfw: {' '.join(lines)}. Die Datei vor dem nächsten Edit neu lesen (Frontmatter geändert).")}}
    if len(lines) > 1:   # stable → draft
        out["systemMessage"] = one_line(f"okfw: {page}: {lines[1]}")
    print(json.dumps(out, ensure_ascii=False))
    return True


def post_edit(event: dict) -> None:
    path = target_path(event)
    try:
        ctx = load(path) if path else None
    except ConfigError as exc:
        notice(f"Ereignisprotokoll ohne Wirkung, {exc}.")
        return
    if not ctx or path.suffix != ".md" or path.name in RESERVED or not path.is_relative_to(ctx["bundle"]):
        return
    rel = path.relative_to(ctx["bundle"])
    if any(part.startswith(".") for part in rel.parts):
        return
    page = rel.with_suffix("").as_posix()
    tool = event.get("tool_name") or "Edit"
    # Körper geändert? Ohne Vorher-Stand aus der Antwort gilt er als geändert: lieber generated zu oft nachziehen
    before = text_before(event)
    if path.is_file() and (before is None or body_of(before) != body_of(path.read_text(encoding="utf-8",
                                                                                         errors="replace"))):
        if pull_generated(ctx, page, tool):
            return
    record = {
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kind": "write" if tool == "Write" else "edit",
        "page": page,
        "by": "process:claude-code-hook",
        "detail": "",
    }
    ctx["events"].parent.mkdir(parents=True, exist_ok=True)
    with ctx["events"].open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def project_root(event: dict):
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()).resolve()
    return root if (root / "wiki.toml").is_file() else None


def run_core(root: Path, *args: str, timeout: int) -> subprocess.CompletedProcess | None:
    uv = shutil.which("uv")
    if uv is None:
        return None
    return subprocess.run([uv, "run", "--quiet", "--script", str(CORE), "--root", str(root), *args],
                          capture_output=True, text=True, timeout=timeout)


def core_failed(step: str, done: subprocess.CompletedProcess) -> str:
    last = (done.stderr or done.stdout).strip().splitlines()
    return f"{step} fehlgeschlagen (Exit {done.returncode}): {last[-1] if last else 'keine Ausgabe'}"


def session_start(event: dict) -> None:
    root = project_root(event)
    if root is None:
        return
    try:
        done = run_core(root, "status", "--hook", timeout=18)
    except subprocess.TimeoutExpired:
        notice("Wiki-Status beim Sitzungsstart nach 18 s abgebrochen (uv lädt beim ersten Start Python und Pakete).")
        return
    if done is None:
        print(json.dumps({"systemMessage": "okfw: uv fehlt im PATH, der Wiki-Kern läuft ohne uv nicht.",
                          "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"Projekt mit wiki.toml ({root}), aber `uv` fehlt im PATH: okfw braucht uv "
                                 "(https://docs.astral.sh/uv/). Darauf hinweisen, bevor am Wiki gearbeitet wird.",
        }}, ensure_ascii=False))
    elif done.returncode == 0:
        sys.stdout.write(done.stdout)
    else:
        notice(core_failed("Wiki-Status", done))


def stop(event: dict) -> None:
    root = project_root(event)
    if root is None:
        return
    try:
        done = run_core(root, "rebuild", "--hook", timeout=55)
    except subprocess.TimeoutExpired:
        notice("Rebuild beim Stop nach 55 s abgebrochen; `rebuild` von Hand ausführen.")
        return
    if done is None:
        notice("uv fehlt im PATH, Rebuild beim Stop übersprungen.")
    elif done.returncode == 0:
        sys.stdout.write(done.stdout)
    else:
        notice(core_failed("Rebuild beim Stop", done))


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        event = {}
    if not isinstance(event, dict):
        return
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    handlers = {"guard": guard, "post-edit": post_edit, "session-start": session_start, "stop": stop}
    try:
        handlers.get(name, lambda e: None)(event)
    except Exception as exc:  # ein Hook darf die Sitzung nie anhalten; Fehler als eine Zeile
        notice(f"Hook {name}: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
