# -*- mode: python ; coding: utf-8 -*-
"""Especificación reproducible para Windows, macOS y Linux.

Windows y Linux generan un ejecutable de un solo archivo. macOS genera un
bundle ``.app`` en modo onedir, que es la forma recomendada para firmar y
notarizar una aplicación PyInstaller.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# ``SPEC`` es la ruta completa/relativa del archivo .spec. Usarlo evita la
# ambigüedad de ``SPECPATH``, cuyo valor ya es el directorio contenedor.
PROJECT_DIR = Path(SPEC).resolve().parent.parent
SOURCE_DIR = PROJECT_DIR / "src"
PACKAGE_DIR = SOURCE_DIR / "betplaycito"
WEB_DIR = PACKAGE_DIR / "web"

version_scope: dict[str, object] = {}
exec(
    (PACKAGE_DIR / "__init__.py").read_text(encoding="utf-8"),
    version_scope,
)
APP_VERSION = str(version_scope["__version__"])

icon_value = os.environ.get("BETPLAYCITO_ICON")
ICON = str(Path(icon_value).resolve()) if icon_value else None
if ICON and not Path(ICON).is_file():
    raise SystemExit(f"No existe el icono indicado por BETPLAYCITO_ICON: {ICON}")

codesign_identity = os.environ.get("BETPLAYCITO_CODESIGN_IDENTITY") or None
entitlements_value = os.environ.get("BETPLAYCITO_ENTITLEMENTS")
entitlements_file = (
    str(Path(entitlements_value).resolve()) if entitlements_value else None
)

a = Analysis(
    [str(PROJECT_DIR / "packaging" / "launcher.py")],
    pathex=[str(SOURCE_DIR)],
    binaries=[],
    datas=[(str(WEB_DIR), "betplaycito/web")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

common_exe_options = {
    "name": "BetPlaycito-Nelson",
    "debug": False,
    "bootloader_ignore_signals": False,
    "strip": False,
    "upx": False,
    "console": False,
    "disable_windowed_traceback": False,
    "argv_emulation": False,
    "target_arch": None,
    "codesign_identity": codesign_identity,
    "entitlements_file": entitlements_file,
    "icon": ICON,
}

if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        **common_exe_options,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name="BetPlaycito-Nelson",
    )
    app = BUNDLE(
        coll,
        name="BetPlaycito Nelson.app",
        icon=ICON,
        bundle_identifier="com.sirhegel.betplaycito-nelson",
        info_plist={
            "CFBundleDisplayName": "BetPlaycito Nelson",
            "CFBundleName": "BetPlaycito Nelson",
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "LSMinimumSystemVersion": "11.0",
            "LSUIElement": True,
            "NSHighResolutionCapable": True,
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        exclude_binaries=False,
        uac_admin=False,
        uac_uiaccess=False,
        **common_exe_options,
    )
