"""Punto de entrada mínimo para los paquetes nativos creados con PyInstaller.

Este archivo mantiene el arranque dentro del paquete ``betplaycito`` para que
las importaciones relativas y ``importlib.resources`` funcionen igual desde el
código fuente y desde un ejecutable congelado.
"""

from __future__ import annotations

from betplaycito.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
