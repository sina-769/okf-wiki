# Änderungen

## 0.3.0 · 28.10.2026

Die Freigabe ist jetzt an den Inhalt gebunden, den jemand geprüft hat.

Verhalten geändert:

- **Prüfwert in jedem Prüfvermerk.** `verify` schreibt in jeden `verified`-Eintrag `body_sha256`, den
  SHA-256 des Seitentexts ohne Frontmatter (eine ausgewiesene Erweiterung zu OKF §5.2). Ändert sich der
  Text danach, verfällt der Vermerk: Lint `verified_outdated` (Warnung, bei `status: stable` Fehler).
- **Rückfall auf draft.** `body` setzt eine stable-Seite auf `draft`, wenn ihre Freigabe nicht mehr zum
  neuen Text passt; `verified` bleibt stehen, das Ereignis nennt die verfallene Freigabe. Abschaltbar mit
  `[trust] edit_resets_stable = false`. Gleicher Text ändert nichts.
- **Freigabe nur nach Gegenprüfung.** `verify --by human:<id> --status stable` verlangt je Seite einen
  Vermerk von Claude oder einem Prozess mit Prüfwert zum selben Text; sonst bricht es ohne Änderung ab
  (`--force` gibt trotzdem frei und vermerkt das, Lint `human_without_check`). `verify` nimmt mehrere
  Seiten und eine gemeinsame `--note` (eine Charge, ein Ereignis je Seite).
- **`status` und `verified` nur über `verify`.** Der Guard blockiert Edit und Write, die diese Felder
  einer Wiki-Seite ändern; eine neue Seite darf `status: draft` tragen.
- **Edit und Write ziehen `generated` nach.** Hat ein Edit oder Write den Text einer Wiki-Seite
  geändert, setzt der PostToolUse-Hook `generated {by, at}` mit dem Akteur aus `[wiki] actor`
  (`body <seite> --nachziehen`); auf einer stable-Seite greift derselbe Rückfall wie bei `body`. Danach
  liest Claude die Datei vor dem nächsten Edit neu.
- **Vertrauensstufen nur aus gültigen Vermerken.** `status` zählt human-reviewed und machine-confirmed
  nur, wenn der Vermerk zum jetzigen Text passt; Seiten, deren Vermerke alle verfallen sind (auch die von
  Prozessen), stehen getrennt als „n verfallen“. Dazu „n zur Freigabe“ und die Zahl der Gegenprüfungen
  ohne Prüfwert.

Neu:

- Dashboard-Abschnitt **„Zur Freigabe“**: Seiten mit Gegenprüfung, aber ohne gültige Freigabe, je mit dem
  ganzen Text und hervorgehobenen Belegen (lange Seiten zuerst die belegten Aussagen, der ganze Text klappt
  auf, eingeklappt mit „n Absätze ohne Fußnote“), Notiz der Gegenprüfung und fertigem `verify`-Aufruf
  für die markierten Seiten zum Kopieren; darunter verfallene Freigaben und „Gegenprüfung ohne Prüfwert“
  mit einer Zeile, die eine neue Gegenprüfung anstößt.
- `[trust] human = "human:<id>"` belegt die Kennung in „Zur Freigabe“ vor; `[trust] check_command`
  (z. B. `/pruefen`) ist der Aufruf der Gegenprüfung in der Liste ohne Prüfwert.
- Lint-Regeln `verified_unhashed` (info: Gegenprüfung ohne Prüfwert) und `check_outdated` (info:
  verfallene Prüfung durch Claude oder einen Prozess); opt-in `[trust] signed_human = true` mit
  `human_unsigned` (warn: Freigabe nicht aus einem signierten Commit).
- Abschnitt „Freigabe über Claude“ in `skills/okfw/docs/konfiguration.md` mit Ablauf einer Charge und
  Einrichtung der Commit-Signatur.
- Nachbau-Test mit zwei Schritten zur Freigabe (Ablehnung ohne Gegenprüfung, Rückfall nach `body`):
  33 von 33 Pflichtschritten bestanden, der Schritt mit `claude -p` ohne Token übersprungen
  ([tests/protokoll-2026-10-28-0.3.0.md](tests/protokoll-2026-10-28-0.3.0.md)).

Migration: Ältere Vermerke ohne Prüfwert bleiben gültig, solange `generated.at` nicht jünger ist, zählen
aber nicht als Gegenprüfung für eine Freigabe; Lint `verified_unhashed` und „Gegenprüfung ohne Prüfwert“
im Dashboard zeigen, welche Seiten vor einer Freigabe neu gegengeprüft werden müssen.

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
