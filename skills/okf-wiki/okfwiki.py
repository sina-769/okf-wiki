#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "markdown>=3.5"]
# ///
"""okf-wiki – gemeinsamer Kern für Wissens-Wikis im Open Knowledge Format v0.2.

Muster: pi-llm-wiki (https://github.com/zosmaai/pi-llm-wiki), übertragen auf Claude Code.
Jedes Projekt beschreibt sein Wiki in einer wiki.toml (Bundle-Ordner, Seitentypen,
Pflichtfelder, Ereignisort, Exporte). Ohne wiki.toml schreibt der Kern nichts.

  okfwiki.py status [--hook]
  okfwiki.py lint [--strict] [--json] [--summary]
  okfwiki.py rebuild [--check] [--quiet]
  okfwiki.py new <typ> <slug> --title T [--description D] [--sources a,b] [--tags x,y]
                 [--access A] [--resource URI] [--csl DATEI|-] [--set feld=wert ...]
                 [--doi D | --pmid P | --arxiv A | --manuell --titel T --url U [--autor --jahr --csl-typ]]
                 [--volltext PFAD [--von URL]] [--evidenz E] [--fundweg ART [--db --query] [--fundweg-von SLUG]]
                 (deutsche Optionen: --titel, --beschreibung, --quellen)
  okfwiki.py new-source <slug> …   (= new source <slug> …)
  okfwiki.py capture <slug> --url URL --file PFAD [--file ...] [--commit SHA]
                 [--license NAME --license-url URL] [--note N]
  okfwiki.py hash <pfad> [--from URL]
  okfwiki.py verify <seite> --by human:<id> [--status stable] [--note N]
  okfwiki.py event <art> <seite> [detail] [--by AKTEUR]
  okfwiki.py body <seite> <datei|->
  okfwiki.py init [--profile NAME]
  okfwiki.py fundweg <seite> --art suche|modellvorschlag|material|person|zitatverfolgung
                 [--db DB --query Q] [--von SLUG] [--at ZEIT] [--by AKTEUR] [--add]
  okfwiki.py rechte [<seite>] [--aktion abbildung] [--json]
  okfwiki.py lizenz <seite> --name N [--url U] [--class K] | --fetch [--force] | --missing --fetch [--dry-run]
  okfwiki.py dashboard [--out PFAD] [--oeffentlich] [--open]

Globale Optionen: --config PFAD (sonst wiki.toml aufwärts ab cwd), --root DIR (Projektordner).
Als Bibliothek: Wiki.load(config=..., root=...) mit pages(), lint(), projections(),
rebuild(), new_page(), capture(), verify(), append_event():

  sys.path.insert(0, str(Path.home() / ".claude/skills/okf-wiki")); import okfwiki
"""

import argparse
import calendar
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import yaml

VERSION = "0.1.0"
SKILL_DIR = Path(__file__).resolve().parent
RESERVED = {"index.md", "log.md"}
STATUS = ("draft", "stable", "deprecated")
SOURCE_TYPE = "source"

MAX_FRONTMATTER_BYTES = 64 * 1024
SLUG_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
ISO_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$")
ACTOR_RE = re.compile(r"^(human:[\w.-]+|process:[\w.-]+|[\w.-]+/[\w.:-]+)$")
FRONTMATTER_RE = re.compile(r"---[ \t]*\n(.*?)^---[ \t]*\n?", re.S | re.M)
LINK_RE = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FOOTNOTE_REF_RE = re.compile(r"\[\^([^\]\s]+)\](?!:)")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([^\]\s]+)\]:", re.M)
CODE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
H2_RE = re.compile(r"^## +(.+?)\s*$", re.M)
CONTRADICTION_RE = re.compile(r"⚠️\s*\*\*Widerspruch:?\*\*")
# Dashboard: Codeblöcke dieser Sprachen (und unmarkierte mit Rahmenzeichen) sind Textdiagramme
DIAGRAM_LANGS = {"text", "txt", "plain", "plaintext", "ascii", "tree", "diagram"}
DIAGRAM_PRE_RE = re.compile(r'<pre><code(?: class="([^"]*)")?>(.*?)</code></pre>', re.S)
BOX_DRAWING_RE = re.compile(r"[─-╿]")
# ausdrücklicher Prüfvermerk: „zu prüfen“ am Blockanfang, in Anführungszeichen oder Klammern, nicht im Fließtext
CHECK_RE = re.compile(r"^\W*zu prüfen\b|[„“”\"‚‘(\[]\s*zu prüfen\b|\bzu prüfen\s*[)\]“”\"‘’]", re.I)

DEFAULT_CONFIG = {
    "wiki": {"title": "Wiki", "bundle": "wiki", "actor": "claude-code/unknown", "okf_version": "0.2",
             "requires_core": ""},
    "paths": {"events": "", "raw": "", "protected": []},
    "index": {"root": "overview", "sort": "title", "entry_tag": "einstieg", "badges": [], "star_field": "",
              "banner": "", "start_heading": "Zuerst lesen", "areas_heading": "Bereiche", "unit": "Seiten"},
    "log": {"title": "Aktivitätslog", "banner": "", "show_actor": False, "link_text": "title", "labels": {}},
    "enums": {},
    "lint": {"orphans": "inbound", "fulltext_access": ["fulltext"], "claims_section": "Kernaussagen",
             "priority_field": "", "severity": {}},
    "types": {},
    "export": {},
    "dashboard": {"path": "build/wiki-dashboard.html", "auto": False, "public_path": "",
                  "glossary": ["concept", "entity"]},   # Typen, deren Seiten ins Glossar kommen
    "taxonomy": {"field": "domain", "label": "Themenbereich"},
    "labels": {},
    "licenses": {"patterns": {}},     # weitere Muster: {"abda.de" = "vorbehalten"}
    "rights": {},                     # Matrix überschreiben: [rights.vorbehalten] abbildung = "nein: …"
    "scope": {"field": "", "label": "Umfang", "default": "", "derive": True},
    # Seiten mit einem Wert aus hidden fehlen in der öffentlichen Ausgabe (dashboard --oeffentlich) ganz
    "visibility": {"field": "", "label": "Sichtbarkeit", "default": "", "hidden": [], "derive": True},
    "fundweg": {"field": "fundweg"},
    # new source --doi/--pmid/--arxiv/--manuell: wohin Metadatenprüfung und Crossref-Hinweise gehen
    "sources": {"checked_field": "metadaten_geprueft", "updates_field": "crossref_hinweise",
                "manual_csl_type": "document"},
}

TYPE_DEFAULTS = {"folder": "", "label": "", "description": "", "required": [], "recommended": ["title", "description"],
                 "sections": [], "min_links": 2, "needs_footnotes": False, "stale_months": 0, "template": "",
                 "defaults": {}, "todo": {}}

# Platzhalter für Kurzreferat und Kernaussagen neuer Quellenkarten je access; [types.source.todo.<access>] ersetzt sie.
TODO_BY_ACCESS = {
    "citation": {"kurzreferat": "> [!todo] Nur Metadaten geprüft – Inhalt noch nicht gelesen. Nichts erfinden.",
                 "kernaussagen": "> [!todo] Erst nach Lektüre (Abstract oder Volltext)."},
    "abstract": {"kurzreferat": "> [!todo] Kurzreferat aus dem Abstract (als *abstract-basiert* kennzeichnen).",
                 "kernaussagen": "> [!todo] Höchstens Abstract-Aussagen, mit „(Abstract)“ markiert."},
    "fulltext": {"kurzreferat": "> [!todo] Kurzreferat aus dem Volltext.",
                 "kernaussagen": "> [!todo] Kernaussagen mit Fundstelle (S./Tab./Abschn.)."},
    "originaldokument": {"kurzreferat": "> [!todo] Kurzreferat aus dem Originaldokument.",
                         "kernaussagen": "> [!todo] Kernaussagen mit Fundstelle (Art./Abs./Abschn./Zeile)."},
}
CROSSREF_TYPES = {"journal-article": "article-journal", "proceedings-article": "paper-conference",
                  "posted-content": "article", "book-chapter": "chapter"}

LOG_LABELS = {
    "init": "Initialisierung", "bootstrap": "Bootstrap", "capture": "Quelle erfasst", "create": "Erstellt",
    "creation": "Erstellt", "update": "Aktualisiert", "verify": "Verifiziert", "deprecate": "Als veraltet markiert",
    "delete": "Entfernt", "merge": "Zusammengeführt", "enrich": "Angereichert", "export": "Export", "note": "Notiz",
}

# Schwere je Befund. Projekte überschreiben einzelne Codes in [lint.severity] (auch mit "off").
SEVERITY = {
    # OKF §8, §9, §11 – Konformität
    "bundle_missing": "error", "frontmatter_invalid": "error", "missing_type": "error",
    "root_index_frontmatter": "error", "okf_version_missing": "warn", "index_frontmatter": "error",
    "log_frontmatter": "error", "log_date_heading": "error", "log_order": "warn",
    # OKF §5, §7 – Herkunft, Vertrauen, Lebenszyklus
    "status_invalid": "error", "generated_invalid": "error", "verified_invalid": "error",
    "timestamp_invalid": "error", "actor_format": "warn", "stable_unverified": "warn", "stale": "warn",
    "source_invalid": "error", "source_duplicate_id": "error", "source_missing": "error",
    "footnote_unsourced": "error", "footnote_undefined": "warn", "source_uncited": "info",
    # Profil aus wiki.toml
    "missing_required": "error", "missing_recommended": "warn", "enum_invalid": "error",
    "type_unknown": "info", "type_folder_mismatch": "warn", "path_not_kebab": "warn",
    "sections_missing": "warn", "no_footnotes": "warn",
    # Graph
    "broken_link": "warn", "link_leaves_bundle": "warn", "few_links": "warn", "orphan": "warn",
    "contradiction_one_sided": "info", "projection_stale": "warn", "projection_unavailable": "info",
    # Quellenkarten und Rohquellen
    "raw_missing": "error", "raw_tampered": "error", "raw_uningested": "info",
    "fulltext_tampered": "error", "fulltext_absent": "warn", "fulltext_unanchored": "warn",
    "citation_with_claims": "error", "claim_on_citation_only": "warn",
    "priority_citation_only": "warn", "csl_incomplete": "error", "source_undated": "warn",
    # Lizenzen und Nutzungsrechte
    "license_missing": "warn", "license_unknown": "info", "license_unclassified": "info",
    "fulltext_rights": "warn", "fulltext_shared": "warn",
    # Umfang, Sichtbarkeit und Fundweg
    "scope_missing": "warn", "visibility_leak": "warn",
    "fundweg_missing": "info", "fundweg_incomplete": "warn", "fundweg_invalid": "error",
}

# Wie eine Quelle gefunden wurde; gemeinsames Vokabular aller Wikis.
FUNDWEG_ARTEN = {
    "suche": "Suche", "modellvorschlag": "Modellvorschlag", "material": "Material",
    "person": "Von der Person", "zitatverfolgung": "Zitatverfolgung",
}
SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}

# Lizenzklassen vom offensten zum strengsten. Passen mehrere Muster, gilt die strengste Klasse.
LICENSE_CLASSES = {
    "frei": "Gemeinfrei", "by": "Namensnennung", "sa": "Namensnennung, gleiche Lizenz",
    "nd": "Keine Bearbeitung", "nc": "Nicht kommerziell", "nc-nd": "Nicht kommerziell, keine Bearbeitung",
    "vorbehalten": "Alle Rechte vorbehalten", "unbekannt": "Unbekannt",
}
LICENSE_PATTERNS = [  # (Klasse, Muster auf Name und URL in Kleinbuchstaben)
    ("frei", r"cc0|publicdomain|public domain|gemeinfrei|amtliches werk|§ ?5 urhg|regierungswerk"
             r"|government work|dl-de/zero|unlicense"),
    ("by", r"\bcc[ -]?by\b|creativecommons\.org/licenses/by/|^(the )?mit( license)?$|opensource\.org/licenses/mit"
           r"|apache|\bbsd[- ]|^isc$|\bmpl\b|2011/833|dl-de/by|open government licen"),
    ("sa", r"by-sa\b|sharealike|\b[al]?gpl|copyleft|odbl"),
    ("nd", r"by-nd\b|noderiv|keine bearbeitung"),
    ("nc", r"by-nc\b|by-nc-sa|noncommercial|nicht kommerziell"),
    ("nc-nd", r"by-nc-nd|nc-nd"),
    ("vorbehalten", r"alle rechte vorbehalten|all rights reserved|nutzungsbedingungen|terms ?(of|and|&) ?(use|service|conditions)"
                    r"|termsandconditions|site-polic|/tdm\b|tdm[_-]?licen|userlicense|urheberrechtlich geschützt"
                    r"|proprietär|proprietary|abdruck|text-and-data-mining|copyright[_-]polic|10\.15223/policy-"
                    r"|arxiv\.org/licenses/nonexclusive"),
]
# Was die Person mit einer Quelle tun will. Werte: ja, bedingt, nein, fragen – jeweils mit Hinweis nach „:“.
RIGHTS_ACTIONS = {
    "zitieren": "Kurz zitieren mit Beleg",
    "volltext_ablegen": "Volltext lokal ablegen (eigene Arbeit)",
    "volltext_weitergeben": "Volltext weitergeben oder versionieren",
    "abbildung": "Abbildung oder Tabelle übernehmen",
    "bearbeiten": "Bearbeiten, übersetzen, nachzeichnen",
    "ki_auswertung": "Volltext maschinell auswerten lassen",
    "kommerziell": "Im kommerziellen Rahmen nutzen",
}
_BY = "mit Namensnennung und Lizenzangabe"
_QUOTE = "ja: im Rahmen des Zitatrechts (§ 51 UrhG)"
RIGHTS_MATRIX = {
    "frei": {a: "ja" for a in RIGHTS_ACTIONS},
    "by": {"zitieren": "ja", "volltext_ablegen": "ja", "volltext_weitergeben": f"bedingt: {_BY}",
           "abbildung": f"bedingt: {_BY}", "bearbeiten": f"bedingt: {_BY}, Änderungen kennzeichnen",
           "ki_auswertung": "ja", "kommerziell": "ja"},
    "sa": {"zitieren": "ja", "volltext_ablegen": "ja", "volltext_weitergeben": f"bedingt: {_BY}, unter gleicher Lizenz",
           "abbildung": f"bedingt: {_BY}, unter gleicher Lizenz",
           "bearbeiten": f"bedingt: {_BY}, Änderungen kennzeichnen, unter gleicher Lizenz",
           "ki_auswertung": "ja", "kommerziell": "ja"},
    "nd": {"zitieren": "ja", "volltext_ablegen": "ja", "volltext_weitergeben": f"bedingt: nur unverändert, {_BY}",
           "abbildung": f"bedingt: nur unverändert, {_BY}", "bearbeiten": "nein: Lizenz verbietet Bearbeitungen",
           "ki_auswertung": "ja", "kommerziell": "ja"},
    "nc": {"zitieren": "ja", "volltext_ablegen": "ja", "volltext_weitergeben": f"bedingt: nicht kommerziell, {_BY}",
           "abbildung": f"bedingt: nicht kommerziell, {_BY}", "bearbeiten": f"bedingt: nicht kommerziell, {_BY}",
           "ki_auswertung": "ja", "kommerziell": "nein: Lizenz erlaubt nur nicht kommerzielle Nutzung"},
    "nc-nd": {"zitieren": "ja", "volltext_ablegen": "ja",
              "volltext_weitergeben": f"bedingt: nicht kommerziell und unverändert, {_BY}",
              "abbildung": f"bedingt: nicht kommerziell und unverändert, {_BY}",
              "bearbeiten": "nein: Lizenz verbietet Bearbeitungen", "ki_auswertung": "ja",
              "kommerziell": "nein: Lizenz erlaubt nur nicht kommerzielle Nutzung"},
    "vorbehalten": {"zitieren": _QUOTE, "volltext_ablegen": "bedingt: nur für die eigene Arbeit, nicht weitergeben",
                    "volltext_weitergeben": "nein: ohne Erlaubnis des Rechteinhabers nicht",
                    "abbildung": "fragen: Genehmigung des Rechteinhabers nötig",
                    "bearbeiten": "nein: ohne Erlaubnis des Rechteinhabers nicht",
                    "ki_auswertung": "bedingt: nur eigene Auswertung; Text-und-Data-Mining-Vorbehalt des Anbieters "
                                     "beachten, nicht an Dienste geben, die speichern oder trainieren",
                    "kommerziell": "fragen: Nutzungsbedingungen prüfen"},
    "unbekannt": {**{a: "fragen: Lizenz zuerst klären" for a in RIGHTS_ACTIONS}, "zitieren": _QUOTE},
}
RIGHT_VALUES = ("ja", "bedingt", "nein", "fragen")


class WikiError(Exception):
    """Bedienfehler: fehlende Konfiguration, ungültiger Slug, vorhandene Datei …"""


# ---------------------------------------------------------------- Grundlagen


class _Loader(yaml.SafeLoader):
    """SafeLoader ohne Anker/Aliase und ohne implizite Zeitstempel.

    Zeitstempel bleiben Strings, damit OKF-Werte wie 2026-06-30T14:00:00Z unverändert
    geprüft und zurückgeschrieben werden.
    """

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise yaml.YAMLError("YAML-Aliase sind nicht erlaubt")
        if getattr(self.peek_event(), "anchor", None):
            raise yaml.YAMLError("YAML-Anker sind nicht erlaubt")
        return super().compose_node(parent, index)


_Loader.yaml_implicit_resolvers = {
    ch: [(tag, rx) for tag, rx in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for ch, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(text: str):
    return yaml.load(text, Loader=_Loader)


def dump_yaml(data) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=None, width=100)


def dump_key(key: str, value) -> str:
    """Ein Top-Level-Schlüssel im Blockstil; Blätter wie {by, at} bleiben einzeilig.

    PyYAML setzt eine Zuordnung, die nur Skalare enthält, ganz in Flow-Stil ({status: stable});
    deshalb Skalare im Blockstil und Sammlungen mit default_flow_style=None.
    """
    style = None if isinstance(value, (dict, list)) else False
    return yaml.safe_dump({key: value}, allow_unicode=True, sort_keys=False, default_flow_style=style, width=100)


def dump_frontmatter(fm: dict) -> str:
    return "".join(dump_key(k, v) for k, v in fm.items())


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def add_months(moment: dt.datetime, months: int) -> dt.datetime:
    year, month = divmod(moment.month - 1 + months, 12)
    year, month = moment.year + year, month + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day, hour=0, minute=0, second=0, microsecond=0)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def one_line(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def is_empty(value) -> bool:
    return value is None or value == "" or value == [] or value == {}


def is_timestamp(value) -> bool:
    return isinstance(value, str) and bool(ISO_TS_RE.match(value))


def as_datetime(value) -> dt.datetime | None:
    if is_timestamp(value):
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None


def as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def split_frontmatter(text: str) -> tuple[str | None, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def set_frontmatter_key(raw: str, key: str, value) -> str:
    """Ersetzt einen Top-Level-Schlüssel im Frontmatter-Text; alles andere bleibt byte-genau."""
    block = dump_key(key, value)
    lines = raw.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if re.match(rf"{re.escape(key)}\s*:", ln)), None)
    if start is None:
        return (raw if not raw or raw.endswith("\n") else raw + "\n") + block
    end = start + 1
    while end < len(lines) and (lines[end].startswith((" ", "\t", "- ")) or lines[end].strip() in ("", "-")):
        end += 1
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return "".join(lines[:start]) + block + "".join(lines[end:])


