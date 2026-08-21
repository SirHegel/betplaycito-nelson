#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
DIST_DIR="${PROJECT_DIR}/dist"
SOURCE_DIR="${PROJECT_DIR}/src"

if [[ ! -f "${SOURCE_DIR}/betplaycito/__main__.py" ]]; then
  echo "No se encontró el punto de entrada de BetPlaycito." >&2
  exit 1
fi

python3 "${SCRIPT_DIR}/check_syntax.py"
if command -v node >/dev/null 2>&1; then
  node --check "${SOURCE_DIR}/betplaycito/web/app.js"
fi
mkdir -p "${DIST_DIR}"
python3 -m zipapp "${SOURCE_DIR}" \
  --main "betplaycito.__main__:main" \
  --python "/usr/bin/env python3" \
  --compress \
  --output "${DIST_DIR}/BetPlaycito-Nelson.pyz"
chmod +x "${DIST_DIR}/BetPlaycito-Nelson.pyz"

cp "${PROJECT_DIR}/packaging/Iniciar BetPlaycito Nelson.sh" "${DIST_DIR}/"
cp "${PROJECT_DIR}/packaging/betplaycito-nelson.svg" "${DIST_DIR}/"
cp "${PROJECT_DIR}/packaging/BetPlaycito Nelson.desktop.example" "${DIST_DIR}/"
cp "${PROJECT_DIR}/config.example.json" "${DIST_DIR}/"
cp "${PROJECT_DIR}/README.md" "${DIST_DIR}/LEEME.md"
chmod +x "${DIST_DIR}/Iniciar BetPlaycito Nelson.sh"

echo "Aplicativo creado en: ${DIST_DIR}/BetPlaycito-Nelson.pyz"
