# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Claude-Code-Hooks für okf-wiki, nur Standardbibliothek (läuft bei jedem Write/Edit).

  okf_hook.py guard          PreToolUse: blockiert Schreibzugriffe auf Rohquellen, Ereignisstrom und Projektionen
  okf_hook.py post-edit      PostToolUse: protokolliert Write/Edit an Wiki-Seiten im Ereignisstrom
  okf_hook.py session-start  SessionStart: `okfwiki.py status --hook`, nur wenn das Projekt eine wiki.toml hat
  okf_hook.py stop           Stop: `okfwiki.py rebuild --quiet`, nur wenn das Projekt eine wiki.toml hat

Guard und Ereignisprotokoll suchen die wiki.toml aufwärts ab der Zieldatei, session-start und stop
im Projektordner ($CLAUDE_PROJECT_DIR); ohne wiki.toml tut der Hook nichts. So kostet das Plugin in
Projekten ohne Wiki keinen Start des Kerns. Braucht Python ≥ 3.11 (tomllib); im Plugin startet es
deshalb über `uv run --script`.
Entspricht Guard und Ereignisprotokoll aus dem Claude-Code-Plugin von pi-llm-wiki.
"""

import datetime as dt
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

RESERVED = ("index.md", "log.md")
CORE = Path(__file__).resolve().parent.parent / "okfwiki.py"


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
    except (OSError, tomllib.TOMLDecodeError):
        return None
    root = config.parent.resolve()
    wiki = cfg.get("wiki", {})
    paths = cfg.get("paths", {})
    bundle_rel = wiki.get("bundle", "wiki")
    return {
        "root": root,
        "bundle": (root / bundle_rel).resolve(),
        "events": (root / (paths.get("events") or f"{bundle_rel}/.events.jsonl")).resolve(),
        "raw": (root / paths["raw"]).resolve() if paths.get("raw") else None,
        "exports": {(root / v["path"]).resolve() for v in cfg.get("export", {}).values()
                    if isinstance(v, dict) and v.get("path")}
                   | {(root / cfg.get("dashboard", {}).get("path", "build/wiki-dashboard.html")).resolve()},
        "protected": list(paths.get("protected", [])),
    }


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


def guard(event: dict) -> None:
    path = target_path(event)
    ctx = load(path) if path else None
    reason = reason_for(ctx, path) if ctx else None
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"Geschützte Wiki-Datei: {reason}",
        }}, ensure_ascii=False))


def post_edit(event: dict) -> None:
    path = target_path(event)
    ctx = load(path) if path else None
    if not ctx or path.suffix != ".md" or path.name in RESERVED or not path.is_relative_to(ctx["bundle"]):
        return
    rel = path.relative_to(ctx["bundle"])
    if any(part.startswith(".") for part in rel.parts):
        return
    record = {
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kind": "write" if event.get("tool_name") == "Write" else "edit",
        "page": rel.with_suffix("").as_posix(),
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


def session_start(event: dict) -> None:
    root = project_root(event)
    if root is None:
        return
    try:
        done = run_core(root, "status", "--hook", timeout=18)
    except subprocess.TimeoutExpired:
        return
    if done is None:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"Projekt mit wiki.toml ({root}), aber `uv` fehlt im PATH: okf-wiki braucht uv "
                                 "(https://docs.astral.sh/uv/). Der Person sagen, bevor am Wiki gearbeitet wird.",
        }}, ensure_ascii=False))
    elif done.returncode == 0:
        sys.stdout.write(done.stdout)


def stop(event: dict) -> None:
    root = project_root(event)
    if root is not None:
        try:
            run_core(root, "rebuild", "--quiet", timeout=55)
        except subprocess.TimeoutExpired:
            pass


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        event = {}
    if not isinstance(event, dict):
        return
    handlers = {"guard": guard, "post-edit": post_edit, "session-start": session_start, "stop": stop}
    handlers.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda e: None)(event)


if __name__ == "__main__":
    main()