def kurzbeleg(csl: dict, narrative: bool = False) -> str:
    """APA-7-Kurzbeleg aus CSL: 'Morath et al., 2024' oder erzählend 'Morath et al. (2024)'."""
    names = [a.get("family") or a.get("literal", "?") for a in csl.get("author") or csl.get("editor") or []]
    names = names or ["o. A."]
    joiner = "und" if narrative else "&"
    if len(names) == 1:
        who = names[0]
    elif len(names) == 2:
        who = f"{names[0]} {joiner} {names[1]}"
    else:
        who = f"{names[0]} et al."
    year = ((csl.get("issued") or {}).get("date-parts") or [["o. D."]])[0][0]
    return f"{who} ({year})" if narrative else f"{who}, {year}"


INITIALS_RE = re.compile(r"(?:[A-ZÄÖÜ][a-zäöü]?\.?[\s-]*)+")
LOCATOR_RE = re.compile(
    r"(?:S\.|Seite|Tab\.|Abb\.|Abschn\.|Kap\.|Art\.|Abs\.|§|Folie|Zeile|Rn\.|Anhang|Erwägungsgrund)\s*[\dIVXLC][\w.–-]*"
    r"(?:(?:,\s*|\s+)(?:(?:S\.|Seite|Tab\.|Abb\.|Abschn\.|Kap\.|Art\.|Abs\.|§|Nr\.|Anhang|und|u\.)\s*)?\d[\w.–-]*)*")


def csl_names(raw) -> list[dict]:
    """Autorenliste aus Strings: "Nachname, V." oder abwechselnd "Nachname", "V. M." (thesis-wiki-Bootstrap)."""
    items = [one_line(a).strip(",; ") for a in as_list(raw) if one_line(a).strip(",; ")]
    out, i = [], 0
    while i < len(items):
        name = items[i]
        if "," in name:
            family, given = name.split(",", 1)
            out.append({"family": family.strip(), "given": given.strip()})
            i += 1
        elif i + 1 < len(items) and INITIALS_RE.fullmatch(items[i + 1]):
            out.append({"family": name, "given": items[i + 1]})
            i += 2
        else:
            out.append({"literal": name})
            i += 1
    return out


