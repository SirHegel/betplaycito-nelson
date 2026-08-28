"""Punto de entrada de ``python -m betplaycito``."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from . import __version__
from .server import hash_password, run_server, store_admin_password_hash


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="betplaycito",
        description="Panel local de estadísticas de fútbol BetPlaycito Nelson.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Puerto local (predeterminado: 8765; use 0 para elegir uno libre).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Directorio de datos; por defecto se usa el almacenamiento de la aplicación.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Archivo local de configuración; por defecto se usa la ubicación de la aplicación.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="No abrir automáticamente el navegador.",
    )
    parser.add_argument(
        "--hash-password",
        action="store_true",
        help="Generar un hash PBKDF2, guardarlo de forma privada en la configuración y salir.",
    )
    return parser


def _store_password_hash(config_path: Path | None = None) -> int:
    first = getpass.getpass("Nueva contraseña: ")
    second = getpass.getpass("Repita la contraseña: ")
    if first != second:
        print("Las contraseñas no coinciden.", file=sys.stderr)
        return 2
    try:
        encoded = hash_password(first)
        destination = store_admin_password_hash(encoded, config_path=config_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, RuntimeError) as exc:
        print(f"No se pudo guardar la configuración: {exc}", file=sys.stderr)
        return 2
    print(f"Hash PBKDF2 guardado de forma privada en {destination}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.hash_password:
        return _store_password_hash(args.config)
    if not 0 <= args.port <= 65535:
        print("El puerto debe estar entre 0 y 65535.", file=sys.stderr)
        return 2
    return run_server(
        port=args.port,
        data_dir=args.data_dir,
        config_path=args.config,
        open_browser=not args.no_browser,
    )


if __name__ == "__main__":
    raise SystemExit(main())
