# Arquitectura

[Volver al README](../README.md)

## Objetivo y límites

BetPlaycito Nelson es una aplicación local y monousuario. Registra cantidades agregadas, calcula frecuencias y presenta tendencias. No obtiene resultados desde Internet ni ejecuta un modelo predictivo.

Un equipo es un contexto opcional de análisis. Un ajuste manual pertenece al contexto global o a un equipo y no exige indicar rival. Además existe un registro detallado de partido opcional para quien sí quiera ingresar marcador y estadísticas de ambos lados.

## Vista general

```text
Navegador en el mismo equipo
          │ HTTP en interfaz de bucle local
          ▼
Servidor Python (biblioteca estándar)
  ├── autenticación y sesión
  ├── validación y reglas de negocio
  ├── cálculo de porcentajes y explicaciones
  ├── clasificación automática de partidos opcionales
  ├── API local y archivos de interfaz
  └── respaldo/exportación
          │ transacciones
          ▼
       SQLite
  ├── administrador
  ├── equipos
  ├── ajustes y partidos inmutables
  ├── categorías derivadas de partidos
  └── sesiones/configuración técnica
```

### Interfaz

HTML, CSS y JavaScript se sirven desde el mismo proceso local. La interfaz muestra los gráficos, administra el contexto seleccionado y envía ajustes al servidor. El navegador no es la fuente de verdad: recargar o cerrar una pestaña no debe perder un movimiento ya confirmado por el servidor.

### Servidor

El backend utiliza únicamente módulos de la biblioteca estándar de Python. Sus responsabilidades son:

- escuchar solo en la interfaz de bucle local;
- autenticar la cuenta administradora;
- validar cuerpos, claves de variable y cantidades;
- aplicar movimientos dentro de transacciones SQLite;
- rechazar cualquier operación que deje un contador negativo;
- convertir un partido detallado en sus categorías estadísticas;
- calcular totales y porcentajes desde los movimientos guardados;
- generar copias de seguridad y exportaciones;
- servir la interfaz web incluida en el paquete.

### Persistencia

SQLite es la fuente principal de verdad. Cada cambio de contador se inserta en `adjustments`; no se actualiza ni elimina un registro histórico para ocultar una corrección. Un decremento crea un segundo movimiento negativo. Los partidos opcionales se guardan en `matches` y sus categorías calculadas en `match_categories`.

Las escrituras deben usar transacciones. Los totales se obtienen sumando los deltas y la aplicación valida que el resultado no sea menor que cero. Consulte [Modelo de datos](MODELO-DE-DATOS.md).

Los ejecutables nativos guardan la base fuera del programa, dentro del perfil del usuario: `%LOCALAPPDATA%\BetPlaycito Nelson` en Windows, `~/Library/Application Support/BetPlaycito Nelson` en macOS y la ruta XDG `~/.local/share/betplaycito-nelson` en Linux. Así, actualizar o reemplazar el ejecutable no sustituye la base.

### Cuenta inicial

Una base nueva crea automáticamente la cuenta pública de arranque `NelsonRuiz` usando una derivación PBKDF2 incluida en el backend. El texto de la contraseña no se escribe en la base. Una configuración local o las variables de entorno pueden reemplazar esa cuenta antes de crear la base; `BETPLAYCITO_REQUIRE_SETUP=1` conserva el flujo alternativo con código de configuración de una sola vez.

## Variables de dominio

La versión actual contempla once grupos:

| Grupo | Opciones | Interpretación |
| --- | --- | --- |
| Resultado | Local / Empate / Visitante | Resultado final agregado |
| Goles 2.5 | Más / Menos | 3 o más frente a 0–2 goles totales |
| Ambos marcan | Gol-Gol / No Gol | Ambos anotaron frente a que al menos uno no anotó |
| Esquinas 9.5 | Más / Menos | 10 o más frente a 0–9 tiros de esquina totales |
| Tiros al arco 9.5 | Más / Menos | 10 o más frente a 0–9 tiros al arco totales |
| Local marcó | Sí / No | El equipo local anotó al menos un gol |
| Remates totales | +25,5 / −26,5 | Indicadores manuales separados para los dos umbrales solicitados |
| Tiros a puerta | +7,5 / −8,5 | Indicadores manuales separados para los dos umbrales solicitados |
| Tiros de esquina | +9,5 / −10,5 | Indicadores manuales separados para los dos umbrales solicitados |
| Tarjetas | +4 / −5 | Indicadores manuales separados para los dos umbrales solicitados |
| Goles por mitades | +0,5 1M / +0,5 2M / == | Más goles en primera, más goles en segunda o cantidades iguales |

El denominador se calcula por grupo de variable y por contexto. Debido a que el usuario alimenta sumadores independientes, los tamaños de muestra de dos gráficos pueden ser diferentes; esto es válido y debe hacerse visible.

Los cuatro pares de umbrales nuevos conservan literalmente las líneas solicitadas y se cargan manualmente. Como algunas líneas adyacentes se solapan en un total entero, el servidor no intenta deducirlas desde un mismo partido. El grupo de mitades sí representa tres resultados excluyentes de la comparación entre goles de la primera y la segunda mitad.

## Flujo de un ajuste manual

1. La interfaz envía el equipo/contexto, variable, opción y cantidad.
2. El servidor comprueba la sesión, el formato y el límite permitido.
3. Dentro de una transacción, calcula el total vigente.
4. Si el nuevo total sería negativo, revierte y responde con un error de validación.
5. Inserta un movimiento con delta positivo o negativo y marca de tiempo.
6. Recalcula el resumen y lo devuelve a la interfaz.
7. La interfaz actualiza gráfico, cantidades, explicación y estado de guardado.

No se debe actualizar la pantalla de forma definitiva antes de recibir confirmación del servidor.

## Flujo de un partido opcional

1. El usuario ingresa goles de local y visitante. Puede indicar equipos, fecha, esquinas, tiros al arco y nota.
2. Córners y tiros al arco deben suministrarse para ambos equipos o dejarse ambos vacíos.
3. El servidor valida los límites y comprueba que local y visitante no sean el mismo equipo.
4. `derive_match_categories` obtiene Resultado, Goles 2.5, Gol-Gol y Local marcó. Si existen datos completos, añade Esquinas 9.5 y Tiros al arco 9.5.
5. `matches` y todas sus filas de `match_categories` se insertan en una sola transacción.
6. Cada partido suma una unidad a las categorías derivadas; no crea ajustes manuales ficticios.

Al filtrar varios equipos, un partido entre dos seleccionados se cuenta una sola vez en el total combinado. En el desglose individual aparece dentro de la historia de cada equipo involucrado.

## Porcentajes y explicación

Para una opción `o` dentro de una variable `v`:

```text
porcentaje(o) = total(o) / suma(total de cada opción de v) × 100
```

- Se muestra un decimal.
- El total almacenado permanece entero; el redondeo es solo visual.
- Con denominador cero se muestra “Sin datos”.
- En variables binarias se informa la diferencia en puntos porcentuales.
- En Resultado, la opción seleccionada se compara con la alternativa de mayor porcentaje; una igualdad se indica como tal.

Estos cálculos son descriptivos. La interfaz y las exportaciones no deben llamarlos probabilidades garantizadas.

## Respaldo y recuperación

`Database.backup` usa la API de respaldo de SQLite y verifica la copia con `PRAGMA integrity_check`. La aplicación guarda automáticamente una copia fechada de una base existente antes del arranque y permite solicitar otras copias desde la interfaz. Desde el código fuente, la base predeterminada es `datos/betplaycito.db` y las copias SQLite se escriben en `respaldos/`. Los paquetes nativos usan las ubicaciones persistentes por plataforma descritas arriba.