def csl_date(value) -> dict | None:
    m = re.match(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", str(value or ""))
    if not m:
        return None
    return {"date-parts": [[int(x) for x in m.groups() if x]]}


UNKNOWN_LICENSE_RE = re.compile(r"^(unknown|unbekannt|unklar|n/?a|none|keine angabe|-+)?$", re.I)
# bewusst undatierte Quelle (date: o. J.): keine Warnung source_undated
UNDATED_RE = re.compile(r"^\s*(o\.\s*j\.?|n\.\s*d\.?|undatiert|ohne datum)\s*$", re.I)


def license_parts(lic) -> tuple[str, str]:
    """(Name, URL) aus license: {name, url, …} oder einem bloßen String."""
    if isinstance(lic, dict):
        return str(lic.get("name") or "").strip(), str(lic.get("url") or "").strip()
    return (str(lic).strip() if lic else ""), ""


def classify_license(lic, patterns: dict | None = None) -> tuple[str, bool]:
    """(Lizenzklasse, eingeordnet). license.class im Frontmatter geht vor, sonst die strengste passende Klasse.

    eingeordnet ist False, wenn ein Name dasteht, aber kein Muster passt.
    """
    if isinstance(lic, dict) and lic.get("class") in LICENSE_CLASSES:
        return lic["class"], True
    name, url = license_parts(lic)
    rules = LICENSE_PATTERNS + [(cls, pat) for pat, cls in (patterns or {}).items() if cls in LICENSE_CLASSES]
    found = {cls for text in (name.lower(), url.lower()) if text for cls, pat in rules if re.search(pat, text)}
    if not found:
        return "unbekannt", bool(UNKNOWN_LICENSE_RE.match(name))
    order = list(LICENSE_CLASSES)
    return max(found, key=order.index), True


def parse_right(value) -> tuple[str, str]:
    """„bedingt: mit Namensnennung“ → ("bedingt", "mit Namensnennung"); Unlesbares gilt als „fragen“."""
    text = str(value or "").strip()
    head, _, note = text.partition(":")
    if head.strip().lower() in RIGHT_VALUES:
        return head.strip().lower(), note.strip()
    return "fragen", text


def license_name_from(text: str) -> str:
    """Lesbarer Lizenzname aus einer Lizenz-URL oder Kurzangabe (Crossref, DataCite, Europe PMC, OpenAlex); leer, wenn unklar."""
    t = str(text or "").strip()
    m = re.search(r"creativecommons\.org/(licenses|publicdomain)/([a-z-]+)/(\d\.\d)(/igo)?", t, re.I)
    if m:
        if m.group(1).lower() == "publicdomain":
            return f"CC0 {m.group(3)}" if m.group(2).lower() == "zero" else "Public Domain Mark"
        return f"CC {m.group(2).upper()} {m.group(3)}" + (" IGO" if m.group(4) else "")
    m = re.match(r"^cc[ -]?(by(?:-(?:nc|nd|sa))*|0)\b\s*([\d.]+)?", t, re.I)
    if m:
        name = "CC0" if m.group(1) == "0" else f"CC {m.group(1).upper()}"
        return name + (f" {m.group(2)}" if m.group(2) else "")
    if classify_license({"name": "", "url": t})[0] == "vorbehalten":
        return "Nutzungsbedingungen des Verlags"
    return ""


def http_json(url: str, timeout: int = 20, accept: str = "application/json"):
    """GET auf eine offizielle API (Crossref, Europe PMC, DataCite, OpenAlex); ohne Kennungen der Person im Kopf."""
    req = urllib.request.Request(url, headers={"User-Agent": f"okf-wiki/{VERSION}", "Accept": accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def http_bytes(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": f"okf-wiki/{VERSION}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def today_parts() -> dict:
    return {"date-parts": [[int(x) for x in dt.date.today().isoformat().split("-")]]}


def crossref_csl(m: dict) -> dict:
    """CSL-JSON ohne id aus der Crossref-Antwort `message` (wie qz lookup.py to_csl)."""
    def year(key):
        return ((m.get(key) or {}).get("date-parts") or [[None]])[0][0]
    y = year("published-print") or year("issued")
    csl = {
        "type": CROSSREF_TYPES.get(m.get("type"), m.get("type") or "article-journal"),
        "title": re.sub(r"<[^>]+>", "", (m.get("title") or [""])[0]),
        "author": [{k: a[k] for k in ("family", "given") if k in a} or {"literal": a.get("name", "")}
                   for a in m.get("author", [])],
        "issued": {"date-parts": [[y]]} if y else None,
        "container-title": (m.get("container-title") or [""])[0],
        "volume": m.get("volume"), "issue": m.get("issue"), "page": m.get("page"), "DOI": m.get("DOI"),
    }
    return {k: v for k, v in csl.items() if v}


DATACITE_CSL_FIELDS = ("type", "title", "author", "issued", "container-title", "publisher", "volume", "issue",
                       "page", "number", "version", "URL")


def datacite_csl(doi: str) -> dict:
    """CSL-JSON ohne id von DataCite (Zenodo, arXiv, OSF, Datensätze) für DOIs, die Crossref nicht kennt.

    DataCite liefert CSL per Inhaltsaushandlung; übernommen werden nur bibliographische Felder, kein Abstract.
    """
    raw = http_json(f"https://api.datacite.org/dois/{urllib.parse.quote(doi)}",
                    accept="application/vnd.citationstyles.csl+json")
    csl = {k: raw[k] for k in DATACITE_CSL_FIELDS if raw.get(k)}
    csl["DOI"] = doi
    return csl


def datacite_rights(doi: str) -> list[dict]:
    """rightsList des DataCite-Eintrags ([{rights, rightsUri, …}]); leer, wenn DataCite die DOI nicht kennt."""
    try:
        return http_json(f"https://api.datacite.org/dois/{urllib.parse.quote(doi)}")["data"]["attributes"].get(
            "rightsList") or []
    except (OSError, ValueError, KeyError):
        return []


def pubmed_csl(pmid: str) -> dict:
    """CSL aus PubMed-esummary, für Artikel mit lückenhaftem Crossref-Eintrag oder ohne DOI."""
    q = urllib.parse.urlencode({"db": "pubmed", "id": pmid, "retmode": "json"})
    r = http_json(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{q}")["result"][pmid]
    authors = []
    for a in r.get("authors", []):
        if a.get("authtype") != "Author":
            continue
        family, _, initials = a["name"].rpartition(" ")
        authors.append({"family": family or initials, "given": ". ".join(initials) + "." if family else ""})
    csl = {"type": "article-journal", "title": r["title"].rstrip("."), "author": authors,
           "issued": {"date-parts": [[int(r["pubdate"][:4])]]}, "container-title": r.get("fulljournalname"),
           "volume": r.get("volume"), "issue": r.get("issue"), "page": r.get("pages"), "PMID": pmid}
    doi = next((x["value"] for x in r.get("articleids", []) if x["idtype"] == "doi"), None)
    if doi:
        csl["DOI"] = doi
    else:
        csl["URL"] = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        csl["accessed"] = today_parts()
    return {k: v for k, v in csl.items() if v}


def arxiv_csl(aid: str) -> dict:
    import xml.etree.ElementTree as ET
    q = urllib.parse.urlencode({"id_list": aid, "max_results": 1})
    ns = {"a": "http://www.w3.org/2005/Atom"}
    e = ET.fromstring(http_bytes(f"https://export.arxiv.org/api/query?{q}")).find("a:entry", ns)
    if e is None or not e.findtext("a:title", "", ns).strip():
        raise WikiError(f"arXiv:{aid} nicht gefunden")
    authors = []
    for a in e.findall("a:author", ns):
        parts = a.findtext("a:name", "", ns).rsplit(" ", 1)
        authors.append({"family": parts[-1], "given": parts[0]} if len(parts) == 2 else {"literal": parts[0]})
    bare = aid.split("v")[0]
    return {"type": "article", "title": " ".join(e.findtext("a:title", "", ns).split()), "author": authors,
            "issued": {"date-parts": [[int(e.findtext("a:published", "", ns)[:4])]]},
            "publisher": "arXiv", "number": f"arXiv:{bare}", "DOI": f"10.48550/arXiv.{bare}"}


def deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def find_config(start: Path) -> Path | None:
    for directory in [start, *start.parents]:
        candidate = directory / "wiki.toml"
        if candidate.is_file():
            return candidate
    return None


@dataclass
class Page:
    path: Path
    id: str
    fm: dict | None
    body: str
    raw_fm: str | None
    error: str | None = None

    @property
    def type(self) -> str:
        return one_line((self.fm or {}).get("type"))

    @property
    def title(self) -> str:
        return one_line((self.fm or {}).get("title")) or self.path.stem.replace("-", " ")

    @property
    def description(self) -> str:
        return one_line((self.fm or {}).get("description"))

    @property
    def folder(self) -> str:
        return self.id.split("/", 1)[0] if "/" in self.id else ""


@dataclass
class Finding:
    severity: str
    code: str
    path: str
    message: str

    def as_dict(self) -> dict:
        return {"severity": self.severity, "code": self.code, "path": self.path, "message": self.message}


# ---------------------------------------------------------------------- Wiki


class Wiki:
    def __init__(self, root: Path, cfg: dict, config_path: Path | None = None):
        self.root = root.resolve()
        self.cfg = cfg
        self.config_path = config_path
        self.bundle = self.root / cfg["wiki"]["bundle"]
        events = cfg["paths"].get("events") or f"{cfg['wiki']['bundle']}/.events.jsonl"
        self.events_path = self.root / events
        self.raw = self.root / cfg["paths"]["raw"] if cfg["paths"].get("raw") else None
        self.actor = os.environ.get("WIKI_ACTOR") or cfg["wiki"]["actor"]
        self.types: dict[str, dict] = {}
        for name, spec in cfg["types"].items():
            merged = {**TYPE_DEFAULTS, **({"min_links": 0} if name == SOURCE_TYPE else {}), **spec}
            merged["folder"] = merged["folder"] or name
            merged["label"] = merged["label"] or merged["folder"]
            self.types[name] = merged
        self.folder_type = {spec["folder"]: name for name, spec in self.types.items()}
        self._pages: list[Page] | None = None
        self.public = False               # public_view(): öffentliche Ausgabe ohne verborgene Seiten
        self.withheld: set[Path] = set()  # public_view(): Pfade der weggelassenen Seiten
        required = cfg["wiki"].get("requires_core")
        if required and tuple(map(int, VERSION.split(".")[:2])) < tuple(map(int, str(required).split(".")[:2])):
            raise WikiError(f"wiki.toml verlangt okf-wiki {required}, installiert ist {VERSION}")

    @classmethod
    def load(cls, config: str | Path | None = None, root: str | Path | None = None,
             start: str | Path | None = None) -> "Wiki":
        if config:
            config_path = Path(config).expanduser().resolve()
        elif root:
            config_path = Path(root).expanduser().resolve() / "wiki.toml"
        else:
            config_path = find_config(Path(start or os.getcwd()).resolve())
        if not config_path or not config_path.is_file():
            raise WikiError("keine wiki.toml gefunden (Projektordner mit --root oder Datei mit --config angeben)")
        with config_path.open("rb") as f:
            cfg = deep_merge(DEFAULT_CONFIG, tomllib.load(f))
        project = Path(root).expanduser().resolve() if root else config_path.parent
        return cls(project, cfg, config_path)

    # ------------------------------------------------------------ Lesen

    def rel(self, path) -> str:
        if not isinstance(path, Path):
            return str(path)
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(path)

    def page_id(self, path: Path) -> str:
        """Konzept-ID nach OKF §2: Pfad im Bundle ohne .md."""
        return path.relative_to(self.bundle).with_suffix("").as_posix()

    def _hidden(self, path: Path) -> bool:
        return any(part.startswith(".") for part in path.relative_to(self.bundle).parts)

    def parse(self, path: Path) -> Page:
        text = path.read_text(encoding="utf-8")
        raw, body = split_frontmatter(text)
        pid = self.page_id(path)
        if raw is None:
            return Page(path, pid, None, text, None, "kein Frontmatter-Block")
        if len(raw.encode("utf-8")) > MAX_FRONTMATTER_BYTES:
            return Page(path, pid, None, body, raw, "Frontmatter größer als 64 KB")
        try:
            fm = load_yaml(raw)
        except yaml.YAMLError as exc:
            return Page(path, pid, None, body, raw, f"YAML nicht lesbar: {exc}".splitlines()[0])
        if fm is None:
            fm = {}
        if not isinstance(fm, dict):
            return Page(path, pid, None, body, raw, "Frontmatter ist keine Zuordnung")
        return Page(path, pid, fm, body, raw)

    def pages(self) -> list[Page]:
        if self._pages is None:
            found = []
            if self.bundle.is_dir():
                for path in sorted(self.bundle.rglob("*.md")):
                    if path.name not in RESERVED and not self._hidden(path):
                        found.append(self.parse(path))
            self._pages = found
        return self._pages

    def resolve(self, src: Path, target: str) -> Path | None:
        """Interner Linkziel-Pfad oder None für externe Links, Anker und Beschreibungen."""
        target = str(target).strip()
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#") or " " in target:
            return None
        target = target.split("#", 1)[0]
        if not target:
            return None
        base = self.bundle if target.startswith("/") else src.parent
        resolved = (base / target.lstrip("/")).resolve()
        if target.endswith("/"):
            resolved = resolved / "index.md"
        return resolved

    def read_events(self) -> list[dict]:
        if not self.events_path.exists():
            return []
        events = []
        for line in self.events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    # ------------------------------------------------------------ Schreiben

    def append_event(self, kind: str, page: str, detail: str = "", by: str | None = None) -> dict:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        event = {"ts": now_iso(), "kind": kind, "page": page, "by": by or self.actor, "detail": one_line(detail)}
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def page_path(self, page: str) -> Path:
        page = page.removeprefix("/").removesuffix(".md")
        path = self.bundle / f"{page}.md"
        if not path.exists():
            raise WikiError(f"Seite fehlt: {self.rel(path)}")
        return path

    def _write_frontmatter(self, path: Path, updates: dict) -> None:
        """Setzt Top-Level-Schlüssel chirurgisch und prüft das Ergebnis vor dem Schreiben."""
        text = path.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        if not m:
            raise WikiError(f"{self.rel(path)}: kein Frontmatter")
        raw = m.group(1)
        for key, value in updates.items():
            raw = set_frontmatter_key(raw, key, value)
        try:
            check = load_yaml(raw)
        except yaml.YAMLError:
            check = None
        if not isinstance(check, dict) or any(check.get(k) != v for k, v in updates.items()):
            raise WikiError(f"{self.rel(path)}: Frontmatter ließ sich nicht sicher ändern, bitte von Hand")
        path.write_text(text[:m.start(1)] + raw + text[m.end(1):], encoding="utf-8")
        self._pages = None

    def verify(self, page: str, by: str, status: str | None = None, note: str = "") -> Path:
        if not ACTOR_RE.match(by):
            raise WikiError("--by muss der Akteurskonvention folgen, z. B. human:<id> (OKF §7)")
        path = self.page_path(page)
        parsed = self.parse(path)
        if parsed.error:
            raise WikiError(f"Frontmatter nicht lesbar: {parsed.error}")
        verified = as_list(parsed.fm.get("verified")) + [{"by": by, "at": now_iso()}]
        updates = {"verified": verified}
        if status:
            updates["status"] = status
        self._write_frontmatter(path, updates)
        self.append_event("verify", parsed.id, note, by=by)
        return path

    def replace_body(self, page: str, body: str, detail: str = "") -> Path:
        path = self.page_path(page)
        text = path.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        if not m:
            raise WikiError(f"{self.rel(path)}: kein Frontmatter")
        path.write_text(text[:m.end()] + "\n" + body.strip() + "\n", encoding="utf-8")
        self._pages = None
        self.append_event("update", self.page_id(path), detail or "Inhalt geschrieben")
        return path

    def new_page(self, type_: str, slug: str, title: str = "", description: str = "", sources=(), tags=(),
                 access: str | None = None, resource: str | None = None, csl: dict | None = None,
                 extra: dict | None = None) -> Path:
        spec = self.types.get(type_)
        if spec is None:
            raise WikiError(f"Typ {type_!r} fehlt in wiki.toml [types] ({', '.join(self.types) or 'keine'})")
        if not SLUG_RE.fullmatch(slug):
            raise WikiError(f"Ungültiger Slug {slug!r}: nur kebab-case (a-z, 0-9, -)")
        path = self.bundle / spec["folder"] / f"{slug}.md"
        if path.exists():
            raise WikiError(f"{self.rel(path)} existiert schon – Karte von Hand bearbeiten")
        if csl:
            csl = {k: v for k, v in csl.items() if k != "id"}
            title = title or one_line(csl.get("title"))
            if not resource:
                resource = f"https://doi.org/{csl['DOI']}" if csl.get("DOI") else csl.get("URL")
        if not title:
            raise WikiError("--title fehlt")
        fm = {"type": type_, "title": title, "description": description}
        if resource:
            fm["resource"] = resource
        fm["status"] = "draft"
        fm["tags"] = list(tags)
        if csl:
            fm["aliases"] = [kurzbeleg(csl)]
        if access:
            fm["access"] = access
        if type_ == SOURCE_TYPE:
            fm["license"] = {"name": "unknown", "url": None}
        if csl:
            fm[self.cfg["export"].get("csl", {}).get("field", "csl")] = csl
        entries = []
        source_folder = self.types.get(SOURCE_TYPE, {}).get("folder", "sources")
        for sid in sources:
            card = self.bundle / source_folder / f"{sid}.md"
            if not card.exists():
                raise WikiError(f"Quellenkarte {self.rel(card)} fehlt")
            entries.append({"id": sid, "resource": f"/{source_folder}/{sid}.md", "title": self.parse(card).title})
        if entries:
            fm["sources"] = entries
        for key, value in spec.get("defaults", {}).items():   # [types.X] defaults, z. B. evidenz = "peer-reviewed"
            if key not in fm and key not in (extra or {}):
                fm[key] = value
        fm.update(extra or {})
        titles = {e["id"]: e.pop("title") for e in entries}
        fm["generated"] = {"by": self.actor, "at": now_iso()}
        if spec["stale_months"]:
            moment = add_months(dt.datetime.now(dt.timezone.utc), int(spec["stale_months"]))
            fm["stale_after"] = moment.strftime("%Y-%m-%dT%H:%M:%SZ")
        body = self.render_template(type_, fm, csl, titles)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n" + dump_frontmatter(fm) + "---\n\n" + body.lstrip(), encoding="utf-8")
        self._pages = None
        self.append_event("create", self.page_id(path), title if self.cfg["log"].get("link_text") == "id" else "")
        return path

    def render_template(self, type_: str, fm: dict, csl: dict | None, titles: dict | None = None) -> str:
        spec = self.types[type_]
        access = fm.get("access") or ""
        todo = {**TODO_BY_ACCESS.get(access, {}), **spec.get("todo", {}).get(access, {})}
        flags = as_list(fm.get(self.cfg["sources"]["updates_field"]))
        values = {
            "title": fm.get("title", ""), "description": fm.get("description", ""), "access": access,
            "kurzbeleg": kurzbeleg(csl, narrative=True) if csl else fm.get("title", ""),
            "apa": (self.render_apa([dict(csl, id="x")]) or "") if csl else "",
            "footnotes": "\n".join(f"[^{s['id']}]: [{(titles or {}).get(s['id'], s['id'])}]({s['resource']})"
                                   for s in fm.get("sources", [])),
            "todo_kurzreferat": todo.get("kurzreferat", "> [!todo] Ausstehend."),
            "todo_kernaussagen": todo.get("kernaussagen", "> [!todo] Ausstehend."),
            "hinweise": f"\n- ⚠ Crossref meldet: {', '.join(map(str, flags))} – vor Nutzung ansehen." if flags else "",
        }
        if spec["template"]:
            template = self.template_path(spec["template"]).read_text(encoding="utf-8")

            def fill(m):
                key = m.group(1)
                if key.startswith("fm."):
                    return one_line(fm.get(key[3:], ""))
                return str(values.get(key, m.group(0)))
            return re.sub(r"\{\{([\w.]+)\}\}", fill, template)
        lines = [f"# {values['kurzbeleg'] + ': ' if csl else ''}{values['title']}", ""]
        if values["apa"]:
            lines += [f"> {values['apa']}", ""]
        elif values["description"] and type_ != SOURCE_TYPE:
            lines += [values["description"], ""]
        claims = self.cfg["lint"]["claims_section"].lower()
        for section in spec["sections"]:
            text = "> [!todo] Ausstehend."
            if type_ == SOURCE_TYPE and section.lower().startswith("kurzreferat"):
                text = values["todo_kurzreferat"]
            elif type_ == SOURCE_TYPE and section.lower().startswith(claims):
                text = values["todo_kernaussagen"]
            lines += [f"## {section}", "", text, ""]
        if values["footnotes"]:
            lines += [values["footnotes"], ""]
        return "\n".join(lines)

    def template_path(self, name: str) -> Path:
        """Vorlage aus [types.X] template: neben der wiki.toml, sonst im Skill (profiles/, templates/)."""
        base = self.config_path.parent if self.config_path else self.root
        for candidate in (base / name, SKILL_DIR / "profiles" / name, SKILL_DIR / "templates" / name):
            if candidate.is_file():
                return candidate
        raise WikiError(f"Vorlage {name} fehlt (gesucht neben der wiki.toml und im Skill unter profiles/, templates/)")

    def fetch_source(self, doi: str = "", pmid: str = "", arxiv: str = "") -> tuple[dict, str, dict, list]:
        """(csl, resource, Metadatenprüfung, Crossref-Hinweise) über Crossref (sonst DataCite), PubMed oder arXiv."""
        try:
            if doi:
                try:
                    m = http_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")["message"]
                except urllib.error.HTTPError as exc:
                    if exc.code != 404:
                        raise
                    # Crossref kennt die DOI nicht: DataCite-DOIs (Zenodo, arXiv, OSF) dort nachschlagen
                    csl = datacite_csl(doi)
                    return csl, f"https://doi.org/{doi}", {"by": "process:datacite", "at": now_iso()}, []
                csl = crossref_csl(m)
                flags = [u.get("type") for u in m.get("updated-by", []) if u.get("type")]
                return csl, f"https://doi.org/{csl['DOI']}", {"by": "process:crossref", "at": now_iso()}, flags
            if pmid:
                csl = pubmed_csl(pmid)
                resource = f"https://doi.org/{csl['DOI']}" if csl.get("DOI") else csl["URL"]
                return csl, resource, {"by": "process:pubmed", "at": now_iso()}, []
            if arxiv:
                return arxiv_csl(arxiv), f"https://arxiv.org/abs/{arxiv}", {"by": "process:arxiv", "at": now_iso()}, []
        except (OSError, ValueError, KeyError) as exc:
            raise WikiError(f"Metadatenabruf fehlgeschlagen ({doi or pmid or arxiv}): {exc}") from exc
        raise WikiError("--doi, --pmid oder --arxiv angeben")

    def capture(self, slug: str, url: str, files, commit: str | None = None, license_name: str | None = None,
                license_url: str | None = None, note: str | None = None, source_path: str | None = None) -> Path:
        """Rohquelle unveränderlich als Paket <raw>/<slug>/original/ + manifest.json ablegen."""
        if self.raw is None:
            raise WikiError("wiki.toml hat kein [paths] raw – Volltexte mit `hash` als fulltext-Block binden")
        if not SLUG_RE.fullmatch(slug):
            raise WikiError(f"Ungültiger Slug {slug!r}: nur kebab-case")
        packet = self.raw / slug
        if packet.exists():
            raise WikiError(f"{self.rel(packet)} existiert. Rohquellen sind unveränderlich; neue Fassung als {slug}-v2")
        paths = [Path(f).expanduser().resolve() for f in files]
        for f in paths:
            if not f.is_file() or f.is_symlink():
                raise WikiError(f"Keine reguläre Datei: {f}")
        (packet / "original").mkdir(parents=True)
        entries, used = [], set()
        for f in paths:
            name = f.name
            while name in used:
                name = f"{f.parent.name}-{name}"
            used.add(name)
            target = packet / "original" / name
            shutil.copyfile(f, target)
            os.chmod(target, 0o444)
            entries.append({"path": f"original/{name}", "sha256": sha256_of(target),
                            "bytes": target.stat().st_size, "source_path": source_path})
        manifest = {"id": slug, "url": url, "retrieved_at": now_iso(), "retrieved_by": self.actor, "commit": commit,
                    "license": {"name": license_name, "url": license_url} if license_name else None,
                    "note": note, "files": entries}
        (packet / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
        os.chmod(packet / "manifest.json", 0o444)
        self.append_event("capture", self.rel(packet), note or url)
        return packet

    def fulltext_block(self, path: str | Path, retrieved_from: str | None = None) -> dict:
        target = (self.root / path).resolve()
        if not target.is_file():
            raise WikiError(f"Keine Datei: {target}")
        block = {"path": self.rel(target), "sha256": sha256_of(target), "retrieved_at": now_iso()}
        if retrieved_from:
            block["retrieved_from"] = retrieved_from
        return {"fulltext": block}

    # ------------------------------------------------------------ Projektionen

    def _sort_key(self, page: Page):
        return page.path.stem if self.cfg["index"]["sort"] == "slug" else page.title.lower()

    def _entry(self, page: Page, href: str) -> str:
        idx = self.cfg["index"]
        title = page.title
        star = idx.get("star_field")
        if star and (page.fm or {}).get(star):
            title += " ★"
        badges = "".join(f" `{v}`" for v in (self._badge(page, b) for b in idx.get("badges", [])) if v)
        return f"* [{title}]({href}){badges}" + (f" - {page.description}" if page.description else "")

    def _badge(self, page: Page, field: str) -> str:
        fm = page.fm or {}
        if field == "license":  # Lizenzname, bei langen Mischangaben die Klasse
            if page.type != SOURCE_TYPE and "license" not in fm:
                return ""
            lic = self.license_of(page)
            if lic["cls"] == "unbekannt":
                return "Lizenz unbekannt" if lic["known"] else "Lizenz nicht eingeordnet"
            return lic["name"] if lic["name"] and len(lic["name"]) <= 28 else lic["label"]
        return str(fm[field]) if fm.get(field) else ""

    def _folder_label(self, name: str) -> tuple[str, str]:
        spec = self.types.get(self.folder_type.get(name, ""), {})
        return spec.get("label") or name, spec.get("description", "")

    def _ordered_folders(self) -> list[str]:
        present = [d.name for d in sorted(self.bundle.iterdir()) if d.is_dir() and not d.name.startswith(".")]
        known = [spec["folder"] for spec in self.types.values() if spec["folder"] in present]
        return known + [d for d in present if d not in known]

    def learning_path(self) -> list[Page]:
        """Einstiegsseiten (Schlagwort aus [index] entry_tag) nach `order`, dann Titel: „Zuerst lesen“
        im Root-Index und Lernpfad im Dashboard."""
        tag = self.cfg["index"].get("entry_tag")
        start = [p for p in self.pages() if p.fm is not None and tag and tag in as_list(p.fm.get("tags"))]
        return sorted(start, key=lambda p: (p.fm.get("order", 99), p.title.lower()))

    def render_root_index(self) -> str:
        idx = self.cfg["index"]
        lines = ["---", f'okf_version: "{self.cfg["wiki"]["okf_version"]}"', "---", "",
                 f"# {self.cfg['wiki']['title']}", ""]
        if idx.get("banner"):
            lines += [idx["banner"], ""]
        pages = [p for p in self.pages() if p.fm is not None]
        start = self.learning_path()
        if start:
            lines += [f"# {idx['start_heading']}", ""] if idx.get("start_heading") else []
            for p in start:
                lines.append(self._entry(p, p.path.relative_to(self.bundle).as_posix()))
            lines.append("")
        folders = self._ordered_folders()
        if idx["root"] == "full":
            for name in folders:
                label, _ = self._folder_label(name)
                members = sorted((p for p in pages if p.folder == name), key=self._sort_key)
                lines += [f"# {label}", "", f"* [{label}]({name}/) - {len(members)} {idx['unit']}"]
                lines += [self._entry(p, f"/{p.id}.md") for p in members] + [""]
        else:
            lines += [f"# {idx['areas_heading']}", ""]
            for name in folders:
                label, desc = self._folder_label(name)
                n = sum(1 for p in self.pages() if p.folder == name)
                lines.append(f"* [{label}]({name}/) - " + (f"{desc} " if desc else "") + f"({n} {idx['unit']})")
            lines.append("")
        root_pages = [p for p in pages if not p.folder]
        if root_pages:
            lines += ["# Seiten im Wurzelordner", ""]
            lines += [self._entry(p, p.path.name) for p in sorted(root_pages, key=self._sort_key)] + [""]
        return "\n".join(lines).rstrip() + "\n"

    def render_dir_index(self, directory: Path) -> str:
        rel = directory.relative_to(self.bundle).as_posix()
        label = self._folder_label(rel)[0] if "/" not in rel else directory.name
        lines = [f"# {label}", ""]
        if self.cfg["index"].get("banner"):
            lines += [self.cfg["index"]["banner"], ""]
        members = [p for p in self.pages() if p.path.parent == directory]
        lines += [self._entry(p, p.path.name) for p in sorted(members, key=self._sort_key)]
        subdirs = [d for d in sorted(directory.iterdir())
                   if d.is_dir() and not d.name.startswith(".") and any(p.path.is_relative_to(d) for p in self.pages())]
        if subdirs:
            lines += ["", "# Unterordner", ""] if members else []
            lines += [f"* [{d.name}]({d.name}/)" for d in subdirs]
        if not members and not subdirs:
            lines.append("_(noch keine)_")
        return "\n".join(lines).rstrip() + "\n"

    def _event_target(self, page: str, titles: dict[str, str], stems: dict[str, list[str]]) -> str:
        pid = page.removeprefix("/").removesuffix(".md")
        if pid not in titles and len(stems.get(pid, [])) == 1:
            pid = stems[pid][0]  # ältere Ereignisse nennen nur den Slug
        if pid in titles:
            text = pid if self.cfg["log"].get("link_text") == "id" else titles[pid]
            return f"[{text}](/{pid}.md)"
        return f"`{page}`"

    def render_log(self) -> str:
        logcfg = self.cfg["log"]
        labels = {**LOG_LABELS, **logcfg.get("labels", {})}
        titles = {p.id: p.title for p in self.pages()}
        stems: dict[str, list[str]] = {}
        for pid in titles:
            stems.setdefault(pid.rsplit("/", 1)[-1], []).append(pid)
        seen: set[str] = set()
        days: dict[str, list[str]] = {}
        for e in self.read_events():
            day = str(e.get("ts", ""))[:10]
            page = str(e.get("page", ""))
            kind = str(e.get("kind", "note"))
            detail = one_line(e.get("detail"))
            if kind in ("write", "edit"):
                label = labels["update"] if page in seen else labels["create"]
                detail = ""
            else:
                label = labels.get(kind, kind.capitalize())
            seen.add(page)
            text = f"* **{label}**: {self._event_target(page, titles, stems)}" + (f" – {detail}" if detail else "")
            if logcfg.get("show_actor") and e.get("by"):
                text += f" ({e['by']})"
            days.setdefault(day, []).append(text)
        lines = [f"# {logcfg['title']}", ""]
        if logcfg.get("banner"):
            lines += [logcfg["banner"], ""]
        for day in sorted(days, reverse=True):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
                continue
            lines += [f"## {day}", ""]
            done: set[str] = set()
            for text in reversed(days[day]):  # OKF §9: neueste zuerst
                if text not in done:
                    done.add(text)
                    lines.append(text)
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def csl_items(self) -> list[dict]:
        field = self.cfg["export"].get("csl", {}).get("field", "csl")
        items = []
        for p in self.pages():
            if p.fm and p.type == SOURCE_TYPE and isinstance(p.fm.get(field), dict):
                items.append(dict({"id": p.path.stem}, **p.fm[field]))
        return sorted(items, key=lambda r: r["id"])

    def render_apa(self, items: list[dict]) -> str | None:
        """Literaturangaben über pandoc --citeproc; None ohne pandoc oder Zitierstil."""
        spec = self.cfg["export"].get("csl", {})
        pandoc = shutil.which("pandoc")
        if not pandoc or not items:
            return None
        doc = f"---\nnocite: '@*'\nlang: {spec.get('lang', 'de-DE')}\n---\n"
        with tempfile.TemporaryDirectory() as tmp:
            bib = Path(tmp) / "refs.json"
            bib.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
            cmd = [pandoc, "--citeproc", f"--bibliography={bib}", "-f", "markdown",
                   "-t", "markdown-smart-fenced_divs-native_divs-raw_html-citations", "--wrap=none"]
            if spec.get("style"):
                cmd.append(f"--csl={self.root / spec['style']}")
            try:
                out = subprocess.run(cmd, input=doc, capture_output=True, text=True, timeout=180, check=True).stdout
            except (OSError, subprocess.SubprocessError):
                return None
        return out.strip()

    def projections(self, include_slow: bool = True) -> dict[Path, str]:
        """{Pfad: Inhalt} aller generierten Dateien: index.md je Ordner, log.md, Exporte."""
        out = {self.bundle / "index.md": self.render_root_index(), self.bundle / "log.md": self.render_log()}
        for d in sorted(p for p in self.bundle.rglob("*") if p.is_dir()):
            if not self._hidden(d) and any(p.path.is_relative_to(d) for p in self.pages()):
                out[d / "index.md"] = self.render_dir_index(d)
        export = self.cfg["export"]
        if export.get("csl", {}).get("path"):
            out[self.root / export["csl"]["path"]] = (
                json.dumps(self.csl_items(), ensure_ascii=False, indent=1) + "\n")
        bib = export.get("bibliography", {})
        if bib.get("path") and include_slow:
            rendered = self.render_apa(self.csl_items())
            if rendered is not None:
                title = bib.get("title", "Literaturverzeichnis")
                out[self.root / bib["path"]] = (f"# {title}\n\n> Generiert aus den Quellenkarten – "
                                                f"nicht von Hand bearbeiten.\n\n{rendered}\n")
        return out

    def rebuild(self, check: bool = False) -> list[Path]:
        if not self.bundle.is_dir():
            return []
        changed = []
        for path, content in self.projections().items():
            if path.exists() and path.read_text(encoding="utf-8") == content:
                continue
            changed.append(path)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        if self.cfg["dashboard"].get("auto") and not check:
            self.write_dashboard()
        return changed

    # ------------------------------------------------------------ Lint

    def edges(self) -> list[tuple[Page, Page, str]]:
        """Gerichtete Kanten im Bundle: Links im Text (link) und sources[].resource (source).

        OKF §5.1: Zeigt eine Quelle auf ein Konzept im Bundle, ist sie bereits eine Kante im Graphen.
        """
        by_path = {p.path.resolve(): p for p in self.pages()}
        out = []
        for p in self.pages():
            if p.fm is None:
                continue
            targets = [(t, "link") for t in LINK_RE.findall(CODE_RE.sub("", p.body))]
            targets += [(str(s["resource"]), "source") for s in as_list(p.fm.get("sources"))
                        if isinstance(s, dict) and s.get("resource")]
            seen = set()
            for target, kind in targets:
                q = by_path.get(self.resolve(p.path, target))
                if q is not None and q is not p and (q.id, kind) not in seen:
                    seen.add((q.id, kind))
                    out.append((p, q, kind))
        return out

    def severity(self, code: str) -> str:
        return self.cfg["lint"]["severity"].get(code, SEVERITY.get(code, "warn"))

    def lint(self) -> list[Finding]:
        findings: list[Finding] = []

        def add(code, path, msg):
            sev = self.severity(code)
            if sev != "off":
                findings.append(Finding(sev, code, self.rel(path), msg))

        if not self.bundle.is_dir():
            add("bundle_missing", self.bundle, "Bundle-Ordner fehlt")
            return findings
        self._lint_reserved(add)
        pages = self.pages()
        by_path = {p.path.resolve(): p for p in pages}
        inbound: Counter = Counter()
        edges: dict[Path, set] = {}
        for p in pages:
            if p.error:
                add("frontmatter_invalid", p.path, p.error)
        for p, q, _ in self.edges():
            out = edges.setdefault(p.path.resolve(), set())
            if q.path.resolve() not in out:
                out.add(q.path.resolve())
                inbound[q.path.resolve()] += 1
        for p in pages:
            if p.fm is not None:
                self._lint_page(p, add, by_path, inbound, edges)
        self._lint_scope(add, pages)
        self._lint_visibility(add, pages)
        self._lint_raw(add, pages)
        return sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.path, f.code))

    def _lint_reserved(self, add) -> None:
        okf = self.cfg["wiki"]["okf_version"]
        for path in sorted(self.bundle.rglob("index.md")):
            if self._hidden(path):
                continue
            raw, _ = split_frontmatter(path.read_text(encoding="utf-8"))
            if path.parent == self.bundle:
                if raw is None:
                    add("okf_version_missing", path, f'Root-index.md ohne okf_version: "{okf}" (OKF §12)')
                    continue
                try:
                    fm = load_yaml(raw)
                except yaml.YAMLError:
                    fm = None
                if not isinstance(fm, dict) or set(fm) != {"okf_version"} or str(fm["okf_version"]) != okf:
                    add("root_index_frontmatter", path, f'Root-index.md darf nur okf_version: "{okf}" tragen (OKF §8)')
            elif raw is not None:
                add("index_frontmatter", path, "index.md unterhalb der Wurzel darf kein Frontmatter haben (OKF §8)")
        for path in sorted(self.bundle.rglob("log.md")):
            if self._hidden(path):
                continue
            text = path.read_text(encoding="utf-8")
            if split_frontmatter(text)[0] is not None:
                add("log_frontmatter", path, "log.md darf kein Frontmatter haben (OKF §9)")
            heads = [h.strip() for h in re.findall(r"^## (.+)$", text, re.M)]
            for h in heads:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", h):
                    add("log_date_heading", path, f"Datumsüberschrift nicht ISO 8601: {h}")
            iso = [h for h in heads if re.fullmatch(r"\d{4}-\d{2}-\d{2}", h)]
            if iso != sorted(iso, reverse=True):
                add("log_order", path, "Datumsgruppen nicht absteigend (OKF §9: neueste zuerst)")
        projections = self.projections()
        for path, content in projections.items():
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                add("projection_stale", path, "veraltet – `okfwiki.py rebuild` ausführen")
        bib = self.cfg["export"].get("bibliography", {})
        if bib.get("path") and self.root / bib["path"] not in projections:
            add("projection_unavailable", self.root / bib["path"], "Literaturverzeichnis nicht erzeugbar (pandoc fehlt?)")

    def _lint_page(self, p: Page, add, by_path, inbound, edges) -> None:
        fm, path = p.fm, p.path
        body = CODE_RE.sub("", p.body)
        spec = self.types.get(p.type)
        if not p.type:
            add("missing_type", path, "Pflichtfeld type fehlt oder ist leer (OKF §4.1)")
        elif spec is None and self.types:
            add("type_unknown", path, f"type {p.type!r} ist in wiki.toml nicht beschrieben")
        expected = self.folder_type.get(p.folder)
        if expected and p.type and expected != p.type:
            add("type_folder_mismatch", path, f"type {p.type!r} liegt im Ordner von {expected!r}")
        if not SLUG_RE.fullmatch(path.stem):
            add("path_not_kebab", path, "Dateiname nicht kebab-case")
        spec = spec or {**TYPE_DEFAULTS, "min_links": 0}
        for key in spec["required"]:
            if is_empty(fm.get(key)):
                add("missing_required", path, f"Pflichtfeld {key} fehlt (Profil)")
        for key in spec["recommended"]:
            if key not in spec["required"] and is_empty(fm.get(key)):
                add("missing_recommended", path, f"{key} fehlt (empfohlen)")
        for key, allowed in self.cfg["enums"].items():
            for value in as_list(fm.get(key)):
                if value not in allowed:
                    add("enum_invalid", path, f"{key} {value!r} nicht in {' | '.join(map(str, allowed))}")

        # Vertrauen und Lebenszyklus (OKF §5.2–5.5, §7)
        status = fm.get("status")
        if status is not None and status not in STATUS:
            add("status_invalid", path, f"status {status!r} nicht in draft | stable | deprecated")
        gen = fm.get("generated")
        if gen is not None:
            if not isinstance(gen, dict) or not gen.get("by"):
                add("generated_invalid", path, "generated braucht by")
            else:
                if not ACTOR_RE.match(str(gen["by"])):
                    add("actor_format", path, f"generated.by {gen['by']!r} folgt nicht der Akteurskonvention")
                if "at" in gen and not is_timestamp(gen["at"]):
                    add("timestamp_invalid", path, "generated.at ist kein ISO-8601-Zeitpunkt mit Offset")
        verified = as_list(fm.get("verified"))
        for v in verified:
            if not isinstance(v, dict) or not v.get("by") or not is_timestamp(v.get("at")):
                add("verified_invalid", path, "verified-Einträge brauchen by und at (ISO 8601 mit Offset)")
            elif not ACTOR_RE.match(str(v["by"])):
                add("actor_format", path, f"verified.by {v['by']!r} folgt nicht der Akteurskonvention")
        if status == "stable" and not verified:
            add("stable_unverified", path, "status stable ohne verified-Eintrag")
        if "stale_after" in fm:
            stale = as_datetime(fm["stale_after"])
            if stale is None:
                add("timestamp_invalid", path, "stale_after ist kein ISO-8601-Zeitpunkt mit Offset")
            elif dt.datetime.now(dt.timezone.utc) >= stale:
                add("stale", path, f"seit {stale.date()} veraltet – Inhalt prüfen")

        # Herkunft: sources[] und Fußnoten (OKF §5.1)
        ids, sources = [], {}
        for s in as_list(fm.get("sources")):
            if not isinstance(s, dict) or not s.get("resource"):
                add("source_invalid", path, f"sources-Eintrag ohne resource: {s!r} (OKF §5.1)")
                continue
            if s.get("id"):
                ids.append(str(s["id"]))
                sources[str(s["id"])] = s
            r = self.resolve(path, str(s["resource"]))
            if r is not None and r.suffix == ".md" and not r.exists():
                add("source_missing", path, f"Quelle {s['resource']} existiert nicht")
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            add("source_duplicate_id", path, f"doppelte sources-IDs: {dupes}")
        refs = set(FOOTNOTE_REF_RE.findall(body))
        defs = set(FOOTNOTE_DEF_RE.findall(body))
        for label in sorted(refs - set(ids)):
            add("footnote_unsourced", path, f"Fußnote [^{label}] hat keinen sources-Eintrag")
        for label in sorted(refs - defs):
            add("footnote_undefined", path, f"Fußnote [^{label}] ohne Definition im Text")
        for label in sorted(set(ids) - refs):
            add("source_uncited", path, f"sources-Eintrag {label} wird im Text nicht zitiert")
        if spec["needs_footnotes"] and not refs and status != "deprecated":
            add("no_footnotes", path, "keine Fußnoten – Sachaussagen brauchen [^id] (Profil)")
        for label in sorted(refs & set(sources)):
            r = self.resolve(path, str(sources[label]["resource"]))
            target = by_path.get(r)
            if target and target.fm and target.fm.get("access") == "citation":
                add("claim_on_citation_only", path,
                    f"[^{label}] belegt mit einer Quelle, deren Karte nur access: citation hat")

        # Aufbau
        if spec["sections"]:
            heads = [h.lower() for h in H2_RE.findall(p.body)]
            missing = [s for s in spec["sections"] if not any(h.startswith(s.lower()) for h in heads)]
            if missing:
                add("sections_missing", path, "Abschnitte fehlen: " + ", ".join(missing))

        # Links und Graph (OKF §6)
        outgoing = 0
        bundle = self.bundle.resolve()
        for target in LINK_RE.findall(body):
            r = self.resolve(path, target)
            if r is None:
                continue
            if not r.is_relative_to(bundle):
                add("link_leaves_bundle", path, f"Link verlässt das Bundle: {target}")
            elif not r.exists():
                add("broken_link", path, f"Linkziel fehlt: {target}")
            elif r != path.resolve():
                outgoing += 1
        if outgoing < int(spec["min_links"]):
            add("few_links", path, f"nur {outgoing} interne Links (Profil: mindestens {spec['min_links']})")
        me = path.resolve()
        isolated = self.cfg["lint"]["orphans"] == "isolated"
        if inbound[me] == 0 and (not isolated or not edges.get(me)):
            add("orphan", path, "keine eingehenden Links" + (" und keine ausgehenden" if isolated else ""))
        self._lint_contradictions(p, add, by_path)

        if p.type == SOURCE_TYPE:
            self._lint_source(p, add)

    def _lint_contradictions(self, p: Page, add, by_path) -> None:
        """Ein Widerspruchsblock braucht mindestens eine verlinkte Gegenseite mit eigenem Marker."""
        for m in CONTRADICTION_RE.finditer(p.body):
            block = p.body[m.start():].split("\n\n", 1)[0]
            others = [by_path.get(self.resolve(p.path, t)) for t in LINK_RE.findall(block)]
            others = [o for o in others if o and o is not p]
            if others and not any(CONTRADICTION_RE.search(o.body) for o in others):
                add("contradiction_one_sided", p.path, "Widerspruch nur hier markiert, nicht auf "
                    + ", ".join(f"/{o.id}.md" for o in others))

    def _lint_source(self, p: Page, add) -> None:
        fm, path = p.fm, p.path
        lint = self.cfg["lint"]
        access = fm.get("access")
        packet = fm.get("raw_packet")
        if packet:
            manifest = self.root / str(packet) / "manifest.json"
            if not manifest.exists():
                add("raw_missing", path, f"{packet}/manifest.json fehlt")
            else:
                for f in json.loads(manifest.read_text(encoding="utf-8")).get("files", []):
                    target = self.root / str(packet) / f["path"]
                    if not target.exists() or sha256_of(target) != f.get("sha256"):
                        add("raw_tampered", path, f"{packet}/{f['path']} weicht vom Manifest ab")
        fulltexts = [f for f in as_list(fm.get("fulltext")) if isinstance(f, dict)]
        for ft in fulltexts:
            target = self.root / str(ft.get("path", ""))
            if not ft.get("path") or not ft.get("sha256"):
                add("fulltext_unanchored", path, "fulltext braucht path und sha256")
            elif not target.is_file():
                add("fulltext_absent", path, f"Volltext {ft['path']} lokal nicht vorhanden (sha256 ungeprüft)")
            elif sha256_of(target) != ft["sha256"]:
                add("fulltext_tampered", path, f"Volltext {ft['path']} weicht vom gespeicherten sha256 ab")
        if access in lint["fulltext_access"] and not packet and not fulltexts:
            add("fulltext_unanchored", path, f"access {access}, aber weder raw_packet noch fulltext-Block")
        if access == "citation":
            section = re.search(rf"^## +{re.escape(lint['claims_section'])}.*?$(.*?)(?=^## |\Z)", p.body, re.M | re.S)
            if section and re.search(r"^\s*(?:[-*]|\d+\.)\s+\S", section.group(1), re.M):
                add("citation_with_claims", path,
                    f"{lint['claims_section']} trotz access citation – Inhalt nicht belegt")
        lic = self.license_of(p)
        if not lic["name"] and not lic["url"]:
            add("license_missing", path, "Quelle ohne license.name (unknown ist gültig; "
                "`lizenz <seite> --fetch` sucht über Crossref, DataCite, Europe PMC und OpenAlex)")
        elif lic["cls"] == "unbekannt" and lic["known"]:
            add("license_unknown", path, "Lizenz unbekannt: vor Volltextablage, Abbildungen oder Weitergabe klären")
        elif lic["cls"] == "unbekannt":
            add("license_unclassified", path, f"Lizenz {lic['name'] or lic['url']!r} nicht eingeordnet: license.class "
                f"setzen ({', '.join(LICENSE_CLASSES)}) oder Muster in [licenses.patterns]")
        self._lint_fundweg(p, add)
        stored = self.fulltext_locations(p)
        if stored:
            rights = self.rights_of(p)
            keep, share = rights["volltext_ablegen"], rights["volltext_weitergeben"]
            if keep[0] in ("nein", "fragen"):
                add("fulltext_rights", path, f"Volltext abgelegt ({', '.join(s['path'] for s in stored)}), "
                    f"Recht dazu nicht geklärt: {keep[1] or keep[0]}")
            shared = [s["path"] for s in stored if s["tracked"]]
            if shared and share[0] in ("nein", "fragen"):
                add("fulltext_shared", path, f"Volltext im Git-Repository versioniert ({', '.join(shared)}), "
                    f"Weitergabe nicht erlaubt: {share[1] or share[0]}")
        priority = lint.get("priority_field")
        if priority and fm.get(priority) and access == "citation":
            add("priority_citation_only", path, f"{priority}: true, aber nur access citation")
        csl = fm.get(self.cfg["export"].get("csl", {}).get("field", "csl"))
        if isinstance(csl, dict):
            if not (csl.get("title") and csl.get("issued") and (csl.get("author") or csl.get("editor"))):
                add("csl_incomplete", path, "csl braucht title, issued und author oder editor")
            if not csl.get("DOI") and not csl.get("accessed"):
                add("csl_incomplete", path, "Quelle ohne DOI braucht csl.accessed (Abrufdatum)")
        elif not self.csl_item(p).get("issued") and not UNDATED_RE.match(str(fm.get("date") or "")):
            add("source_undated", path, "Quellenkarte ohne Datum: erscheint im Beleg als „o. J.“; date, created, "
                "published oder year setzen (Commit-, Veröffentlichungs- oder Stand-Datum), bei echt undatierten "
                "Quellen date: o. J.")

    # ------------------------------------------------------------ Umfang, Sichtbarkeit und Fundweg

    def scope_values(self) -> list[str]:
        """Werte des Umfangsfelds in Rangfolge vom Kern nach außen (aus [enums])."""
        field = self.cfg["scope"].get("field")
        return [str(v) for v in self.cfg["enums"].get(field, [])] if field else []

    def scopes(self) -> dict[str, tuple[str, bool]]:
        """{Seiten-ID: (Umfang, abgeleitet)}.

        Eigener Wert geht vor. Quellen ohne Wert erben den engsten Umfang der Seiten, die sie verlinken
        oder in sources[] führen ([scope] derive); abgeleitet wird nur hier, geschrieben wird nichts.
        """
        field = self.cfg["scope"].get("field")
        if not field:
            return {}
        own = {}
        for p in self.pages():
            values = [str(v) for v in as_list((p.fm or {}).get(field)) if not is_empty(v)]
            if values:
                own[p.id] = values[0]
        out = {pid: (v, False) for pid, v in own.items()}
        if self.cfg["scope"].get("derive", True):
            order = self.scope_values()
            rank = lambda v: order.index(v) if v in order else len(order)
            sources = {q.id for q in self.source_cards()}
            best: dict[str, str] = {}
            for p, q, _ in self.edges():
                if q.id in sources and q.id not in own and p.id not in sources and p.id in own:
                    if q.id not in best or rank(own[p.id]) < rank(best[q.id]):
                        best[q.id] = own[p.id]
            out.update({qid: (v, True) for qid, v in best.items()})
        return out

    def _lint_scope(self, add, pages) -> None:
        field = self.cfg["scope"].get("field")
        if not field:
            return
        scopes = self.scopes()
        values = " | ".join(self.scope_values()) or "Wert laut Profil"
        for p in pages:
            if p.fm is None or p.id in scopes:
                continue
            if p.type == SOURCE_TYPE and self.cfg["scope"].get("derive", True):
                add("scope_missing", p.path, f"{field} fehlt und lässt sich nicht ableiten "
                    f"(keine Seite mit {field} nutzt diese Quelle; {values})")
            else:
                add("scope_missing", p.path, f"{field} fehlt ({values})")

    def visibility_values(self) -> list[str] | None:
        """Erlaubte Werte des Sichtbarkeitsfelds: aus [enums], sonst default und hidden; None ohne Angabe."""
        spec = self.cfg["visibility"]
        field = spec.get("field")
        if field in self.cfg["enums"]:
            return [str(v) for v in self.cfg["enums"][field]]
        if spec.get("default"):
            return [str(spec["default"]), *map(str, as_list(spec.get("hidden")))]
        return None

    def visibility(self) -> dict[str, tuple[str, bool]]:
        """{Seiten-ID: (Sichtbarkeit, abgeleitet)}; leer ohne [visibility] field.

        Eigener Wert geht vor, sonst [visibility] default. Quellenkarten ohne eigenen Wert, die nur von
        verborgenen Seiten verlinkt oder in sources[] geführt werden, gelten selbst als verborgen ([visibility]
        derive), damit die Quellenauswahl eine interne Linie nicht verrät. Abgeleitet wird nur hier.
        """
        spec = self.cfg["visibility"]
        field = spec.get("field")
        if not field:
            return {}
        default = str(spec.get("default") or "")
        hidden = {str(v) for v in as_list(spec.get("hidden"))}
        out, own = {}, set()
        for p in self.pages():
            values = [str(v) for v in as_list((p.fm or {}).get(field)) if not is_empty(v)]
            if values:
                own.add(p.id)
            out[p.id] = (values[0] if values else default, False)
        if spec.get("derive", True) and hidden:
            sources = {q.id for q in self.source_cards()}
            users: dict[str, set[str]] = {}
            for p, q, _ in self.edges():
                if q.id in sources and q.id not in own:
                    users.setdefault(q.id, set()).add(p.id)
            # Quellen, die nur verborgene Quellen nutzen, erst im nächsten Durchgang
            changed = True
            while changed:
                changed = False
                for qid, ids in users.items():
                    if out[qid][0] not in hidden and all(out[i][0] in hidden for i in ids):
                        out[qid] = (min(out[i][0] for i in ids), True)
                        changed = True
        return out

    def hidden_ids(self) -> set[str]:
        """IDs der Seiten, die in der öffentlichen Ausgabe fehlen: Wert aus [visibility] hidden oder unbekannter
        Wert (ein Tippfehler soll eine Seite nicht veröffentlichen; der Lint meldet ihn als enum_invalid)."""
        hidden = {str(v) for v in as_list(self.cfg["visibility"].get("hidden"))}
        allowed = self.visibility_values()
        return {pid for pid, (v, _) in self.visibility().items()
                if v in hidden or (v and allowed is not None and v not in allowed)}

    def _lint_visibility(self, add, pages) -> None:
        field = self.cfg["visibility"].get("field")
        if not field:
            return
        allowed = self.visibility_values()
        if field not in self.cfg["enums"] and allowed is not None:  # sonst prüft das [enums] schon
            for p in pages:
                for value in as_list((p.fm or {}).get(field)):
                    if str(value) not in allowed:
                        add("enum_invalid", p.path, f"{field} {value!r} nicht in {' | '.join(allowed)}")
        for p, targets in self.visibility_leaks():
            add("visibility_leak", p.path, f"öffentliche Seite verweist auf verborgene: {', '.join(targets)} "
                "(in der öffentlichen Ausgabe wird der Link zu Text, der Beleg entfällt)")

    def visibility_leaks(self) -> list[tuple[Page, list[str]]]:
        """Öffentliche Seiten, die verborgene verlinken oder in sources[] führen, mit den Zielen."""
        hidden = self.hidden_ids()
        leaks: dict[str, tuple[Page, set[str]]] = {}
        for p, q, _ in self.edges():
            if p.id not in hidden and q.id in hidden:
                leaks.setdefault(p.id, (p, set()))[1].add(f"/{q.id}.md")
        return [(p, sorted(targets)) for p, targets in leaks.values()]

    def fundweg_of(self, page: Page) -> list[dict]:
        return [e for e in as_list((page.fm or {}).get(self.cfg["fundweg"].get("field") or "fundweg"))
                if isinstance(e, dict)]

    def fundweg_entry(self, art: str, db: str | None = None, query: str | None = None, von: str | None = None,
                      at: str | None = None, by: str | None = None) -> dict:
        """Ein Fundweg-Eintrag {art, db, query, von, at, by}; at und by stehen ohne Angabe auf jetzt und [wiki] actor."""
        if art not in FUNDWEG_ARTEN:
            raise WikiError(f"Fundweg-Art {art!r}: eine von {', '.join(FUNDWEG_ARTEN)}")
        if art == "zitatverfolgung" and not von:
            raise WikiError("zitatverfolgung braucht --von <slug> (die Quelle, deren Literatur verfolgt wurde)")
        if at and not is_timestamp(at):
            raise WikiError("--at muss ein ISO-8601-Zeitpunkt mit Offset sein, z. B. 2026-10-25T09:30:00Z")
        if by and not ACTOR_RE.match(by):
            raise WikiError("--by folgt der Akteurskonvention, z. B. claude-code/claude-opus-5-5 oder human:<id>")
        entry = {"art": art}
        entry.update({k: v for k, v in (("db", db), ("query", query), ("von", von)) if v})
        entry.update({"at": at or now_iso(), "by": by or self.actor})
        return entry

    def set_fundweg(self, page: str, entry: dict, append: bool = False) -> Path:
        path = self.page_path(page)
        parsed = self.parse(path)
        field = self.cfg["fundweg"].get("field") or "fundweg"
        value = self.fundweg_of(parsed) + [entry] if append and self.fundweg_of(parsed) else entry
        self._write_frontmatter(path, {field: value})
        self.append_event("update", parsed.id, f"Fundweg: {entry['art']}" + (f" ({entry['db']})" if entry.get("db") else ""))
        return path

    def _lint_fundweg(self, p: Page, add) -> None:
        field = self.cfg["fundweg"].get("field") or "fundweg"
        raw = (p.fm or {}).get(field)
        if is_empty(raw):
            add("fundweg_missing", p.path, f"{field} fehlt: Wie wurde die Quelle gefunden? ({' | '.join(FUNDWEG_ARTEN)})")
            return
        folder = self.types.get(SOURCE_TYPE, {}).get("folder", "sources")
        for e in as_list(raw):
            if not isinstance(e, dict) or e.get("art") not in FUNDWEG_ARTEN:
                add("fundweg_invalid", p.path, f"{field}.art muss eine von {' | '.join(FUNDWEG_ARTEN)} sein")
                continue
            if e["art"] == "zitatverfolgung" and not e.get("von"):
                add("fundweg_invalid", p.path, f"{field}: zitatverfolgung braucht von: <slug>")
            if e.get("von") and not (self.bundle / folder / f"{e['von']}.md").exists():
                add("fundweg_invalid", p.path, f"{field}.von {e['von']!r} ist keine Quellenkarte")
            if e["art"] == "suche" and not (e.get("db") and e.get("query")):
                add("fundweg_incomplete", p.path, f"{field}: Suche ohne db und query ist nicht reproduzierbar")
            if "at" in e and not is_timestamp(e["at"]):
                add("timestamp_invalid", p.path, f"{field}.at ist kein ISO-8601-Zeitpunkt mit Offset")
            if e.get("by") and not ACTOR_RE.match(str(e["by"])):
                add("actor_format", p.path, f"{field}.by {e['by']!r} folgt nicht der Akteurskonvention")

    # ------------------------------------------------------------ Lizenzen und Nutzungsrechte

    def license_of(self, page: Page) -> dict:
        lic = (page.fm or {}).get("license")
        name, url = license_parts(lic)
        cls, known = classify_license(lic, self.cfg["licenses"].get("patterns"))
        return {"name": name, "url": url, "cls": cls, "label": LICENSE_CLASSES[cls], "known": known}

    def rights_matrix(self) -> dict[str, dict[str, tuple[str, str]]]:
        """Rechte je Lizenzklasse, mit den Abweichungen aus [rights.<klasse>] der wiki.toml."""
        return {cls: {a: parse_right({**row, **self.cfg["rights"].get(cls, {})}.get(a)) for a in RIGHTS_ACTIONS}
                for cls, row in RIGHTS_MATRIX.items()}

    def rights_of(self, page: Page) -> dict[str, tuple[str, str]]:
        """Nutzungsrechte einer Quelle: Klasse laut Lizenz, darüber `rights:` der Karte (z. B. eine Genehmigung)."""
        rights = dict(self.rights_matrix()[self.license_of(page)["cls"]])
        own = (page.fm or {}).get("rights")
        if isinstance(own, dict):
            rights.update({a: parse_right(v) for a, v in own.items() if a in RIGHTS_ACTIONS})
        return rights

    def fulltext_locations(self, page: Page) -> list[dict]:
        """Wo Volltexte der Quelle liegen (Rohquellen-Paket, fulltext-Blöcke) und ob Git sie versioniert."""
        fm = page.fm or {}
        tracked = self._git_tracked()
        out = []
        if fm.get("raw_packet"):
            prefix = str(fm["raw_packet"]).rstrip("/") + "/"
            out.append({"path": prefix.rstrip("/"), "tracked": bool(tracked) and any(t.startswith(prefix) for t in tracked)})
        for ft in as_list(fm.get("fulltext")):
            if isinstance(ft, dict) and ft.get("path"):
                out.append({"path": str(ft["path"]), "tracked": bool(tracked) and str(ft["path"]) in tracked})
        return out

    def _git_tracked(self) -> set[str] | None:
        """Von Git versionierte Dateien relativ zum Projektordner; None ohne Git."""
        if not hasattr(self, "_tracked"):
            try:
                out = subprocess.run(["git", "-C", str(self.root), "ls-files", "-z"], capture_output=True, timeout=30)
                self._tracked = (set(out.stdout.decode("utf-8", "replace").split("\0")) - {""}
                                 if out.returncode == 0 else None)
            except (OSError, subprocess.SubprocessError):
                self._tracked = None
        return self._tracked

    def identifiers(self, page: Page) -> tuple[str, str, str]:
        """(DOI, PMID, PMCID) aus csl-Block, Frontmatter, resource oder Lizenz-URL."""
        fm = page.fm or {}
        csl = fm.get(self.cfg["export"].get("csl", {}).get("field", "csl"))
        csl = csl if isinstance(csl, dict) else {}
        urls = " ".join(str(u) for u in (fm.get("resource"), csl.get("URL"), license_parts(fm.get("license"))[1]) if u)
        doi = str(csl.get("DOI") or fm.get("doi") or "").strip()
        if not doi:
            m = re.search(r"doi\.org/(10\.[^\s?#]+)", urls)
            doi = m.group(1) if m else ""
        pmcid = str(csl.get("PMCID") or fm.get("pmcid") or "").strip()
        if not pmcid:
            m = re.search(r"\b(PMC\d{5,})\b", urls)
            pmcid = m.group(1) if m else ""
        return doi, str(csl.get("PMID") or fm.get("pmid") or "").strip(), pmcid

    def lookup_license(self, doi: str = "", pmid: str = "", pmcid: str = "") -> dict | None:
        """Lizenz über Crossref oder DataCite (DOI), Europe PMC (DOI, PMID oder PMCID) und OpenAlex (DOI oder PMID).

        Nur offizielle APIs, keine Webseiten. Die erste eindeutige Angabe in dieser Reihenfolge gewinnt; sonst die
        erste unklare (Lizenzangabe ohne bekanntes Muster).
        """
        today = dt.date.today().isoformat()
        unclear = []
        if doi:
            in_crossref = True
            try:
                entries = http_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")["message"].get("license") or []
            except urllib.error.HTTPError as exc:
                entries, in_crossref = [], exc.code != 404
            except (OSError, ValueError, KeyError):
                entries = []
            rank = {"vor": 0, "unspecified": 1, "am": 2, "tdm": 3}
            for e in sorted(entries, key=lambda e: rank.get(e.get("content-version"), 9)):
                name = license_name_from(e.get("URL", ""))
                if name:
                    return {"name": name, "url": e["URL"], "checked": today,
                            "via": f"crossref ({e.get('content-version', '?')})"}
            if entries:
                unclear.append({"name": "Lizenz laut Verlag, siehe URL", "url": entries[0].get("URL"), "checked": today,
                                "via": f"crossref ({entries[0].get('content-version', '?')})"})
            # DataCite-DOIs (Zenodo, arXiv, OSF) kennt Crossref nicht; ihre Lizenz steht in der rightsList
            for r in [] if in_crossref else datacite_rights(doi):
                uri, text = str(r.get("rightsUri") or ""), str(r.get("rights") or "").strip()
                named = license_name_from(uri) or license_name_from(text)
                lic = {"name": named if named.startswith(("CC", "Public")) else text or named or "Lizenz laut DataCite",
                       "url": uri or None, "checked": today, "via": "datacite"}
                if named or classify_license(lic)[0] != "unbekannt":
                    return lic
                unclear.append(lic)
        if doi or pmid or pmcid:
            query = f'DOI:"{doi}"' if doi else f"EXT_ID:{pmid} AND SRC:MED" if pmid else f"PMCID:{pmcid}"
            url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
                {"query": query, "resultType": "core", "format": "json", "pageSize": 1})
            try:
                hits = http_json(url).get("resultList", {}).get("result", [])
            except (OSError, ValueError):
                hits = []
            if hits and hits[0].get("license"):
                raw = str(hits[0]["license"])
                return {"name": license_name_from(raw) or raw, "url": None, "checked": today, "via": "europepmc"}
        if doi or pmid:
            # OpenAlex führt die Lizenz je Fundort (Verlag, Repositorium) und Fassung; die Verlagsfassung geht vor
            key = f"doi:{doi}" if doi else f"pmid:{pmid}"
            try:
                work = http_json(f"https://api.openalex.org/works/{urllib.parse.quote(key, safe=':/')}")
            except (OSError, ValueError):
                work = {}
            rank = {"publishedVersion": 0, "acceptedVersion": 1, "submittedVersion": 2}
            for loc in sorted((x for x in work.get("locations") or [] if x.get("license")),
                              key=lambda x: rank.get(x.get("version"), 9)):
                raw = str(loc["license"])
                name = license_name_from(raw) or ("Public Domain" if raw == "public-domain" else "")
                via = f"openalex ({loc.get('version') or '?'})"
                if name:
                    return {"name": name, "url": None, "checked": today, "via": via}
                unclear.append({"name": f"Lizenz laut OpenAlex: {raw}", "url": None, "checked": today, "via": via})
        return unclear[0] if unclear else None

    def set_license(self, page: str, lic: dict, detail: str = "") -> Path:
        path = self.page_path(page)
        lic = {k: v for k, v in lic.items() if v not in ("", None) or k in ("name", "url")}
        self._write_frontmatter(path, {"license": lic})
        self.append_event("update", self.page_id(path), detail or f"Lizenz: {lic.get('name')}")
        return path

    def _lint_raw(self, add, pages) -> None:
        if not self.raw or not self.raw.is_dir():
            return
        linked = {str((p.fm or {}).get("raw_packet", "")).rstrip("/") for p in pages}
        stems = {p.path.stem for p in pages if p.type == SOURCE_TYPE}
        for packet in sorted(d for d in self.raw.iterdir() if d.is_dir()):
            if self.rel(packet) not in linked and packet.name not in stems:
                add("raw_uningested", packet, "Rohquelle ohne Quellenkarte")

    # ------------------------------------------------------------ Zitieren (APA 7 über CSL)

    def source_cards(self) -> list[Page]:
        """Quellenkarten: type source oder eine Karte im Quellenordner (z. B. Altlasten mit anderem type)."""
        folder = self.types.get(SOURCE_TYPE, {}).get("folder", "sources")
        return [p for p in self.pages() if p.fm and (p.type == SOURCE_TYPE or p.folder == folder)]

    def page_refs(self, page: Page, by_path: dict) -> list[tuple[str, "Page | None", object]]:
        """(Label, Quellenkarte oder None, Eintrag) je sources-Eintrag. Bloße Slugs (Altform) werden
        nachsichtig als /<quellenordner>/<slug>.md gelesen; der Lint meldet sie trotzdem."""
        out = []
        for entry in as_list((page.fm or {}).get("sources")):
            label = str(entry.get("id") or entry.get("resource", "")) if isinstance(entry, dict) else str(entry)
            out.append((label, by_path.get(self.ref_path(page, entry)), entry))
        return out

    def ref_path(self, page: Page, entry) -> Path | None:
        """Zielpfad eines sources-Eintrags (None für externe Ressourcen)."""
        if isinstance(entry, dict):
            return self.resolve(page.path, str(entry.get("resource", "")))
        folder = self.types.get(SOURCE_TYPE, {}).get("folder", "sources")
        return (self.bundle / folder / f"{entry}.md").resolve()

    def _drop_withheld(self, page: Page, body: str, refs: list) -> tuple[str, list]:
        """Öffentliche Ausgabe: Belege auf weggelassene Seiten entfallen samt Fußnote und Literaturangabe."""
        gone = {label for label, _, entry in refs if self.ref_path(page, entry) in self.withheld}
        if not gone:
            return body, refs
        alt = "|".join(map(re.escape, sorted(gone)))

        def clean(segment: str) -> str:
            segment = re.sub(rf"^\[\^(?:{alt})\]:.*\n?(?:[ \t]+\S.*\n?)*", "", segment, flags=re.M)
            return re.sub(rf"[ \t]*\[\^(?:{alt})\](?!:)", "", segment)

        parts = re.split(f"({CODE_RE.pattern})", body, flags=re.S)
        body = "".join(clean(seg) if i % 2 == 0 else seg for i, seg in enumerate(parts))
        return body, [r for r in refs if r[0] not in gone]

    def _apa_cites(self, body: str, labels: dict, catalog: dict) -> tuple[str, list[str]]:
        """Fußnoten [^id] auf Quellenkarten werden zu APA-Klammerbelegen; ihre Definitionen entfallen.

        Fundstellen aus der Fußnote (S., Art., § …) wandern in den Beleg, der übrige Fußnotentext in den
        Tooltip. Satzzeichen direkt vor dem Beleg rücken dahinter, außer nach Abkürzungen wie „z. B.“.
        """
        notes, cites = {}, []

        def drop_def(m):
            label, text = m.group(1), m.group(2).strip()
            if label not in labels:
                return m.group(0)
            if text and not re.fullmatch(r"\[[^\]]*\]\([^)]*\)", text):
                notes[label] = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
            return ""

        run_re = re.compile(r"(?P<pre>[.!?,;:])?(?P<run>\[\^[^\]\s]+\](?!:)(?:[ \t]*\[\^[^\]\s]+\](?!:))*)")

        def abbreviation(text: str) -> bool:
            word = re.search(r"(\S+)$", text)
            w = word.group(1) if word else ""
            return len(w) <= 2 or bool(re.fullmatch(r"(?:\w\.)+\w?", w)) or w.lower() in {
                "bzw", "vgl", "ca", "etc", "abb", "nr", "art", "abs", "tab", "kap", "inkl", "ggf", "evtl", "usw"}

        def convert(segment: str) -> str:
            segment = re.sub(r"^\[\^([^\]\s]+)\]:[ \t]*(.*)$\n?", drop_def, segment, flags=re.M)

            def repl(m):
                ids = re.findall(r"\[\^([^\]\s]+)\]", m.group("run"))
                known = [i for i in ids if i in labels]
                if not known:
                    return m.group(0)
                parts = []
                for i in known:
                    key = labels[i].path.stem
                    text = catalog[key]["cite"]
                    loc = LOCATOR_RE.search(notes.get(i, ""))
                    if loc:
                        text += ", " + html.escape(loc.group(0))
                    tip = html.escape(notes.get(i, ""), quote=True)
                    parts.append(f'<a class="cite-ref" href="#lit-{key}"' + (f' title="{tip}"' if tip else "") + f">{text}</a>")
                cites.append('<span class="cite">(' + "; ".join(parts) + ")</span>")
                token = f"⟦c{len(cites) - 1}⟧" + "".join(f"[^{u}]" for u in ids if u not in labels)
                pre, before = m.group("pre") or "", segment[:m.start()]
                if pre and not (pre == "." and abbreviation(before)):
                    return f" {token}{pre}"
                gap = "" if (pre or before[-1:].isspace() or not before) else " "
                return f"{pre}{' ' if pre else gap}{token}"

            return run_re.sub(repl, segment)

        parts = re.split(f"({CODE_RE.pattern})", body, flags=re.S)
        # Definitionen erst sammeln (stehen meist am Ende), dann Belege ersetzen
        for i in range(0, len(parts), 2):
            for m in re.finditer(r"^\[\^([^\]\s]+)\]:[ \t]*(.*)$", parts[i], re.M):
                drop_def(m)
        parts = [convert(seg) if i % 2 == 0 else seg for i, seg in enumerate(parts)]
        return "".join(parts), cites

    def csl_item(self, page: Page) -> dict:
        """CSL-JSON für eine Quellenkarte: der csl-Block, sonst aus flachen Feldern oder Repo-Angaben abgeleitet."""
        fm = page.fm or {}
        field = self.cfg["export"].get("csl", {}).get("field", "csl")
        if isinstance(fm.get(field), dict):
            return dict(fm[field], id=page.path.stem)
        item = {"id": page.path.stem, "title": one_line(fm.get("title")) or page.title}
        url = str(fm.get("url") or fm.get("resource") or "")
        if fm.get("authors") or fm.get("doi") or fm.get("year"):
            worktype = str(fm.get("worktype") or fm.get("type") or "")
            item["type"] = {"article-review": "article-journal", "standard": "report", "web-page": "webpage",
                            "conference": "paper-conference", "journal_article": "article-journal"}.get(
                worktype, worktype if worktype in ("article-journal", "book", "report", "thesis", "dataset") else "article-journal")
            if csl_names(fm.get("authors")):
                item["author"] = csl_names(fm.get("authors"))
            for key, target in (("container", "container-title"), ("venue", "container-title"), ("volume", "volume"),
                                ("issue", "issue"), ("pages", "page")):
                if fm.get(key) and target not in item:
                    item[target] = str(fm[key])
            if csl_date(fm.get("year")):
                item["issued"] = csl_date(fm.get("year"))
            if fm.get("doi"):
                item["DOI"] = str(fm["doi"])
            elif url:
                item["URL"] = url
            return item
        fmt = str(fm.get("format") or "")
        item["type"] = {"code": "software", "dataset": "dataset"}.get(fmt, "webpage")
        if fmt == "pull-request":
            item["genre"] = "Pull Request"
        pinned = fm.get("pinned") if isinstance(fm.get("pinned"), dict) else {}
        if fm.get("author"):
            item["author"] = [{"literal": str(a)} for a in as_list(fm["author"])]
        elif pinned.get("repo") and fmt in ("documentation", "code", "specification", "dataset"):
            item["author"] = [{"literal": str(pinned["repo"]).split("/")[0]}]
        if "github.com" in url:
            item["publisher" if item["type"] in ("software", "dataset") else "container-title"] = "GitHub"
        issued = csl_date(fm.get("date") or fm.get("created") or fm.get("published"))
        if issued:
            item["issued"] = issued
        if url:
            item["URL"] = url
        packet = fm.get("raw_packet")
        manifest = self.root / str(packet) / "manifest.json" if packet else None
        if manifest and manifest.is_file():
            accessed = csl_date(json.loads(manifest.read_text(encoding="utf-8")).get("retrieved_at"))
            if accessed:
                item["accessed"] = accessed
        return item

    def apa_catalog(self) -> dict[str, dict]:
        """{Slug: {cite, entry, order}} für alle Quellenkarten; ein einziger pandoc-Aufruf mit APA-7-CSL.

        cite ist der Klammerbeleg ohne Klammern ("Sarkar &amp; Drosos, 2025"), entry die Literaturangabe als HTML.
        Ohne pandoc einfache Ersatzform aus Autor, Jahr, Titel, URL.
        """
        if getattr(self, "_apa", None) is not None:
            return self._apa
        items = [self.csl_item(p) for p in self.source_cards()]
        spec = self.cfg["export"].get("csl", {})
        style = self.root / spec["style"] if spec.get("style") else SKILL_DIR / "templates" / "apa.csl"
        pandoc = shutil.which("pandoc")
        out = None
        if pandoc and items:
            doc = (f"---\nnocite: '@*'\nlang: {spec.get('lang', 'de-DE')}\n---\n\n"
                   + "\n\n".join(f"::: {{#cite-{it['id']}}}\n[@{it['id']}]\n:::" for it in items))
            with tempfile.TemporaryDirectory() as tmp:
                bib = Path(tmp) / "refs.json"
                bib.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
                cmd = [pandoc, "--citeproc", f"--bibliography={bib}", f"--csl={style}", "-f", "markdown-raw_html",
                       "-t", "html", "--wrap=none"]
                try:
                    out = subprocess.run(cmd, input=doc, capture_output=True, text=True, timeout=180, check=True).stdout
                except (OSError, subprocess.SubprocessError):
                    out = None
        catalog = {}
        if out:
            cites = dict(re.findall(r'<div id="cite-([^"]+)">\s*<p><span class="citation"[^>]*>(.*?)</span></p>', out, re.S))
            for order, (key, entry) in enumerate(re.findall(r'<div id="ref-([^"]+)" class="csl-entry"[^>]*>(.*?)</div>', out, re.S)):
                cite = " ".join(cites.get(key, "").split())
                catalog[key] = {"cite": cite[1:-1] if cite.startswith("(") and cite.endswith(")") else cite,
                                "entry": " ".join(entry.split()), "order": order}
        for order, it in enumerate(sorted(items, key=lambda i: i["id"])):
            if it["id"] in catalog:
                continue
            year = ((it.get("issued") or {}).get("date-parts") or [["o. D."]])[0][0]
            who = kurzbeleg(it).rsplit(",", 1)[0] if it.get("author") else it.get("title", it["id"])
            link = it.get("URL") or (f"https://doi.org/{it['DOI']}" if it.get("DOI") else "")
            entry = f"{html.escape(who)} ({year}). <em>{html.escape(it.get('title', ''))}</em>."
            if link:
                entry += f' <a href="{html.escape(link)}">{html.escape(link)}</a>'
            catalog[it["id"]] = {"cite": html.escape(f"{who}, {year}"), "entry": entry, "order": 10000 + order}
        self._apa = catalog
        return catalog

    # ------------------------------------------------------------ Dashboard

    def subtype_field(self, type_: str, fm: dict) -> str:
        """Feld mit der Unterart eines Typs: [types.X] subtype, sonst das erste vorhandene Standardfeld."""
        spec = self.types.get(type_, {})
        if spec.get("subtype"):
            return spec["subtype"]
        return next((f for f in ("category", "format", "evidenz", "worktype") if fm.get(f)), "")

    def dashboard_data(self) -> dict:
        """Was das Dashboard zum inhaltlichen Erkunden braucht: Seiten mit Vorschau und Kategorien, Kanten.

        Bewusst ohne Lint-Befunde, Prüfstatus und Dateipfade; dafür gibt es `lint` und `status`.
        """
        edges = self.edges()
        inbound: Counter = Counter()
        outbound: Counter = Counter()
        pairs = set()
        for p, q, _ in edges:
            if (p.id, q.id) not in pairs:
                pairs.add((p.id, q.id))
                inbound[q.id] += 1
                outbound[p.id] += 1
        reader = self.reader_html()
        catalog = self.apa_catalog()
        sources = {q.id for q in self.source_cards()}
        domain_field = self.cfg["taxonomy"].get("field", "domain")
        scopes = self.scopes()
        vis_field = self.cfg["visibility"].get("field")
        vis = self.visibility() if not self.public else {}
        hidden = self.hidden_ids() if vis else set()
        nodes = []
        for p in self.pages():
            fm = p.fm or {}
            sub_field = self.subtype_field(p.type, fm)
            cite = catalog.get(p.path.stem, {}).get("cite") if p.id in sources else None
            is_source = p.id in sources
            rights = self.rights_of(p) if is_source else {}
            nodes.append({
                **({"visibility": vis[p.id][0], "visibility_derived": vis[p.id][1], "internal": p.id in hidden}
                   if vis else {}),
                "license": self.license_of(p) if is_source else None,
                "rights": [[a, *rights[a]] for a in RIGHTS_ACTIONS] if is_source else [],
                "stored": self.fulltext_locations(p) if is_source else [],
                "fundweg": self.fundweg_of(p) if is_source else [],
                "scope": scopes.get(p.id, ("", False))[0], "scope_derived": scopes.get(p.id, ("", False))[1],
                "id": p.id, "title": p.title, "type": p.type or "?", "description": p.description,
                "access": str(fm.get("access") or "") if p.id in sources else "",
                "in": inbound[p.id], "out": outbound[p.id],
                "domain": [str(v) for v in as_list(fm.get(domain_field)) if not is_empty(v)],
                "subtype": str(fm.get(sub_field) or "") if sub_field else "", "subfield": sub_field,
                "tags": [str(t) for t in as_list(fm.get("tags"))][:12],
                "aliases": [str(a) for a in as_list(fm.get("aliases"))][:6],
                "cite": html.unescape(re.sub(r"<[^>]+>", "", cite)) if cite else "",
                "ris": ris_record(self.csl_item(p)) if p.id in sources else "",
                "heading": reader[p.id]["heading"], "html": reader[p.id]["html"],
                "excerpt": reader[p.id]["excerpt"], "outline": reader[p.id]["outline"],
                "refs": reader[p.id]["refs"], "apa": reader[p.id]["apa"], "open": reader[p.id]["open"],
                "updated": str((fm.get("generated") or {}).get("at", ""))[:10] if isinstance(fm.get("generated"), dict) else "",
            })
        types, labels = self.types, self.cfg.get("labels", {})
        scope_values = self.scope_values() or sorted({v for v, _ in scopes.values()})
        if self.public:
            # Nur Namen, die öffentliche Seiten brauchen: kein Typ, Umfang oder lesbarer Wert, den allein
            # weggelassene Seiten tragen (etwa ein Themenbereich nur für interne Seiten).
            used = {str(v) for p in self.pages() for value in (p.fm or {}).values()
                    for v in as_list(value) if isinstance(v, (str, int, float))}
            types = {n: spec for n, spec in types.items() if any(p.type == n for p in self.pages())}
            labels = {f: {v: text for v, text in m.items() if v in used} for f, m in labels.items()
                      if f != vis_field and isinstance(m, dict)}
            scope_values = [v for v in scope_values if any(s == v for s, _ in scopes.values())]
        return {
            "title": self.dashboard_title(), "generated": now_iso(), "version": VERSION,
            "types": [{"name": n, "label": spec["label"], "folder": spec["folder"]} for n, spec in types.items()],
            "domain_label": self.cfg["taxonomy"].get("label", "Themenbereich"),
            "labels": labels,
            "scope": ({"field": self.cfg["scope"]["field"], "label": self.cfg["scope"].get("label") or "Umfang",
                       "default": self.cfg["scope"].get("default") or "",
                       "values": [[v, self.cfg["labels"].get(self.cfg["scope"]["field"], {}).get(v, v)]
                                  for v in scope_values]}
                      if self.cfg["scope"].get("field") else None),
            "visibility": ({"field": vis_field, "label": self.cfg["visibility"].get("label") or "Sichtbarkeit",
                            "values": [[v, self.cfg["labels"].get(vis_field, {}).get(v, v)]
                                       for v in (self.visibility_values() or sorted({v for v, _ in vis.values()}))]}
                           if vis else None),
            "fundweg_arten": FUNDWEG_ARTEN,
            "path": [p.id for p in self.learning_path()],
            "glossary": [str(t) for t in as_list(self.cfg["dashboard"].get("glossary"))],
            "license_classes": LICENSE_CLASSES, "rights_actions": RIGHTS_ACTIONS,
            "rights_matrix": {cls: [[a, *row[a]] for a in RIGHTS_ACTIONS] for cls, row in self.rights_matrix().items()},
            "nodes": nodes,
            "edges": [{"s": p.id, "t": q.id, "kind": kind} for p, q, kind in edges],
        }

    def dashboard_title(self) -> str:
        """Wiki-Titel ohne den Index-Zusatz „– zuerst lesen“; der gehört in index.md, nicht ins Dashboard."""
        return re.sub(r"\s*[–—-]\s*zuerst lesen\s*$", "", self.cfg["wiki"]["title"], flags=re.I)

    def render_dashboard(self) -> str:
        template = (SKILL_DIR / "templates" / "dashboard.html").read_text(encoding="utf-8")
        data = json.dumps(self.dashboard_data(), ensure_ascii=False).replace("<", "\\u003c")
        title = html.escape(f"{self.dashboard_title()} – Dashboard")
        return (template.replace("/*__FONTS__*/", embedded_fonts())
                .replace("__TITLE__", title).replace("__DATA__", data))

    def reader_html(self) -> dict[str, dict]:
        """{Konzept-ID: {heading, html, refs, apa, open}} für die Leseansicht des Dashboards.
        Belege erscheinen als APA-7-Klammerbelege, refs ist das Literaturverzeichnis der Seite.

        Rohes HTML in Seiten wird als Text gezeigt, interne Links zeigen auf Konzept-IDs,
        `> [!todo]` und `> ⚠️ **Widerspruch:**` werden zu gekennzeichneten Kästen, Textdiagramme
        (```text) zu `pre.diagram`. open sind die offenen Stellen der Seite (Widerspruch, ausdrückliches
        „zu prüfen“, [!todo]) mit Anker `offen-N` für den Sprung zur Fundstelle.
        """
        try:
            import markdown
            from markdown.treeprocessors import Treeprocessor
        except ImportError:
            return {p.id: {"heading": p.title, "html": f"<pre>{html.escape(p.body)}</pre>", "refs": [], "apa": None,
                           "excerpt": "", "outline": [], "open": []}
                    for p in self.pages()}
        wiki, by_path = self, {q.path.resolve(): q for q in self.pages()}
        catalog = self.apa_catalog()
        sources = {q.id for q in self.source_cards()}

        class Rewrite(Treeprocessor):
            page: Page
            cites: list[str]
            spots: list[dict]

            def plain(self, el, skip=("ul", "ol", "blockquote", "pre")) -> str:
                """Text eines Elements ohne Fußnotenzeichen und ohne verschachtelte Listen und Kästen."""
                parts = [el.text or ""]
                for child in el:
                    if not (child.tag in skip or child.tag == "sup" and child.find("a[@class='footnote-ref']") is not None):
                        parts.append(self.plain(child, skip))
                    parts.append(child.tail or "")
                text = re.sub(r"⟦c(\d+)⟧", lambda m: html.unescape(re.sub(r"<[^>]+>", "", self.cites[int(m.group(1))])),
                              "".join(parts))
                return one_line(text)

            def spot(self, el, kind: str) -> None:
                anchor = f"offen-{len(self.spots) + 1}"
                el.set("id", anchor)
                text = self.plain(el, skip=("pre",))
                if kind == "contra":
                    text = re.sub(r"^\W*Widerspruch:?\s*", "", text)
                if len(text) > 220:
                    text = text[:220].rsplit(" ", 1)[0].rstrip(",;:") + " …"
                self.spots.append({"kind": kind, "id": anchor, "text": text})

            def scan(self, parent) -> None:
                # Widersprüche und Prüfvermerke außerhalb der Kästen, je Absatz, Listenpunkt oder Zelle
                for el in parent:
                    if el.tag in ("pre", "code") or el.tag == "blockquote" and "callout" in el.get("class", "") \
                            or el.tag == "div" and el.get("class") == "footnote":
                        continue
                    if el.tag in ("p", "li", "td", "th", "dd", "h2", "h3", "h4"):
                        text = self.plain(el)
                        if "⚠" in text and "Widerspruch" in text:
                            self.spot(el, "contra")
                            continue
                        if CHECK_RE.search(text) or self.emphasised(el):
                            self.spot(el, "check")
                            continue
                    self.scan(el)

            def split_callouts(self, root) -> None:
                """Teilt Zitate an jedem Absatz, der mit [!todo] oder ⚠️ Widerspruch beginnt: Python-Markdown fasst
                durch Leerzeilen getrennte `>`-Blöcke zu einem Zitat zusammen, gemeint sind getrennte Kästen."""
                from xml.etree import ElementTree

                def starts(el) -> bool:
                    text = (el.text or "").lstrip()
                    return el.tag == "p" and (text.startswith("[!todo]")
                                              or text.startswith("⚠") and "Widerspruch" in self.plain(el)[:40])

                pairs = [(parent, bq) for parent in root.iter() for bq in parent if bq.tag == "blockquote"]
                for parent, bq in pairs:
                    parts: list[list] = []
                    for child in bq:
                        if not parts or starts(child) and parts[-1]:
                            parts.append([])
                        parts[-1].append(child)
                    if len(parts) < 2:
                        continue
                    at = list(parent).index(bq)
                    parent.remove(bq)
                    for i, part in enumerate(parts):
                        new = ElementTree.Element("blockquote")
                        new.extend(part)
                        new.text = bq.text if i == 0 else "\n"
                        new.tail = bq.tail if i == len(parts) - 1 else "\n"
                        parent.insert(at + i, new)

            def emphasised(self, el) -> bool:
                """**zu prüfen** oder *zu prüfen* im Element selbst, nicht in verschachtelten Listen."""
                for child in el:
                    if child.tag in ("ul", "ol", "blockquote", "pre"):
                        continue
                    if child.tag in ("strong", "em") and re.match(r"\W*zu prüfen\b", self.plain(child), re.I) \
                            or self.emphasised(child):
                        return True
                return False

            def run(self, root):
                linkify(root)
                for a in root.iter("a"):
                    href = a.get("href", "")
                    if re.match(r"^[a-z][a-z0-9+.-]*:", href):
                        a.set("target", "_blank")
                        a.set("rel", "noopener")
                        continue
                    if href.startswith("#"):
                        continue
                    resolved = wiki.resolve(self.page.path, href)
                    target = by_path.get(resolved)
                    if target is not None:
                        a.set("href", "#" + target.id)
                        a.set("data-page", target.id)
                    elif resolved in wiki.withheld:
                        # öffentliche Ausgabe: Link auf eine weggelassene Seite wird zu reinem Text
                        a.tag = "span"
                        a.attrib.clear()
                    else:
                        a.set("href", "#")
                        a.set("class", "missing")
                        a.set("title", "Seite gibt es (noch) nicht")
                self.split_callouts(root)
                for bq in root.iter("blockquote"):
                    first = bq.find("p")
                    text = (first.text or "").lstrip() if first is not None else ""
                    if text.startswith("[!todo]"):
                        first.text = text[len("[!todo]"):].lstrip()
                        bq.set("class", "callout todo")
                        self.spot(bq, "todo")
                    elif "⚠" in (t := "".join(bq.itertext())) and "Widerspruch" in t:
                        bq.set("class", "callout contra")
                        self.spot(bq, "contra")
                self.scan(root)

        def diagram(m: re.Match) -> str:
            langs = {c.removeprefix("language-") for c in (m.group(1) or "").split()}
            if langs & DIAGRAM_LANGS or not langs and BOX_DRAWING_RE.search(m.group(2)):
                return m.group(0).replace("<pre>", '<pre class="diagram">', 1)
            return m.group(0)

        md = markdown.Markdown(extensions=["extra", "sane_lists"], output_format="html")
        md.preprocessors.deregister("html_block")
        md.inlinePatterns.deregister("html")
        rewrite = Rewrite(md)
        md.treeprocessors.register(rewrite, "okf_rewrite", 1)
        out = {}
        for p in self.pages():
            body = p.body.lstrip("\n")
            heading = p.title
            m = re.match(r"# +(.+?)\s*\n", body)
            if m:
                heading, body = m.group(1).strip(), body[m.end():]
            if p.id in sources:
                # Quellenkarten: Titel statt Kurzbeleg- oder APA-Überschrift; die Literaturangabe steht
                # in der Leseansicht unten unter „Zitieren“, nicht noch einmal als Zitatblock oben.
                heading = p.title
                body = strip_reference_block(body)
            refs = self.page_refs(p, by_path)
            if self.withheld:
                body, refs = self._drop_withheld(p, body, refs)
            labels = {label: t for label, t, _ in refs if t is not None and t.path.stem in catalog}
            body, cites = self._apa_cites(body, labels, catalog)
            rewrite.page, rewrite.cites, rewrite.spots = p, cites, []
            md.reset()
            rendered = re.sub(r"⟦c(\d+)⟧", lambda m, c=cites: c[int(m.group(1))], md.convert(body))
            rendered = DIAGRAM_PRE_RE.sub(diagram, rendered)
            literature, seen = [], set()
            for label, target, entry in refs:
                key = target.path.stem if target is not None else None
                if key in seen:
                    continue
                seen.add(key)
                if key in catalog:
                    literature.append({"key": key, "page": target.id, "entry": catalog[key]["entry"],
                                       "access": str((target.fm or {}).get("access") or ""), "order": catalog[key]["order"]})
                else:
                    resource = entry.get("resource", "") if isinstance(entry, dict) else entry
                    literature.append({"key": None, "page": None, "entry": html.escape(str(resource or label)),
                                       "access": "", "order": 10 ** 6, "missing": True})
            literature.sort(key=lambda r: r["order"])
            excerpt, outline = page_preview(rendered, p.description)
            out[p.id] = {"heading": heading, "html": rendered, "refs": literature, "excerpt": excerpt, "outline": outline,
                         "apa": catalog.get(p.path.stem, {}).get("entry") if p.id in sources else None,
                         "open": rewrite.spots}
        return out

    def public_view(self) -> "Wiki":
        """Dasselbe Wiki ohne die Seiten aus hidden_ids(): Graph, Tabelle, Leseansicht, Übersichten, Kennzahlen,
        Literaturverzeichnis und Vorschauen entstehen dann nur aus öffentlichen Seiten."""
        if not self.cfg["visibility"].get("field") or not as_list(self.cfg["visibility"].get("hidden")):
            raise WikiError("öffentliche Ausgabe braucht [visibility] field und hidden in der wiki.toml")
        hidden = self.hidden_ids()
        view = Wiki(self.root, self.cfg, self.config_path)
        view.public = True
        view._pages = [p for p in self.pages() if p.id not in hidden]
        view.withheld = {p.path.resolve() for p in self.pages() if p.id in hidden}
        return view

    def dashboard_path(self, public: bool = False) -> Path:
        spec = self.cfg["dashboard"]
        if not public:
            return self.root / spec["path"]
        if spec.get("public_path"):
            return self.root / spec["public_path"]
        path = Path(spec["path"])
        return self.root / path.with_name(f"{path.stem}-oeffentlich{path.suffix}")

    def write_dashboard(self, out: str | Path | None = None, public: bool = False) -> Path:
        path = Path(out).expanduser().resolve() if out else self.dashboard_path(public)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text((self.public_view() if public else self).render_dashboard(), encoding="utf-8")
        return path

    # ------------------------------------------------------------ Status

    def status(self) -> dict:
        by_type: Counter = Counter()
        tiers: Counter = Counter()
        drafts = stale = todos = 0
        now = dt.datetime.now(dt.timezone.utc)
        for p in self.pages():
            fm = p.fm or {}
            by_type[p.type or "?"] += 1
            drafts += fm.get("status") == "draft"
            when = as_datetime(fm.get("stale_after"))
            stale += bool(when and now >= when)
            todos += p.body.count("[!todo]")
            actors = [str(v.get("by", "")) for v in as_list(fm.get("verified")) if isinstance(v, dict)]
            tiers["human-reviewed" if any(a.startswith("human:") for a in actors)
                  else "machine-confirmed" if actors else "unverified"] += 1
        pending = []
        if self.raw and self.raw.is_dir():
            linked = {str((p.fm or {}).get("raw_packet", "")).rstrip("/") for p in self.pages()}
            stems = {p.path.stem for p in self.pages() if p.type == SOURCE_TYPE}
            pending = [d.name for d in sorted(self.raw.iterdir())
                       if d.is_dir() and self.rel(d) not in linked and d.name not in stems]
        events = self.read_events()
        fundweg: Counter = Counter()
        for q in self.source_cards():
            if q.fm is not None:
                fundweg.update([e["art"] for e in self.fundweg_of(q) if e.get("art")][:1] or ["fehlt"])
        scope = Counter(v for v, _ in self.scopes().values())
        return {"bundle": self.rel(self.bundle), "pages": len(self.pages()), "by_type": dict(sorted(by_type.items())),
                "draft": drafts, "stale": stale, "todo": todos, "trust": dict(tiers), "raw_pending": pending,
                "events": len(events), "last_event": events[-1].get("ts", "") if events else "",
                "fundweg": dict(fundweg), "scope": dict(scope), "hidden": len(self.hidden_ids())}


# ----------------------------------------------------------------------- CLI


URL_RE = re.compile(r"https?://[^\s<>\"']*[^\s<>\"'.,;:!?)\]]")


def linkify(parent) -> None:
    """Macht nackte URLs in einem Markdown-Elementbaum klickbar (nicht in a, code, pre)."""
    from xml.etree import ElementTree

    def anchors(text):
        pieces, last, out = [], 0, []
        for m in URL_RE.finditer(text):
            pieces.append(text[last:m.start()])
            a = ElementTree.Element("a", {"href": m.group(0)})
            a.text = m.group(0)
            out.append(a)
            last = m.end()
        pieces.append(text[last:])
        for a, tail in zip(out, pieces[1:], strict=True):
            a.tail = tail
        return pieces[0], out

    if parent.tag in ("a", "code", "pre"):
        return
    if parent.text and URL_RE.search(parent.text):
        parent.text, new = anchors(parent.text)
        for i, a in enumerate(new):
            parent.insert(i, a)
    for child in list(parent):
        linkify(child)
        if child.tail and URL_RE.search(child.tail):
            child.tail, new = anchors(child.tail)
            at = list(parent).index(child) + 1
            for i, a in enumerate(new):
                parent.insert(at + i, a)


def strip_reference_block(body: str) -> str:
    """Entfernt einen Zitatblock mit der Literaturangabe am Anfang einer Quellenkarte."""
    lines = body.lstrip("\n").split("\n")
    block = []
    for line in lines:
        if not line.startswith(">"):
            break
        block.append(line)
    text = " ".join(line.lstrip("> ") for line in block)
    if block and "[!todo]" not in text and "⚠" not in text and re.search(r"\(\d{4}[a-z]?\)|doi\.org|APA", text):
        return "\n".join(lines[len(block):]).lstrip("\n")
    return body


RIS_TYPES = {"article-journal": "JOUR", "article": "JOUR", "book": "BOOK", "chapter": "CHAP",
             "paper-conference": "CPAPER", "report": "RPRT", "thesis": "THES", "webpage": "ELEC",
             "post-weblog": "BLOG", "software": "COMP", "dataset": "DATA", "legislation": "STAT",
             "legal_case": "CASE", "standard": "STAND", "manuscript": "UNPB"}


def ris_record(item: dict) -> str:
    """RIS-Eintrag (für Zotero und andere Literaturverwaltungen) aus einem CSL-JSON-Eintrag."""
    def date(value) -> str:
        parts = ((value or {}).get("date-parts") or [[]])[0]
        if not parts:
            return ""
        try:
            y, m, d = [int(x) if x not in (None, "") else None for x in (list(parts) + [None, None])[:3]]
        except (TypeError, ValueError):
            return ""
        return f"{y}/{m:02d}/{d:02d}/" if d and m else f"{y}/{m:02d}//" if m else f"{y}///"

    lines = [("TY", RIS_TYPES.get(item.get("type", ""), "GEN"))]
    for role, tag in (("author", "AU"), ("editor", "ED")):
        for name in item.get(role) or []:
            text = name.get("literal") or ", ".join(x for x in (name.get("family"), name.get("given")) if x)
            if text:
                lines.append((tag, text))
    lines.append(("TI", one_line(item.get("title"))))
    for key, tag in (("container-title", "T2"), ("publisher", "PB"), ("publisher-place", "CY"),
                     ("volume", "VL"), ("issue", "IS"), ("number", "M1"), ("genre", "M3"), ("language", "LA")):
        if item.get(key):
            lines.append((tag, one_line(item[key])))
    issued = date(item.get("issued"))
    if issued:
        lines += [("PY", issued.split("/")[0]), ("DA", issued)]
    page = str(item.get("page") or "")
    if page:
        start, _, end = page.replace("–", "-").partition("-")
        lines.append(("SP", start.strip()))
        if end.strip():
            lines.append(("EP", end.strip()))
    if item.get("DOI"):
        lines.append(("DO", str(item["DOI"])))
    url = item.get("URL") or (f"https://doi.org/{item['DOI']}" if item.get("DOI") else "")
    if url:
        lines.append(("UR", str(url)))
    if date(item.get("accessed")):
        lines.append(("Y2", date(item.get("accessed"))))
    lines.append(("ER", ""))
    return "\r\n".join(f"{tag}  - {value}" for tag, value in lines) + "\r\n"


def page_preview(rendered: str, description: str = "", limit: int = 320) -> tuple[str, list[str]]:
    """(Anriss, Gliederung) aus dem gerenderten HTML einer Seite für Vorschauen im Dashboard.

    Anriss ist der erste eigene Absatz außerhalb von Zitat- und Hinweiskästen, der nicht nur die
    Beschreibung wiederholt; Gliederung sind die H2-Überschriften.
    """
    def text(fragment: str) -> str:
        return one_line(html.unescape(re.sub(r"<[^>]+>", "", fragment)))

    outline = [text(m) for m in re.findall(r"<h2[^>]*>(.*?)</h2>", rendered, re.S)][:8]
    body = re.sub(r"<blockquote.*?</blockquote>|<div class=\"footnote\">.*?</div>", "", rendered, flags=re.S)
    excerpt = ""
    for para in re.findall(r"<p>(.*?)</p>", body, re.S):
        candidate = text(para)
        if candidate and candidate != one_line(description):
            excerpt = candidate
            break
    if len(excerpt) > limit:
        excerpt = excerpt[:limit].rsplit(" ", 1)[0].rstrip(",;:") + " …"
    return excerpt, outline


def embedded_fonts() -> str:
    """@font-face-Regeln mit eingebetteten Schriften aus templates/fonts/ (SIL OFL 1.1, siehe README dort)."""
    import base64
    faces = [("IBM Plex Serif", 400, "ibmplexserif-regular.woff2"), ("IBM Plex Sans", 400, "ibmplexsans-regular.woff2"),
             ("IBM Plex Sans", 600, "ibmplexsans-semibold.woff2"), ("JetBrains Mono", 400, "jetbrainsmono-regular.woff2")]
    rules = []
    for family, weight, name in faces:
        font = SKILL_DIR / "templates" / "fonts" / name
        if font.is_file():
            data = base64.b64encode(font.read_bytes()).decode("ascii")
            rules.append(f"@font-face {{ font-family: '{family}'; font-style: normal; font-weight: {weight}; "
                         f"font-display: swap; src: url(data:font/woff2;base64,{data}) format('woff2'); }}")
    return "\n".join(rules)


def protected_paths(wiki: Wiki) -> list[str]:
    paths = [wiki.rel(wiki.events_path), f"{wiki.rel(wiki.bundle)}/**/index.md", f"{wiki.rel(wiki.bundle)}/log.md"]
    if wiki.raw:
        paths.append(f"{wiki.rel(wiki.raw)}/**")
    paths += [v["path"] for v in wiki.cfg["export"].values() if isinstance(v, dict) and v.get("path")]
    paths.append(wiki.cfg["dashboard"]["path"])
    if wiki.cfg["visibility"].get("field"):
        paths.append(wiki.rel(wiki.dashboard_path(public=True)))
    return paths + list(wiki.cfg["paths"].get("protected", []))


def cmd_status(wiki: Wiki, args) -> int:
    s = wiki.status()
    if args.hook:
        counts = ", ".join(f"{k} {v}" for k, v in s["by_type"].items())
        text = [
            f"OKF-v0.2-Wiki unter {wiki.bundle}: {s['pages']} Seiten ({counts}), davon {s['draft']} draft, "
            f"{s['stale']} veraltet, {s['todo']} offene [!todo].",
            f"Letztes Ereignis: {s['last_event'] or 'keins'}.",
            f"Rohquellen ohne Quellenkarte: {', '.join(s['raw_pending'])}." if s["raw_pending"] else "",
            f"{s['hidden']} Seiten nicht öffentlich ([visibility]); öffentliche Seiten nicht auf sie verweisen lassen."
            if s["hidden"] else "",
            f"Vor inhaltlicher Arbeit {wiki.rel(wiki.bundle)}/index.md lesen und im Wiki suchen.",
            f"Nicht direkt bearbeiten: {', '.join(protected_paths(wiki))}.",
            f"Werkzeug: uv run --quiet {SKILL_DIR / 'okfwiki.py'} (new, capture, verify, lint vor Abschluss).",
        ]
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                 "additionalContext": " ".join(t for t in text if t)}},
                         ensure_ascii=False))
        return 0
    print(f"Bundle: {s['bundle']} ({s['pages']} Seiten)")
    print("Seiten nach Typ: " + ", ".join(f"{k} {v}" for k, v in s["by_type"].items()))
    print(f"draft: {s['draft']} · veraltet: {s['stale']} · offene [!todo]: {s['todo']}")
    print("Vertrauen: " + ", ".join(f"{k} {v}" for k, v in sorted(s["trust"].items())))
    if wiki.raw:
        print("Rohquellen ohne Karte: " + (", ".join(s["raw_pending"]) or "keine"))
    if s["scope"]:
        field = wiki.cfg["scope"]["field"]
        print(f"{wiki.cfg['scope'].get('label') or field}: " + " · ".join(
            f"{wiki.cfg['labels'].get(field, {}).get(v, v)} {n}" for v, n in sorted(s["scope"].items())))
    if wiki.cfg["visibility"].get("field"):
        print(f"{wiki.cfg['visibility'].get('label') or 'Sichtbarkeit'}: {s['hidden']} Seiten fehlen in der "
              "öffentlichen Ausgabe (dashboard --oeffentlich)")
    if set(s["fundweg"]) - {"fehlt"}:
        total = sum(s["fundweg"].values())
        print("Fundweg der Quellen: " + " · ".join(f"{FUNDWEG_ARTEN.get(a, a)} {n}" for a, n in
                                                   sorted(s["fundweg"].items(), key=lambda t: -t[1]))
              + f" (Modellvorschlag {100 * s['fundweg'].get('modellvorschlag', 0) // max(total, 1)} %)")
    print(f"Ereignisse: {s['events']}" + (f", zuletzt {s['last_event']}" if s["last_event"] else "")
          + f" ({wiki.rel(wiki.events_path)})")
    return 0


