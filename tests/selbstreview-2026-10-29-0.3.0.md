# Selbstreview okfw 0.3.0 · 29.10.2026

Geprüfter Stand: 0.3.0, Commit c1daaf6 (28.10.2026). Verfahren: [selbstreview.md](selbstreview.md).
Wegwerf-Wiki: `.nachbau/selbstreview-0.3.0/` (nicht im Repo), Lint dort 178 Seiten · 0 Fehler · 0 Warnungen.

## Zahlen

| | Zahl |
|---|---|
| Konzeptkarten | 156 (16 Befehle, 63 Lint-Regeln, 73 `wiki.toml`-Schlüssel, 4 Hooks) und 4 Übersichten |
| Karten mit Vermerk | 34 |
| Widersprüche (Doku sagt anderes, als der Code tut) | 23 |
| Lücken (Doku verschweigt Verhalten) | 25 |
| Mechanisch: im Code, in keiner Doku | 1 (`body --detail`) |
| Mechanisch: in der Doku, nicht im Code | 0 |
| Mechanisch: ohne Test | 110 (4 Befehle, 53 Regeln, 53 Schlüssel) |
| Gegenprüfung der 48 Vermerke | 39 ✓ · 9 ~ (eingearbeitet) · 0 ✗ · 0 ? |

## Behoben

Im Kern (Commit a1cc736, mit Tests in `test_doku_code.py`, Klasse `SelbstreviewNullDreiNull`):

- `rebuild --quiet` beendete sich bei jedem Bedienfehler still (Operatorreihenfolge in `main`); jetzt nur ohne
  `wiki.toml`.
- `[lint.severity]` übernahm jeden Wert; `lint --summary` brach bei einem Tippfehler mit KeyError ab. Jetzt
  Bedienfehler mit Nennung von Code und Wert.
- `requires_core = "v0.3"` brach mit ValueError ab; jetzt Bedienfehler mit Hinweis auf MAJOR.MINOR.
- `source_undated`: Karten mit `authors`, `doi` oder `year` lasen nur `year`, eine Karte mit `authors` und
  `date` bekam die Warnung trotzdem.
- `lizenz --class` ohne `--name` auf einer Karte ohne Lizenznamen schrieb die Lizenz und endete mit KeyError.
- Die Meldung zur Zitatverfolgung bei `new` verlangte `--von` (dort die Abruf-URL) statt `--fundweg-von`.

In der Doku (`konfiguration.md`, `SKILL.md`, `README.md`): 41 Vermerke, darunter Exit-Codes (0, 1 bei
`lint`-Fehlern und `rebuild --check`, 2 bei Bedienfehlern), vollständige Ereignisarten mit `bootstrap`,
`enrich`, `export`, `write`, `edit`; `body --detail`; Auslöser von `license_missing`, `license_unknown`,
`csl_incomplete`, `citation_with_claims`, `fulltext_*`, `fundweg_*`, `verified_outdated`; Vorrang von
`license.class` vor Mustern und die gültigen Klassen; `checked_field` mit dem Dienst, der geantwortet hat;
`body` setzt stable auf draft (auch „`status` und `verified` ändert nur `verify`“ war zu eng); Hooks im Plugin
und in der Vorlage für den Skill-Ordner verhalten sich verschieden; Standardwerte für `[wiki] actor` und
`[dashboard] public_path`; `[paths] protected` nach `fnmatch`; `[log] labels`-Beispiel mit `create`.

Tests: Die 110 Einträge ohne Test haben jetzt je mindestens einen (`test_regeln.py`, `test_schluessel.py`).
`test_abdeckung.py` hält das bei jedem Testlauf fest.

## Offen

Mit Entscheidung im Backlog (Abschnitt „Selbstreview 29.10.2026“), die Doku beschreibt das heutige Verhalten:

- Guard meldet ein fehlendes `uv` nicht; ein `|| echo` wie bei den anderen Hooks würde die Ablehnung (Exit 2)
  verschlucken.
- Die Vorlage `settings.example.json` ruft SessionStart und Stop am Hook-Skript vorbei auf (keine Meldung bei
  Zeitüberschreitung, `wiki.toml` nur im Projektordner).
- Eine mit Write neu angelegte Seite bekommt `update`, nie `create`.
- `verify --status deprecated` ist für jeden Akteur erlaubt.
- `citation_with_claims` sieht nur Listenpunkte; `[visibility]` ohne `[enums]` und `default` lässt Tippfehler
  öffentlich; `[taxonomy] label` wird nirgends angezeigt; unbekannte `wiki.toml`-Schlüssel und Lint-Codes
  bleiben still; Crossref-Hinweise erscheinen im Text nur mit eigener Vorlage.

Nicht geändert: Der veröffentlichte CHANGELOG-Eintrag 0.3.0 nennt für verfallene Gegenprüfungen von Claude oder
Prozessen `verified_outdated`; der Kern meldet `check_outdated`. Klargestellt im Abschnitt „Unveröffentlicht“.

## Begriffe

Verschieden benannt, ohne dass es verschiedene Dinge sind: Ereignisstrom, Ereignisprotokoll und Log; Art, Typ
und `kind`; verfallen, veraltet und outdated; `--von` (bei `new` die Abruf-URL, bei `fundweg` die Quelle)
neben `--fundweg-von`; `--license` neben `--name`; zwei Stufenschemata der Vertrauensstufen
(draft · geprüft · stable neben human-reviewed · machine-confirmed · unverified); zwei Wortreihen für
Rechtewerte; deutsche und englische Optionen (`--titel`/`--title`, `--streng`/`--strict`,
`--oeffentlich`/`--public`) und Aliase (`index`, `quellen`, `sha`, `rights`, `license`). Vereinheitlichen
steht im Backlog.

## Modelle

| Schritt | Modell |
|---|---|
| Verfahren, Skript, Kern-Fehler, Prüfung jeder Fundstelle am Original, Vermerke, Synthese, Bericht | Claude Opus 5.5 |
| Befund-Entwürfe je Kartengruppe (Befehle, Regeln, Schlüssel, Hooks) | Claude Sonnet 5.5 |
| Gegenprüfung (`/pruefen`, Agent `beleg-pruefer`, frisch) | Claude Sonnet 5.5 |
| Doku-Angleichung nach fester Liste | Claude Sonnet 5.5 |
| Neue Tests für Regeln, Schlüssel und Befehle | Claude Sonnet 5.5 |

Der GitHub-Workflow ist lokal nur auf YAML-Syntax geprüft; der erste echte Lauf folgt mit dem nächsten
Export ins öffentliche Repository.
