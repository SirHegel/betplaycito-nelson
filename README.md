# BetPlaycito Nelson

Dashboard local para registrar tendencias históricas de fútbol mediante sumadores y compararlas en gráficos circulares. La aplicación funciona sin servicios externos, conserva sus datos en SQLite y deja un historial de cada ajuste.

> [!IMPORTANT]
> Los porcentajes son un resumen descriptivo de los registros ingresados. No garantizan resultados futuros, no sustituyen un análisis estadístico y no deben interpretarse como asesoría para apostar.

## Funciones principales

- Acceso local con una cuenta administradora.
- Contexto global y equipos opcionales, sin exigir rival ni un partido detallado.
- Sumadores `+` y `−`, además de carga por cantidad para lotes grandes.
- Registro detallado de partido opcional; el sistema deriva automáticamente las variables compatibles.
- Seis grupos de variables:
  - resultado: local, empate o visitante;
  - total de goles: más o menos de 2.5;
  - ambos equipos marcan: Gol-Gol o No Gol;
  - tiros de esquina: más o menos de 9.5;
  - tiros al arco: más o menos de 9.5;
  - el local marcó o no marcó.
- Porcentajes, cantidades y tamaño de muestra en gráficos tipo dona.
- Explicación de la opción seleccionada y su diferencia frente a la alternativa más fuerte.
- Guardado inmediato y un historial de movimientos que no se reescribe.
- Respaldo y exportación de datos en los formatos ofrecidos por la aplicación.

## Requisitos

- Linux con Python 3.11 o posterior.
- Un navegador web moderno.
- No se requieren paquetes de Python de terceros para ejecutar la aplicación.

## Configuración privada

El repositorio público no incluye credenciales. Antes del primer inicio, copie la plantilla y defina una cuenta propia:

```bash
cp config.example.json config.local.json
```

La plantilla admite una contraseña inicial en texto plano:

```json
{
  "admin_username": "SU_USUARIO_LOCAL",
  "admin_password": "UNA_CONTRASENA_LARGA_Y_UNICA"
}
```

`config.local.json` está excluido por [`.gitignore`](.gitignore). No lo agregue al repositorio, no lo adjunte a reportes de errores y no reutilice una contraseña importante.

Es más seguro generar una derivación PBKDF2 de forma interactiva y guardar `admin_password_hash` en vez de `admin_password`:

```bash
PYTHONPATH=src python3 -m betplaycito --hash-password
chmod 600 config.local.json
```

El comando no muestra la contraseña mientras se escribe. Pegue únicamente la cadena generada en su configuración:

```json
{
  "admin_username": "SU_USUARIO_LOCAL",
  "admin_password_hash": "PBKDF2_GENERADO_LOCALMENTE"
}
```

Como alternativa, si inicia sin configuración y aún no existe un administrador, la consola muestra un código aleatorio de configuración de una sola vez. La pantalla inicial permite usarlo para crear la cuenta. No comparta ese código.

## Construcción

Desde la raíz del proyecto:

```bash
bash scripts/build.sh
```

El script valida los módulos y crea:

- `dist/BetPlaycito-Nelson.pyz`;
- `dist/Iniciar BetPlaycito Nelson.sh`;
- `dist/betplaycito-nelson.svg`;
- `dist/BetPlaycito Nelson.desktop.example`;
- `dist/config.example.json`;
- `dist/LEEME.md`.

Copie o cree su `config.local.json` en la misma carpeta que el archivo `.pyz`, y abra `Iniciar BetPlaycito Nelson.sh`. El servicio se limita al equipo local y abre la interfaz en el navegador.

Para ejecutar desde el código fuente, consulte el flujo vigente en [Arquitectura](docs/ARQUITECTURA.md#ejecución-y-empaquetado).

## Datos y copias de seguridad

SQLite es la fuente principal de verdad. De forma predeterminada se guarda en `datos/betplaycito.db`. Antes de abrir una base existente, el aplicativo crea una copia fechada en `respaldos/`. También permite crear una copia SQLite a petición, descargar un respaldo JSON restaurable y exportar CSV o XLSX.

Los archivos de hoja de cálculo son exportaciones, no deben editarse esperando que la base cambie automáticamente.

- No borre la base de datos ni las carpetas `datos/` y `respaldos/`.
- Guarde copias de respaldo en otra unidad de forma periódica.
- Revise que un respaldo sea legible antes de depender de él.
- Una resta corrige el total mediante un nuevo movimiento; no elimina el movimiento anterior.

Consulte [Modelo de datos](docs/MODELO-DE-DATOS.md) para conocer las reglas de integridad y [Manual de uso](docs/MANUAL-DE-USO.md#respaldos-y-exportaciones) para el procedimiento operativo.

## Por qué no se publica directamente en Vercel

Esta versión usa una base SQLite local. El sistema de archivos de una función de Vercel es efímero y no ofrece la persistencia que necesita la aplicación. Una versión alojada requeriría, como mínimo, autenticación preparada para Internet, HTTPS y migrar los datos a una base administrada como PostgreSQL.

No exponga este servidor local mediante reenvío de puertos, túneles o un proxy público. Consulte [Seguridad](SECURITY.md).

## Documentación

- [Arquitectura](docs/ARQUITECTURA.md)
- [Modelo de datos](docs/MODELO-DE-DATOS.md)
- [Manual de uso](docs/MANUAL-DE-USO.md)
- [Política y recomendaciones de seguridad](SECURITY.md)
- [Guía para contribuir](CONTRIBUTING.md)

## Licencia

Este proyecto se distribuye bajo la [licencia MIT](LICENSE).