def cmd_lint(wiki: Wiki, args) -> int:
    findings = wiki.lint()
    counts = Counter(f.severity for f in findings)
    if args.json:
        print(json.dumps({"pages": len(wiki.pages()), "counts": dict(counts),
                          "findings": [f.as_dict() for f in findings]}, ensure_ascii=False, indent=1))
    elif args.summary:
        for (sev, code), n in sorted(Counter((f.severity, f.code) for f in findings).items(),
                                     key=lambda t: (SEVERITY_ORDER[t[0][0]], -t[1])):
            print(f"{sev:5}  {code:24}  {n}")
    else:
        for f in findings:
            print(f"{f.severity:5}  {f.code:24}  {f.path}  {f.message}")
    if not args.json:
        print(f"\n{len(wiki.pages())} Seiten · {counts['error']} Fehler · {counts['warn']} Warnungen · "
              f"{counts['info']} Hinweise")
    return 1 if counts["error"] or (args.strict and counts["warn"]) else 0


def cmd_rebuild(wiki: Wiki, args) -> int:
    changed = wiki.rebuild(check=args.check)
    if args.check:
        for path in changed:
            print(f"veraltet: {wiki.rel(path)}")
        return 1 if changed else 0
    if not args.quiet:
        print(f"Projektionen neu erzeugt: {len(changed)} Datei(en) geändert")
    return 0


