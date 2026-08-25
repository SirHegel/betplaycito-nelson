#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${PROJECT_DIR}/src"
DEBIAN_SOURCE_DIR="${PROJECT_DIR}/packaging/debian"
DIST_DIR="${PROJECT_DIR}/dist"

for required_command in python3 dpkg-deb install sed; do
  if ! command -v "${required_command}" >/dev/null 2>&1; then
    echo "Falta la herramienta requerida: ${required_command}" >&2
    exit 1
  fi
done

VERSION="$({ sed -n 's/^__version__ = "\([^"]*\)"$/\1/p' \
  "${SOURCE_DIR}/betplaycito/__init__.py"; } | head -n 1)"
if [[ -z "${VERSION}" || ! "${VERSION}" =~ ^[0-9][0-9A-Za-z.+:~-]*$ ]]; then
  echo "No se pudo obtener una versión Debian válida." >&2
  exit 1
fi

for required_file in \
  "${SOURCE_DIR}/betplaycito/__main__.py" \
  "${DEBIAN_SOURCE_DIR}/control.in" \
  "${DEBIAN_SOURCE_DIR}/betplaycito-nelson" \
  "${DEBIAN_SOURCE_DIR}/betplaycito-nelson.desktop" \
  "${DEBIAN_SOURCE_DIR}/io.github.sirhegel.betplaycito-nelson.metainfo.xml.in" \
  "${PROJECT_DIR}/packaging/icons/betplaycito-nelson.png" \
  "${PROJECT_DIR}/packaging/betplaycito-nelson.svg"; do
  if [[ ! -f "${required_file}" ]]; then
    echo "Falta el archivo requerido: ${required_file}" >&2
    exit 1
  fi
done

python3 "${SCRIPT_DIR}/check_syntax.py"
python3 -m unittest discover -s "${PROJECT_DIR}/tests" -v
bash -n "${DEBIAN_SOURCE_DIR}/betplaycito-nelson"
bash -n "${DEBIAN_SOURCE_DIR}/postinst"
bash -n "${DEBIAN_SOURCE_DIR}/postrm"
if command -v node >/dev/null 2>&1; then
  node --check "${SOURCE_DIR}/betplaycito/web/app.js"
fi
if command -v desktop-file-validate >/dev/null 2>&1; then
  desktop-file-validate "${DEBIAN_SOURCE_DIR}/betplaycito-nelson.desktop"
fi

BUILD_DIR="$(mktemp -d -t betplaycito-deb.XXXXXXXX)"
PACKAGE_ROOT="${BUILD_DIR}/betplaycito-nelson_${VERSION}_all"
PACKAGE_OUTPUT="${BUILD_DIR}/betplaycito-nelson_${VERSION}_all.deb"
trap 'rm -rf -- "${BUILD_DIR}"' EXIT

STAGING_DIR="${BUILD_DIR}/source"
mkdir -p "${STAGING_DIR}"
cp -a "${SOURCE_DIR}/." "${STAGING_DIR}/"
find "${STAGING_DIR}" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
find "${STAGING_DIR}" -depth -type d -name '__pycache__' -empty -delete

install -d -m 0755 \
  "${PACKAGE_ROOT}/DEBIAN" \
  "${PACKAGE_ROOT}/opt/betplaycito-nelson" \
  "${PACKAGE_ROOT}/usr/bin" \
  "${PACKAGE_ROOT}/usr/share/applications" \
  "${PACKAGE_ROOT}/usr/share/icons/hicolor/512x512/apps" \
  "${PACKAGE_ROOT}/usr/share/icons/hicolor/scalable/apps" \
  "${PACKAGE_ROOT}/usr/share/metainfo" \
  "${PACKAGE_ROOT}/usr/share/doc/betplaycito-nelson"

sed "s/@VERSION@/${VERSION}/g" "${DEBIAN_SOURCE_DIR}/control.in" \
  > "${PACKAGE_ROOT}/DEBIAN/control"
chmod 0644 "${PACKAGE_ROOT}/DEBIAN/control"
install -m 0755 "${DEBIAN_SOURCE_DIR}/postinst" "${PACKAGE_ROOT}/DEBIAN/postinst"
install -m 0755 "${DEBIAN_SOURCE_DIR}/postrm" "${PACKAGE_ROOT}/DEBIAN/postrm"

python3 -m zipapp "${STAGING_DIR}" \
  --main "betplaycito.__main__:main" \
  --python "/usr/bin/env python3" \
  --compress \
  --output "${PACKAGE_ROOT}/opt/betplaycito-nelson/BetPlaycito-Nelson.pyz"
chmod 0755 "${PACKAGE_ROOT}/opt/betplaycito-nelson/BetPlaycito-Nelson.pyz"

install -m 0755 "${DEBIAN_SOURCE_DIR}/betplaycito-nelson" \
  "${PACKAGE_ROOT}/usr/bin/betplaycito-nelson"
install -m 0644 "${DEBIAN_SOURCE_DIR}/betplaycito-nelson.desktop" \
  "${PACKAGE_ROOT}/usr/share/applications/betplaycito-nelson.desktop"
sed "s/@VERSION@/${VERSION}/g" \
  "${DEBIAN_SOURCE_DIR}/io.github.sirhegel.betplaycito-nelson.metainfo.xml.in" \
  > "${PACKAGE_ROOT}/usr/share/metainfo/io.github.sirhegel.betplaycito-nelson.metainfo.xml"
chmod 0644 \
  "${PACKAGE_ROOT}/usr/share/metainfo/io.github.sirhegel.betplaycito-nelson.metainfo.xml"
install -m 0644 "${PROJECT_DIR}/packaging/betplaycito-nelson.svg" \
  "${PACKAGE_ROOT}/usr/share/icons/hicolor/scalable/apps/betplaycito-nelson.svg"
install -m 0644 "${PROJECT_DIR}/packaging/icons/betplaycito-nelson.png" \
  "${PACKAGE_ROOT}/usr/share/icons/hicolor/512x512/apps/betplaycito-nelson.png"
install -m 0644 "${DEBIAN_SOURCE_DIR}/README.Debian" \
  "${PACKAGE_ROOT}/usr/share/doc/betplaycito-nelson/README.Debian"
install -m 0644 "${PROJECT_DIR}/LICENSE" \
  "${PACKAGE_ROOT}/usr/share/doc/betplaycito-nelson/copyright"

if command -v appstreamcli >/dev/null 2>&1; then
  appstreamcli validate --no-net \
    "${PACKAGE_ROOT}/usr/share/metainfo/io.github.sirhegel.betplaycito-nelson.metainfo.xml"
fi

find "${PACKAGE_ROOT}" -type d -exec chmod 0755 {} +

dpkg-deb --root-owner-group --build "${PACKAGE_ROOT}" "${PACKAGE_OUTPUT}"

mkdir -p "${DIST_DIR}"
install -m 0644 "${PACKAGE_OUTPUT}" \
  "${DIST_DIR}/betplaycito-nelson_${VERSION}_all.deb"

dpkg-deb --info "${DIST_DIR}/betplaycito-nelson_${VERSION}_all.deb" >/dev/null
dpkg-deb --contents "${DIST_DIR}/betplaycito-nelson_${VERSION}_all.deb" >/dev/null

echo "Paquete creado: ${DIST_DIR}/betplaycito-nelson_${VERSION}_all.deb"
