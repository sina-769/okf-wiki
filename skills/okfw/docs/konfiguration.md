# okfw: Aufbau und Konfiguration

## Aufbau des Skills

```text
~/.claude/skills/okfw/
├── SKILL.md                  Arbeitsweise für Claude (Recall → Capture → Ingest → Retro → Lint)
├── okfw.py                   Kern: PEP 723 (Python ≥ 3.11, PyYAML und Markdown über uv), CLI und Bibliothek
├── hooks/okf_hook.py         Guard und Ereignisprotokoll für Claude Code, nur Standardbibliothek
├── hooks/settings.example.json   Hook-Block für .claude/settings.json eines Projekts
├── profiles/default.toml     Grundprofil für neue Wikis (okfw.py init)
├── profiles/dokumentation.toml   Profil für Wikis über Projektdoku und Code (init --profile dokumentation)
├── profiles/…                weitere fertige wiki.toml je Installation (nicht im Plugin)
├── templates/dashboard.html  Vorlage des HTML-Dashboards (okfw.py dashboard)
├── templates/fonts/          IBM Plex Serif/Sans, JetBrains Mono (SIL OFL 1.1, Lizenztexte dabei), werden eingebettet
├── templates/apa.csl         Zitierstil APA 7 (Zotero, CC BY-SA 3.0), Standard für Literaturangaben
├── docs/konfiguration.md     diese Datei
├── local.example.md          Vorlage für local.md
└── local.md                  optional: Ergänzung je Installation (Projekte, Begleit-Skills), nicht im Plugin
```

`profiles/dokumentation.toml` ist für Wikis über Projektdoku und Code gedacht: Quellen mit den Unterarten
Dokumentation, Code, Spezifikation und Datensatz (`format`), Lizenz und Rohquellen-Paket als Pflicht,
fehlender Fundweg als Warnung.

Ohne `local.md` gilt allein `SKILL.md`; `local.example.md` zeigt die Abschnitte, die eine Installation
dort festlegen kann (Webzugriff, externe Dienste, Begleit-Skills, Altbestand).

Aufteilung: Der **Kern** kennt OKF v0.2, das gemeinsame pi-llm-wiki-Profil und alles, was in mehr
als einem Wiki gebraucht wird (auch Lizenzsuche und Metadatenabruf über offizielle APIs). Alles, was
sich zwischen Projekten unterscheidet, steht in der **`wiki.toml`** des Projekts. Nur projekteigene
Register und Korpora bleiben **im Projekt** (etwa ein Prüfskript für Zitate oder ein Aussagenregister,
beschrieben in der `CLAUDE.md` des Projekts).

Aufs Netz greift der Kern nur in Befehlen zu, die dafür da sind (`new source --doi/--pmid/--arxiv`:
Crossref, sonst DataCite, PubMed, arXiv; `lizenz --fetch`: Crossref oder DataCite, Europe PMC,
OpenAlex), nie bei `lint`, `rebuild`, `status` oder `dashboard`. Ohne `wiki.toml` schreibt er
nichts; `status --hook`, `rebuild --hook` und `rebuild --quiet` beenden sich dann still, damit Hooks in
fremden Ordnern nicht stören. Andere Bedienfehler (kaputte `wiki.toml`, `requires_core` zu neu) melden
`status --hook` und `rebuild --hook` als eine Zeile (`systemMessage`, Exit 0).

## Aufruf

```bash
uv run --quiet ~/.claude/skills/okfw/okfw.py <befehl> …
```

Die `wiki.toml` wird aufwärts ab dem aktuellen Ordner gesucht. `--root DIR` nimmt `DIR/wiki.toml`,
`--config PFAD` eine beliebige Datei (Projektordner ist dann ihr Ordner, außer `--root` ist gesetzt). `init` legt die
Datei immer unter `--root` bzw. im aktuellen Ordner an, `--config` gilt dort nicht.

Exit 0 ist ok, 1 steht für `lint` mit Fehlern (mit `--strict` auch Warnungen) oder `rebuild --check` mit veralteten
Projektionen, 2 für einen Bedienfehler (`status --hook` und `rebuild --hook` enden dabei mit 0).