def cmd_new(wiki: Wiki, args) -> int:
    csl = None
    if args.csl:
        raw = sys.stdin.read() if args.csl == "-" else Path(args.csl).read_text(encoding="utf-8")
        csl = json.loads(raw)
        csl = csl[0] if isinstance(csl, list) else csl
    extra = {}
    for item in args.set:
        key, _, value = item.partition("=")
        extra[key] = load_yaml(value) if value else ""
    lookup = args.doi or args.pmid or args.arxiv
    if (lookup or args.manuell or args.volltext or args.evidenz) and args.type != SOURCE_TYPE:
        raise WikiError("--doi, --pmid, --arxiv, --manuell, --volltext und --evidenz gibt es nur für Quellen")
    if sum(map(bool, (args.doi, args.pmid, args.arxiv, args.manuell, args.csl))) > 1:
        raise WikiError("nur eine Metadatenquelle: --doi, --pmid, --arxiv, --manuell oder --csl")
    src = wiki.cfg["sources"]
    if lookup:
        csl, resource, checked, flags = wiki.fetch_source(args.doi or "", args.pmid or "", args.arxiv or "")
        args.resource = args.resource or resource
        extra[src["checked_field"]] = checked
        if flags:
            extra[src["updates_field"]] = flags
    elif args.manuell:
        if not (args.title and args.url):
            raise WikiError("--manuell braucht --titel und --url")
        csl = {"type": args.csl_typ or src["manual_csl_type"], "title": args.title,
               "author": [{"literal": args.autor or "?"}],
               "issued": {"date-parts": [[args.jahr or dt.date.today().year]]}, "URL": args.url,
               "accessed": today_parts()}
        args.resource = args.resource or args.url
    if args.type == SOURCE_TYPE and not args.access and (lookup or args.manuell):
        manual_access = "originaldokument" in wiki.cfg["enums"].get("access", [])
        args.access = "originaldokument" if args.manuell and manual_access else "citation"
    if args.evidenz:
        extra["evidenz"] = args.evidenz
    if args.volltext:
        extra["fulltext"] = wiki.fulltext_block(args.volltext, args.von or args.resource)["fulltext"]
    if args.fundweg:
        if args.type != SOURCE_TYPE:
            raise WikiError("--fundweg gibt es nur für Quellen")
        extra[wiki.cfg["fundweg"].get("field") or "fundweg"] = wiki.fundweg_entry(
            args.fundweg, db=args.db, query=args.query, von=args.fundweg_von)
    path = wiki.new_page(args.type, args.slug, title=args.title or "", description=args.description or "",
                         sources=[s for s in (args.sources or "").split(",") if s],
                         tags=[t for t in (args.tags or "").split(",") if t],
                         access=args.access, resource=args.resource, csl=csl, extra=extra)
    print(f"angelegt: {wiki.rel(path)}")
    return 0


