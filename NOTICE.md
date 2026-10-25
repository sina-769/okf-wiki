# Fremde Bestandteile und Vorbilder

## Mitgeliefert (Lizenztexte liegen bei)

| Bestandteil | Datei | Herkunft | Lizenz |
|---|---|---|---|
| IBM Plex Serif, IBM Plex Sans (Regular, SemiBold) | `skills/okf-wiki/templates/fonts/ibmplex*.woff2` | https://github.com/IBM/plex, Copyright © 2017 IBM Corp. | SIL Open Font License 1.1, Reserved Font Name „Plex“ (`OFL-IBM-Plex.txt`) |
| JetBrains Mono Regular | `skills/okf-wiki/templates/fonts/jetbrainsmono-regular.woff2` | https://github.com/JetBrains/JetBrainsMono, Copyright 2020 The JetBrains Mono Project Authors | SIL Open Font License 1.1 (`OFL-JetBrains-Mono.txt`) |
| CSL-Stil „APA Style 7th edition“ | `skills/okf-wiki/templates/apa.csl` | citation-style-language/styles @ 3c6698d791a83016d699f50cbbea857f6ee3d2f8, unverändert; Autorinnen und Autoren im Stil unter `<author>`/`<contributor>` | CC BY-SA 3.0 (im Stil unter `<rights>`) |

Die Schriften werden unverändert weitergegeben und von `okfwiki.py dashboard` in die erzeugte HTML-Datei
eingebettet, was die OFL erlaubt. Einzelheiten: `skills/okf-wiki/templates/fonts/README.md`.

## Zur Laufzeit geholt (nicht mitgeliefert)

| Paket | Wozu | Lizenz |
|---|---|---|
| [PyYAML](https://pyyaml.org) ≥ 6.0 | Frontmatter lesen und schreiben | MIT |
| [Python-Markdown](https://python-markdown.github.io) ≥ 3.5 | Leseansicht im Dashboard | BSD-3-Clause |

uv holt beide beim ersten Start des Kerns aus PyPI (Skriptkopf nach PEP 723 in `okfwiki.py`).

## Vorbilder (kein Code übernommen)

- **pi-llm-wiki** (Zosma AI, https://github.com/zosmaai/pi-llm-wiki, MIT): LLM-Wiki-Muster
  (Recall, Capture, Ingest, Retro, Lint), Schichten aus Rohquellen, Seiten, Ereignissen und Projektionen,
  Aufbau des Claude-Code-Plugins mit SessionStart-Hinweis und Schreibschutz. okf-wiki setzt das neu in
  Python um; Guard und Ereignisprotokoll entsprechen in der Wirkung den Hooks von pi-llm-wiki.
- **Open Knowledge Format v0.2** (GoogleCloudPlatform/knowledge-catalog, `okf/SPEC.md` @
  a8291a1a656669b8766fd4ff0f985505fb955e94, Apache-2.0): das Format der Wikis (Bundle, Frontmatter,
  `generated`/`verified`, Index- und Log-Dateien, Akteurskonvention). okf-wiki implementiert die
  Spezifikation; ihr Text ist nicht enthalten.
- **LLM-Wiki-Muster** von Andrej Karpathy, auf das sich pi-llm-wiki beruft.
