#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${PROJECT_DIR}/src"
DIST_DIR="${PROJECT_DIR}/dist"
BUILD_PYTHON="${BETPLAYCITO_BUILD_PYTHON:-python3}"

if ! "${BUILD_PYTHON}" -c 'import PyInstaller' >/dev/null 2>&1; then
  echo "PyInstaller no está instalado para ${BUILD_PYTHON}." >&2
  echo "Cree un entorno e instale packaging/requirements-build.txt." >&2
  exit 1
fi

VERSION="$({ sed -n 's/^__version__ = "\([^"]*\)"$/\1/p' \
  "${SOURCE_DIR}/betplaycito/__init__.py"; } | head -n 1)"
if [[ ! "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "No se pudo obtener una versión válida." >&2
  exit 1
fi

case "$(uname -m)" in
  x86_64|amd64) ARCHITECTURE="x86_64" ;;
  aarch64|arm64) ARCHITECTURE="arm64" ;;
  *)
    echo "Arquitectura Linux no admitida: $(uname -m)" >&2
    exit 1
    ;;
esac

python3 "${SCRIPT_DIR}/check_syntax.py"
python3 -m unittest discover -s "${PROJECT_DIR}/tests" -v
if command -v node >/dev/null 2>&1; then
  node --check "${SOURCE_DIR}/betplaycito/web/app.js"
fi

BUILD_DIR="$(mktemp -d -t betplaycito-native.XXXXXXXX)"
trap 'rm -rf -- "${BUILD_DIR}"' EXIT

"${BUILD_PYTHON}" -m PyInstaller --noconfirm --clean \
  --distpath "${BUILD_DIR}/dist" \
  --workpath "${BUILD_DIR}/work" \
  "${PROJECT_DIR}/packaging/BetPlaycito-Nelson.spec"

SOURCE_EXECUTABLE="${BUILD_DIR}/dist/BetPlaycito-Nelson"
OUTPUT_EXECUTABLE="${DIST_DIR}/BetPlaycito-Nelson-${VERSION}-Linux-${ARCHITECTURE}"
if [[ ! -x "${SOURCE_EXECUTABLE}" ]]; then
  echo "PyInstaller no produjo el ejecutable esperado." >&2
  exit 1
fi

mkdir -p "${DIST_DIR}"
install -m 0755 "${SOURCE_EXECUTABLE}" "${OUTPUT_EXECUTABLE}"
python3 "${SCRIPT_DIR}/smoke_native.py" "${OUTPUT_EXECUTABLE}" --version "${VERSION}"
echo "Ejecutable Linux creado: ${OUTPUT_EXECUTABLE}"
