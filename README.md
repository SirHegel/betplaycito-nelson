# BetPlaycito Nelson

Dashboard local y persistente para registrar tendencias históricas de fútbol, comparar equipos y visualizar porcentajes en gráficos circulares. Funciona en Windows, macOS y Ubuntu; no necesita una cuenta en la nube ni envía los datos a servicios externos.

> [!IMPORTANT]
> Los porcentajes resumen únicamente los registros ingresados. No garantizan resultados futuros ni constituyen asesoría de apuestas.

## Descargar e instalar

La versión más reciente está en [GitHub Releases](https://github.com/SirHegel/betplaycito-nelson/releases/latest).

| Sistema | Archivo recomendado | Uso |
| --- | --- | --- |
| Windows 10/11 x64 | `BetPlaycito-Nelson-*-Windows-x64-Setup.exe` | Abrir, aceptar el permiso de instalación y seguir el asistente. |
| Windows x64 portable | `BetPlaycito-Nelson-*-Windows-x64-portable.exe` | Un solo archivo; doble clic sin instalar. |
| Mac con Apple Silicon | `BetPlaycito-Nelson-*-macOS-arm64.dmg` | Abrir la imagen y arrastrar la app a Aplicaciones. |
| Mac Intel | `BetPlaycito-Nelson-*-macOS-x86_64.dmg` | Abrir la imagen y arrastrar la app a Aplicaciones. |
| Ubuntu/Debian | `betplaycito-nelson_*_all.deb` | Abrir con el instalador de software o instalar con `apt`. |

Los binarios publicados automáticamente todavía no están firmados con certificados comerciales. Windows o macOS pueden mostrar una advertencia de editor/desarrollador desconocido la primera vez; revise que la descarga provenga de este repositorio antes de permitir su apertura.

## Acceso inicial

Todas las instalaciones nuevas crean automáticamente la misma cuenta solicitada:

```text
Usuario: NelsonRuiz
Contraseña: 1075271744
```

El usuario ya aparece escrito en la pantalla de acceso. La contraseña se valida localmente mediante PBKDF2 y no se guarda en texto plano en la base. Puede cambiarla después en **Seguridad**. Como esta credencial es pública, conviene cambiarla si otras personas pueden usar la misma cuenta del computador.

## Funciones principales

- Sumadores `+` y `−`, además de carga por cantidad para lotes grandes.
- Contexto global o por equipos, sin exigir rival ni partido detallado.
- Comparación agregada entre varios equipos.
- Registro opcional de partidos con derivación automática de variables.
- Seis grupos de análisis: resultado; goles 2.5; Gol-Gol; marcador local; córners 9.5; y tiros al arco 9.5.
- Cantidad, porcentaje y tamaño de muestra en gráficos tipo dona.
- Explicación automática de la opción seleccionada frente a su alternativa.
- Historial inmutable: una corrección agrega un movimiento inverso, no borra el original.
- Copias SQLite automáticas y exportaciones JSON, CSV y XLSX.
- Diseño adaptable con transiciones, navegación de escritorio y móvil.

## Persistencia

SQLite es la fuente principal de verdad. Cada cambio confirmado se guarda inmediatamente y permanece disponible al cerrar, actualizar o reinstalar la aplicación. Las ubicaciones predeterminadas son:

| Sistema | Datos y respaldos |
| --- | --- |
| Windows | `%LOCALAPPDATA%\BetPlaycito Nelson` |
| macOS | `~/Library/Application Support/BetPlaycito Nelson` |
| Ubuntu/Debian | `~/.local/share/betplaycito-nelson` |
| Código fuente/zipapp | `datos/` y `respaldos/` junto al proyecto |

Desinstalar conserva deliberadamente los datos del usuario. Además, descargue periódicamente un respaldo JSON desde la aplicación y guárdelo en otra unidad.

## Vista previa del diseño

Puede abrir [`src/betplaycito/web/index.html`](src/betplaycito/web/index.html) directamente para revisar el diseño con datos ficticios. Esa modalidad se identifica como **Vista de demostración**, es de solo lectura y no guarda cambios. El aplicativo real debe abrirse desde su instalador o ejecutable.

## Ejecutar desde el código fuente

Requiere Python 3.10 o posterior y un navegador moderno. La aplicación en ejecución usa únicamente la biblioteca estándar de Python.

```bash
PYTHONPATH=src python3 -m betplaycito
```

Para crear el zipapp y el paquete de Ubuntu:

```bash
bash scripts/build.sh
bash scripts/build-deb.sh
```

La configuración predeterminada se puede reemplazar con `config.local.json`, variables de entorno o las opciones `--config` y `--data-dir`. Consulte [Arquitectura](docs/ARQUITECTURA.md#ejecución-y-empaquetado).

## Construcciones nativas

El workflow `release-native.yml` construye cada artefacto en su sistema operativo de destino: Windows x64, macOS Apple Silicon, macOS Intel y Ubuntu. Esto evita presentar un archivo de Linux como si pudiera ejecutarse en Windows o Mac. Las instrucciones técnicas están en [Publicaciones nativas](packaging/NATIVE-RELEASES.md).

## Alcance local

El servidor escucha únicamente en `127.0.0.1`; no debe exponerse por túneles, reenvío de puertos ni un proxy público. Esta edición no se publica en Vercel porque su SQLite local necesita almacenamiento persistente. Una versión web requeriría autenticación para Internet y una base administrada distinta.

Consulte [Seguridad](SECURITY.md), [Modelo de datos](docs/MODELO-DE-DATOS.md) y [Manual de uso](docs/MANUAL-DE-USO.md) para más detalles.

## Documentación

- [Arquitectura](docs/ARQUITECTURA.md)
- [Modelo de datos](docs/MODELO-DE-DATOS.md)
- [Manual de uso](docs/MANUAL-DE-USO.md)
- [Seguridad](SECURITY.md)
- [Contribuir](CONTRIBUTING.md)

## Licencia

Este proyecto se distribuye bajo la [licencia MIT](LICENSE).
