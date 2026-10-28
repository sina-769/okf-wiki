# Änderungen

## 0.2.0 · 28.10.2026

Verhalten geändert:

- **`verify --status stable` nur noch mit `human:`-Akteur.** Ein Prüfvermerk durch Claude oder ein
  anderes Werkzeug hält die Prüfung fest, hebt den Status aber nicht mehr; `verify --status stable`
  bricht mit anderem Akteur ab. Lint `stable_unverified` meldet jetzt auch `status: stable`, wenn nur
  ein maschineller Prüfvermerk da ist. Bestehende Karten: von einem Menschen prüfen lassen und
  `verify <seite> --by human:<id> --status stable` setzen, oder den Status auf `draft` zurücknehmen.
- **`capture --license` prüft die Rechte.** Erlaubt die Rechtematrix „Volltext lokal ablegen“ für die
  Lizenz nicht, bricht `capture` ab; „erst fragen“ und Auflagen kommen als Warnung.
- `capture` lehnt Symlinks als Datei ab.
- `body`, `lizenz` und `fundweg` ziehen `generated: {by, at}` nach wie `new`; `verify` nicht.
- Widerspruchs- und `[!todo]`-Marker in Code-Spannen und Codeblöcken zählen nicht mehr (`status`,
  Lint `contradiction_one_sided`, „Offene Stellen“ im Dashboard).

Neu:

- **Befehl `sources <seite> --add a,b | --remove c`**: Quellen einer Karte nachtragen oder entfernen,
  ohne den Rest der Datei anzufassen. `--add ID=SLUG` legt eine eigene Fußnote je Fundstelle auf
  dieselbe Quellenkarte an; `--remove` nur, wenn der Text `[^id]` nicht mehr zitiert.
- **`capture --file PFAD=REPO-PFAD`** trägt je Datei den Pfad im Quell-Repo ins Manifest;
  `--source-path` gilt für Dateien ohne eigenen. `capture --commit` warnt, wenn es kein voller SHA ist.
- `new source --set raw_packet=raw/<slug>` übernimmt die Lizenz aus `manifest.json` (via `capture`).
- **`skills/okfw/local.example.md`**: Vorlage für eine `local.md` je Installation (Projekte,
  Begleit-Skills, Altbestand). Ohne `local.md` gilt allein `SKILL.md`.
- `rebuild --hook` für den Stop-Hook: neu erzeugen ohne Ausgabe, Lint-Fehler als eine Zeile, ohne zu
  blockieren.
- Hooks melden Bedienfehler (kaputte `wiki.toml`, `requires_core`, fehlendes uv, Zeitüberschreitung) als
  eine Zeile statt still; ohne `wiki.toml` bleiben sie stumm.
- Profil `dokumentation` erlaubt `format: specification` und `dataset`.
- APA 7 auch im APA-Block neuer Karten und im Literaturverzeichnis (derselbe CSL-Stil wie im Dashboard);
  „Z.“ und „Zeilen“ gelten als Fundstellenkürzel.
- Das öffentliche Dashboard zeigt keine Ablageorte von Volltexten (`stored`) mehr; der Schreibschutz
  deckt auch das öffentliche Dashboard ab.
- Python-Tests unter `tests/` (`uv run python -m unittest`); Nachbau-Test 32 von 32 mit echter
  Claude-Sitzung ([tests/protokoll-2026-10-28.md](tests/protokoll-2026-10-28.md)).

## 0.1.0 · 25.10.2026

Erste Veröffentlichung.