def cmd_capture(wiki: Wiki, args) -> int:
    packet = wiki.capture(args.slug, args.url, args.file, commit=args.commit, license_name=args.license,
                          license_url=args.license_url, note=args.note, source_path=args.source_path)
    print(f"erfasst: {wiki.rel(packet)} ({len(args.file)} Datei(en))")
    return 0


def cmd_hash(wiki: Wiki, args) -> int:
    print(yaml.safe_dump(wiki.fulltext_block(args.path, args.retrieved_from), allow_unicode=True, sort_keys=False,
                         default_flow_style=False), end="")
    return 0


def cmd_verify(wiki: Wiki, args) -> int:
    path = wiki.verify(args.page, args.by, status=args.status, note=args.note or "")
    print(f"verifiziert: {wiki.page_id(path)} durch {args.by}")
    return 0


def cmd_event(wiki: Wiki, args) -> int:
    wiki.append_event(args.kind, args.page, args.detail or "", by=args.by)
    return 0


def cmd_body(wiki: Wiki, args) -> int:
    body = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
    path = wiki.replace_body(args.page, body, args.detail or "")
    print(f"aktualisiert: {wiki.rel(path)}")
    return 0


def cmd_fundweg(wiki: Wiki, args) -> int:
    entry = wiki.fundweg_entry(args.art, db=args.db, query=args.query, von=args.von, at=args.at, by=args.by)
    path = wiki.set_fundweg(args.page, entry, append=args.add)
    print(f"{wiki.page_id(path)}: Fundweg {FUNDWEG_ARTEN[args.art]}" + (" (ergänzt)" if args.add else ""))
    return 0


