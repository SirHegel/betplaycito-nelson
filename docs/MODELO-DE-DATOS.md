# Modelo de datos · aplicación 1.1.0

[Volver al README](../README.md) · [Ver arquitectura](ARQUITECTURA.md)

## Principios

- SQLite es la fuente principal de verdad.
- Los datos reales pertenecen al perfil local del usuario; no al ejecutable, al instalador ni al navegador.
- Los contadores visibles se derivan de movimientos; no son cifras sueltas guardadas en el navegador.
- Un movimiento confirmado es inmutable.
- Una corrección se representa mediante un movimiento compensatorio.
- Ningún total por equipo, variable y opción puede quedar negativo.
- El total manual global de cada opción tampoco puede quedar negativo.
- Las claves de variables y opciones forman un catálogo cerrado validado por el servidor.

## Esquema físico v1

La aplicación está en la versión **1.1.0**, mientras que el esquema SQLite continúa en la versión **1**. Son numeraciones distintas: una actualización visual o de empaquetado no obliga a cambiar la estructura de la base.

| Tabla | Responsabilidad |
| --- | --- |
| `schema_migrations` | Versiones de esquema aplicadas y su fecha |
| `app_meta` | Metadatos técnicos, incluida la versión de aplicación |
| `users` | Administrador, derivación de contraseña y estado |
| `sessions` | Sesiones revocables y con vencimiento |
| `teams` | Equipos opcionales activos o archivados |
| `adjustments` | Eventos manuales positivos o negativos |
| `matches` | Partidos detallados opcionales |
| `match_categories` | Categorías derivadas de cada partido |

SQLite conserva además `PRAGMA user_version = 1`. Las claves foráneas se habilitan en cada conexión y la base usa WAL, `synchronous = FULL` y un tiempo de espera para escrituras concurrentes.

## Ubicación y persistencia por plataforma

Los paquetes nativos separan el programa de la información mutable. PyInstaller puede extraer temporalmente un ejecutable de un archivo, pero la base nunca se crea dentro de esa extracción ni dentro del `.exe`, `.app`, `.dmg` o `.deb`.

