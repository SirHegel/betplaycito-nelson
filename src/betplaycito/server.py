"""Servidor HTTP local, API JSON y persistencia SQLite de BetPlaycito.

El módulo usa exclusivamente la biblioteca estándar. El servicio escucha siempre
en ``127.0.0.1`` y crea una cuenta administradora predeterminada en las bases nuevas,
a menos que la instalación proporcione una configuración local diferente.
"""

from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import hmac
import io
import json
import logging
import mimetypes
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from contextlib import contextmanager
from datetime import date, datetime, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from email.utils import formatdate
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping, Sequence
from xml.sax.saxutils import escape as xml_escape

from . import __version__


LOGGER = logging.getLogger("betplaycito")
HOST = "127.0.0.1"
COOKIE_NAME = "betplaycito_session"
SESSION_SECONDS = 12 * 60 * 60
PBKDF2_ITERATIONS = 600_000
PASSWORD_ALGORITHM = "pbkdf2_sha256"
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_RESTORE_BYTES = 50 * 1024 * 1024
SCHEMA_VERSION = 1
MAX_SQLITE_ID = 9_223_372_036_854_775_807

# Credencial pública de arranque solicitada para todas las instalaciones.
# Solo se conserva la derivación PBKDF2; la contraseña nunca se almacena en claro.
DEFAULT_ADMIN_USERNAME = "NelsonRuiz"
DEFAULT_ADMIN_PASSWORD_HASH = (
    "pbkdf2_sha256$600000$3jqMgsiHrtYPYxrhiOhSs1cZfFA5REJS$"
    "mvDfQtNDD6wxQBpr7ZBTi-KQuTP3PSLr6Ep4Sq9fVKk"
)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
BACKUP_NAME_RE = re.compile(r"^betplaycito-\d{8}T\d{6}(?:\d{6})?Z\.db$")


VARIABLE_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "key": "result",
        "label": "Resultado del partido",
        "categories": ("home_win", "draw", "away_win"),
    },
    {
        "key": "goals",
        "label": "Total de goles 2.5",
        "categories": ("over25", "under25"),
    },
    {
        "key": "btts",
        "label": "Ambos equipos marcan",
        "categories": ("btts_yes", "btts_no"),
    },
    {
        "key": "local_goal",
        "label": "Marcador local",
        "categories": ("local_scored", "local_blank"),
    },
    {
        "key": "corners",
        "label": "Tiros de esquina 9.5",
        "categories": ("corners_over95", "corners_under95"),
    },
    {
        "key": "shots_on_target",
        "label": "Tiros al arco 9.5",
        "categories": ("shots_over95", "shots_under95"),
    },
    {
        "key": "total_shots_range",
        "label": "Remates totales",
        "categories": ("total_shots_over255", "total_shots_under265"),
    },
    {
        "key": "shots_on_target_range",
        "label": "Tiros a puerta",
        "categories": ("shots_on_target_over75", "shots_on_target_under85"),
    },
    {
        "key": "corners_range",
        "label": "Tiros de esquina",
        "categories": ("corners_plus95", "corners_minus105"),
    },
    {
        "key": "cards_range",
        "label": "Tarjetas",
        "categories": ("cards_plus4", "cards_minus5"),
    },
    {
        "key": "half_goals",
        "label": "Goles por mitades",
        "categories": (
            "first_half_more_goals",
            "second_half_more_goals",
            "halves_equal_goals",
        ),
    },
)

_VARIABLE_LABELS = {
    "home_win": "Ganó el local",
    "draw": "Empate",
    "away_win": "Ganó el visitante",
    "over25": "Más de 2.5 goles",
    "under25": "Menos de 2.5 goles",
    "btts_yes": "Gol / Gol",
    "btts_no": "No Gol / Gol",
    "local_scored": "Local marcó",
    "local_blank": "Local no marcó",
    "corners_over95": "Más de 9.5 tiros de esquina",
    "corners_under95": "Menos de 9.5 tiros de esquina",
    "shots_over95": "Más de 9.5 tiros al arco",
    "shots_under95": "Menos de 9.5 tiros al arco",
    "total_shots_over255": "+25,5 remates",
    "total_shots_under265": "−26,5 remates",
    "shots_on_target_over75": "+7,5 tiros a puerta",
    "shots_on_target_under85": "−8,5 tiros a puerta",
    "corners_plus95": "+9,5 tiros de esquina",
    "corners_minus105": "−10,5 tiros de esquina",
    "cards_plus4": "+4 tarjetas",
    "cards_minus5": "−5 tarjetas",
    "first_half_more_goals": "+0,5 · 1M",
    "second_half_more_goals": "+0,5 · 2M",
    "halves_equal_goals": "== · mismas cantidades",
}

VARIABLES: dict[str, dict[str, Any]] = {}
for _group in VARIABLE_GROUPS:
    _categories = tuple(_group["categories"])
    for _key in _categories:
        _others = tuple(value for value in _categories if value != _key)
        VARIABLES[_key] = {
            "key": _key,
            "group": _group["key"],
            "label": _VARIABLE_LABELS[_key],
            "opposite": _others[0] if len(_others) == 1 else None,
            "alternatives": _others,
        }


class APIError(Exception):
    """Error esperado que puede serializarse de forma segura al cliente."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        *,
        fields: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = dict(fields or {})
        self.headers = dict(headers or {})


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def utc_epoch() -> int:
    return int(time.time())


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    if not value or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Base64 no válido")
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Base64 no válido") from exc


def _validate_new_password(password: Any) -> str:
    if not isinstance(password, str):
        raise ValueError("La contraseña debe ser texto.")
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if len(password) > 1024:
        raise ValueError("La contraseña es demasiado larga.")
    return password


def hash_password(password: str, *, iterations: int = PBKDF2_ITERATIONS) -> str:
    """Devuelve ``pbkdf2_sha256$iteraciones$sal$hash`` para configuración/BD."""

    password = _validate_new_password(password)
    if not 200_000 <= iterations <= 5_000_000:
        raise ValueError("Número de iteraciones PBKDF2 fuera del rango permitido.")
    salt = secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations, dklen=32
    )
    return f"{PASSWORD_ALGORITHM}${iterations}${_b64encode(salt)}${_b64encode(digest)}"


def _parse_password_hash(encoded: str) -> tuple[int, bytes, bytes]:
    if not isinstance(encoded, str):
        raise ValueError("El hash de contraseña debe ser texto.")
    parts = encoded.split("$")
    if len(parts) != 4 or parts[0] != PASSWORD_ALGORITHM:
        raise ValueError("Formato de hash de contraseña no reconocido.")
    try:
        iterations = int(parts[1])
    except ValueError as exc:
        raise ValueError("Iteraciones PBKDF2 no válidas.") from exc
    if not 200_000 <= iterations <= 5_000_000:
        raise ValueError("Iteraciones PBKDF2 fuera del rango permitido.")
    salt = _b64decode(parts[2])
    digest = _b64decode(parts[3])
    if not 16 <= len(salt) <= 64 or len(digest) != 32:
        raise ValueError("Longitud del hash de contraseña no válida.")
    return iterations, salt, digest


def verify_password(password: Any, encoded: str) -> bool:
    if not isinstance(password, str) or len(password) > 1024:
        return False
    try:
        iterations, salt, expected = _parse_password_hash(encoded)
    except (TypeError, ValueError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected)
    )
    return hmac.compare_digest(actual, expected)


def normalize_team_name(name: Any) -> tuple[str, str]:
    if not isinstance(name, str):
        raise APIError(422, "validation_error", "El nombre del equipo debe ser texto.")
    cleaned = " ".join(name.split())
    if not 2 <= len(cleaned) <= 100:
        raise APIError(
            422,
            "validation_error",
            "El nombre del equipo debe tener entre 2 y 100 caracteres.",
            fields={"name": "Longitud no válida."},
        )
    if any(ord(char) < 32 for char in cleaned):
        raise APIError(422, "validation_error", "El nombre contiene caracteres no válidos.")
    return cleaned, cleaned.casefold()


def clean_optional_text(value: Any, *, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise APIError(422, "validation_error", f"{field} debe ser texto.")
    value = value.strip()
    if not value:
        return None
    if len(value) > maximum:
        raise APIError(
            422,
            "validation_error",
            f"{field} no puede superar {maximum} caracteres.",
        )
    return value


def require_int(
    value: Any,
    *,
    field: str,
    minimum: int | None = None,
    maximum: int | None = None,
    optional: bool = False,
) -> int | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise APIError(422, "validation_error", f"{field} debe ser un número entero.")
    if minimum is not None and value < minimum:
        raise APIError(422, "validation_error", f"{field} no puede ser menor que {minimum}.")
    if maximum is not None and value > maximum:
        raise APIError(422, "validation_error", f"{field} no puede ser mayor que {maximum}.")
    return value


def parse_iso_timestamp(value: Any, *, field: str = "created_at") -> str:
    if not isinstance(value, str) or len(value) > 40:
        raise APIError(422, "invalid_backup", f"{field} no es una fecha válida.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise APIError(422, "invalid_backup", f"{field} no es una fecha válida.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def default_user_storage(root: Path) -> tuple[Path, Path, Path]:
    """Devuelve datos, configuración y respaldos apropiados para la plataforma.

    El código fuente y el zipapp portátil conservan sus carpetas junto al proyecto.
    Los binarios PyInstaller usan ubicaciones persistentes y escribibles por usuario.
    """

    if not getattr(sys, "frozen", False):
        return root / "datos", root / "config.local.json", root / "respaldos"
    home = Path.home()
    if os.name == "nt":
        data_base = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        config_base = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
        data_dir = data_base / "BetPlaycito Nelson"
        config_path = config_base / "BetPlaycito Nelson" / "config.local.json"
    elif sys.platform == "darwin":
        data_dir = home / "Library" / "Application Support" / "BetPlaycito Nelson"
        config_path = data_dir / "config.local.json"
    else:
        data_base = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
        config_base = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
        data_dir = data_base / "betplaycito-nelson"
        config_path = config_base / "betplaycito-nelson" / "config.local.json"
    return data_dir, config_path, data_dir / "respaldos"


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if not path.is_file():
        raise RuntimeError(f"La ruta de configuración no es un archivo: {path}")
    try:
        if path.stat().st_size > 64 * 1024:
            raise RuntimeError("El archivo config.local.json es demasiado grande.")
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"No se pudo leer la configuración local: {exc}") from exc
    if not isinstance(raw, dict):
        raise RuntimeError("config.local.json debe contener un objeto JSON.")
    try:
        mode = path.stat().st_mode & 0o777
        if mode & 0o077:
            LOGGER.warning(
                "Se recomienda limitar los permisos de %s a 600 (actuales: %o).", path, mode
            )
    except OSError:
        pass
    return raw


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_seen_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    revoked_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_teams_archived_name ON teams(archived, name);

CREATE TABLE IF NOT EXISTS adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER REFERENCES teams(id) ON DELETE RESTRICT,
    variable_key TEXT NOT NULL,
    delta INTEGER NOT NULL CHECK (delta BETWEEN -10000 AND 10000 AND delta <> 0),
    note TEXT,
    created_at TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_adjustments_variable ON adjustments(variable_key);
CREATE INDEX IF NOT EXISTS idx_adjustments_team ON adjustments(team_id);
CREATE INDEX IF NOT EXISTS idx_adjustments_created ON adjustments(created_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    played_at TEXT NOT NULL,
    home_team_id INTEGER REFERENCES teams(id) ON DELETE RESTRICT,
    away_team_id INTEGER REFERENCES teams(id) ON DELETE RESTRICT,
    home_team_name TEXT,
    away_team_name TEXT,
    home_goals INTEGER NOT NULL CHECK (home_goals BETWEEN 0 AND 100),
    away_goals INTEGER NOT NULL CHECK (away_goals BETWEEN 0 AND 100),
    corners_home INTEGER CHECK (corners_home BETWEEN 0 AND 1000),
    corners_away INTEGER CHECK (corners_away BETWEEN 0 AND 1000),
    shots_on_target_home INTEGER CHECK (shots_on_target_home BETWEEN 0 AND 1000),
    shots_on_target_away INTEGER CHECK (shots_on_target_away BETWEEN 0 AND 1000),
    note TEXT,
    created_at TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    CHECK (home_team_id IS NULL OR away_team_id IS NULL OR home_team_id <> away_team_id),
    CHECK ((corners_home IS NULL) = (corners_away IS NULL)),
    CHECK ((shots_on_target_home IS NULL) = (shots_on_target_away IS NULL))
);
CREATE INDEX IF NOT EXISTS idx_matches_played ON matches(played_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_matches_home_team ON matches(home_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_away_team ON matches(away_team_id);

CREATE TABLE IF NOT EXISTS match_categories (
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    variable_key TEXT NOT NULL,
    PRIMARY KEY (match_id, variable_key)
);
CREATE INDEX IF NOT EXISTS idx_match_categories_variable ON match_categories(variable_key);
"""