RIGHT_WORDS = {"ja": "erlaubt", "bedingt": "mit Auflage", "nein": "nicht erlaubt", "fragen": "erst fragen"}


def cmd_rechte(wiki: Wiki, args) -> int:
    cards = [p for p in wiki.source_cards() if p.fm is not None]
    if args.page:
        page = wiki.parse(wiki.page_path(args.page))
        lic, rights, stored = wiki.license_of(page), wiki.rights_of(page), wiki.fulltext_locations(page)
        if args.json:
            print(json.dumps({"page": page.id, "license": lic, "stored": stored,
                              "rights": {a: {"value": v, "note": n} for a, (v, n) in rights.items()}},
                             ensure_ascii=False, indent=1))
            return 0
        print(f"{page.title}\nLizenz: {lic['name'] or '–'}" + (f" ({lic['url']})" if lic["url"] else "")
              + f"\nKlasse: {lic['label']}")
        for s in stored:
            print(f"Volltext: {s['path']} ({'von Git versioniert' if s['tracked'] else 'nicht versioniert'})")
        for a, (value, note) in rights.items():
            print(f"  {RIGHTS_ACTIONS[a]:42} {RIGHT_WORDS[value]}" + (f" – {note}" if note else ""))
        return 0
    if args.aktion:
        if args.aktion not in RIGHTS_ACTIONS:
            raise WikiError(f"--aktion: eine von {', '.join(RIGHTS_ACTIONS)}")
        groups: dict[str, list[str]] = {v: [] for v in RIGHT_VALUES}
        for p in cards:
            groups[wiki.rights_of(p)[args.aktion][0]].append(p.id)
        if args.json:
            print(json.dumps(groups, ensure_ascii=False, indent=1))
            return 0
        print(f"{RIGHTS_ACTIONS[args.aktion]} ({len(cards)} Quellen)")
        for value, ids in groups.items():
            if ids:
                print(f"\n{RIGHT_WORDS[value]} ({len(ids)}):\n  " + "\n  ".join(sorted(ids)))
        return 0
    by_class = Counter(wiki.license_of(p)["cls"] for p in cards)
    matrix = wiki.rights_matrix()
    if args.json:
        print(json.dumps({"classes": dict(by_class), "matrix": {c: {a: list(v) for a, v in matrix[c].items()}
                                                               for c in by_class}}, ensure_ascii=False, indent=1))
        return 0
    print(f"Lizenzen und Nutzungsrechte ({len(cards)} Quellen)")
    for cls in LICENSE_CLASSES:
        if not by_class[cls]:
            continue
        print(f"\n{LICENSE_CLASSES[cls]} ({by_class[cls]})")
        for a, (value, note) in matrix[cls].items():
            print(f"  {RIGHTS_ACTIONS[a]:42} {RIGHT_WORDS[value]}" + (f" – {note}" if note else ""))
    open_ = sorted(p.id for p in cards if wiki.license_of(p)["cls"] == "unbekannt")
    if open_:
        print(f"\nLizenz ungeklärt ({len(open_)}): " + ", ".join(open_))
    return 0