| Befehl | Zweck |
|---|---|
| `status [--hook]` | Seiten je Typ, draft, veraltet, offene `[!todo]` (ohne Code), Vertrauensstufen, gültige und verfallene Freigaben (davon „stable, seit Änderung ungeprüft“) und Seiten „zur Freigabe“, Seiten mit Gegenprüfung ohne Prüfwert, Rohquellen ohne Karte, Umfang, bei `[visibility] field` die Zahl verborgener Seiten, Fundweg, Zahl der Ereignisse und Zeitpunkt des letzten; `--hook` gibt SessionStart-JSON aus |
| `lint [--strict] [--json] [--summary]` | OKF-Konformität und Profilregeln; Exit 1 bei Fehlern (mit `--strict` auch bei Warnungen) |
| `rebuild [--check] [--quiet \| --hook]` (Alias `index`) | `index.md` je Ordner, `log.md`, Exporte; `--check` schreibt nichts und endet mit Exit 1, wenn etwas veraltet ist; `--hook` (Stop-Hook) erzeugt still neu und meldet Lint-Fehler als eine Zeile (`systemMessage`), ohne zu blockieren |
| `new <typ> <slug> --title … [--description] [--sources a,b] [--tags] [--access] [--resource] [--csl DATEI\|-] [--set feld=wert] [--fundweg ART --db --query --fundweg-von SLUG]` | Seite aus Vorlage, `generated` gesetzt, `stale_after` nur bei Typen mit `stale_months`, Quellen mit `license: unknown` (mit `--set raw_packet=…` die Lizenz aus dessen `manifest.json`, `via: capture`) und auf Wunsch `fundweg`, Ereignis `create`. Deutsche Optionen `--titel`, `--beschreibung`, `--quellen` |
| `new source <slug>` bzw. `new-source <slug>` mit `--doi` · `--pmid` · `--arxiv` · `--manuell --titel … --url … [--autor] [--jahr] [--csl-typ]`, dazu `[--volltext PFAD --von URL] [--evidenz E]` | Quellenkarte mit Metadaten aus Crossref (DOIs, die Crossref nicht kennt: DataCite), PubMed oder arXiv (CSL, Kurzbeleg, APA-Block); setzt `[sources] checked_field` (`{by, at}` mit dem Dienst, der geantwortet hat: `process:crossref`, `process:datacite`, `process:pubmed` oder `process:arxiv`) und bei Rückzug oder Korrektur `[sources] updates_field`; `access` ohne Angabe `citation`, bei `--manuell` `originaldokument`, wenn das Profil ihn kennt |
| `fundweg <seite> --art … [--db] [--query] [--von] [--at] [--by] [--add]` | Fundweg einer Quelle setzen; `--add` hängt einen weiteren an; `--at`/`--by` für Nachträge mit dem echten Zeitpunkt; zieht `generated` nach |
| `capture <slug> --url … --file PFAD[=REPO-PFAD] … [--source-path] [--commit] [--license … --license-url …] [--note]` | Rohquellen-Paket mit Manifest (SHA-256, 0444); Symlinks werden abgelehnt. `--file` mehrfach, je Datei mit ihrem Pfad im Quell-Repository (`--file /tmp/x/hooks.json=hooks/hooks.json`); `--source-path` gilt für Dateien ohne eigenen. `--commit` warnt, wenn es kein voller SHA ist. Prüft vorher „Volltext lokal ablegen“ für die Lizenz aus `--license`/`--license-url`: nicht erlaubt → Abbruch, erst fragen oder Auflage → Warnung (ohne `--license` gilt die Lizenz als unbekannt) |
| `hash <pfad> [--from URL]` (Alias `sha`) | `fulltext`-Block für Karten ohne Rohquellen-Paket |
| `verify <seite> [<seite> …] --by human:<id> [--status STATUS] [--note] [--force]` | Prüfvermerk nach OKF §5.2 mit Prüfwert des Seitenkörpers (`body_sha256`, siehe [Freigabe](#freigabe-über-claude)) für eine oder mehrere Seiten (eine Charge), `--note` für alle, ein Ereignis je Seite; ändert nur `verified` und `status`, alles andere bleibt byte-genau. `--status` nimmt `draft` und `deprecated` mit jedem Akteur, `stable` nur mit einem `human:`-Akteur und nur, wenn jede Seite eine Gegenprüfung durch Claude oder einen Prozess (Akteur ohne `human:`) mit Prüfwert zum jetzigen Inhalt hat; sonst Abbruch ohne Änderung, `--force` gibt trotzdem frei und vermerkt das im Ereignis |
| `event <art> <seite> [detail] [--by]` | Ereignis anhängen |
| `body <seite> <datei\|-> [--detail TEXT]` · `body <seite> --nachziehen [--detail TEXT]` | Körper ersetzen; im Frontmatter ändert sich nur `generated {by, at}`, auf einer stable-Seite ohne gültige Freigabe (auch ohne jede Freigabe) dazu `status: draft` (`[trust] edit_resets_stable`; `verified` bleibt stehen, das Ereignis nennt die verfallene Freigabe). `--detail` ist der Text des Ereignisses. Gleicher Inhalt (gleicher Prüfwert) ändert nichts. `--nachziehen`: der Körper ist schon geändert (Edit oder Write, ruft der PostToolUse-Hook auf), nur `generated` und `status` wie eben |
| `sources <seite> [--add a,b] [--remove c]` (Alias `quellen`) | `sources[]` chirurgisch ergänzen oder kürzen, zieht `generated` nach und gibt die Fußnotenzeilen für den Text aus. `--add ID=SLUG` legt eine weitere Fußnote auf dieselbe Karte an (eigene Fundstelle). `--remove` nur, wenn der Text `[^id]` nicht mehr zitiert |
| `init [--profile NAME]` | `wiki.toml` aus `profiles/NAME.toml`, Ordner, erstes Ereignis |
| `rechte [<seite>] [--aktion A] [--json]` (Alias `rights`) | Lizenzen und Nutzungsrechte: Übersicht je Lizenzklasse, eine Quelle im Detail oder alle Quellen nach einem Recht gruppiert (`--aktion abbildung`) |
| `lizenz <seite> --name … [--url] [--class] [--via]` · `lizenz <seite> --fetch [--force]` · `lizenz --missing --fetch [--dry-run]` (Alias `license`) | Lizenz setzen oder suchen (DOI, PMID, PMCID): Crossref bzw. DataCite, Europe PMC, OpenAlex (je Fundort, Verlagsfassung zuerst; `via` nennt Dienst und Fassung); schreibt `license {name, url, checked, via}` chirurgisch, zieht `generated` nach und protokolliert; `--dry-run` gilt für jede Form und zeigt, was geschrieben würde |
| `dashboard [--out PFAD] [--oeffentlich] [--open]` | eine HTML-Datei mit Netz, Kennzahlen, Struktur, Lernpfad, Glossar, offenen Stellen, „Zur Freigabe“ und Tabelle; `--oeffentlich` (Alias `--public`) ohne verborgene Seiten aus `[visibility]` |

## wiki.toml

Alle Pfade relativ zum Projektordner. Nicht gesetzte Werte nehmen den Standard in Klammern.

```toml
[wiki]
title = "…"                     # Überschrift des Root-Index ("Wiki")
bundle = "wiki"                 # OKF-Bundle-Wurzel ("wiki")
actor = "claude-code/claude-opus-5-5"   # generated.by neuer Seiten ("claude-code/unknown"); Umgebungsvariable WIKI_ACTOR geht vor
okf_version = "0.2"
requires_core = "0.1"           # Version als MAJOR.MINOR ("0.3", ein Patch-Teil zählt nicht), anderes ist ein Bedienfehler; Kern verweigert die Arbeit, wenn er älter ist

[paths]
events = "wiki/.events.jsonl"   # Ereignisstrom ("<bundle>/.events.jsonl")
raw = "raw"                     # Rohquellen-Pakete; leer = keine Pakete, nur fulltext-Blöcke
protected = ["quellen/volltexte/**"]   # weitere Muster für den Guard-Hook: fnmatch auf den Pfad relativ zum Projektordner, * passt auch über /, ** hat keine eigene Bedeutung

[index]
root = "overview"               # overview: „Zuerst lesen“ + Bereiche mit Anzahl | full: jede Seite im Root-Index
sort = "title"                  # title | slug
entry_tag = "einstieg"          # Seiten mit diesem Tag kommen nach „Zuerst lesen“, sortiert nach order; zugleich Lernpfad im Dashboard
start_heading = "Zuerst lesen"  # leer = Einstiegsseiten direkt unter dem Titel
areas_heading = "Bereiche"
unit = "Seiten"                 # „54 Seiten“ / „54 Karten“
badges = ["access", "license"]  # Felder als `Badge` hinter dem Link; license zeigt den Lizenznamen
star_field = "core"             # ★ hinter dem Titel, wenn das Feld wahr ist
banner = "> Generiert – nicht von Hand bearbeiten."   # Zeile unter jeder Index-Überschrift

[log]
title = "Aktivitätslog"
banner = ""
link_text = "title"             # title | id (bei id trägt das create-Ereignis den Titel als detail)
show_actor = false              # „(claude-code/…)“ anhängen
labels = {create = "Creation"}   # Beschriftung je Ereignisart, Standard: deutsche Wörter

[enums]                         # Feld = erlaubte Werte; gilt auf allen Seiten, die das Feld tragen
access = ["fulltext", "abstract", "citation"]

[lint]
orphans = "inbound"             # inbound | isolated
fulltext_access = ["fulltext"]  # access-Werte, die raw_packet oder fulltext verlangen
claims_section = "Kernaussagen" # Abschnitt, in dem bei access: citation kein Listenpunkt (-, *, 1.) stehen darf; Fließtext wird nicht gemeldet
priority_field = ""             # z. B. "core": warnt, wenn solche Quellen nur citation haben

[lint.severity]                 # Code = "error" | "warn" | "info" | "off"
path_not_kebab = "error"

[export.csl]
path = "quellen/references.json"   # CSL-JSON aller Quellenkarten mit `csl`-Block (id = Slug)
field = "csl"                   # Frontmatter-Feld mit dem CSL-Eintrag
style = "quellen/apa.csl"       # Zitierstil für pandoc (APA-Block in neuen Karten, Literaturverzeichnis)
lang = "de-DE"

[export.bibliography]
path = "00_arbeit/literaturverzeichnis.md"   # Markdown über pandoc --citeproc
title = "Literaturverzeichnis"

[scope]                         # Umfang: eine Ebene, auf die das Dashboard einengt (ohne field: aus)
field = "umfang"                # Frontmatter-Feld auf allen Seitentypen; Werte vom Kern nach außen in [enums]
label = "Umfang"
default = "kern"                # Voreinstellung im Dashboard ("" = alle); die Wahl merkt sich der Browser
derive = true                   # Quellen ohne Wert erben den engsten Umfang der Seiten, die sie zitieren

[visibility]                    # Sichtbarkeit: was in der öffentlichen Ausgabe ganz fehlt (ohne field: aus)
field = "sichtbarkeit"          # Frontmatter-Feld; erlaubte Werte in [enums], sonst default und hidden
label = "Sichtbarkeit"
default = "oeffentlich"         # Wert für Seiten ohne Feld
hidden = ["intern"]             # diese Werte fehlen in dashboard --oeffentlich
derive = true                   # Quellen ohne Wert, die nur verborgene Seiten nutzen, fehlen dort ebenfalls

[fundweg]
field = "fundweg"               # Feld für den Fundweg der Quellen

[sources]                       # new source --doi/--pmid/--arxiv/--manuell
checked_field = "metadaten_geprueft"   # Metadatenabgleich {by: process:<dienst>, at} – nicht verified
updates_field = "crossref_hinweise"    # Crossref updated-by (Rückzug, Korrektur); im Text nur über {{hinweise}} in einer eigenen Vorlage
manual_csl_type = "document"    # CSL-Typ bei --manuell ohne --csl-typ (z. B. legislation für Gesetze)

[trust]                         # Freigabe (siehe „Freigabe über Claude“)
edit_resets_stable = true       # body auf einer stable-Seite setzt status: draft
signed_human = false            # true: Lint human_unsigned prüft die Commit-Signatur jeder human:-Freigabe (nur mit Git)
human = "human:jdoe"            # Kennung, die „Zur Freigabe“ im Dashboard vorbelegt (sonst die häufigste im Wiki)
check_command = "/pruefen"      # Aufruf der Gegenprüfung für „Gegenprüfung ohne Prüfwert“ (sonst ein Hinweis an Claude)

[licenses.patterns]             # weitere Muster (regulärer Ausdruck, gesucht in Name und URL in Kleinbuchstaben) = Lizenzklasse
"example\\.org" = "vorbehalten"

[rights.vorbehalten]            # Rechtematrix je Klasse überschreiben: "ja", "bedingt: …", "nein: …", "fragen: …"
ki_auswertung = "fragen: Verlag erlaubt kein Text-und-Data-Mining"

[dashboard]
path = "build/wiki-dashboard.html"   # Ziel von okfw.py dashboard; der Guard schützt die Datei
auto = false                    # true: rebuild (also auch der Stop-Hook) schreibt das Dashboard mit (nie öffentlich)
public_path = ""                # Ziel von dashboard --oeffentlich ("": <path> mit Zusatz -oeffentlich vor der Endung, also build/wiki-dashboard-oeffentlich.html)
glossary = ["concept", "entity"]  # Typen, deren Seiten ins Glossar des Dashboards kommen ([] = kein Glossar)

# Je Typ ein Block. Reihenfolge = Reihenfolge der Bereiche im Root-Index.
[types.source]
folder = "sources"              # (Typname)
label = "Quellen"
description = "Je eine Karte pro Quelle"
required = ["title", "description", "resource", "access", "status", "generated"]   # Fehler
recommended = ["license"]       # Warnung ([title, description])
sections = ["Kurzreferat", "Kernaussagen", "Relevanz", "Verbindungen", "Zugang"]  # H2, Präfixvergleich
min_links = 0                   # ausgehende interne Links im Text (2, bei source 0)
needs_footnotes = false         # Seite braucht mindestens eine Fußnote [^id] (nicht bei status: deprecated)
stale_months = 0                # new setzt stale_after = heute + N Monate
template = ""                   # eigene Vorlage, gesucht neben der wiki.toml, dann im Skill unter profiles/ und templates/;
                                # Platzhalter {{title}}, {{description}}, {{apa}}, {{kurzbeleg}}, {{access}}, {{footnotes}},
                                # {{todo_kurzreferat}}, {{todo_kernaussagen}}, {{hinweise}} und {{fm.<feld>}}
defaults = {evidenz = "peer-reviewed"}   # Werte für neue Seiten, wenn nichts angegeben ist

[types.source.todo.abstract]    # Platzhaltertexte je access für Kurzreferat und Kernaussagen überschreiben
kernaussagen = "> [!todo] …"
```

## Gemeinsames Frontmatter-Profil

Fest im Kern (OKF v0.2): `type` Pflicht; `status` ∈ draft | stable | deprecated; `generated {by, at}`
und `verified [{by, at, body_sha256}]` mit Akteurskonvention `<producer>/<version>`, `human:<id>`, `process:<id>`
und ISO-8601-Zeitpunkt mit Offset; `stale_after` als Zeitpunkt; `sources [{id, resource}]`;
Fußnotenlabel = `sources[].id`. `body_sha256` in `verified` ist eine Erweiterung von okfw (OKF §5.2 kennt nur
`by` und `at`; zusätzliche Schlüssel erlaubt §4.1): SHA-256 des Markdown-Körpers ohne Frontmatter, Zeilenenden als
LF, Leerzeilen an Anfang und Ende entfernt. Andere OKF-Werkzeuge lesen den Eintrag weiter als `{by, at}`. Zeitstempel bleiben beim Lesen Strings (kein Umbau zu `datetime`),
YAML-Anker und -Aliase sind verboten.

Quellenkarten (`type: source`) zusätzlich, wenn vorhanden: `access`; `raw_packet` (Pfad zum
Paket mit `manifest.json`) oder `fulltext` als Zuordnung oder Liste mit `path` und `sha256`
(empfohlen außerdem `retrieved_at`, `retrieved_from`; ältere Schlüssel `abgerufen`, `von`,
`fetched_from` bleiben gültig); `license {name, url, checked, via, class}` (Pflicht im Sinn von
`license_missing`, `unknown` ist ein gültiger Name; `class` legt die Lizenzklasse fest und geht jedem Muster vor); `rights {aktion: "wert: Hinweis"}` für Abweichungen von der Klasse, etwa eine erteilte
Genehmigung; `csl` als CSL-JSON ohne `id`; `fundweg` als Zuordnung oder Liste
`{art, db, query, von, at, by}` mit `art` ∈ `suche` | `modellvorschlag` | `material` | `person` |
`zitatverfolgung` (dann `von: <slug>` Pflicht). `db` nennt Datenbank oder Werkzeug (`pubmed`,
`crossref`, `tooluniverse:PubMed_search_articles`), `query` den exakten Suchstring. `person` heißt, die
Quelle wurde ausdrücklich genannt, etwa im Auftrag „README von pi-llm-wiki am Commit 46bd677“; `material`
heißt, sie lag in mitgegebenem Material, ohne einzeln genannt zu sein, etwa eine Datei aus einem
übergebenen Ordner oder ein Eintrag einer mitgeschickten Literaturliste. Quellen aus
Git-Repositorien tragen `pinned {repo, commit}` mit `repo` als `owner/name` und dem vollen Commit-SHA;
ohne `author` bildet die APA-Angabe daraus den Gruppenautor (der Inhaber aus `repo`, bei `format`
documentation, code, specification oder dataset). `capture --commit SHA` schreibt den Commit ins
`manifest.json` des Rohquellen-Pakets und warnt bei einem Kurz-SHA; dass er mit `pinned.commit` übereinstimmt,
prüft der Kern nicht.

Mit `[scope]` trägt jede Seite das Umfangsfeld (z. B. `umfang: kern`). Quellen dürfen es weglassen,
dann gilt der engste Umfang der Seiten, die sie verlinken oder in `sources[]` führen. Abgeleitet
wird nur in Lint, Status und Dashboard, nichts wird geschrieben; ein Wert auf der Karte geht vor.

Mit `[visibility]` darf jede Seite das Sichtbarkeitsfeld tragen (z. B. `sichtbarkeit: intern`); ohne
Feld gilt `default`. Seiten mit einem Wert aus `hidden` fehlen in der öffentlichen Ausgabe ganz,
ebenso Seiten mit einem unbekannten Wert (ein Tippfehler soll nichts veröffentlichen). Unbekannt heißt: nicht in
`[enums]` für das Feld, ohne solchen Eintrag nicht `default` oder `hidden`; ohne `[enums]`-Eintrag und ohne `default`
prüft der Kern keine Werte. Quellen ohne
eigenen Wert, die nur von verborgenen Seiten verlinkt oder in `sources[]` geführt werden, gelten als
verborgen (`derive`); auch das wird nur abgeleitet, nicht geschrieben. `[scope]` bleibt davon
unberührt: Der Umfang blendet im Dashboard nur ein und aus, die Sichtbarkeit lässt Seiten weg.

Unbekannte Felder bleiben erhalten (OKF §4.1). `verify`, `body`, `sources`, `lizenz` und `fundweg` schreiben
chirurgisch: nur die betroffenen Schlüssel bzw. der Körper ändern sich, das Ergebnis wird vor dem Schreiben
geparst. Alle außer `verify` sind inhaltliche Änderungen und setzen `generated {by, at}` auf `[wiki] actor`
und jetzt; `verify` hält nur eine Prüfung fest.

## Fundstellen

Die Fundstelle steht im Fußnotentext: `[^q]: [Titel](/sources/q.md), S. 4`. Erkannt werden S., Seite,
Tab., Abb., Abschn., Kap., Art., Abs., §, Folie, Zeile(n), Z., Rn., Anhang und Erwägungsgrund; das
Dashboard setzt sie in den APA-Beleg („…, 2026, Z. 120–135“).

Eine Fußnote trägt nur eine Fundstelle. Belegt eine Seite viele Stellen derselben Quelle, etwa Zeilen
einer Code-Datei, gibt es zwei Wege:

- **Fundstelle im Satz**, eine Fußnote je Quelle: „`verify` hebt den Status nur mit `human:` (okfw.py
  Z. 763–765).[^okfw-kern]“. Einfach; der APA-Beleg im Dashboard zeigt die Zeile dann nicht.
- **Eine Fußnote je Fundstelle** auf dieselbe Karte: `sources concepts/x --add okfw-kern-z763=okfw-kern`
  legt den Eintrag an, im Text dann `…[^okfw-kern-z763]` mit
  `[^okfw-kern-z763]: [okfw.py](/sources/okfw-kern.md), Z. 763–765`. Das Literaturverzeichnis nennt
  die Quelle trotzdem nur einmal.

## Ereignisse

Eine JSON-Zeile je Ereignis, nur anhängen:

```json
{"ts": "2026-10-25T09:30:00Z", "kind": "verify", "page": "concepts/local-tool", "by": "human:jdoe", "detail": ""}
```

`page` ist die Konzept-ID (Pfad im Bundle ohne `.md`), `raw/<slug>` für Rohquellen, `.` für das ganze
Bundle. Arten: `init`, `bootstrap`, `capture`, `create`, `update`, `verify`, `deprecate`, `delete`, `merge`, `enrich`, `export`, `note`, dazu die Hook-Formen `write` und `edit`;
der PostToolUse-Hook schreibt nach einem Edit oder Write, der den Körper geändert hat, über `body --nachziehen`
ein `update` mit dem Akteur aus `[wiki] actor`, sonst `write`/`edit` mit `by: process:claude-code-hook`; im Log werden nur
`write`/`edit` zu „Erstellt“ (erstes Ereignis einer Seite) bzw. „Aktualisiert“, ein `update` steht immer als „Aktualisiert“. Ältere Formen werden gelesen, nie
umgeschrieben: `creation`, fehlendes `by`, `page` als bloßer Slug (wird über den Dateinamen aufgelöst).

## Lint-Codes und Standardschwere

| Schwere | Codes |
|---|---|
| error | `bundle_missing`, `frontmatter_invalid`, `missing_type`, `root_index_frontmatter`, `index_frontmatter`, `log_frontmatter`, `log_date_heading`, `status_invalid`, `generated_invalid`, `verified_invalid`, `timestamp_invalid`, `source_invalid`, `source_duplicate_id`, `source_missing`, `footnote_unsourced`, `missing_required`, `enum_invalid`, `raw_missing`, `raw_tampered`, `fulltext_tampered`, `citation_with_claims`, `csl_incomplete`, `fundweg_invalid` |
| warn | `okf_version_missing`, `log_order`, `actor_format`, `stable_unverified`, `verified_outdated` (bei stable error), `human_without_check`, `human_unsigned`, `stale`, `footnote_undefined`, `missing_recommended`, `type_folder_mismatch`, `path_not_kebab`, `sections_missing`, `no_footnotes`, `broken_link`, `link_leaves_bundle`, `few_links`, `orphan`, `projection_stale`, `fulltext_absent`, `fulltext_unanchored`, `claim_on_citation_only`, `priority_citation_only`, `source_undated`, `license_missing`, `fulltext_rights`, `fulltext_shared`, `scope_missing`, `visibility_leak`, `fundweg_incomplete` |
| info | `verified_unhashed`, `check_outdated`, `source_uncited`, `type_unknown`, `contradiction_one_sided`, `projection_unavailable`, `raw_uningested`, `license_unknown`, `license_unclassified`, `fundweg_missing` |

Umfang, Sichtbarkeit und Fundweg: `scope_missing` = Seite ohne Umfangsfeld (bei Quellen nur, wenn sich nichts
ableiten lässt); ungültige Werte meldet `enum_invalid`, auch für das Sichtbarkeitsfeld.
`visibility_leak` = öffentliche Seite verlinkt eine verborgene oder führt sie in `sources[]`; in der
öffentlichen Ausgabe wird der Link zu reinem Text, Beleg, Fußnote und Literaturangabe entfallen, der
übrige Satz bleibt stehen. `fundweg_missing` = Quelle ohne Fundweg
(Standard info, im Profil auch warn; `--strict` lässt `lint` bei Warnungen mit Exit 1 enden, der Befund bleibt `warn`, bei `info` wirkt `--strict` nicht); `fundweg_incomplete` = Suche ohne
`db` oder `query`; `fundweg_invalid` = unbekannte Art, Zitatverfolgung ohne `von` oder `von` ohne
Quellenkarte; ein ungültiges `fundweg.at` meldet `timestamp_invalid`, ein ungültiges `by` `actor_format`.

Lizenzbefunde: `license_missing` = Quellenkarte mit weder `license.name` noch `license.url`; `license_unknown` = Name
`unknown` oder gleichwertig (unbekannt, unklar, n/a, none, keine Angabe, nur Striche; Groß/klein egal); `license_unclassified` = Name ohne passendes Muster (`license.class` setzen);
`fulltext_rights` = Volltext abgelegt (Rohquellen-Paket oder `fulltext`), obwohl das Recht dazu
ungeklärt ist; `fulltext_shared` = Volltext von Git versioniert, obwohl die Lizenz keine Weitergabe
erlaubt (Git-Status über `git ls-files`). Fehlt das Feld `license` ganz, meldet das Profil es zusätzlich als
`missing_recommended` (default) bzw. `missing_required` (dokumentation). Zum Volltext selbst: `fulltext_unanchored` =
`access` verlangt einen Volltext (`[lint] fulltext_access`), aber weder `raw_packet` noch `fulltext`-Block, oder ein
`fulltext`-Eintrag ohne `path` oder `sha256`; `fulltext_absent` = die Datei aus `fulltext.path` liegt lokal nicht
vor (Prüfsumme ungeprüft); `fulltext_tampered` = sie weicht vom gespeicherten `sha256` ab.

Vertrauen: `stable_unverified` = `status: stable` ohne `verified`-Eintrag eines Menschen (`human:<id>`);
ein Vermerk durch Claude oder einen Prozess reicht dafür nicht. `verified_outdated` = die letzte Freigabe
durch `human:<id>` gilt nicht mehr dem jetzigen Inhalt: ihr Prüfwert passt nicht mehr, oder sie hat keinen
(Eintrag aus der Zeit vor dem Prüfwert, nicht vergleichbar) und `generated.at` ist jünger als ihr `at`, oder eine spätere
Prüfung mit Prüfwert galt einem anderen Inhalt.
Warnung, bei `status: stable` Fehler (eigene Schwere in `[lint.severity]` gilt für beides). Mit Prüfwert
entscheidet nur er: `lizenz`, `fundweg` und `sources` ziehen `generated` nach, ändern aber den geprüften Text
nicht und lassen die Freigabe stehen. `human_without_check` = eine stable-Seite ist durch `human:<id>` freigegeben,
aber kein anderer Akteur (`[wiki] actor`, `process:…`) hat denselben Inhalt mit Prüfwert gegengeprüft;
Freigaben ohne Prüfwert lösen das nicht aus. `verified_unhashed` = die gültige Gegenprüfung einer noch nicht
freigegebenen Seite hat keinen Prüfwert (Vermerk aus der Zeit vor 0.3.0): sie gilt weiter, zählt aber nicht als
Gegenprüfung für eine Freigabe; neu gegenprüfen lassen und mit `verify` vermerken. `check_outdated` = eine Seite
ohne Freigabe hat Vermerke von Claude oder einem Prozess, aber keiner passt mehr zum Inhalt. Ein Vermerk ohne
Prüfwert gilt, solange weder `generated.at` noch ein späterer Vermerk mit anderem Prüfwert eine Änderung nach
ihm zeigt. `human_unsigned` (nur mit `[trust] signed_human = true` und in
einem Git-Repo) = ein `verified`-Eintrag durch `human:<id>` ist noch nicht committet oder kam mit einem Commit ohne
gültige Signatur (`git blame` je Seite, dann `%G?` des Commits; gültig sind G und U). OKF §5.2 nennt `verified` unabhängig von `generated.at`; okfw bindet die
Freigabe strenger an den Inhalt.

Datum: `source_undated` = Quellenkarte ohne `csl`-Block, aus deren Feldern sich kein Datum ergibt
(`date`, `created`, `published`, `year`); im APA-Beleg stünde „o. J.“. Für Repo-Dateien und Webseiten
das Commit-, Veröffentlichungs- oder Stand-Datum setzen. Ist eine Quelle wirklich undatiert, das bewusst
mit `date: o. J.` (auch `n. d.`, `undatiert`) vermerken; dann entfällt die Warnung. `csl_incomplete` meldet
einen `csl`-Block ohne Titel, ohne `issued` oder ohne Autorschaft (`author` oder `editor`) und einen Block ohne `DOI`
und ohne `accessed`; ein fehlendes `issued` fällt also schon dort auf.

## Freigabe über Claude

Ziel: Eine Freigabe, die Claude auf Zuruf schreibt („Charge 3 freigeben“), bleibt an den Inhalt gebunden,
den ein Mensch gesehen hat, und lässt sich außerhalb von Claude nachprüfen. Drei Stufen:

| Stufe | Woran erkennbar | Wer |
|---|---|---|
| draft | `status: draft`, kein gültiger Vermerk zum jetzigen Inhalt | Claude schreibt mit `new`, `body`, `sources` |
| geprüft | `verified`-Eintrag eines anderen Akteurs (`[wiki] actor`, `process:…`) mit Prüfwert zum jetzigen Inhalt | Gegenprüfung am Original (Skill `pruefen` oder ein Prozess), dann `verify <seite> --by <akteur> --note …` |
| stable | zusätzlich `verified` durch `human:<id>` mit demselben Prüfwert, `status: stable` | nur ein Mensch: `verify <seiten> --by human:<id> --status stable` |

Jeder `verify`-Vermerk trägt den Prüfwert `body_sha256` des Inhalts, den er geprüft hat. Ändert sich der
Körper danach, verfällt die Freigabe: `body` setzt eine stable-Seite auf `draft`, Lint meldet
`verified_outdated`, `status` und Dashboard zählen verfallene Freigaben. Die Vertrauensstufen in `status`
(human-reviewed, machine-confirmed, unverified) zählen nur Vermerke, die zum jetzigen Inhalt passen; Seiten mit
Vermerken, von denen keiner mehr passt, stehen getrennt als „n verfallen“, dazu „n zur Freigabe“. Ohne frische Gegenprüfung lehnt
`verify --status stable` ab (`--force` schreibt trotzdem und vermerkt das im Ereignis; Lint
`human_without_check`). `status` und `verified` ändert nur `verify` und `body` (auch `--nachziehen`), das eine stable-Seite auf draft setzt: Der Guard blockiert Edit und Write, die
diese Schlüssel einer Wiki-Seite ändern; eine neue Seite darf `status: draft` tragen.

Ablauf einer Charge:

1. Claude schreibt die Seiten (`body`), ein frischer Agent prüft sie gegen die Originale (`pruefen`), Claude
   arbeitet die Befunde ein und setzt `verify <seiten> --by <[wiki] actor> --note "Charge 3: …"`.
2. `dashboard` erzeugen, „Zur Freigabe“ aufklappen: je Seite der ganze Text mit hervorgehobenen Belegen (lange
   Seiten zuerst die belegten Aussagen, der ganze Text klappt auf, eingeklappt mit „n Absätze ohne Fußnote“)
   und die Notiz der Gegenprüfung. Lesen, Seiten markieren, Kennung (aus `[trust] human`) und Notiz („Charge 3“)
   eintragen.
3. Die Zeile darunter kopieren und selbst im Terminal ausführen (oder Claude wörtlich übergeben): ein Aufruf,
   ein Ereignis je Seite. Wer eine Seite danach ändert, findet sie unter „Freigabe verfallen“ wieder.
4. Den Stand committen, mit `[trust] signed_human = true` signiert. Lint `human_unsigned` meldet jede
   Freigabe, die nicht aus einem signierten Commit stammt; diese Signatur kann Claude nicht leisten.

Commit-Signatur einrichten (SSH-Schlüssel, Git ≥ 2.34; einmal je Rechner, der Schlüssel bleibt außerhalb von Claude):

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
echo "$(git config user.email) $(cat ~/.ssh/id_ed25519.pub)" >> ~/.ssh/allowed_signers
git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers
git commit -S -m "Charge 3 freigegeben"    # oder dauerhaft: git config --global commit.gpgsign true
```

## Lizenzen und Nutzungsrechte

Jede Quellenkarte trägt eine Lizenz. Der Kern ordnet sie über Name und URL einer Klasse zu; passen
mehrere Muster (Mischangaben wie „Metadaten gemeinfrei; Abstracts geschützt“), gilt die strengste. Ein
`license.class` auf der Karte geht jedem Muster vor. Gültige Klassen: `frei`, `by`, `sa`, `nd`, `nc`, `nc-nd`,
`vorbehalten`, `unbekannt`; andere Werte werden ignoriert.
Je Klasse legt eine Matrix fest, was die Person mit der Quelle tun darf. Werte: **erlaubt**, **mit
Auflage** (Hinweis sagt welche), **nicht erlaubt**, **erst fragen**. Die Matrix ist eine Arbeitshilfe,
keine Rechtsberatung; im Zweifel gilt „erst fragen“.

| Aktion | Gemeinfrei | Namensnennung (CC BY, MIT, Apache) | … gleiche Lizenz (SA, GPL) | Keine Bearbeitung (ND) | Nicht kommerziell (NC) | NC-ND | Alle Rechte vorbehalten | Unbekannt |
|---|---|---|---|---|---|---|---|---|
| Kurz zitieren mit Beleg | ja | ja | ja | ja | ja | ja | ja (Zitatrecht) | ja (Zitatrecht) |
| Volltext lokal ablegen | ja | ja | ja | ja | ja | ja | Auflage: nur eigene Arbeit | fragen |
| Volltext weitergeben, versionieren | ja | Auflage | Auflage + gleiche Lizenz | nur unverändert | nicht kommerziell | nicht kommerziell, unverändert | nein | fragen |
| Abbildung, Tabelle übernehmen | ja | Auflage | Auflage + gleiche Lizenz | nur unverändert | nicht kommerziell | nicht kommerziell, unverändert | fragen (Genehmigung) | fragen |
| Bearbeiten, übersetzen, nachzeichnen | ja | Auflage, Änderungen kennzeichnen | dto. + gleiche Lizenz | nein | nicht kommerziell | nein | nein | fragen |
| Volltext maschinell auswerten | ja | ja | ja | ja | ja | ja | Auflage: eigene Auswertung, TDM-Vorbehalt beachten, keine Dienste, die speichern oder trainieren | fragen |
| Kommerzieller Rahmen | ja | ja | ja | ja | nein | nein | fragen | fragen |

Auflage bei Namensnennung: Urheber und Lizenz angeben. Projekte überschreiben Zellen in
`[rights.<klasse>]`, einzelne Quellen mit `rights:` auf der Karte (z. B.
`rights: {abbildung: "ja: Abdruckgenehmigung des Verlags vom 2026-10-20"}`; den Beleg dafür als
Quelle erfassen).

Lizenzen finden: `lizenz <seite> --fetch` fragt Crossref (bevorzugt die Lizenz der Verlagsfassung), für
DOIs, die Crossref nicht kennt, DataCite, dann Europe PMC und OpenAlex (je Fundort, Verlagsfassung zuerst);
ohne DOI, PMID oder PMCID bleibt nur das Original (Lizenzhinweis im PDF, Impressum, Kopf einer Datei),
dann `lizenz <seite> --name … --url … --via originaldokument`. Unpaywall braucht eine E-Mail-Adresse
im Aufruf und ist deshalb nicht eingebaut.

`via` sagt, woher die Lizenzangabe stammt. Werte:

| `via` | Herkunft |
|---|---|
| `crossref (vor)`, `datacite`, `europepmc`, `openalex (publishedVersion)` | `lizenz --fetch`, mit Dienst und Fassung |
| `capture` | `capture --license`, von `new source --set raw_packet=…` aus dem Manifest übernommen |
| `originaldokument` | Lizenzhinweis im Dokument selbst (PDF, Impressum, Kopfzeile einer Datei) |
| `repo-lizenz` | `LICENSE`-Datei des Repositoriums am gepinnten Commit; am besten selbst als Rohquelle erfasst |
| `github-api` | Lizenzfeld der GitHub-API (`/repos/<owner>/<name>/license`, `spdx_id`) |
| `manuell` | Standard von `lizenz --name` ohne `--via`; besser einen der Werte oben setzen |

Erläuterungen gehören nicht in `via`, sondern in eine Notiz auf der Karte (`event note …` oder den
Abschnitt „Zugang“).

Graph: Kanten sind Links im Text **und** `sources[].resource`, die auf Seiten im Bundle zeigen
(OKF §5.1: eine Quelle, die ein Konzept ist, ist schon eine Kante). `few_links` zählt nur Links im Text.

## Als Bibliothek

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/okfw"))
import okfw   # braucht PyYAML im laufenden Python

wiki = okfw.Wiki.load(root="/pfad/zum/projekt")      # liest wiki.toml
findings = [f.as_dict() for f in wiki.lint()]
wiki.rebuild()
wiki.new_page("source", "shaw-2024", csl=csl_dict, access="fulltext",
              extra={"fulltext": wiki.fulltext_block("00_arbeit/pdfs/x.pdf")["fulltext"]})
wiki.verify("concepts/iso-9001", by="claude-code/claude-opus-5-5")                 # Gegenprüfung
wiki.verify_pages(["concepts/iso-9001"], by="human:jdoe", status="stable", note="Charge 1")
wiki.append_event("enrich", "sources/shaw-2024", "Lizenz aus Crossref")
```

Was mehr als ein Wiki braucht (z. B. `new-source --doi`), kommt als Befehl in den Kern
Projektskripte nutzen den Kern nur noch für wirklich projekteigene
Register und Korpora.

## Dashboard

`okfw.py dashboard` schreibt eine eigenständige HTML-Datei zum **inhaltlichen Erkunden** des Wikis:
Daten als JSON eingebettet, Layout und Bedienung in reinem JavaScript, keine Bibliotheken aus dem Netz,
in unter einer Sekunde erzeugt. Technische Angaben (Lint-Befunde, Prüfstatus) stehen bewusst nicht darin;
dafür gibt es `lint` und `status`. Ausnahme ist die Freigabe („Zur Freigabe“, verfallene Freigaben), die nur die
normale Ausgabe zeigt. Dateipfade erscheinen nur als Ablageort der Volltexte auf Quellenkarten,
in der öffentlichen Ausgabe nicht. Zeitangaben (Stand, Fundweg) stehen nur als Datum darin,
auch in den eingebetteten Daten, keine Uhrzeiten. Was die Seiten selbst als offen markieren, zeigt die
Übersicht „Offene Stellen“ (`[!todo]` dort eingeklappt). Mermaid ist bewusst nicht eingebettet (mehrere MB
je Datei, kein Wiki nutzt es); Diagramme stehen als Textdiagramm in einem `text`-Block.

- **Überschrift:** `[wiki] title` ohne einen Zusatz „– zuerst lesen“ (der gehört in den Root-Index).
- **Verfallene Freigaben:** Die Kopfzeile nennt ihre Zahl, Vorschau und Leseansicht zeigen an der Seite
  „stable, seit Änderung ungeprüft“ bzw. „Freigabe verfallen“ (nur in der normalen Ausgabe).
- **Überblick:** Kacheln nur für Seiten je Art, „Fundweg dokumentiert“ und „Lizenz geklärt“.
- **Netzwerkgraph:** Kanten wie im Lint (durchgezogen „verlinkt“ = Link im Text, gestrichelt „zitiert als
  Quelle“ = nur über `sources[]`). Layout nach Fruchterman-Reingold mit schwachem Zug zum Typ-Anker,
  deterministisch (Startwerte aus der Konzept-ID), ohne Überlappung; das größte Netz links, Inseln
  daneben, Seiten ohne Verbindung als Raster darunter. Runde Knoten, Größe = eingehende Verbindungen;
  bewusst klein (Trefferfläche größer als der Punkt).
- **Vorschau und Karte:** Zeigen öffnet eine kurze Vorschau (Art, Unterart, Titel,
  Kurzbeleg, Beschreibung, erster Absatz, Abschnitte). Ein Klick heftet eine Karte mit der ganzen Seite
  an, zum Scrollen: Text mit APA-Belegen, Literatur, Verknüpfungen; Links öffnen die Zielseite in
  derselben Karte, „Ganze Seite“ führt in die Leseansicht, × oder Esc schließt. Im Netzwerkgraph liegt
  die Karte über der Seitenleiste, im Schichtengraph neben dem Klick. Doppelklick öffnet direkt die
  Leseansicht.
- **Übersichtsseiten:** Die Unterart im Kopf einer Seite, Lizenz und Fundweg einer Quelle sind klickbar und
  öffnen – in Karte oder Leseansicht – eine Übersicht aller Seiten mit diesem Wert, nach Art gruppiert,
  mit Kurzbeleg oder Beschreibung. „Zurück“ führt zur Ausgangsseite,
  „Im Graphen hervorheben“ markiert dieselben Seiten im Dashboard.
- **Schichtengraph (Crosswalk):** Umschalter „Netzwerkgraph | Schichtengraph“. Ein geschichteter Graph
  nach dem Sugiyama-Verfahren: je Art eine Spalte, von der Grundlage zum
  Querschnitt (Quellen, Entitäten, Konzepte, Synthesen, Analysen; Typen außerhalb des Profils neben dem
  Typ ihres Ordners), je Seite eine Zeile mit Titel und zweiter Zeile (bei Quellen Kurzbeleg und
  Unterart, sonst Beschreibung oder erster Absatz), Fäden zwischen Seiten verschiedener Spalten.
  Reihenfolge nach Verbindungen (Baryzentren, weniger Kreuzungen) oder alphabetisch; Seiten ohne Faden
  lassen sich ausblenden. Zeigen: Vorschau; Klick: Karte mit der ganzen Seite und hervorgehobene Fäden.
  Der Bereich ist fast bildschirmhoch (Höhe des Fensters minus 80 px, mindestens 560 px) und scrollt in sich.
- **Filter und Farbe:** Art-Chips blenden aus, Suche durchsucht Titel, Beschreibung, ersten Absatz,
  Kurzbeleg, Aliase, Schlagwörter und Themenbereiche (nur als Suchtext, angezeigt werden sie nicht).
  „Kategorie“ hebt eine Unterart, Lizenzklasse oder Fundweg-Art hervor. „Farbe“ wechselt zwischen Art und
  Umfang (nur mit `[scope]`).
- **Reihenfolge der Arten:** Art-Chips, Kachel „Seiten“, Tabelle (Spalte „Art“), Übersichtsseiten, Glossar,
  Offene Stellen und die Spalten des Schichtengraphen stehen einheitlich von der Grundlage zum Querschnitt:
  Quellen, Entitäten, Konzepte, Synthesen, Analysen, danach weitere Profiltypen in der Reihenfolge der
  `wiki.toml`; Typen außerhalb des Profils neben dem Typ ihres Ordners. Die Reihenfolge der `[types.*]`
  in der `wiki.toml` gilt im Dashboard nur noch für das Layout des Netzwerkgraphen (und weiter für den Root-Index).
- **Bewusst nicht enthalten (nicht wieder einführen):** Themenbereiche und
  Schlagwörter erscheinen nirgends (keine Kachel, keine Tabellenspalte, nicht unter „Kategorie“ oder „Farbe“,
  keine Angaben oder Übersichtsseiten an der Seite), keine Übersichtskästen unter dem Graphen, keine
  Kacheln „Verbindungen“ und „Quellenlage“.
- **Tabelle:** alle Seiten mit Beschreibung, Art, Unterart, Lizenz und Verbindungen, sortierbar.
- **Lernpfad:** Seiten mit dem Schlagwort aus `[index] entry_tag` (Standard `einstieg`) in der Reihenfolge
  von `order`, dann Titel, wie „Zuerst lesen“ im Root-Index. Unter dem Überblick als nummerierte Schritte mit
  Art und Beschreibung, „Lernpfad starten“ öffnet Schritt 1 in der Leseansicht. Dort steht über dem Titel
  „Lernpfad · Schritt N von M“ mit ‹ ›, nach dem Text „← Schritt N−1“ und „Schritt N+1 →“, am Ende „Ende
  des Lernpfads“. Ohne solche Seiten fehlt der Abschnitt.
- **Textdiagramme:** Codeblöcke ```` ```text ```` (auch `txt`, `plain`, `plaintext`, `ascii`, `tree`,
  `diagram` und unmarkierte Blöcke mit Rahmenzeichen U+2500–U+257F) erscheinen in der Leseansicht als
  Abbildung: heller Grund, JetBrains Mono ohne Ligaturen, Zeilenhöhe 1,45, damit `│ ├ └` senkrecht
  durchgehen; breite Bäume scrollen waagerecht im Kasten, auf schmalen Bildschirmen in 12 px.
- **Glossar:** eingeklappter Abschnitt mit allen Seiten der Typen aus `[dashboard] glossary` (Standard
  Konzepte und Entitäten), A–Z gruppiert, mit Beschreibung und „Auch: …“ aus `aliases`. Suche über Titel,
  Aliase und Beschreibung, Buchstabenleiste springt zur Gruppe, Klick öffnet die Seite in der Leseansicht.
- **Offene Stellen:** eingeklappter Abschnitt mit allem, was die Seiten selbst als offen markieren, je mit
  Seite, Art und Textanfang; ein Klick öffnet die Leseansicht an der Fundstelle und hebt sie kurz hervor.
  Erfasst werden Kästen `> ⚠️ **Widerspruch:**` (auch als Absatz oder Listenpunkt), ausdrückliche
  Prüfvermerke „zu prüfen“ (am Absatzanfang, in Anführungszeichen, Klammern oder fett/kursiv; nicht im
  Fließtext wie „um zu prüfen, ob“) und Kästen `> [!todo]`. Widersprüche und Prüfvermerke stehen als Liste,
  `[!todo]` eingeklappt je Seite, weil große Wikis über tausend davon haben. Durch Leerzeilen getrennte
  `>`-Kästen bleiben getrennt, auch wo Markdown sie zu einem Zitat zusammenfassen würde.
- **Zur Freigabe:** eingeklappter Abschnitt (nur normale Ausgabe, nur lesend) mit allen Seiten, die ein anderer
  Akteur als ein Mensch (Claude, `process:…`) zum jetzigen Inhalt gegengeprüft hat und die keine gültige
  menschliche Freigabe haben: je Seite Titel (öffnet die Leseansicht), Gegenprüfung mit Akteur, Datum und
  Notiz aus dem Ereignis, „Freigabe verfallen, neu gegengeprüft“, falls zutreffend, die Zahl der Absätze ohne
  Fußnote und der ganze Text wie in der Leseansicht, Absätze und Listenpunkte mit Beleg hervorgehoben. Ist der
  Text länger als rund 1600 Zeichen, stehen zuerst die belegten Aussagen mit dem Text ihrer Fußnoten, der ganze
  Text klappt darunter auf („Ganze Seite · n Absätze ohne Fußnote“). Darunter die Seiten mit verfallener
  Freigabe ohne neue Gegenprüfung, mit Grund, und „Gegenprüfung ohne Prüfwert“ (Lint `verified_unhashed`) mit
  einer Zeile zum Kopieren, die eine neue Gegenprüfung anstößt: `[trust] check_command` und die Seiten, sonst
  eine Bitte an Claude mit Prüfablauf und `verify --by <[wiki] actor>`; kein `verify`-Aufruf. Kennung
  (vorbelegt aus `[trust] human`, sonst mit der häufigsten `human:`-Kennung im Wiki) und Notiz für die Charge
  eingeben, Seiten markieren; die Zeile darunter ist der fertige Aufruf
  `uv run --quiet …/okfw.py --root … verify <seiten> --by human:<id> --status stable --note …` mit „Kopieren“.
  Pfade unter dem Home-Ordner stehen mit `~`. Ohne solche Seiten fehlt der Abschnitt.
- **Sprungleiste:** unter dem Titel Links zu Lernpfad, Glossar, Offene Stellen, Zur Freigabe und Alle Seiten, soweit
  vorhanden; ein eingeklappter Abschnitt klappt dabei auf.
- Glossar und Offene Stellen folgen dem Umschalter „Umfang“; die Kopfzeile nennt dann auch die Gesamtzahl.
- **Umfang:** Mit `[scope]` steht neben den Art-Chips ein Umschalter „Umfang: alle | Kern | …“. Er
  blendet Seiten außerhalb des gewählten Umfangs in Netz, Schichtengraph und Tabelle aus, startet mit
  `[scope] default` und merkt sich die Wahl im Browser. „Farbe: Umfang“ färbt nach Wert; abgeleitete
  Quellen erscheinen als Ring, die Tabelle zeigt „(abgeleitet)“.
- **Sichtbarkeit und öffentliche Ausgabe:** Mit `[visibility]` zeigt die normale Ausgabe alles; verborgene
  Seiten tragen in Vorschau, Karte und Leseansicht ein Abzeichen („Intern“, Name aus
  `[labels.<feld>]`), die Tabelle eine Spalte und die Kopfzeile „davon N nicht öffentlich“.
  `dashboard --oeffentlich` schreibt nach `[dashboard] public_path` (Standard
  `build/wiki-dashboard-oeffentlich.html`) und lässt verborgene Seiten vor allem anderen weg: Sie fehlen
  in Graph, Schichtengraph, Tabelle, Leseansicht, Übersichtsseiten, Kennzahlen, Literaturverzeichnis,
  RIS und Vorschauen, ihre Kanten zählen nicht. Ablageorte der Volltexte stehen in der öffentlichen Datei
  bei keiner Quelle. Links auf sie werden zu reinem Text, Belege auf sie
  entfallen samt Fußnote. Arten, Umfänge und lesbare Namen (`[labels]`), die nur verborgene Seiten
  tragen, und das Sichtbarkeitsfeld selbst stehen nicht in der Datei. Die Konsole nennt jede Stelle
  mit `visibility_leak`; geschrieben wird trotzdem. Ohne `[visibility] field` und `hidden` bricht
  `--oeffentlich` ab. Was eine öffentliche Seite selbst über eine interne schreibt, bleibt stehen: Der
  Kern entfernt Seiten und Verweise, keine Sätze.
- **Fundweg:** Kachel „Fundweg dokumentiert“ mit dem Anteil der Modellvorschläge, Fundweg als
  Kategorie und Übersichtsseite, auf jeder Quellenkarte der Abschnitt „Fundweg“ (Art, Datenbank,
  Suchstring, Datum, bei Zitatverfolgung ein Link zur Ausgangsquelle).
- **Lizenzen und Nutzungsrechte:** Kachel „Lizenz geklärt“, Lizenzklasse als Kategorie. Jede
  Quellenkarte hat über der Literaturangabe den Abschnitt „Lizenz und Nutzungsrechte“, eingeklappt
  mit der Lizenz in der Kopfzeile. Aufgeklappt: Lizenzname (verlinkt), Klasse, wo der Volltext liegt und ob Git ihn versioniert (nur in der
  normalen Ausgabe), dazu die Rechte als Tabelle
  (erlaubt, mit Auflage, nicht erlaubt, erst fragen). Die Übersichtsseite einer Lizenzklasse zeigt
  zuerst, was diese Klasse erlaubt, dann alle Quellen mit ihr.

Kategorien in `wiki.toml` (`[taxonomy]` bestimmt nur noch, welches Feld die Suche als Themenbereich
mitliest; angezeigt wird es im Dashboard nicht):

```toml
[taxonomy]
field = "domain"                # Frontmatter-Feld für Themenbereiche (eine Liste oder ein Wert)
label = "Themenbereich"

[types.source]
subtype = "evidenz"             # Feld der Unterart; ohne Angabe das erste von category, format, evidenz, worktype

[labels.domain]                 # lesbare Namen je Feld und Wert, sonst erscheint der Rohwert
qm = "Qualitätsmanagement"
```
- **Belege nach APA 7:** In der Leseansicht wird jede Fußnote `[^id]`, deren `id` auf eine Quellenkarte
  zeigt, zum APA-Klammerbeleg „(Sarkar & Drosos, 2025)“ vor dem Satzzeichen; mehrere hintereinander
  werden zu „(A, 2020; B, 2021)“. Fundstellen aus dem Fußnotentext (S., Art., §, Abs., Kap., Tab. …)
  wandern in den Beleg („…, 2016, Art. 9“), der übrige Fußnotentext in den Tooltip. Am Ende steht
  genau ein Literaturverzeichnis in APA 7 (alphabetisch, hängender Einzug) mit dem `access` jeder
  Quelle und einem Sprung zur Quellenkarte; Fußnotenblock und eine zweite Quellenliste entfallen.
  Quellenkarten zeigen oben Kurzbeleg und Titel; eine Überschrift im Stil „Autor (Jahr): Titel“ und ein
  Zitatblock mit der Literaturangabe am Anfang des Textes entfallen in der Anzeige. Ganz unten steht
  die Literaturangabe (Vollbeleg nach APA 7) ohne eigene Überschrift, mit klickbaren Links, „Kopieren“
  (reiner Text) und „RIS herunterladen“ für Zotero und andere Literaturverwaltungen; Seiten mit Literatur
  bieten „Literatur als RIS“, die Fußzeile „Alle Quellen als RIS“. Das RIS entsteht aus demselben CSL-Eintrag wie die APA-Angabe. Nackte URLs im Text
  werden klickbar (nicht in Code). Die Seiten selbst bleiben unverändert: Im Wiki gilt weiter die
  Fußnote mit `sources[].id`.
  Formatiert wird mit pandoc `--citeproc` und dem Stil aus `[export.csl] style`, sonst
  `templates/apa.csl` (Zotero „APA Style 7th edition“), Sprache `[export.csl] lang` (de-DE): ein Aufruf
  für alle Quellen, rund 0,4 s für 54 Quellen. Denselben Stil nutzen der APA-Block neuer Quellenkarten
  und `[export.bibliography]`. Ohne pandoc gibt es eine einfache Ersatzform.
  CSL je Quellenkarte: der `csl`-Block; sonst aus flachen Feldern `authors`, `year`, `container`,
  `volume`, `issue`, `pages`, `doi` (Autorenlisten „Nachname“, „V. M.“ werden gepaart);
  sonst aus `title`, `resource`, `author` (Pull Requests), Repo-Inhaber aus `pinned.repo` als
  Gruppenautor, `created` als Datum und `retrieved_at` des Rohquellen-Manifests als Abrufdatum.
  Die APA-Angabe ist nur so gut wie diese Daten (fehlende Daten ergeben „o. J.“, gleiche Autor:innen
  ohne Jahr „o. J.-a, -b …“); für exakte Angaben gehört ein `csl`-Block auf die Karte.
- **Leseansicht:** Doppelklick auf einen Knoten, „Seite lesen“ in der Seitenleiste oder „Lesen“ in der
  Tabelle zeigt die Seite wie einen Blogartikel der Website: Überschrift, Beschreibung, Unterart,
  Stand, formatierter Text mit APA-Belegen, `> [!todo]` als Kasten „Offen“,
  `> ⚠️ **Widerspruch:**` hervorgehoben, Literatur nach APA 7, eingeklappt „Verweist auf“ (ohne die
  Literatur) und „Verlinkt von“. Interne Links öffnen die Zielseite in der Leseansicht; nur dann
  erscheint „Zurück“. „Schließen“ oder Esc beendet die Leseansicht. Der Kern rendert das Markdown (Python-Markdown mit `extra`); rohes HTML
  in Seiten wird nur als Text gezeigt, nie ausgeführt.

Gestaltung: Alabaster-Grund #F4F3ED,
weiße Karten mit 14 px Radius, Charcoal #1A1A1A, Akzent Gelb #FCE53A (dunkel: Blau #3a5efc),
Überschriften IBM Plex Serif, Text IBM Plex Sans, Code und Metadaten JetBrains Mono; der Artikeltext
übernimmt `.prose-content`. Die Schriften liegen in `templates/fonts/` und werden eingebettet
(etwa 400 KB je Dashboard), damit die Datei auch ohne Netz gleich aussieht; ein CSS-Kommentar davor nennt
Copyright und Lizenz.

Farben: Nach Art haben die vier gemeinsamen Typen in jedem Wiki dieselbe Farbe (Quelle blau,
Konzept grün, Entität gelb, Synthese magenta), alle Knoten sind rund; Entitäten erscheinen als Ring,
weil Gelb und Grün im Dunkelmodus für manche Formen von Farbenfehlsichtigkeit nah beieinander liegen.
Weitere Typen sind graue Ringe. Nach Umfang (`[scope]`) bekommen die vier
ersten Werte dieselben vier Farben. Für ein Netz zählen alle Farbpaare; diese Vierergruppe besteht
den Palettenvalidator des dataviz-Skills mit `--pairs all` in hell und dunkel, auch auf den
Website-Flächen (#FFFFFF, #161616). Mehr Farben bestehen ihn nicht, deshalb Grau ab dem fünften Wert.
Legende, Beschriftungen und die Tabelle sind die nicht farbliche Alternative. Umschaltbar ist nur
hell und dunkel; ohne gespeicherte Wahl gilt die Einstellung des Systems.

## Hooks (Claude Code)

Als Plugin kommen die Hooks aus `hooks/hooks.json` des Plugins; im Projekt ist nichts einzutragen. Alle
laufen über `uv run --script`, `python3` braucht es nicht:

| Ereignis | Aufruf (Plugin) | Wirkung |
|---|---|---|
| SessionStart | `uv run --quiet --script "${CLAUDE_PLUGIN_ROOT}/skills/okfw/hooks/okf_hook.py" session-start` → `okfw.py status --hook` | Stand des Wikis und geschützte Pfade als Kontext |
| PreToolUse `Write\|Edit\|MultiEdit\|NotebookEdit` | `… okf_hook.py guard` | blockiert Ereignisstrom, `raw/`, Exporte, Dashboards (mit `[visibility]` auch das öffentliche), `index.md`/`log.md` im Bundle, `[paths] protected`; auf Wiki-Seiten Edit, MultiEdit und Write, die `status` oder `verified` ändern |
| PostToolUse `Write\|Edit\|MultiEdit` | `… okf_hook.py post-edit` | hat das Werkzeug den Körper einer Seite im Bundle geändert (Vergleich mit dem Stand davor aus der Antwort von Claude Code; fehlt er, gilt der Körper als geändert): `okfw.py body <seite> --nachziehen` zieht `generated` nach, stable wie bei `body`, und bittet Claude, die Datei vor dem nächsten Edit neu zu lesen; sonst Ereignis `write`/`edit` |
| Stop | `… okf_hook.py stop` → `okfw.py rebuild --hook` | Projektionen nachziehen; Lint-Fehler als eine Zeile, ohne zu blockieren |

Nebenfall **Skill-Ordner** (`~/.claude/skills/okfw`, ohne Plugin): `hooks/settings.example.json` in die
`.claude/settings.json` des Projekts übernehmen. Dort rufen SessionStart und Stop den Kern direkt auf
(`uv run --quiet ~/.claude/skills/okfw/okfw.py --root "$CLAUDE_PROJECT_DIR" status --hook` bzw.
`rebuild --hook`), Guard und Ereignisprotokoll wie oben `okf_hook.py` über `uv run --script`. Nicht beide
Arten zugleich, sonst laufen die Hooks doppelt.

Der Guard sucht die `wiki.toml` aufwärts ab der Zieldatei (rund 30 ms, nur Standardbibliothek,
Python ≥ 3.11 wegen `tomllib`, das uv bereitstellt). Er schützt dieselben Pfade, die `status --hook` als
„Nicht direkt bearbeiten“ nennt (`protected_paths` im Kern). Für die Vertrauensfelder vergleicht er die
Schlüssel `status` und `verified` im Frontmatter vor und nach der Änderung als Text (Edit und MultiEdit
werden auf die Datei angewandt, Write bringt den ganzen Inhalt); jede Abweichung wird abgelehnt, nur eine neue Seite darf `status: draft` tragen.
Schreibzugriffe über Bash erfasst er nicht, auch `okfw.py verify` nicht; das bleibt Regel, und dafür gibt es
die Signatur. Bedienfehler (kaputte `wiki.toml`, `requires_core` neuer als der Kern, fehlendes `uv`, dies außer beim
Guard) melden die Hooks als eine Zeile (`systemMessage`), eine Zeitüberschreitung meldet nur das Plugin (`hooks.json` über
`okf_hook.py`); die Vorlage `settings.example.json` ruft für SessionStart und Stop den Kern direkt auf. Ohne `wiki.toml`
bleiben sie still.
