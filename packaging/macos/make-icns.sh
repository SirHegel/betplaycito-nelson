#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Uso: $0 ICONO.(png|svg) SALIDA.icns" >&2
  exit 2
fi

SVG_PATH="$(cd -- "$(dirname -- "$1")" && pwd)/$(basename -- "$1")"
OUTPUT_PATH="$(cd -- "$(dirname -- "$2")" && pwd)/$(basename -- "$2")"

for required_command in sips iconutil; do
  if ! command -v "${required_command}" >/dev/null 2>&1; then
    echo "Falta la herramienta requerida: ${required_command}" >&2
    exit 1
  fi
done

if [[ ! -f "${SVG_PATH}" ]]; then
  echo "No existe el icono fuente: ${SVG_PATH}" >&2
  exit 1
fi

TEMP_DIR="$(mktemp -d -t betplaycito-icon.XXXXXXXX)"
trap 'rm -rf -- "${TEMP_DIR}"' EXIT
ICONSET_DIR="${TEMP_DIR}/betplaycito.iconset"
MASTER_PNG="${TEMP_DIR}/master.png"
mkdir -p "${ICONSET_DIR}"

case "${SVG_PATH}" in
  *.png)
    sips --resampleHeightWidth 1024 1024 "${SVG_PATH}" --out "${MASTER_PNG}" >/dev/null
    ;;
  *.svg)
    if ! command -v rsvg-convert >/dev/null 2>&1; then
      echo "Para usar un SVG hace falta rsvg-convert; use el PNG incluido." >&2
      exit 1
    fi
    rsvg-convert --width 1024 --height 1024 "${SVG_PATH}" > "${MASTER_PNG}"
    ;;
  *)
    echo "El icono debe ser PNG o SVG: ${SVG_PATH}" >&2
    exit 1
    ;;
esac

while read -r filename pixels; do
  sips --resampleHeightWidth "${pixels}" "${pixels}" "${MASTER_PNG}" \
    --out "${ICONSET_DIR}/${filename}" >/dev/null
done <<'EOF'
icon_16x16.png 16
icon_16x16@2x.png 32
icon_32x32.png 32
icon_32x32@2x.png 64
icon_128x128.png 128
icon_128x128@2x.png 256
icon_256x256.png 256
icon_256x256@2x.png 512
icon_512x512.png 512
icon_512x512@2x.png 1024
EOF

iconutil --convert icns --output "${OUTPUT_PATH}" "${ICONSET_DIR}"
echo "Icono creado: ${OUTPUT_PATH}"