class Database:
    def __init__(self, path: Path, *, backup_dir: Path | None = None) -> None:
        self.path = path.resolve()
        self.backup_dir = (backup_dir or self.path.parent / "respaldos").resolve()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=10,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.path.parent.chmod(0o700)
            self.backup_dir.chmod(0o700)
        except OSError:
            pass
        connection = self.connect()
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"La base usa el esquema {version}, superior al compatible {SCHEMA_VERSION}."
                )
            connection.executescript(SCHEMA_SQL)
            if version < 1:
                now = utc_now()
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (1, now),
                )
                connection.execute("PRAGMA user_version = 1")
            connection.execute(
                "INSERT OR REPLACE INTO app_meta(key, value) VALUES ('app_version', ?)",
                (__version__,),
            )
        finally:
            connection.close()
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    @contextmanager
    def transaction(self, *, immediate: bool = True) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def backup(self) -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        destination = self.backup_dir / f"betplaycito-{stamp}.db"
        source = self.connect()
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
            check = target.execute("PRAGMA integrity_check").fetchone()[0]
            if check != "ok":
                raise RuntimeError(f"El respaldo no superó integrity_check: {check}")
        finally:
            target.close()
            source.close()
        try:
            destination.chmod(0o600)
        except OSError:
            pass
        return destination


