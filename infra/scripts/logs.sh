#!/usr/bin/env bash
# Placeholder: consulta de logs de los contenedores de EGRESA.
set -euo pipefail
docker compose -f "$(dirname "$0")/../docker/docker-compose.yml" logs -f "$@"