El JSON completo es el formato de intercambio que la aplicación valida para restaurar. CSV y XLSX sirven para revisión y análisis, pero no para reconstruir por sí solos todas las relaciones. Consulte [Manual de uso](MANUAL-DE-USO.md#respaldos-y-exportaciones).

## Ejecución y empaquetado

El código fuente usa el paquete `betplaycito` dentro de `src/`. El punto de entrada empaquetado es `betplaycito.__main__:main`.

Construcción reproducible:

```bash
bash scripts/build.sh
```

El script analiza la sintaxis Python con `scripts/check_syntax.py`, comprueba JavaScript con `node --check` cuando Node está disponible y usa `zipapp` para crear `dist/BetPlaycito-Nelson.pyz`, sin descargar dependencias. Además copia el lanzador, el icono SVG, la plantilla `.desktop`, la plantilla de configuración y el archivo de lectura a `dist/`.

`scripts/build-deb.sh` crea el instalador de Ubuntu/Debian y `scripts/build-linux-native.sh` crea un ejecutable Linux autónomo con PyInstaller. El workflow `.github/workflows/release-native.yml` usa ejecutores nativos para producir el ejecutable e instalador de Windows, dos imágenes DMG de macOS —Apple Silicon e Intel—, el binario Linux x86_64 y el paquete `.deb`.

En desarrollo, una vez creado `config.local.json`, el punto de entrada puede iniciarse con:

```bash
PYTHONPATH=src python3 -m betplaycito
```

Opciones operativas relevantes:

- `--port`: puerto local; el predeterminado es `8765` y `0` elige uno libre;
- `--data-dir`: reemplaza la carpeta `datos/`;
- `--config`: reemplaza la ruta de `config.local.json`;
- `--no-browser`: evita abrir el navegador automáticamente;
- `--hash-password`: genera una derivación PBKDF2 interactiva y sale.

También existen las variables de entorno `BETPLAYCITO_DATA_DIR`, `BETPLAYCITO_BACKUP_DIR`, `BETPLAYCITO_CONFIG`, `BETPLAYCITO_ADMIN_USER`, `BETPLAYCITO_ADMIN_PASSWORD_HASH`, `BETPLAYCITO_ADMIN_PASSWORD`, `BETPLAYCITO_SETUP_TOKEN` y `BETPLAYCITO_REQUIRE_SETUP`. No guarde valores sensibles en scripts versionados.

No ejecute dos instancias contra el mismo archivo de datos salvo que la implementación lo controle explícitamente.

## Despliegue

La aplicación se diseña para `localhost`, no para hosting público. Vercel no conserva una base SQLite escrita por una función entre ejecuciones. Publicar una versión web implica una arquitectura diferente:

- PostgreSQL u otra base administrada;
- sesiones y secretos administrados fuera del repositorio;
- HTTPS, protección CSRF y límites de solicitudes adecuados para Internet;
- migraciones, observabilidad y política de copias de seguridad;
- revisión de privacidad y autorización multiusuario.

Cambiar únicamente la dirección de escucha no convierte esta aplicación local en un servicio seguro.

## Decisiones de diseño

- **SQLite en lugar de Excel:** ofrece transacciones, restricciones y consultas consistentes. Excel/CSV son salidas, no almacenamiento primario.
- **Eventos en lugar de sobrescribir contadores:** preservan el historial y permiten explicar una corrección.
- **Equipos opcionales:** satisfacen el análisis por equipo sin forzar partidos ni rivales.
- **Partidos detallados opcionales:** permiten derivar varias categorías coherentes con una sola entrada, sin quitar el flujo rápido de sumadores.
- **Biblioteca estándar:** permite crear un `.pyz` pequeño y ejecutarlo con Python sin instalar paquetes.
- **Bucle local:** reduce la superficie de ataque de una herramienta personal, aunque no sustituye otras medidas de seguridad.