| Ejecución | Base SQLite | Respaldos | Configuración opcional |
| --- | --- | --- | --- |
| Windows instalado o portable | `%LOCALAPPDATA%\BetPlaycito Nelson\betplaycito.db` | `%LOCALAPPDATA%\BetPlaycito Nelson\respaldos\` | `%APPDATA%\BetPlaycito Nelson\config.local.json` |
| macOS Apple Silicon o Intel | `~/Library/Application Support/BetPlaycito Nelson/betplaycito.db` | `~/Library/Application Support/BetPlaycito Nelson/respaldos/` | `~/Library/Application Support/BetPlaycito Nelson/config.local.json` |
| Ubuntu/Debian | `~/.local/share/betplaycito-nelson/betplaycito.db` | `~/.local/share/betplaycito-nelson/respaldos/` | `~/.config/betplaycito-nelson/config.local.json` |
| Código fuente o zipapp | `datos/betplaycito.db` bajo la raíz del proyecto | `respaldos/` bajo la raíz | `config.local.json` bajo la raíz |

En Linux, `XDG_DATA_HOME` y `XDG_CONFIG_HOME` reemplazan sus rutas predeterminadas cuando apuntan dentro del perfil del usuario. Los argumentos `--data-dir` y `--config`, o sus variables de entorno equivalentes, también pueden reemplazar ubicaciones en una ejecución avanzada, siempre dentro del perfil o de la carpeta de la aplicación.

Actualizar, reinstalar o desinstalar el programa no elimina deliberadamente los directorios del perfil. Cada cuenta de Windows, macOS o Linux obtiene una base independiente. Por tanto:

- copiar solo el ejecutable portable a otro computador no transfiere estadísticas;
- sustituir la versión 1.1.0 por una posterior no debe reiniciar los contadores;
- para migrar datos se debe exportar un JSON restaurable o realizar una copia coherente con la aplicación cerrada;
- una copia improvisada de `betplaycito.db` mientras WAL está activo puede quedar incompleta.

## Entidades

### Administrador

La tabla `users` representa la cuenta local autorizada: `id`, `username`, `password_hash`, `active`, `created_at` y `updated_at`. `username` es único sin distinguir mayúsculas y minúsculas. La contraseña en texto plano no pertenece a la base.

Cuando una base nueva no contiene administradores y no existe una configuración que la reemplace, la versión 1.1.0 crea esta credencial pública predeterminada:

```text
Usuario: NelsonRuiz
Contraseña: 1075271744
```

El backend incluye una derivación PBKDF2 de la contraseña predeterminada y escribe únicamente el hash en `users`; el texto `1075271744` no se inserta en SQLite. Al cambiar la contraseña desde **Seguridad**, se guarda una nueva derivación y la credencial pública deja de funcionar para esa base.

Esta inicialización solo ocurre cuando no hay ningún administrador. Abrir una base existente, actualizar o reinstalar la aplicación no reemplaza el usuario ni restablece su contraseña. Antes de crear la primera base, una instalación avanzada puede proporcionar `admin_username` y `admin_password_hash` mediante `config.local.json` o variables de entorno. `BETPLAYCITO_REQUIRE_SETUP=1` conserva el flujo alternativo con código de configuración de una sola vez. Una vez creado el usuario, cambiar el archivo de configuración no modifica la fila existente. Consulte [Seguridad](../SECURITY.md).

### Equipo

La tabla `teams` es el contexto opcional para separar estadísticas. Incluye `id`, `name`, `normalized_name`, `archived`, `created_at` y `updated_at`.

- No representa un enfrentamiento.
- No requiere rival.
- Archivar oculta el equipo de la operación diaria, pero conserva sus movimientos.
- El contexto general se representa de forma explícita por la implementación o mediante la ausencia de equipo; no debe confundirse con un equipo real llamado “General”.

### Ajuste manual

Cada fila de `adjustments` es un registro inmutable de una modificación manual:

| Campo | Propósito |
| --- | --- |
| `id` | Distinguir el evento de forma estable |
| `team_id` | Equipo opcional; `NULL` significa Global |
| `variable_key` | Categoría concreta afectada |
| `delta` | Entero positivo o negativo, distinto de cero |
| `created_at` | Momento registrado por el servidor |
| `created_by` | Administrador que realizó el cambio |
| `note` | Contexto opcional de una carga o corrección |

`delta` está limitado entre −10 000 y 10 000 y no puede ser cero. El historial se ordena por `created_at` e `id`. El cliente no proporciona ni puede alterar la fecha definitiva del servidor.

### Partido detallado

`matches` almacena un registro opcional con:

- fecha de juego;
- identificador y nombre conservado de local/visitante;
- goles de ambos equipos;
- esquinas de ambos lados, opcionales como pareja completa;
- tiros al arco de ambos lados, opcionales como pareja completa;
- nota, fecha de creación y administrador creador.

`match_categories` relaciona el partido con cada `variable_key` derivada. Su clave primaria compuesta `(match_id, variable_key)` impide duplicar una categoría para el mismo partido.

El marcador siempre deriva Resultado, Goles 2.5, Ambos marcan y Local marcó. Esquinas y Tiros al arco se derivan únicamente cuando se ingresó la pareja de valores correspondiente.

### Sesión

La tabla `sessions` guarda `user_id`, un SHA-256 del token aleatorio, creación, último uso, vencimiento y revocación. Nunca guarda la contraseña ni el token de cookie en claro. La duración vigente de una sesión es de 12 horas.

## Separación entre la aplicación y la vista `file://`

La aplicación instalada sirve la interfaz desde `http://127.0.0.1:8765/` y las escrituras pasan por la API local, sus validaciones y transacciones SQLite. El navegador no es la fuente de verdad.

Si se abre `src/betplaycito/web/index.html` directamente, el protocolo es `file://` y el frontend entra en **Vista de demostración**. En ese modo:

- carga un conjunto fijo de equipos, movimientos y porcentajes ficticios;
- muestra un banner permanente de solo lectura;
- no ejecuta solicitudes `fetch` hacia la API;
- rechaza las acciones de escritura y no usa SQLite, `localStorage` ni otra persistencia;
- no lee ni altera la base real del perfil del usuario.

Los conteos de la demostración no deben incluirse en respaldos, pruebas de migración ni diagnósticos de pérdida de datos. Para consultar o modificar datos reales, se debe iniciar el ejecutable o la aplicación nativa.

## Catálogo de variables

| Clave lógica | Opciones | Número de segmentos |
| --- | --- | ---: |
| `result` | `home_win`, `draw`, `away_win` | 3 |
| `goals` | `over25`, `under25` | 2 |
| `btts` | `btts_yes`, `btts_no` | 2 |
| `local_goal` | `local_scored`, `local_blank` | 2 |
| `corners` | `corners_over95`, `corners_under95` | 2 |
| `shots_on_target` | `shots_over95`, `shots_under95` | 2 |