class LoginLimiter:
    """Limitador sencillo en memoria para desalentar intentos repetidos."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: dict[tuple[str, str], list[float]] = {}

    def retry_after(self, address: str, username: str) -> int:
        key = (address, username.casefold())
        now = time.monotonic()
        with self._lock:
            recent = [stamp for stamp in self._failures.get(key, []) if now - stamp < 900]
            self._failures[key] = recent
            if len(recent) < 5:
                return 0
            delay = min(300, 30 * (len(recent) - 4))
            remaining = int(delay - (now - recent[-1]))
            return max(0, remaining)

    def failed(self, address: str, username: str) -> None:
        key = (address, username.casefold())
        with self._lock:
            self._failures.setdefault(key, []).append(time.monotonic())

    def succeeded(self, address: str, username: str) -> None:
        with self._lock:
            self._failures.pop((address, username.casefold()), None)


def derive_match_categories(
    home_goals: int,
    away_goals: int,
    corners_home: int | None,
    corners_away: int | None,
    shots_home: int | None,
    shots_away: int | None,
) -> list[str]:
    categories: list[str] = []
    if home_goals > away_goals:
        categories.append("home_win")
    elif home_goals == away_goals:
        categories.append("draw")
    else:
        categories.append("away_win")
    categories.append("over25" if home_goals + away_goals >= 3 else "under25")
    categories.append("btts_yes" if home_goals > 0 and away_goals > 0 else "btts_no")
    categories.append("local_scored" if home_goals > 0 else "local_blank")
    if corners_home is not None and corners_away is not None:
        categories.append(
            "corners_over95" if corners_home + corners_away >= 10 else "corners_under95"
        )
    if shots_home is not None and shots_away is not None:
        categories.append(
            "shots_over95" if shots_home + shots_away >= 10 else "shots_under95"
        )
    return categories


class BetPlaycitoApp:
    def __init__(self, *, data_dir: Path | None = None, config_path: Path | None = None) -> None:
        root = default_project_root()
        default_data, default_config, default_backups = default_user_storage(root)
        configured_data = os.environ.get("BETPLAYCITO_DATA_DIR")
        self.data_dir = Path(data_dir or configured_data or default_data).expanduser().resolve()
        configured_file = os.environ.get("BETPLAYCITO_CONFIG")
        self.config_path = Path(
            config_path or configured_file or default_config
        ).expanduser().resolve()
        configured_backups = os.environ.get("BETPLAYCITO_BACKUP_DIR")
        backup_dir = Path(configured_backups or default_backups).expanduser().resolve()
        self.database = Database(
            self.data_dir / "betplaycito.db", backup_dir=backup_dir
        )
        if self.database.path.is_file() and self.database.path.stat().st_size > 0:
            automatic = self.database.backup()
            LOGGER.info("Respaldo automático previo al arranque: %s", automatic)
        self.database.initialize()
        self.login_limiter = LoginLimiter()
        self.setup_token: str | None = None
        self._bootstrap_admin()

    @property
    def setup_required(self) -> bool:
        connection = self.database.connect()
        try:
            count = connection.execute(
                "SELECT COUNT(*) FROM users WHERE active = 1"
            ).fetchone()[0]
        finally:
            connection.close()
        return count == 0

    def _bootstrap_admin(self) -> None:
        if not self.setup_required:
            return
        config = _load_config(self.config_path)
        username = os.environ.get("BETPLAYCITO_ADMIN_USER", config.get("admin_username"))
        encoded = os.environ.get(
            "BETPLAYCITO_ADMIN_PASSWORD_HASH", config.get("admin_password_hash")
        )
        plaintext = os.environ.get("BETPLAYCITO_ADMIN_PASSWORD", config.get("admin_password"))
        supplied = any(value is not None for value in (username, encoded, plaintext))
        require_setup = os.environ.get("BETPLAYCITO_REQUIRE_SETUP", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        if not supplied and not require_setup:
            username = DEFAULT_ADMIN_USERNAME
            encoded = DEFAULT_ADMIN_PASSWORD_HASH
            supplied = True
        if supplied:
            if not isinstance(username, str) or not USERNAME_RE.fullmatch(username):
                raise RuntimeError(
                    "admin_username debe tener 3-64 caracteres: letras, números, _, . o -."
                )
            if encoded is not None and plaintext is not None:
                raise RuntimeError(
                    "Use admin_password_hash o admin_password, pero no ambos a la vez."
                )
            if encoded is not None:
                try:
                    _parse_password_hash(encoded)
                except ValueError as exc:
                    raise RuntimeError(f"admin_password_hash no es válido: {exc}") from exc
            elif plaintext is not None:
                try:
                    encoded = hash_password(plaintext)
                except ValueError as exc:
                    raise RuntimeError(f"admin_password no es válido: {exc}") from exc
            else:
                raise RuntimeError("Falta admin_password_hash en la configuración local.")
            self._create_initial_user(username, encoded)
            LOGGER.info("Administrador inicial creado desde configuración segura.")
            return
        self.setup_token = os.environ.get("BETPLAYCITO_SETUP_TOKEN") or secrets.token_urlsafe(32)
        LOGGER.warning(
            "No existe administrador. Token de configuración de una sola vez: %s",
            self.setup_token,
        )

    def _create_initial_user(self, username: str, password_hash: str) -> dict[str, Any]:
        now = utc_now()
        with self.database.transaction() as connection:
            if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                raise APIError(409, "setup_complete", "La configuración inicial ya fue realizada.")
            cursor = connection.execute(
                "INSERT INTO users(username, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (username, password_hash, now, now),
            )
        return {"id": cursor.lastrowid, "username": username}

    def complete_setup(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not self.setup_required:
            raise APIError(409, "setup_complete", "La configuración inicial ya fue realizada.")
        token = payload.get("token")
        if not isinstance(token, str) or self.setup_token is None or not hmac.compare_digest(
            token, self.setup_token
        ):
            raise APIError(403, "invalid_setup_token", "El token de configuración no es válido.")
        username = payload.get("username")
        if not isinstance(username, str) or not USERNAME_RE.fullmatch(username):
            raise APIError(
                422,
                "validation_error",
                "El usuario debe tener 3-64 caracteres: letras, números, _, . o -.",
            )
        try:
            encoded = hash_password(payload.get("password"))
        except ValueError as exc:
            raise APIError(422, "validation_error", str(exc)) from exc
        user = self._create_initial_user(username, encoded)
        self.setup_token = None
        return user

    def authenticate_credentials(
        self, username: Any, password: Any, remote_address: str
    ) -> tuple[dict[str, Any], str, int]:
        if not isinstance(username, str) or not isinstance(password, str):
            raise APIError(401, "invalid_credentials", "Usuario o contraseña incorrectos.")
        username = username.strip()
        retry = self.login_limiter.retry_after(remote_address, username)
        if retry:
            raise APIError(
                429,
                "too_many_attempts",
                f"Demasiados intentos. Espere {retry} segundos.",
                headers={"Retry-After": str(retry)},
            )
        connection = self.database.connect()
        try:
            row = connection.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ? AND active = 1",
                (username,),
            ).fetchone()
        finally:
            connection.close()
        if row is None or not verify_password(password, row["password_hash"]):
            self.login_limiter.failed(remote_address, username)
            raise APIError(401, "invalid_credentials", "Usuario o contraseña incorrectos.")
        self.login_limiter.succeeded(remote_address, username)
        token, expires = self.create_session(int(row["id"]))
        return {"id": row["id"], "username": row["username"]}, token, expires

    def create_session(self, user_id: int) -> tuple[str, int]:
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        now_epoch = utc_epoch()
        expires = now_epoch + SESSION_SECONDS
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE expires_at < ? OR revoked_at IS NOT NULL",
                (now_epoch,),
            )
            connection.execute(
                """INSERT INTO sessions
                   (user_id, token_hash, created_at, last_seen_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, token_hash, utc_now(), now_epoch, expires),
            )
        return token, expires

    def session_user(self, token: str | None) -> dict[str, Any] | None:
        if not token or len(token) > 256:
            return None
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = utc_epoch()
        with self.database.transaction(immediate=False) as connection:
            row = connection.execute(
                """SELECT s.id AS session_id, s.last_seen_at, s.expires_at,
                          u.id, u.username
                   FROM sessions s JOIN users u ON u.id = s.user_id
                   WHERE s.token_hash = ? AND s.revoked_at IS NULL AND u.active = 1""",
                (token_hash,),
            ).fetchone()
            if row is None:
                return None
            if int(row["expires_at"]) <= now:
                connection.execute(
                    "UPDATE sessions SET revoked_at = ? WHERE id = ?", (utc_now(), row["session_id"])
                )
                return None
            if now - int(row["last_seen_at"]) >= 300:
                connection.execute(
                    "UPDATE sessions SET last_seen_at = ? WHERE id = ?",
                    (now, row["session_id"]),
                )
        return {
            "id": int(row["id"]),
            "username": row["username"],
            "session_id": int(row["session_id"]),
            "expires_at": int(row["expires_at"]),
        }

    def revoke_session(self, token: str | None) -> None:
        if not token:
            return
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
                (utc_now(), token_hash),
            )

    def state(self, user: Mapping[str, Any]) -> dict[str, Any]:
        groups = [
            {"key": item["key"], "label": item["label"], "categories": list(item["categories"])}
            for item in VARIABLE_GROUPS
        ]
        return {
            "authenticated": True,
            "user": {"id": user["id"], "username": user["username"]},
            "setup_required": False,
            "features": {
                "teams": True,
                "matches": True,
                "backups": True,
                "restore": True,
                "xlsx": True,
                "shutdown": True,
                "persistent_sqlite": True,
            },
            "variables": [dict(item) for item in VARIABLES.values()],
            "groups": groups,
            "version": __version__,
        }

    def list_teams(self, *, include_archived: bool = False) -> list[dict[str, Any]]:
        query = "SELECT id, name, archived, created_at, updated_at FROM teams"
        parameters: tuple[Any, ...] = ()
        if not include_archived:
            query += " WHERE archived = 0"
        query += " ORDER BY archived, name COLLATE NOCASE, id"
        connection = self.database.connect()
        try:
            rows = connection.execute(query, parameters).fetchall()
        finally:
            connection.close()
        return [
            {
                "id": int(row["id"]),
                "name": row["name"],
                "archived": bool(row["archived"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def create_team(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        name, normalized = normalize_team_name(payload.get("name"))
        now = utc_now()
        try:
            with self.database.transaction() as connection:
                cursor = connection.execute(
                    """INSERT INTO teams(name, normalized_name, created_at, updated_at)
                       VALUES (?, ?, ?, ?)""",
                    (name, normalized, now, now),
                )
                team_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            connection = self.database.connect()
            try:
                existing = connection.execute(
                    "SELECT id, archived FROM teams WHERE normalized_name = ?", (normalized,)
                ).fetchone()
            finally:
                connection.close()
            fields = {"name": "Ya existe un equipo con este nombre."}
            if existing is not None and existing["archived"]:
                fields["name"] = "El equipo ya existe y está archivado; puede reactivarlo."
            raise APIError(409, "team_exists", fields["name"], fields=fields) from exc
        return {
            "id": team_id,
            "name": name,
            "archived": False,
            "created_at": now,
            "updated_at": now,
        }

    def archive_team(self, team_id: int, payload: Mapping[str, Any]) -> dict[str, Any]:
        archived = payload.get("archived")
        if not isinstance(archived, bool):
            raise APIError(
                422,
                "validation_error",
                "archived debe ser verdadero o falso.",
                fields={"archived": "Valor booleano requerido."},
            )
        now = utc_now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "UPDATE teams SET archived = ?, updated_at = ? WHERE id = ?",
                (int(archived), now, team_id),
            )
            if cursor.rowcount == 0:
                raise APIError(404, "team_not_found", "El equipo no existe.")
            row = connection.execute(
                "SELECT id, name, archived, created_at, updated_at FROM teams WHERE id = ?",
                (team_id,),
            ).fetchone()
        return {
            "id": int(row["id"]),
            "name": row["name"],
            "archived": bool(row["archived"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _ensure_team(
        connection: sqlite3.Connection, team_id: int, *, allow_archived: bool = False
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT id, name, archived FROM teams WHERE id = ?", (team_id,)
        ).fetchone()
        if row is None:
            raise APIError(422, "team_not_found", f"No existe el equipo {team_id}.")
        if row["archived"] and not allow_archived:
            raise APIError(422, "team_archived", f"El equipo {row['name']} está archivado.")
        return row

    def create_adjustment(
        self, payload: Mapping[str, Any], user: Mapping[str, Any]
    ) -> dict[str, Any]:
        variable = payload.get("variable")
        if variable not in VARIABLES:
            raise APIError(
                422,
                "unknown_variable",
                "La variable indicada no existe.",
                fields={"variable": "Variable desconocida."},
            )
        delta = require_int(payload.get("delta"), field="delta", minimum=-10000, maximum=10000)
        if delta == 0:
            raise APIError(422, "validation_error", "delta no puede ser cero.")
        team_id = require_int(
            payload.get("team_id"),
            field="team_id",
            minimum=1,
            maximum=MAX_SQLITE_ID,
            optional=True,
        )
        note = clean_optional_text(payload.get("note"), field="note", maximum=500)
        now = utc_now()
        with self.database.transaction() as connection:
            team_name = None
            if team_id is not None:
                team = self._ensure_team(connection, team_id)
                team_name = team["name"]
            global_current = int(
                connection.execute(
                    """SELECT COALESCE(SUM(delta), 0) FROM adjustments
                       WHERE variable_key = ?""",
                    (variable,),
                ).fetchone()[0]
            )
            if team_id is None:
                current = global_current
            else:
                current = int(
                    connection.execute(
                        """SELECT COALESCE(SUM(delta), 0) FROM adjustments
                           WHERE variable_key = ? AND team_id = ?""",
                        (variable, team_id),
                    ).fetchone()[0]
                )
            if current + delta < 0:
                raise APIError(
                    409,
                    "negative_counter",
                    f"El contador manual actual es {current}; no puede quedar por debajo de cero.",
                    fields={"delta": "La disminución supera el total disponible."},
                )
            if global_current + delta < 0:
                raise APIError(
                    409,
                    "negative_counter",
                    f"El contador manual global actual es {global_current}; no puede quedar por debajo de cero.",
                    fields={"delta": "La disminución supera el total global disponible."},
                )
            cursor = connection.execute(
                """INSERT INTO adjustments
                   (team_id, variable_key, delta, note, created_at, created_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (team_id, variable, delta, note, now, user["id"]),
            )
            adjustment_id = int(cursor.lastrowid)
        return {
            "type": "adjustment",
            "id": adjustment_id,
            "team_id": team_id,
            "team_name": team_name,
            "variable": variable,
            "variable_label": VARIABLES[variable]["label"],
            "delta": delta,
            "note": note,
            "created_at": now,
        }

    def _validate_match_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        home_team_id = require_int(
            payload.get("home_team_id"),
            field="home_team_id",
            minimum=1,
            maximum=MAX_SQLITE_ID,
            optional=True,
        )
        away_team_id = require_int(
            payload.get("away_team_id"),
            field="away_team_id",
            minimum=1,
            maximum=MAX_SQLITE_ID,
            optional=True,
        )
        if home_team_id is not None and home_team_id == away_team_id:
            raise APIError(422, "validation_error", "Local y visitante no pueden ser el mismo equipo.")
        home_name = clean_optional_text(
            payload.get("home_team_name"), field="home_team_name", maximum=100
        )
        away_name = clean_optional_text(
            payload.get("away_team_name"), field="away_team_name", maximum=100
        )
        home_goals = require_int(
            payload.get("home_goals"), field="home_goals", minimum=0, maximum=100
        )
        away_goals = require_int(
            payload.get("away_goals"), field="away_goals", minimum=0, maximum=100
        )
        corners_home = require_int(
            payload.get("corners_home"),
            field="corners_home",
            minimum=0,
            maximum=1000,
            optional=True,
        )
        corners_away = require_int(
            payload.get("corners_away"),
            field="corners_away",
            minimum=0,
            maximum=1000,
            optional=True,
        )
        if (corners_home is None) != (corners_away is None):
            raise APIError(
                422,
                "validation_error",
                "Debe indicar los tiros de esquina de ambos equipos o dejar ambos vacíos.",
            )
        shots_home = require_int(
            payload.get("shots_on_target_home"),
            field="shots_on_target_home",
            minimum=0,
            maximum=1000,
            optional=True,
        )
        shots_away = require_int(
            payload.get("shots_on_target_away"),
            field="shots_on_target_away",
            minimum=0,
            maximum=1000,
            optional=True,
        )
        if (shots_home is None) != (shots_away is None):
            raise APIError(
                422,
                "validation_error",
                "Debe indicar los tiros al arco de ambos equipos o dejar ambos vacíos.",
            )
        played_at = payload.get("played_at") or date.today().isoformat()
        if not isinstance(played_at, str) or len(played_at) != 10:
            raise APIError(422, "validation_error", "played_at debe usar el formato AAAA-MM-DD.")
        try:
            date.fromisoformat(played_at)
        except ValueError as exc:
            raise APIError(422, "validation_error", "played_at no es una fecha válida.") from exc
        note = clean_optional_text(payload.get("note"), field="note", maximum=1000)
        return {
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_team_name": home_name,
            "away_team_name": away_name,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "corners_home": corners_home,
            "corners_away": corners_away,
            "shots_on_target_home": shots_home,
            "shots_on_target_away": shots_away,
            "played_at": played_at,
            "note": note,
        }

    def create_match(self, payload: Mapping[str, Any], user: Mapping[str, Any]) -> dict[str, Any]:
        values = self._validate_match_payload(payload)
        categories = derive_match_categories(
            values["home_goals"],
            values["away_goals"],
            values["corners_home"],
            values["corners_away"],
            values["shots_on_target_home"],
            values["shots_on_target_away"],
        )
        now = utc_now()
        with self.database.transaction() as connection:
            if values["home_team_id"] is not None:
                home = self._ensure_team(connection, values["home_team_id"])
                if values["home_team_name"] is None:
                    values["home_team_name"] = home["name"]
            if values["away_team_id"] is not None:
                away = self._ensure_team(connection, values["away_team_id"])
                if values["away_team_name"] is None:
                    values["away_team_name"] = away["name"]
            cursor = connection.execute(
                """INSERT INTO matches
                   (played_at, home_team_id, away_team_id, home_team_name, away_team_name,
                    home_goals, away_goals, corners_home, corners_away,
                    shots_on_target_home, shots_on_target_away, note, created_at, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    values["played_at"],
                    values["home_team_id"],
                    values["away_team_id"],
                    values["home_team_name"],
                    values["away_team_name"],
                    values["home_goals"],
                    values["away_goals"],
                    values["corners_home"],
                    values["corners_away"],
                    values["shots_on_target_home"],
                    values["shots_on_target_away"],
                    values["note"],
                    now,
                    user["id"],
                ),
            )
            match_id = int(cursor.lastrowid)
            connection.executemany(
                "INSERT INTO match_categories(match_id, variable_key) VALUES (?, ?)",
                [(match_id, variable) for variable in categories],
            )
        return {
            "type": "match",
            "id": match_id,
            **values,
            "categories": categories,
            "created_at": now,
        }

    def validate_team_ids(self, team_ids: Sequence[int]) -> list[dict[str, Any]]:
        if len(team_ids) > 100:
            raise APIError(422, "too_many_teams", "Puede comparar como máximo 100 equipos.")
        unique: list[int] = []
        seen: set[int] = set()
        for team_id in team_ids:
            if (
                isinstance(team_id, bool)
                or not isinstance(team_id, int)
                or not 1 <= team_id <= MAX_SQLITE_ID
            ):
                raise APIError(422, "validation_error", "team_ids contiene un identificador inválido.")
            if team_id not in seen:
                unique.append(team_id)
                seen.add(team_id)
        if not unique:
            return []
        placeholders = ",".join("?" for _ in unique)
        connection = self.database.connect()
        try:
            rows = connection.execute(
                f"SELECT id, name, archived FROM teams WHERE id IN ({placeholders})", unique
            ).fetchall()
        finally:
            connection.close()
        by_id = {int(row["id"]): row for row in rows}
        missing = [team_id for team_id in unique if team_id not in by_id]
        if missing:
            raise APIError(422, "team_not_found", f"No existen los equipos: {missing}.")
        return [
            {"id": team_id, "name": by_id[team_id]["name"], "archived": bool(by_id[team_id]["archived"])}
            for team_id in unique
        ]

    @staticmethod
    def _group_payload(
        manual_counts: Mapping[str, int],
        match_counts: Mapping[str, int],
        decrementable_counts: Mapping[str, int],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for group in VARIABLE_GROUPS:
            keys = group["categories"]
            combined = {
                key: max(
                    0,
                    int(manual_counts.get(key, 0)) + int(match_counts.get(key, 0)),
                )
                for key in keys
            }
            total = sum(combined.values())
            categories = []
            for key in keys:
                manual_count = max(0, int(manual_counts.get(key, 0)))
                match_count = max(0, int(match_counts.get(key, 0)))
                decrementable_count = max(0, int(decrementable_counts.get(key, 0)))
                count = combined[key]
                categories.append(
                    {
                        "key": key,
                        "label": VARIABLES[key]["label"],
                        "count": count,
                        "manual_count": manual_count,
                        "match_count": match_count,
                        "decrementable_count": decrementable_count,
                        "can_decrement": decrementable_count > 0,
                        "percentage": round(count * 100 / total, 2) if total else 0.0,
                        "opposite": VARIABLES[key]["opposite"],
                        "alternatives": list(VARIABLES[key]["alternatives"]),
                    }
                )
            result.append(
                {
                    "key": group["key"],
                    "label": group["label"],
                    "total": total,
                    "categories": categories,
                }
            )
        return result

    def _aggregate(self, connection: sqlite3.Connection, team_ids: Sequence[int]) -> dict[str, Any]:
        manual_counts = {key: 0 for key in VARIABLES}
        match_counts = {key: 0 for key in VARIABLES}
        adjustment_where = ""
        match_where = ""
        adjustment_params: list[Any] = []
        match_params: list[Any] = []
        if team_ids:
            placeholders = ",".join("?" for _ in team_ids)
            adjustment_where = f" WHERE team_id IN ({placeholders})"
            adjustment_params.extend(team_ids)
            match_where = (
                f" WHERE (m.home_team_id IN ({placeholders}) "
                f"OR m.away_team_id IN ({placeholders}))"
            )
            match_params.extend(team_ids)
            match_params.extend(team_ids)
        adjustment_rows = connection.execute(
            f"""SELECT variable_key, COALESCE(SUM(delta), 0) AS amount,
                       COUNT(*) AS event_count, COALESCE(SUM(ABS(delta)), 0) AS units
                FROM adjustments{adjustment_where} GROUP BY variable_key""",
            adjustment_params,
        ).fetchall()
        adjustment_events = 0
        adjustment_units = 0
        for row in adjustment_rows:
            if row["variable_key"] in manual_counts:
                manual_counts[row["variable_key"]] += int(row["amount"])
            adjustment_events += int(row["event_count"])
            adjustment_units += int(row["units"])
        if team_ids:
            global_manual_counts = {key: 0 for key in VARIABLES}
            for row in connection.execute(
                """SELECT variable_key, COALESCE(SUM(delta), 0) AS amount
                   FROM adjustments GROUP BY variable_key"""
            ).fetchall():
                if row["variable_key"] in global_manual_counts:
                    global_manual_counts[row["variable_key"]] = int(row["amount"])
        else:
            global_manual_counts = dict(manual_counts)
        decrementable_counts = {
            key: min(
                max(0, int(manual_counts.get(key, 0))),
                max(0, int(global_manual_counts.get(key, 0))),
            )
            for key in VARIABLES
        }
        category_rows = connection.execute(
            f"""SELECT mc.variable_key, COUNT(*) AS amount
                FROM match_categories mc JOIN matches m ON m.id = mc.match_id
                {match_where} GROUP BY mc.variable_key""",
            match_params,
        ).fetchall()
        for row in category_rows:
            if row["variable_key"] in match_counts:
                match_counts[row["variable_key"]] += int(row["amount"])
        match_count = int(
            connection.execute(
                f"SELECT COUNT(*) FROM matches m{match_where}", match_params
            ).fetchone()[0]
        )
        groups = self._group_payload(manual_counts, match_counts, decrementable_counts)
        return {
            "groups": groups,
            "totals": {
                "adjustments": adjustment_events,
                "adjustment_units": adjustment_units,
                "matches": match_count,
                "observations": sum(group["total"] for group in groups),
            },
        }

    def dashboard(self, team_ids: Sequence[int]) -> dict[str, Any]:
        teams = self.validate_team_ids(team_ids)
        ids = [item["id"] for item in teams]
        connection = self.database.connect()
        try:
            aggregate = self._aggregate(connection, ids)
            breakdown = []
            for team in teams:
                team_stats = self._aggregate(connection, [team["id"]])
                breakdown.append(
                    {
                        "id": team["id"],
                        "name": team["name"],
                        "archived": team["archived"],
                        **team_stats,
                    }
                )
        finally:
            connection.close()
        return {
            "scope": {
                "team_ids": ids,
                "team_names": [item["name"] for item in teams],
                "mode": "selected" if ids else "all",
            },
            **aggregate,
            "team_breakdown": breakdown,
            "generated_at": utc_now(),
        }

    @staticmethod
    def _match_from_row(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        categories = [
            item["variable_key"]
            for item in connection.execute(
                "SELECT variable_key FROM match_categories WHERE match_id = ? ORDER BY rowid",
                (row["id"],),
            ).fetchall()
        ]
        return {
            "type": "match",
            "id": int(row["id"]),
            "played_at": row["played_at"],
            "home_team_id": row["home_team_id"],
            "away_team_id": row["away_team_id"],
            "home_team_name": row["home_team_name"] or "Local",
            "away_team_name": row["away_team_name"] or "Visitante",
            "home_goals": int(row["home_goals"]),
            "away_goals": int(row["away_goals"]),
            "corners_home": row["corners_home"],
            "corners_away": row["corners_away"],
            "shots_on_target_home": row["shots_on_target_home"],
            "shots_on_target_away": row["shots_on_target_away"],
            "note": row["note"],
            "categories": categories,
            "category_labels": [VARIABLES[key]["label"] for key in categories if key in VARIABLES],
            "created_at": row["created_at"],
        }

    @staticmethod
    def _adjustment_from_row(row: sqlite3.Row) -> dict[str, Any]:
        key = row["variable_key"]
        return {
            "type": "adjustment",
            "id": int(row["id"]),
            "team_id": row["team_id"],
            "team_name": row["team_name"],
            "variable": key,
            "variable_label": VARIABLES.get(key, {}).get("label", key),
            "delta": int(row["delta"]),
            "note": row["note"],
            "created_at": row["created_at"],
        }

    def history(
        self,
        *,
        page: int,
        page_size: int,
        item_type: str,
        team_ids: Sequence[int],
    ) -> dict[str, Any]:
        teams = self.validate_team_ids(team_ids)
        ids = [item["id"] for item in teams]
        queries: list[str] = []
        parameters: list[Any] = []
        placeholders = ",".join("?" for _ in ids)
        if item_type in ("all", "adjustment"):
            adjustment_where = f" WHERE team_id IN ({placeholders})" if ids else ""
            queries.append(
                f"SELECT 'adjustment' AS item_type, id, created_at FROM adjustments{adjustment_where}"
            )
            parameters.extend(ids)
        if item_type in ("all", "match"):
            match_where = (
                f" WHERE home_team_id IN ({placeholders}) OR away_team_id IN ({placeholders})"
                if ids
                else ""
            )
            queries.append(f"SELECT 'match' AS item_type, id, created_at FROM matches{match_where}")
            if ids:
                parameters.extend(ids)
                parameters.extend(ids)
        union = " UNION ALL ".join(queries)
        connection = self.database.connect()
        try:
            total = int(
                connection.execute(f"SELECT COUNT(*) FROM ({union})", parameters).fetchone()[0]
            )
            offset = (page - 1) * page_size
            keys = connection.execute(
                f"""SELECT item_type, id, created_at FROM ({union})
                    ORDER BY created_at DESC, id DESC, item_type
                    LIMIT ? OFFSET ?""",
                [*parameters, page_size, offset],
            ).fetchall()
            items: list[dict[str, Any]] = []
            for key in keys:
                if key["item_type"] == "adjustment":
                    row = connection.execute(
                        """SELECT a.*, t.name AS team_name FROM adjustments a
                           LEFT JOIN teams t ON t.id = a.team_id WHERE a.id = ?""",
                        (key["id"],),
                    ).fetchone()
                    if row is not None:
                        items.append(self._adjustment_from_row(row))
                else:
                    row = connection.execute(
                        "SELECT * FROM matches WHERE id = ?", (key["id"],)
                    ).fetchone()
                    if row is not None:
                        items.append(self._match_from_row(connection, row))
        finally:
            connection.close()
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }

    def change_password(
        self, user: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> tuple[str, int]:
        current_password = payload.get("current_password")
        new_password = payload.get("new_password")
        if not isinstance(current_password, str):
            raise APIError(422, "validation_error", "Debe indicar la contraseña actual.")
        connection = self.database.connect()
        try:
            row = connection.execute(
                "SELECT password_hash FROM users WHERE id = ? AND active = 1", (user["id"],)
            ).fetchone()
        finally:
            connection.close()
        if row is None or not verify_password(current_password, row["password_hash"]):
            raise APIError(401, "invalid_current_password", "La contraseña actual es incorrecta.")
        try:
            encoded = hash_password(new_password)
        except ValueError as exc:
            raise APIError(422, "validation_error", str(exc)) from exc
        if verify_password(new_password, row["password_hash"]):
            raise APIError(422, "password_unchanged", "La contraseña nueva debe ser diferente.")
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        now_text = utc_now()
        now_epoch = utc_epoch()
        expires = now_epoch + SESSION_SECONDS
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (encoded, now_text, user["id"]),
            )
            connection.execute(
                "UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (now_text, user["id"]),
            )
            connection.execute(
                """INSERT INTO sessions
                   (user_id, token_hash, created_at, last_seen_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (user["id"], token_hash, now_text, now_epoch, expires),
            )
        return token, expires

    def export_payload(self) -> dict[str, Any]:
        connection = self.database.connect()
        try:
            teams = [
                {
                    "id": int(row["id"]),
                    "name": row["name"],
                    "archived": bool(row["archived"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in connection.execute(
                    "SELECT id, name, archived, created_at, updated_at FROM teams ORDER BY id"
                ).fetchall()
            ]
            adjustments = [
                self._adjustment_from_row(row)
                for row in connection.execute(
                    """SELECT a.*, t.name AS team_name FROM adjustments a
                       LEFT JOIN teams t ON t.id = a.team_id ORDER BY a.id"""
                ).fetchall()
            ]
            matches = [
                self._match_from_row(connection, row)
                for row in connection.execute("SELECT * FROM matches ORDER BY id").fetchall()
            ]
        finally:
            connection.close()
        return {
            "format": "betplaycito-backup",
            "version": SCHEMA_VERSION,
            "app_version": __version__,
            "exported_at": utc_now(),
            "variables": [dict(item) for item in VARIABLES.values()],
            "teams": teams,
            "adjustments": adjustments,
            "matches": matches,
        }

    @staticmethod
    def _validate_restore_payload(payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            wrapped = payload.get("data")
            if isinstance(wrapped, dict) and wrapped.get("format") == "betplaycito-backup":
                payload = wrapped
        if not isinstance(payload, dict) or payload.get("format") != "betplaycito-backup":
            raise APIError(422, "invalid_backup", "El JSON no es un respaldo de BetPlaycito.")
        if payload.get("version") != SCHEMA_VERSION:
            raise APIError(
                422,
                "unsupported_backup",
                f"Solo se admite la versión de respaldo {SCHEMA_VERSION}.",
            )
        teams = payload.get("teams")
        adjustments = payload.get("adjustments")
        matches = payload.get("matches")
        if not isinstance(teams, list) or not isinstance(adjustments, list) or not isinstance(matches, list):
            raise APIError(422, "invalid_backup", "El respaldo no contiene listas válidas.")
        if len(teams) > 100_000 or len(adjustments) > 500_000 or len(matches) > 500_000:
            raise APIError(413, "backup_too_large", "El respaldo supera los límites permitidos.")

        validated_teams: list[dict[str, Any]] = []
        team_ids: set[int] = set()
        normalized_names: set[str] = set()
        for item in teams:
            if not isinstance(item, dict):
                raise APIError(422, "invalid_backup", "Hay un equipo no válido.")
            team_id = require_int(
                item.get("id"), field="team.id", minimum=1, maximum=MAX_SQLITE_ID
            )
            if team_id in team_ids:
                raise APIError(422, "invalid_backup", f"El equipo {team_id} está repetido.")
            name, normalized = normalize_team_name(item.get("name"))
            if normalized in normalized_names:
                raise APIError(422, "invalid_backup", f"El equipo {name} está repetido.")
            archived = item.get("archived", False)
            if not isinstance(archived, bool):
                raise APIError(422, "invalid_backup", "archived debe ser booleano.")
            created_at = parse_iso_timestamp(item.get("created_at"), field="team.created_at")
            updated_at = parse_iso_timestamp(item.get("updated_at"), field="team.updated_at")
            team_ids.add(team_id)
            normalized_names.add(normalized)
            validated_teams.append(
                {
                    "id": team_id,
                    "name": name,
                    "normalized_name": normalized,
                    "archived": int(archived),
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            )

        validated_adjustments: list[dict[str, Any]] = []
        adjustment_ids: set[int] = set()
        team_balances: dict[tuple[int, str], int] = {}
        global_balances: dict[str, int] = {}
        staged_adjustments: list[tuple[int, dict[str, Any]]] = []
        for item in adjustments:
            if not isinstance(item, dict):
                raise APIError(422, "invalid_backup", "Hay un ajuste no válido.")
            adjustment_id = require_int(
                item.get("id"), field="adjustment.id", minimum=1, maximum=MAX_SQLITE_ID
            )
            if adjustment_id in adjustment_ids:
                raise APIError(422, "invalid_backup", f"El ajuste {adjustment_id} está repetido.")
            adjustment_ids.add(adjustment_id)
            staged_adjustments.append((adjustment_id, item))
        for adjustment_id, item in sorted(staged_adjustments, key=lambda value: value[0]):
            team_id = require_int(
                item.get("team_id"),
                field="adjustment.team_id",
                minimum=1,
                maximum=MAX_SQLITE_ID,
                optional=True,
            )
            if team_id is not None and team_id not in team_ids:
                raise APIError(422, "invalid_backup", f"El ajuste usa el equipo inexistente {team_id}.")
            variable = item.get("variable")
            if variable not in VARIABLES:
                raise APIError(422, "invalid_backup", f"Variable desconocida: {variable!r}.")
            delta = require_int(
                item.get("delta"), field="adjustment.delta", minimum=-10000, maximum=10000
            )
            if delta == 0:
                raise APIError(422, "invalid_backup", "Un ajuste no puede tener delta cero.")
            global_balances[variable] = global_balances.get(variable, 0) + delta
            if global_balances[variable] < 0:
                raise APIError(422, "invalid_backup", "Un ajuste deja el contador global bajo cero.")
            if team_id is not None:
                key = (team_id, variable)
                team_balances[key] = team_balances.get(key, 0) + delta
                if team_balances[key] < 0:
                    raise APIError(
                        422, "invalid_backup", "Un ajuste deja el contador de un equipo bajo cero."
                    )
            note = clean_optional_text(item.get("note"), field="adjustment.note", maximum=500)
            created_at = parse_iso_timestamp(item.get("created_at"), field="adjustment.created_at")
            validated_adjustments.append(
                {
                    "id": adjustment_id,
                    "team_id": team_id,
                    "variable": variable,
                    "delta": delta,
                    "note": note,
                    "created_at": created_at,
                }
            )

        validated_matches: list[dict[str, Any]] = []
        match_ids: set[int] = set()
        for item in matches:
            if not isinstance(item, dict):
                raise APIError(422, "invalid_backup", "Hay un partido no válido.")
            match_id = require_int(
                item.get("id"), field="match.id", minimum=1, maximum=MAX_SQLITE_ID
            )
            if match_id in match_ids:
                raise APIError(422, "invalid_backup", f"El partido {match_id} está repetido.")
            home_team_id = require_int(
                item.get("home_team_id"),
                field="match.home_team_id",
                minimum=1,
                maximum=MAX_SQLITE_ID,
                optional=True,
            )
            away_team_id = require_int(
                item.get("away_team_id"),
                field="match.away_team_id",
                minimum=1,
                maximum=MAX_SQLITE_ID,
                optional=True,
            )
            if home_team_id is not None and home_team_id not in team_ids:
                raise APIError(422, "invalid_backup", f"Equipo local inexistente: {home_team_id}.")
            if away_team_id is not None and away_team_id not in team_ids:
                raise APIError(422, "invalid_backup", f"Equipo visitante inexistente: {away_team_id}.")
            if home_team_id is not None and home_team_id == away_team_id:
                raise APIError(422, "invalid_backup", "Un partido repite el mismo equipo.")
            home_goals = require_int(
                item.get("home_goals"), field="match.home_goals", minimum=0, maximum=100
            )
            away_goals = require_int(
                item.get("away_goals"), field="match.away_goals", minimum=0, maximum=100
            )
            corners_home = require_int(
                item.get("corners_home"),
                field="match.corners_home",
                minimum=0,
                maximum=1000,
                optional=True,
            )
            corners_away = require_int(
                item.get("corners_away"),
                field="match.corners_away",
                minimum=0,
                maximum=1000,
                optional=True,
            )
            shots_home = require_int(
                item.get("shots_on_target_home"),
                field="match.shots_on_target_home",
                minimum=0,
                maximum=1000,
                optional=True,
            )
            shots_away = require_int(
                item.get("shots_on_target_away"),
                field="match.shots_on_target_away",
                minimum=0,
                maximum=1000,
                optional=True,
            )
            if (corners_home is None) != (corners_away is None):
                raise APIError(422, "invalid_backup", "Córners incompletos en un partido.")
            if (shots_home is None) != (shots_away is None):
                raise APIError(422, "invalid_backup", "Tiros al arco incompletos en un partido.")
            played_at = item.get("played_at")
            if not isinstance(played_at, str):
                raise APIError(422, "invalid_backup", "Fecha de partido no válida.")
            try:
                date.fromisoformat(played_at)
            except ValueError as exc:
                raise APIError(422, "invalid_backup", "Fecha de partido no válida.") from exc
            home_name = clean_optional_text(
                item.get("home_team_name"), field="match.home_team_name", maximum=100
            )
            away_name = clean_optional_text(
                item.get("away_team_name"), field="match.away_team_name", maximum=100
            )
            note = clean_optional_text(item.get("note"), field="match.note", maximum=1000)
            created_at = parse_iso_timestamp(item.get("created_at"), field="match.created_at")
            categories = derive_match_categories(
                home_goals,
                away_goals,
                corners_home,
                corners_away,
                shots_home,
                shots_away,
            )
            match_ids.add(match_id)
            validated_matches.append(
                {
                    "id": match_id,
                    "played_at": played_at,
                    "home_team_id": home_team_id,
                    "away_team_id": away_team_id,
                    "home_team_name": home_name,
                    "away_team_name": away_name,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "corners_home": corners_home,
                    "corners_away": corners_away,
                    "shots_on_target_home": shots_home,
                    "shots_on_target_away": shots_away,
                    "note": note,
                    "created_at": created_at,
                    "categories": categories,
                }
            )
        return {
            "teams": validated_teams,
            "adjustments": validated_adjustments,
            "matches": validated_matches,
        }

    def restore_payload(self, payload: Any, user: Mapping[str, Any]) -> dict[str, Any]:
        validated = self._validate_restore_payload(payload)
        backup = self.database.backup()
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM match_categories")
            connection.execute("DELETE FROM matches")
            connection.execute("DELETE FROM adjustments")
            connection.execute("DELETE FROM teams")
            connection.executemany(
                """INSERT INTO teams
                   (id, name, normalized_name, archived, created_at, updated_at)
                   VALUES (:id, :name, :normalized_name, :archived, :created_at, :updated_at)""",
                validated["teams"],
            )
            connection.executemany(
                """INSERT INTO adjustments
                   (id, team_id, variable_key, delta, note, created_at, created_by)
                   VALUES (:id, :team_id, :variable, :delta, :note, :created_at, :created_by)""",
                [dict(item, created_by=user["id"]) for item in validated["adjustments"]],
            )
            for item in validated["matches"]:
                connection.execute(
                    """INSERT INTO matches
                       (id, played_at, home_team_id, away_team_id, home_team_name,
                        away_team_name, home_goals, away_goals, corners_home, corners_away,
                        shots_on_target_home, shots_on_target_away, note, created_at, created_by)
                       VALUES (:id, :played_at, :home_team_id, :away_team_id, :home_team_name,
                               :away_team_name, :home_goals, :away_goals, :corners_home,
                               :corners_away, :shots_on_target_home, :shots_on_target_away,
                               :note, :created_at, :created_by)""",
                    dict(item, created_by=user["id"]),
                )
                connection.executemany(
                    "INSERT INTO match_categories(match_id, variable_key) VALUES (?, ?)",
                    [(item["id"], variable) for variable in item["categories"]],
                )
        return {
            "restored": {
                "teams": len(validated["teams"]),
                "adjustments": len(validated["adjustments"]),
                "matches": len(validated["matches"]),
            },
            "safety_backup": backup.name,
        }

    def create_backup(self) -> dict[str, Any]:
        path = self.database.backup()
        stat = path.stat()
        return {
            "filename": path.name,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        }

    def list_backups(self) -> list[dict[str, Any]]:
        result = []
        for path in sorted(self.database.backup_dir.glob("betplaycito-*.db"), reverse=True):
            if not path.is_file() or not BACKUP_NAME_RE.fullmatch(path.name):
                continue
            stat = path.stat()
            result.append(
                {
                    "filename": path.name,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                    .replace(microsecond=0)
                    .isoformat()
                    .replace("+00:00", "Z"),
                }
            )
        return result

    def backup_path(self, filename: str) -> Path:
        if not BACKUP_NAME_RE.fullmatch(filename):
            raise APIError(404, "backup_not_found", "El respaldo no existe.")
        path = (self.database.backup_dir / filename).resolve()
        if path.parent != self.database.backup_dir or not path.is_file():
            raise APIError(404, "backup_not_found", "El respaldo no existe.")
        return path


def export_csv(payload: Mapping[str, Any]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(
        [
            "tipo",
            "id",
            "fecha_registro",
            "fecha_partido",
            "equipo",
            "local",
            "visitante",
            "marcador",
            "variable",
            "cambio",
            "categorias",
            "nota",
        ]
    )
    for item in payload["adjustments"]:
        writer.writerow(
            [
                "ajuste",
                item["id"],
                item["created_at"],
                "",
                item.get("team_name") or "General",
                "",
                "",
                "",
                item["variable_label"],
                item["delta"],
                "",
                item.get("note") or "",
            ]
        )
    for item in payload["matches"]:
        writer.writerow(
            [
                "partido",
                item["id"],
                item["created_at"],
                item["played_at"],
                "",
                item["home_team_name"],
                item["away_team_name"],
                f"{item['home_goals']}-{item['away_goals']}",
                "",
                "",
                " | ".join(item["category_labels"]),
                item.get("note") or "",
            ]
        )
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def _xlsx_col(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _safe_xml_text(value: Any) -> str:
    text = str(value)
    text = "".join(char for char in text if char in "\t\n\r" or ord(char) >= 32)
    return xml_escape(text, {'"': "&quot;"})


def _xlsx_sheet(rows: Sequence[Sequence[Any]]) -> str:
    output = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "<sheetData>",
    ]
    for row_number, row in enumerate(rows, 1):
        output.append(f'<row r="{row_number}">')
        for column_number, value in enumerate(row, 1):
            if value is None:
                continue
            reference = f"{_xlsx_col(column_number)}{row_number}"
            style = ' s="1"' if row_number == 1 else ""
            if isinstance(value, bool):
                output.append(f'<c r="{reference}" t="b"{style}><v>{int(value)}</v></c>')
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                output.append(f'<c r="{reference}"{style}><v>{value}</v></c>')
            else:
                output.append(
                    f'<c r="{reference}" t="inlineStr"{style}><is><t xml:space="preserve">'
                    f"{_safe_xml_text(value)}</t></is></c>"
                )
        output.append("</row>")
    output.extend(["</sheetData>", "</worksheet>"])
    return "".join(output)


def export_xlsx(payload: Mapping[str, Any], dashboard: Mapping[str, Any]) -> bytes:
    summary_rows: list[list[Any]] = [["Grupo", "Categoría", "Conteo", "Porcentaje"]]
    for group in dashboard["groups"]:
        for category in group["categories"]:
            summary_rows.append(
                [group["label"], category["label"], category["count"], category["percentage"]]
            )
    team_rows = [["ID", "Equipo", "Archivado", "Creado", "Actualizado"]]
    team_rows.extend(
        [item["id"], item["name"], item["archived"], item["created_at"], item["updated_at"]]
        for item in payload["teams"]
    )
    adjustment_rows = [["ID", "Equipo", "Variable", "Cambio", "Nota", "Fecha"]]
    adjustment_rows.extend(
        [
            item["id"],
            item.get("team_name") or "General",
            item["variable_label"],
            item["delta"],
            item.get("note") or "",
            item["created_at"],
        ]
        for item in payload["adjustments"]
    )
    match_rows = [
        [
            "ID",
            "Fecha",
            "Local",
            "Visitante",
            "Goles local",
            "Goles visitante",
            "Córners local",
            "Córners visitante",
            "Tiros al arco local",
            "Tiros al arco visitante",
            "Categorías",
            "Nota",
            "Registrado",
        ]
    ]
    match_rows.extend(
        [
            item["id"],
            item["played_at"],
            item["home_team_name"],
            item["away_team_name"],
            item["home_goals"],
            item["away_goals"],
            item["corners_home"],
            item["corners_away"],
            item["shots_on_target_home"],
            item["shots_on_target_away"],
            " | ".join(item["category_labels"]),
            item.get("note") or "",
            item["created_at"],
        ]
        for item in payload["matches"]
    )
    sheets = [
        ("Resumen", summary_rows),
        ("Equipos", team_rows),
        ("Ajustes", adjustment_rows),
        ("Partidos", match_rows),
    ]
    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for index in range(1, len(sheets) + 1):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append("</Types>")
    workbook_sheets = "".join(
        f'<sheet name="{_safe_xml_text(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _) in enumerate(sheets, 1)
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{workbook_sheets}</sheets></workbook>"
    )
    workbook_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for index in range(1, len(sheets) + 1):
        workbook_rels.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    workbook_rels.append(
        f'<Relationship Id="rId{len(sheets) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    workbook_rels.append("</Relationships>")
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>"
    )
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="2"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )
    created = utc_now()
    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:creator>BetPlaycito Nelson</dc:creator><cp:lastModifiedBy>BetPlaycito Nelson</cp:lastModifiedBy>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>'
        "</cp:coreProperties>"
    )
    app_props = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>BetPlaycito Nelson</Application></Properties>'
    )
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "".join(content_types))
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("docProps/core.xml", core)
        archive.writestr("docProps/app.xml", app_props)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", "".join(workbook_rels))
        archive.writestr("xl/styles.xml", styles)
        for index, (_, rows) in enumerate(sheets, 1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _xlsx_sheet(rows))
    return stream.getvalue()


class BetPlaycitoHTTPServer(ThreadingHTTPServer):
    """Servidor en localhost con hilos daemon y referencia a la aplicación."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], app: BetPlaycitoApp) -> None:
        self.app = app
        super().__init__(address, BetPlaycitoHandler)


class BetPlaycitoHandler(BaseHTTPRequestHandler):
    server_version = "BetPlaycito"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    @property
    def app(self) -> BetPlaycitoApp:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.client_address[0], fmt % args)

    def do_GET(self) -> None:  # noqa: N802 - nombre exigido por BaseHTTPRequestHandler
        self._handle_request("GET")

    def do_HEAD(self) -> None:  # noqa: N802
        self._handle_request("HEAD")

    def do_POST(self) -> None:  # noqa: N802
        self._handle_request("POST")

    def do_PATCH(self) -> None:  # noqa: N802
        self._handle_request("PATCH")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._handle_request("OPTIONS")

    def do_PUT(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_DELETE(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def _method_not_allowed(self) -> None:
        self._send_error(
            APIError(
                HTTPStatus.METHOD_NOT_ALLOWED,
                "method_not_allowed",
                "Método HTTP no permitido.",
                headers={"Allow": "GET, HEAD, POST, PATCH, OPTIONS"},
            )
        )

    def _handle_request(self, method: str) -> None:
        try:
            self._validate_host()
            if method in {"POST", "PATCH", "PUT", "DELETE"}:
                self._validate_origin()
            if method == "OPTIONS":
                self._send_bytes(
                    HTTPStatus.NO_CONTENT,
                    b"",
                    "text/plain; charset=utf-8",
                    headers={"Allow": "GET, HEAD, POST, PATCH, OPTIONS"},
                )
                return
            parsed = urllib.parse.urlsplit(self.path)
            if parsed.path.startswith("/api/") or parsed.path == "/api":
                self._dispatch_api(method, parsed)
            elif method in {"GET", "HEAD"}:
                self._serve_static(parsed.path, head_only=method == "HEAD")
            else:
                raise APIError(404, "not_found", "Ruta no encontrada.")
        except APIError as exc:
            self._send_error(exc)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            LOGGER.exception("Error interno al procesar %s %s", method, self.path)
            try:
                self._send_error(
                    APIError(500, "internal_error", "Ocurrió un error interno inesperado.")
                )
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _validate_host(self) -> None:
        host = self.headers.get("Host")
        if not host or len(host) > 255 or any(char in host for char in "\r\n/\\"):
            raise APIError(400, "invalid_host", "Encabezado Host no válido.")
        try:
            parsed = urllib.parse.urlsplit(f"//{host}")
            hostname = (parsed.hostname or "").lower()
            port = parsed.port
        except ValueError as exc:
            raise APIError(400, "invalid_host", "Encabezado Host no válido.") from exc
        expected_port = int(self.server.server_address[1])
        if hostname not in {"127.0.0.1", "localhost"} or (port or 80) != expected_port:
            raise APIError(403, "host_not_allowed", "El servicio solo admite acceso local.")

    def _validate_origin(self) -> None:
        origin = self.headers.get("Origin")
        if origin is None:
            return
        try:
            parsed = urllib.parse.urlsplit(origin)
            hostname = (parsed.hostname or "").lower()
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except ValueError as exc:
            raise APIError(403, "origin_not_allowed", "Origen no permitido.") from exc
        if (
            parsed.scheme != "http"
            or hostname not in {"127.0.0.1", "localhost"}
            or port != int(self.server.server_address[1])
        ):
            raise APIError(403, "origin_not_allowed", "Origen no permitido.")

    def _security_headers(self, *, api: bool = False) -> dict[str, str]:
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            "Content-Security-Policy": (
                "default-src 'self'; base-uri 'self'; object-src 'none'; "
                "frame-ancestors 'none'; form-action 'self'; "
                "img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                "script-src 'self'; connect-src 'self'"
            ),
            "Cache-Control": "no-store" if api else "no-cache",
        }

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        content_type: str,
        *,
        headers: Mapping[str, str] | None = None,
        api: bool = False,
        head_only: bool = False,
    ) -> None:
        self.send_response(int(status))
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        response_headers = self._security_headers(api=api)
        response_headers.update(headers or {})
        for key, value in response_headers.items():
            self.send_header(key, value)
        self.end_headers()
        if not head_only and body:
            self.wfile.write(body)

    def _send_json(
        self,
        status: int,
        data: Any,
        *,
        headers: Mapping[str, str] | None = None,
        head_only: bool = False,
    ) -> None:
        body = json.dumps(
            {"ok": True, "data": data}, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        self._send_bytes(
            status,
            body,
            "application/json; charset=utf-8",
            headers=headers,
            api=True,
            head_only=head_only,
        )

    def _send_error(self, error: APIError) -> None:
        self.close_connection = True
        payload: dict[str, Any] = {
            "ok": False,
            "error": {"code": error.code, "message": error.message},
        }
        if error.fields:
            payload["error"]["fields"] = error.fields
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_bytes(
            error.status,
            body,
            "application/json; charset=utf-8",
            headers={**error.headers, "Connection": "close"},
            api=True,
            head_only=self.command == "HEAD",
        )

    def _read_json(self, *, maximum: int = MAX_JSON_BYTES) -> dict[str, Any]:
        if self.headers.get("Transfer-Encoding"):
            raise APIError(400, "unsupported_encoding", "No se admite Transfer-Encoding.")
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise APIError(415, "json_required", "Se requiere Content-Type application/json.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise APIError(400, "invalid_length", "Content-Length no válido.") from exc
        if length <= 0:
            raise APIError(400, "empty_body", "El cuerpo JSON está vacío.")
        if length > maximum:
            raise APIError(413, "payload_too_large", "El cuerpo JSON es demasiado grande.")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise APIError(400, "invalid_json", "El cuerpo JSON no es válido.") from exc
        if not isinstance(payload, dict):
            raise APIError(422, "object_required", "El JSON debe contener un objeto.")
        return payload

    def _session_token(self) -> str | None:
        raw = self.headers.get("Cookie")
        if not raw or len(raw) > 4096:
            return None
        cookie = SimpleCookie()
        try:
            cookie.load(raw)
        except Exception:
            return None
        morsel = cookie.get(COOKIE_NAME)
        return morsel.value if morsel else None

    def _require_user(self) -> dict[str, Any]:
        user = self.app.session_user(self._session_token())
        if user is None:
            raise APIError(401, "unauthenticated", "Debe iniciar sesión.")
        return user

    @staticmethod
    def _cookie_header(token: str, expires_at: int) -> str:
        max_age = max(0, expires_at - utc_epoch())
        return (
            f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict; "
            f"Max-Age={max_age}; Expires={formatdate(expires_at, usegmt=True)}"
        )

    @staticmethod
    def _clear_cookie_header() -> str:
        return (
            f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0; "
            "Expires=Thu, 01 Jan 1970 00:00:00 GMT"
        )

    @staticmethod
    def _parse_team_ids(query: Mapping[str, list[str]]) -> list[int]:
        pieces: list[str] = []
        for raw in query.get("team_ids", []):
            pieces.extend(raw.split(","))
        result: list[int] = []
        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            try:
                value = int(piece)
            except ValueError as exc:
                raise APIError(422, "validation_error", "team_ids contiene un valor inválido.") from exc
            if not 1 <= value <= MAX_SQLITE_ID:
                raise APIError(422, "validation_error", "team_ids contiene un valor inválido.")
            result.append(value)
        return result

    @staticmethod
    def _query_int(
        query: Mapping[str, list[str]], key: str, default: int, minimum: int, maximum: int
    ) -> int:
        raw = query.get(key, [str(default)])[-1]
        try:
            value = int(raw)
        except ValueError as exc:
            raise APIError(422, "validation_error", f"{key} debe ser un entero.") from exc
        if not minimum <= value <= maximum:
            raise APIError(
                422, "validation_error", f"{key} debe estar entre {minimum} y {maximum}."
            )
        return value

    def _dispatch_api(self, method: str, parsed: urllib.parse.SplitResult) -> None:
        path = parsed.path.rstrip("/") or "/api"
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if method in {"GET", "HEAD"}:
            self._api_get(path, query, head_only=method == "HEAD")
            return
        if method == "POST":
            self._api_post(path, query)
            return
        if method == "PATCH":
            self._api_patch(path)
            return
        raise APIError(405, "method_not_allowed", "Método no permitido para esta ruta.")

    def _api_get(
        self, path: str, query: Mapping[str, list[str]], *, head_only: bool
    ) -> None:
        if path == "/api/health":
            connection = self.app.database.connect()
            try:
                check = connection.execute("PRAGMA quick_check").fetchone()[0]
            finally:
                connection.close()
            self._send_json(
                200,
                {
                    "status": "ok" if check == "ok" else "degraded",
                    "database": check,
                    "setup_required": self.app.setup_required,
                    "version": __version__,
                },
                head_only=head_only,
            )
            return
        if path == "/api/setup/status":
            self._send_json(
                200,
                {
                    "setup_required": self.app.setup_required,
                    "token_required": self.app.setup_required,
                },
                head_only=head_only,
            )
            return
        user = self._require_user()
        if path == "/api/state":
            self._send_json(200, self.app.state(user), head_only=head_only)
            return
        if path == "/api/teams":
            include_archived = query.get("include_archived", ["0"])[-1].lower() in {
                "1",
                "true",
                "yes",
            }
            self._send_json(
                200,
                {"items": self.app.list_teams(include_archived=include_archived)},
                head_only=head_only,
            )
            return
        if path == "/api/dashboard":
            team_ids = self._parse_team_ids(query)
            self._send_json(200, self.app.dashboard(team_ids), head_only=head_only)
            return
        if path == "/api/history":
            page = self._query_int(query, "page", 1, 1, 1_000_000)
            page_size = self._query_int(query, "page_size", 25, 1, 200)
            item_type = query.get("type", ["all"])[-1]
            if item_type not in {"all", "adjustment", "match"}:
                raise APIError(422, "validation_error", "type debe ser all, adjustment o match.")
            self._send_json(
                200,
                self.app.history(
                    page=page,
                    page_size=page_size,
                    item_type=item_type,
                    team_ids=self._parse_team_ids(query),
                ),
                head_only=head_only,
            )
            return
        if path == "/api/backups":
            self._send_json(200, {"items": self.app.list_backups()}, head_only=head_only)
            return
        backup_match = re.fullmatch(r"/api/backups/([^/]+)", path)
        if backup_match:
            filename = urllib.parse.unquote(backup_match.group(1))
            backup = self.app.backup_path(filename)
            self._send_bytes(
                200,
                backup.read_bytes(),
                "application/vnd.sqlite3",
                headers={"Content-Disposition": f'attachment; filename="{backup.name}"'},
                api=True,
                head_only=head_only,
            )
            return
        if path == "/api/export":
            output_format = query.get("format", ["json"])[-1].lower()
            payload = self.app.export_payload()
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            if output_format == "json":
                body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                content_type = "application/json; charset=utf-8"
                filename = f"betplaycito-{stamp}.json"
            elif output_format == "csv":
                body = export_csv(payload)
                content_type = "text/csv; charset=utf-8"
                filename = f"betplaycito-{stamp}.csv"
            elif output_format == "xlsx":
                body = export_xlsx(payload, self.app.dashboard([]))
                content_type = (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                filename = f"betplaycito-{stamp}.xlsx"
            else:
                raise APIError(422, "unsupported_format", "format debe ser json, csv o xlsx.")
            self._send_bytes(
                200,
                body,
                content_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                api=True,
                head_only=head_only,
            )
            return
        raise APIError(404, "not_found", "Ruta API no encontrada.")

    def _api_post(self, path: str, query: Mapping[str, list[str]]) -> None:
        del query
        if path == "/api/login":
            if self.app.setup_required:
                raise APIError(503, "setup_required", "Debe completar la configuración inicial.")
            payload = self._read_json()
            username = payload.get("username", payload.get("usuario"))
            password = payload.get("password", payload.get("contrasena"))
            if not isinstance(username, str) or len(username) > 128:
                raise APIError(401, "invalid_credentials", "Usuario o contraseña incorrectos.")
            user, token, expires = self.app.authenticate_credentials(
                username, password, self.client_address[0]
            )
            self._send_json(
                200,
                {"user": user, "expires_at": expires},
                headers={"Set-Cookie": self._cookie_header(token, expires)},
            )
            return
        if path == "/api/setup":
            payload = self._read_json()
            user = self.app.complete_setup(payload)
            self._send_json(201, {"user": user, "login_required": True})
            return
        user = self._require_user()
        if path == "/api/logout":
            self.app.revoke_session(self._session_token())
            self._send_json(
                200,
                {"logged_out": True},
                headers={"Set-Cookie": self._clear_cookie_header()},
            )
            return
        if path == "/api/teams":
            team = self.app.create_team(self._read_json())
            self._send_json(201, team)
            return
        if path == "/api/adjustments":
            adjustment = self.app.create_adjustment(self._read_json(), user)
            selected = [adjustment["team_id"]] if adjustment["team_id"] is not None else []
            self._send_json(
                201,
                {"adjustment": adjustment, "dashboard": self.app.dashboard(selected)},
            )
            return
        if path == "/api/matches":
            match = self.app.create_match(self._read_json(), user)
            selected = [
                item
                for item in (match["home_team_id"], match["away_team_id"])
                if item is not None
            ]
            self._send_json(201, {"match": match, "dashboard": self.app.dashboard(selected)})
            return
        if path == "/api/password":
            token, expires = self.app.change_password(user, self._read_json())
            self._send_json(
                200,
                {"changed": True, "expires_at": expires},
                headers={"Set-Cookie": self._cookie_header(token, expires)},
            )
            return
        if path == "/api/backup":
            self._send_json(201, self.app.create_backup())
            return
        if path == "/api/restore":
            restored = self.app.restore_payload(
                self._read_json(maximum=MAX_RESTORE_BYTES), user
            )
            self._send_json(200, restored)
            return
        if path == "/api/shutdown":
            if self.headers.get("Content-Length", "0") != "0":
                self._read_json()
            self.close_connection = True
            self._send_json(202, {"shutting_down": True})
            threading.Thread(
                target=self.server.shutdown,  # type: ignore[attr-defined]
                name="betplaycito-shutdown",
                daemon=True,
            ).start()
            return
        raise APIError(404, "not_found", "Ruta API no encontrada.")

    def _api_patch(self, path: str) -> None:
        self._require_user()
        team_match = re.fullmatch(r"/api/teams/(\d+)", path)
        if team_match:
            team_id = int(team_match.group(1))
            if not 1 <= team_id <= MAX_SQLITE_ID:
                raise APIError(404, "team_not_found", "El equipo no existe.")
            self._send_json(200, self.app.archive_team(team_id, self._read_json()))
            return
        raise APIError(404, "not_found", "Ruta API no encontrada.")

    def _serve_static(self, request_path: str, *, head_only: bool) -> None:
        decoded = urllib.parse.unquote(request_path)
        if "\x00" in decoded or "\\" in decoded:
            raise APIError(400, "invalid_path", "Ruta no válida.")
        relative = PurePosixPath(decoded.lstrip("/"))
        if any(part in {"", ".", ".."} for part in relative.parts):
            if decoded not in {"", "/"}:
                raise APIError(400, "invalid_path", "Ruta no válida.")
        parts = [part for part in relative.parts if part not in {"", "."}]
        if not parts:
            parts = ["index.html"]
        try:
            root = resources.files(__package__).joinpath("web")
            target = root.joinpath(*parts)
            if not target.is_file() and "." not in parts[-1]:
                target = root.joinpath("index.html")
            if not target.is_file():
                raise FileNotFoundError
            body = target.read_bytes()
            effective_name = target.name
        except (FileNotFoundError, ModuleNotFoundError, OSError):
            raise APIError(404, "not_found", "Recurso no encontrado.")
        suffix = PurePosixPath(effective_name).suffix.lower()
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".ico": "image/x-icon",
            ".woff2": "font/woff2",
        }.get(suffix, mimetypes.guess_type(effective_name)[0] or "application/octet-stream")
        cache = "no-cache" if suffix == ".html" else "public, max-age=3600"
        self._send_bytes(
            200,
            body,
            content_type,
            headers={"Cache-Control": cache},
            head_only=head_only,
        )


def _existing_server_is_ready(base_url: str) -> bool:
    try:
        request = urllib.request.Request(
            f"{base_url}api/health", headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=1.5) as response:
            payload = json.loads(response.read(64 * 1024).decode("utf-8"))
            data = payload.get("data")
            return (
                response.status == 200
                and payload.get("ok") is True
                and isinstance(data, dict)
                and data.get("status") == "ok"
                and data.get("database") == "ok"
                and isinstance(data.get("version"), str)
            )
    except (OSError, UnicodeError, ValueError):
        return False


def run_server(
    *,
    port: int = 8765,
    data_dir: Path | None = None,
    config_path: Path | None = None,
    open_browser: bool = True,
) -> int:
    """Inicializa la aplicación y atiende exclusivamente en ``127.0.0.1``."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    requested_url = f"http://{HOST}:{port}/" if port else None
    if requested_url and _existing_server_is_ready(requested_url):
        LOGGER.info("BetPlaycito ya estaba abierto en %s", requested_url)
        if open_browser:
            webbrowser.open(requested_url, new=1)
        return 0
    app = BetPlaycitoApp(data_dir=data_dir, config_path=config_path)
    try:
        server = BetPlaycitoHTTPServer((HOST, port), app)
    except OSError:
        if requested_url and _existing_server_is_ready(requested_url):
            LOGGER.info("BetPlaycito ya estaba abierto en %s", requested_url)
            if open_browser:
                webbrowser.open(requested_url, new=1)
            return 0
        raise
    actual_port = int(server.server_address[1])
    url = f"http://{HOST}:{actual_port}/"
    LOGGER.info("BetPlaycito %s disponible en %s", __version__, url)
    LOGGER.info("Base de datos: %s", app.database.path)
    LOGGER.info("Respaldos: %s", app.database.backup_dir)
    if open_browser:
        timer = threading.Timer(0.5, lambda: webbrowser.open(url, new=1))
        timer.daemon = True
        timer.start()
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        LOGGER.info("Cierre solicitado por teclado.")
    finally:
        server.server_close()
        LOGGER.info("BetPlaycito cerrado.")
    return 0
