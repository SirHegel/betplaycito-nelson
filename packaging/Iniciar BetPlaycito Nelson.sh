#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_FILE="${APP_DIR}/BetPlaycito-Nelson.pyz"

if [[ ! -x "${APP_FILE}" ]]; then
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="BetPlaycito Nelson" \
      --text="No se encontró el aplicativo BetPlaycito-Nelson.pyz en esta carpeta."
  else
    echo "No se encontró ${APP_FILE}" >&2
  fi
  exit 1
fi

exec "${APP_FILE}"