Las etiquetas de pantalla pueden cambiar o traducirse; las claves almacenadas deben permanecer estables para no romper datos anteriores.

## Totales derivados

Para un contexto y una categoría concreta, el total visible combina dos fuentes:

```text
total = SUM(adjustments.delta) + COUNT(match_categories coincidentes)
```

Sin filtro, la vista global incluye ajustes sin equipo, ajustes de todos los equipos y todos los partidos. Con filtro, incluye ajustes asignados a los equipos seleccionados y partidos en los que cualquiera de ellos aparezca como local o visitante. La consulta combinada usa una condición `OR`, por lo que un partido entre dos equipos seleccionados se cuenta una sola vez.

El tamaño de muestra de una variable es la suma de los totales de sus opciones. No existe la obligación de que Goles, Esquinas y Tiros al arco tengan el mismo tamaño de muestra, ya que se alimentan independientemente.

El indicador agregado `observations` suma los tamaños de muestra de los seis grupos; no equivale necesariamente al número de partidos únicos. El número de partidos se informa por separado.

## Invariantes transaccionales

Al aplicar un decremento:

1. se inicia una transacción de escritura;
2. se obtiene el total aplicable: el del equipo cuando existe `team_id`, o el agregado manual completo para una corrección Global;
3. se rechaza la operación si `total + delta < 0`;
4. se inserta el movimiento;
5. se confirma la transacción.

Un ajuste negativo con `team_id = NULL` es una corrección del agregado Global: puede compensar ajustes positivos asociados a equipos, pero no aparece al consultar un equipo individual. Por eso su saldo aislado no se interpreta como un contador independiente. La validación de respaldo reproduce la misma regla mediante un balance global por variable y balances separados para cada `team_id` no nulo.

Esta comprobación debe hacerse en el servidor, incluso si la interfaz ya deshabilita el botón `−` en cero. La validación solo en JavaScript no protege la base.

Otras reglas:

- el delta debe ser entero y distinto de cero;
- variable y opción deben ser una combinación permitida;
- el equipo debe existir y estar disponible para nuevas cargas;
- los nombres de equipo se normalizan y no deben duplicarse de forma ambigua;
- cargas muy grandes deben respetar el límite definido por el servidor;
- fechas y claves se generan o validan en el backend.

## Historial y eliminación

No se proporciona un borrado silencioso de ajustes ni partidos. Para corregir `+25`, el usuario puede registrar `−25`; ambos ajustes permanecen visibles. Un equipo se archiva en lugar de borrar sus registros.

Si en el futuro se incorpora una función administrativa de purga, debe estar separada de la operación normal, requerir confirmación y generar un respaldo previo. No forma parte del flujo actual.

## Respaldo y exportación

El respaldo JSON restaurable debe preservar como mínimo:

- versión del formato/esquema;
- equipos y su estado;
- todos los ajustes, partidos, categorías y sus identificadores;
- fechas necesarias para auditoría;
- configuración funcional no sensible.

CSV y XLSX son apropiados para análisis tabular, pero pueden perder relaciones, tipos o metadatos y no son restaurables. El XLSX generado contiene las hojas `Resumen`, `Equipos`, `Ajustes` y `Partidos`.

La interfaz identifica JSON como respaldo integral y valida versión, límites, referencias, claves e invariantes antes de restaurarlo. La restauración reemplaza equipos, ajustes, partidos y categorías, conserva la cuenta administradora actual, mantiene los identificadores del respaldo y recalcula las categorías de cada partido. Antes del reemplazo crea una copia SQLite de seguridad.

Una copia `.db` creada por la aplicación usa la API de respaldo de SQLite y supera `PRAGMA integrity_check` antes de considerarse válida.

Las credenciales, secretos de sesión y hashes no deben incluirse en exportaciones ordinarias.

## Evolución del esquema

Todo cambio futuro debe incrementar la versión de esquema y aplicar migraciones dentro de una transacción. Antes de migrar:

1. cerrar escrituras nuevas;
2. crear y comprobar una copia coherente;
3. aplicar la migración;
4. verificar invariantes y versión;
5. conservar una ruta de recuperación.

No edite manualmente la base SQLite con una hoja de cálculo.
