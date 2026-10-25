# Frische Umgebung für den Nachbau-Test: Debian mit Node (für Claude Code), git, curl und uv.
# Kein Python, kein Claude-Login, keine Plugins, kein ~/.claude.
#
#   docker build -t okfw-nachbau -f tests/Dockerfile tests
#   docker run --rm -v "$PWD:/src:ro" -v "$PWD/.nachbau:/out" okfw-nachbau /src /out/lauf-$(date +%H%M%S)
#
# Je Lauf ein neuer Unterordner: Unter OrbStack sah der Container Dateien, die der Mac kurz vorher
# gelöscht hatte, noch einige Sekunden lang als fehlend, und Protokollzeilen gingen verloren.
#
# /src ist ein Git-Checkout (Repo-Wurzel oder Plugin-Ordner); der Test klont ihn und installiert
# das Plugin aus dem Klon, nicht aus dem Arbeitsverzeichnis.
FROM node:22-bookworm-slim@sha256:d649c27dae7ba0137b3cef5dd75baa422c08dc3d9e3fc0c23dfb172dc3cc6436

ARG CLAUDE_CODE_VERSION=2.1.291
RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g --no-fund --no-audit "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
 && npm cache clean --force
COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /uvx /usr/local/bin/

RUN useradd --create-home --shell /bin/bash tester
COPY nachbau.sh /usr/local/bin/nachbau.sh
COPY container-start.sh /usr/local/bin/container-start.sh
USER tester
WORKDIR /home/tester
ENV DISABLE_AUTOUPDATER=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    DISABLE_TELEMETRY=1 \
    DISABLE_ERROR_REPORTING=1
ENTRYPOINT ["bash", "/usr/local/bin/container-start.sh"]