def cmd_lizenz(wiki: Wiki, args) -> int:
    if args.missing:
        targets = [p for p in wiki.source_cards() if p.fm is not None and wiki.license_of(p)["cls"] == "unbekannt"]
    elif args.page:
        targets = [wiki.parse(wiki.page_path(args.page))]
    else:
        raise WikiError("Seite angeben oder --missing")
    if not args.fetch:
        if args.missing or not (args.name or args.cls):
            raise WikiError("--name (mit --url, --class) setzen oder --fetch nutzen")
        if args.cls and args.cls not in LICENSE_CLASSES:
            raise WikiError(f"--class: eine von {', '.join(LICENSE_CLASSES)}")
        page = targets[0]
        lic = dict((page.fm or {}).get("license") or {}) if isinstance((page.fm or {}).get("license"), dict) else {}
        lic.update({k: v for k, v in (("name", args.name), ("url", args.url), ("class", args.cls)) if v})
        lic.update({"checked": dt.date.today().isoformat(), "via": args.via or "manuell"})
        if args.dry_run:
            print(f"{page.id}: {lic}")
        else:
            wiki.set_license(page.id, lic)
            print(f"{page.id}: {lic['name']} → {LICENSE_CLASSES[classify_license(lic, wiki.cfg['licenses'].get('patterns'))[0]]}")
        return 0
    found = 0
    for i, page in enumerate(targets):
        if not args.missing and not args.force and wiki.license_of(page)["cls"] != "unbekannt":
            print(f"{page.id}: hat schon eine Lizenz ({wiki.license_of(page)['name']}); --force zum Überschreiben")
            continue
        ids = wiki.identifiers(page)
        if not any(ids):
            print(f"{page.id}: weder DOI noch PMID oder PMCID – Lizenz am Original prüfen und mit --name setzen")
            continue
        if i:
            time.sleep(0.3)
        lic = wiki.lookup_license(*ids)
        if not lic:
            print(f"{page.id}: keine Lizenzangabe bei Crossref, DataCite, Europe PMC oder OpenAlex")
            continue
        found += 1
        cls = LICENSE_CLASSES[classify_license(lic, wiki.cfg["licenses"].get("patterns"))[0]]
        if args.dry_run:
            print(f"{page.id}: {lic['name']} ({lic['via']}) → {cls}")
        else:
            wiki.set_license(page.id, lic, f"Lizenz über {lic['via']}: {lic['name']}")
            print(f"{page.id}: {lic['name']} ({lic['via']}) → {cls}")
    if args.missing:
        print(f"\n{found} von {len(targets)} Lizenzen gefunden" + (" (nichts geschrieben)" if args.dry_run else ""))
    return 0


def cmd_dashboard(wiki: Wiki, args) -> int:
    path = wiki.write_dashboard(args.out, public=args.public)
    if args.public:
        hidden = wiki.hidden_ids()
        print(f"Öffentliches Dashboard: {path} ({len(wiki.pages()) - len(hidden)} Seiten, {len(hidden)} weggelassen)")
        for p, targets in wiki.visibility_leaks():
            print(f"  Achtung {p.id} verweist auf verborgene {', '.join(targets)}: Link wird zu Text, Beleg entfällt "
                  "(lint: visibility_leak)", file=sys.stderr)
    else:
        print(f"Dashboard: {path}")
    if args.open:
        webbrowser.open(path.as_uri())
    return 0


def cmd_init(args) -> int:
    root = Path(args.root or os.getcwd()).resolve()
    target = root / "wiki.toml"
    if target.exists():
        raise WikiError(f"{target} existiert schon")
    profile = SKILL_DIR / "profiles" / f"{args.profile}.toml"
    if not profile.is_file():
        raise WikiError(f"Profil fehlt: {profile}")
    shutil.copyfile(profile, target)
    wiki = Wiki.load(config=target)
    for spec in wiki.types.values():
        (wiki.bundle / spec["folder"]).mkdir(parents=True, exist_ok=True)
    wiki.append_event("init", ".", f"Bundle angelegt (Profil {args.profile}, okf-wiki {VERSION})")
    wiki.rebuild()
    print(f"angelegt: {wiki.rel(target)}, Bundle {wiki.rel(wiki.bundle)}/ – Titel und Typen in wiki.toml anpassen")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help="Pfad zur wiki.toml")
    parser.add_argument("--root", help="Projektordner (Standard: Ordner der wiki.toml)")
    parser.add_argument("--version", action="version", version=f"okf-wiki {VERSION}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status", help="Kurzstatistik")
    p.add_argument("--hook", action="store_true", help="als SessionStart-Hook-JSON ausgeben")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("lint", help="OKF-Konformität und Profilregeln prüfen")
    p.add_argument("--strict", "--streng", action="store_true", help="Warnungen ebenfalls als Fehler werten")
    p.add_argument("--json", action="store_true")
    p.add_argument("--summary", action="store_true", help="nur Anzahl je Befund-Code")
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("rebuild", aliases=["index"], help="index.md, log.md und Exporte neu erzeugen")
    p.add_argument("--check", action="store_true", help="nichts schreiben, veraltete Projektionen melden")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_rebuild)

    def new_options(p):
        p.add_argument("--title", "--titel")
        p.add_argument("--description", "--beschreibung")
        p.add_argument("--sources", "--quellen", help="Komma-Liste von Quellen-Slugs → sources[] für Fußnoten [^slug]")
        p.add_argument("--tags")
        p.add_argument("--access")
        p.add_argument("--resource")
        p.add_argument("--csl", help="CSL-JSON-Datei oder - für stdin")
        p.add_argument("--set", action="append", default=[], metavar="FELD=WERT", help="weiteres Feld (YAML-Wert)")
        p.add_argument("--doi", help="Quelle: Metadaten aus Crossref")
        p.add_argument("--pmid", help="Quelle: Metadaten aus PubMed (Crossref lückenhaft oder keine DOI)")
        p.add_argument("--arxiv", help="Quelle: Metadaten aus arXiv")
        p.add_argument("--manuell", action="store_true", help="Quelle ohne DOI: braucht --titel und --url")
        p.add_argument("--autor", help="--manuell: Autor oder Institution (als literal)")
        p.add_argument("--jahr", type=int, help="--manuell: Jahr")
        p.add_argument("--url", help="--manuell: Fundort")
        p.add_argument("--csl-typ", help="--manuell: CSL-Typ (Standard: [sources] manual_csl_type)")
        p.add_argument("--volltext", help="Quelle: lokaler Volltext (Pfad relativ zum Projekt) → fulltext-Block")
        p.add_argument("--evidenz", help="Quelle: Evidenzart laut Profil ([enums] evidenz)")
        p.add_argument("--fundweg", choices=list(FUNDWEG_ARTEN), help="wie die Quelle gefunden wurde")
        p.add_argument("--db", help="Fundweg: Datenbank oder Werkzeug, z. B. pubmed, crossref, tooluniverse:PubMed_search")
        p.add_argument("--query", help="Fundweg: exakter Suchstring")
        p.add_argument("--fundweg-von", help="Fundweg zitatverfolgung: Slug der Quelle, deren Literatur verfolgt wurde")
        p.add_argument("--von", help="mit --volltext: Abruf-URL des Volltexts")
        p.set_defaults(func=cmd_new)

    p = sub.add_parser("new", help="Seite aus Vorlage anlegen")
    p.add_argument("type")
    p.add_argument("slug")
    new_options(p)

    p = sub.add_parser("new-source", help="Quellenkarte anlegen (= new source)")
    p.add_argument("slug")
    new_options(p)
    p.set_defaults(type=SOURCE_TYPE)

    p = sub.add_parser("fundweg", help="Fundweg einer Quelle setzen oder ergänzen")
    p.add_argument("page")
    p.add_argument("--art", required=True, choices=list(FUNDWEG_ARTEN))
    p.add_argument("--db")
    p.add_argument("--query")
    p.add_argument("--von")
    p.add_argument("--at", help="Zeitpunkt (ISO 8601 mit Offset), Standard: jetzt")
    p.add_argument("--by", help="Akteur, Standard: [wiki] actor")
    p.add_argument("--add", action="store_true", help="weiteren Fundweg anhängen statt ersetzen")
    p.set_defaults(func=cmd_fundweg)

    p = sub.add_parser("capture", help="Rohquelle unveränderlich als Paket ablegen")
    p.add_argument("slug")
    p.add_argument("--url", required=True)
    p.add_argument("--file", action="append", default=[], required=True)
    p.add_argument("--source-path", help="Pfad der Datei im Quell-Repository")
    p.add_argument("--commit")
    p.add_argument("--license")
    p.add_argument("--license-url")
    p.add_argument("--note")
    p.set_defaults(func=cmd_capture)

    p = sub.add_parser("hash", aliases=["sha"], help="fulltext-Block (path, sha256, retrieved_at) ausgeben")
    p.add_argument("path")
    p.add_argument("--from", dest="retrieved_from")
    p.set_defaults(func=cmd_hash)

    p = sub.add_parser("verify", help="Prüfvermerk eintragen (OKF §5.2)")
    p.add_argument("page", help="Konzept-ID, z. B. concepts/local-tool")
    p.add_argument("--by", required=True)
    p.add_argument("--status", choices=STATUS)
    p.add_argument("--note")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("event", help="Ereignis anhängen")
    p.add_argument("kind")
    p.add_argument("page")
    p.add_argument("detail", nargs="?")
    p.add_argument("--by")
    p.set_defaults(func=cmd_event)

    p = sub.add_parser("body", help="Körper einer Seite ersetzen, Frontmatter bleibt byte-genau")
    p.add_argument("page")
    p.add_argument("file", help="Markdown-Datei, - für stdin")
    p.add_argument("--detail")
    p.set_defaults(func=cmd_body)

    p = sub.add_parser("rechte", aliases=["rights"], help="Lizenzen und Nutzungsrechte der Quellen anzeigen")
    p.add_argument("page", nargs="?", help="eine Quelle, z. B. sources/x")
    p.add_argument("--aktion", help=f"Quellen nach einem Recht gruppieren: {', '.join(RIGHTS_ACTIONS)}")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_rechte)

    p = sub.add_parser("lizenz", aliases=["license"], help="Lizenz einer Quelle setzen oder über APIs suchen")
    p.add_argument("page", nargs="?")
    p.add_argument("--name")
    p.add_argument("--url")
    p.add_argument("--class", dest="cls", help=f"Klasse festlegen: {', '.join(LICENSE_CLASSES)}")
    p.add_argument("--via", help="Herkunft der Angabe, z. B. originaldokument (Standard: manuell)")
    p.add_argument("--fetch", action="store_true", help="über Crossref, DataCite, Europe PMC und OpenAlex suchen (DOI oder PMID)")
    p.add_argument("--missing", action="store_true", help="alle Quellen mit fehlender oder unbekannter Lizenz")
    p.add_argument("--force", action="store_true", help="vorhandene Lizenz überschreiben")
    p.add_argument("--dry-run", action="store_true", help="nur anzeigen, nichts schreiben")
    p.set_defaults(func=cmd_lizenz)

    p = sub.add_parser("dashboard", help="HTML-Dashboard mit Netz, Struktur und Befunden schreiben")
    p.add_argument("--out", help="Zieldatei (Standard: [dashboard] path, build/wiki-dashboard.html)")
    p.add_argument("--oeffentlich", "--public", dest="public", action="store_true",
                   help="ohne Seiten aus [visibility] hidden, nach build/wiki-dashboard-oeffentlich.html")
    p.add_argument("--open", action="store_true", help="im Browser öffnen")
    p.set_defaults(func=cmd_dashboard)

    p = sub.add_parser("init", help="wiki.toml aus einem Profil anlegen")
    p.add_argument("--profile", default="default")
    p.set_defaults(func=None)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    quiet_hook = (args.cmd == "status" and args.hook) or (args.cmd in ("rebuild", "index") and args.quiet)
    try:
        if args.cmd == "init":
            return cmd_init(args)
        wiki = Wiki.load(config=args.config, root=args.root)
        return args.func(wiki, args)
    except WikiError as exc:
        if quiet_hook:
            return 0
        print(f"okf-wiki: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
