#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Uso: $0 APLICACION.app SALIDA.dmg" >&2
  exit 2
fi

APP_PATH="$(cd -- "$(dirname -- "$1")" && pwd)/$(basename -- "$1")"
OUTPUT_PATH="$(cd -- "$(dirname -- "$2")" && pwd)/$(basename -- "$2")"

for required_command in ditto hdiutil; do
  if ! command -v "${required_command}" >/dev/null 2>&1; then
    echo "Falta la herramienta requerida: ${required_command}" >&2
    exit 1
  fi
done

if [[ ! -d "${APP_PATH}" || "${APP_PATH}" != *.app ]]; then
  echo "No existe el bundle .app: ${APP_PATH}" >&2
  exit 1
fi

TEMP_DIR="$(mktemp -d -t betplaycito-dmg.XXXXXXXX)"
trap 'rm -rf -- "${TEMP_DIR}"' EXIT
STAGING_DIR="${TEMP_DIR}/BetPlaycito Nelson"
mkdir -p "${STAGING_DIR}"

ditto "${APP_PATH}" "${STAGING_DIR}/BetPlaycito Nelson.app"
ln -s /Applications "${STAGING_DIR}/Applications"

hdiutil create \
  -volname "BetPlaycito Nelson" \
  -srcfolder "${STAGING_DIR}" \
  -format UDZO \
  -ov \
  "${OUTPUT_PATH}"

echo "Imagen creada: ${OUTPUT_PATH}"
