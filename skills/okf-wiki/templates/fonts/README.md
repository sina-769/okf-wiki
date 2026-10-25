# Schriften für das Dashboard

Eingebettet von `okfwiki.py dashboard`. Alle vier stehen unter der SIL Open Font License 1.1, die
Weitergabe und Einbettung erlaubt; der Lizenztext liegt bei (`OFL-IBM-Plex.txt`,
`OFL-JetBrains-Mono.txt`, Text unverändert aus den Repositorien der Schriften, Zeilenenden LF, ohne Leerzeichen am Zeilenende).

| Datei | Schrift | Glyphen | Original | Lizenz |
|---|---|---|---|---|
| `ibmplexserif-regular.woff2` | IBM Plex Serif Regular 3.006 | 1054 | IBM/plex `packages/plex-serif/fonts/complete/woff2/IBMPlexSerif-Regular.woff2` | OFL 1.1, Reserved Font Name „Plex“ |
| `ibmplexsans-regular.woff2` | IBM Plex Sans Regular 3.005 | 1019 | IBM/plex `packages/plex-sans/fonts/complete/woff2/IBMPlexSans-Regular.woff2` | OFL 1.1, Reserved Font Name „Plex“ |
| `ibmplexsans-semibold.woff2` | IBM Plex Sans SemiBold 3.005 | 1019 | IBM/plex `packages/plex-sans/fonts/complete/woff2/IBMPlexSans-SemiBold.woff2` | OFL 1.1, Reserved Font Name „Plex“ |
| `jetbrainsmono-regular.woff2` | JetBrains Mono Regular 2.305 | 1754 | JetBrains/JetBrainsMono `fonts/webfonts/JetBrainsMono-Regular.woff2` | OFL 1.1 |

Die Dateien sind bytegleich mit den Originalen der Rechteinhaber (Git-Blob-Hash verglichen am 2026-10-25,
https://github.com/IBM/plex @ 71f558992315a12ca1f06a2215d57962a1992162,
https://github.com/JetBrains/JetBrainsMono @ 19371302b95d218af43299bce79ddbddd0bc364d). Nur die Dateinamen
sind kleingeschrieben; Schriftnamen, Daten und Metadaten sind unverändert. Es sind die vollständigen Schnitte
aus `complete/`, nicht die Teilmengen aus `split/` (Glyphenzahl gelesen mit fontTools). Die Dateien sind also
keine veränderte Fassung (Modified Version) im Sinn der OFL; die Einschränkung des Reserved Font Name
(Bedingung 3, betrifft den Nutzern angezeigten Schriftnamen) gilt nur für veränderte Fassungen.
Lizenztexte: IBM/plex `LICENSE.txt` und JetBrains/JetBrainsMono `OFL.txt` an denselben Commits.

`okfwiki.py dashboard` schreibt vor die eingebetteten Schriften einen CSS-Kommentar mit dem
Copyright-Vermerk (erste Zeile des jeweiligen Lizenztexts) und dem Lizenzhinweis (Name, Link), damit beides
in der erzeugten Datei im Klartext steht; den Lizenzhinweis mit Link tragen auch die Schriftdateien selbst
in ihren Metadaten. Eine Schrift ohne ihren Lizenztext in diesem Ordner wird nicht eingebettet.

# Zitierstil

`../apa.csl` ist der CSL-Stil „APA Style 7th edition“ (http://www.zotero.org/styles/apa), unverändert
(SHA-256 gleich mit citation-style-language/styles `apa.csl` @ 3c6698d791a83016d699f50cbbea857f6ee3d2f8),
Lizenz CC BY-SA 3.0 (steht im Stil unter `<rights>`, Autorinnen und Autoren unter `<author>`). Standard für
Literaturangaben im Dashboard, wenn `wiki.toml` unter `[export.csl] style` keinen eigenen Stil nennt.
