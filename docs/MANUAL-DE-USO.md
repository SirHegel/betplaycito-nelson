# Manual de uso · versión 1.1.0

[Volver al README](../README.md)

> Los porcentajes describen únicamente los registros ingresados. No garantizan resultados futuros ni constituyen asesoría de apuestas.

## 1. Descargar el archivo correcto

Descargue la versión 1.1.0 desde [GitHub Releases](https://github.com/SirHegel/betplaycito-nelson/releases). Cada archivo sirve únicamente para la plataforma indicada:

| Sistema | Archivo recomendado | Cuándo elegirlo |
| --- | --- | --- |
| Windows 10/11 x64 | `BetPlaycito-Nelson-1.1.0-Windows-x64-Setup.exe` | Opción normal: instala accesos directos y permite desinstalar desde Windows. |
| Windows 10/11 x64 portable | `BetPlaycito-Nelson-1.1.0-Windows-x64-portable.exe` | Un solo archivo ejecutable, sin asistente de instalación. |
| Mac Apple Silicon | `BetPlaycito-Nelson-1.1.0-macOS-arm64.dmg` | Equipos con chip M1, M2, M3, M4 o posterior. |
| Mac Intel | `BetPlaycito-Nelson-1.1.0-macOS-x86_64.dmg` | Macs con procesador Intel. |
| Ubuntu/Debian | `betplaycito-nelson_1.1.0_all.deb` | Instalación integrada con el menú de aplicaciones. |

Un `.exe` no funciona en macOS o Ubuntu; un `.dmg` no funciona en Windows; y el `.deb` no es un instalador para Windows. Si no conoce el procesador de su Mac, consulte **Apple > Acerca de esta Mac** antes de descargar.

## 2. Instalar y abrir

### Windows

**Instalador recomendado**

1. Haga doble clic en `BetPlaycito-Nelson-1.1.0-Windows-x64-Setup.exe`.
2. Acepte la solicitud de Control de cuentas de usuario únicamente si el archivo proviene del repositorio oficial.
3. Siga el asistente; puede dejar marcada la creación del acceso directo.
4. Abra **BetPlaycito Nelson** desde el escritorio o el menú Inicio.

**Ejecutable portable de un solo archivo**

1. Guarde `BetPlaycito-Nelson-1.1.0-Windows-x64-portable.exe` en una carpeta reconocible.
2. Haga doble clic. No necesita copiar HTML, Python ni otras carpetas a su lado.
3. Para pasarlo a otro computador, copie ese único `.exe`. Los datos del computador anterior no viajan dentro del archivo; expórtelos como JSON si también necesita trasladarlos.

Los artefactos pueden publicarse sin certificado comercial. Microsoft Defender SmartScreen evalúa la reputación de las aplicaciones descargadas y puede mostrar una advertencia para un archivo nuevo o no reconocido. No desactive la protección globalmente: compruebe el nombre, la versión y que la descarga provenga de este repositorio; continúe solo si confía en ella. Consulte la [explicación de SmartScreen de Microsoft](https://support.microsoft.com/en-us/office/protect-my-pc-from-viruses).

### macOS

1. Haga doble clic en el `.dmg` correspondiente a Apple Silicon o Intel.
2. Arrastre **BetPlaycito Nelson.app** a la carpeta **Aplicaciones**.
3. Expulse la imagen y abra la aplicación desde **Aplicaciones**.

Si el paquete no está firmado o notarizado, macOS puede impedir la primera apertura. Después de intentar abrirlo, y solo tras verificar que procede del repositorio oficial, vaya a **Configuración del Sistema > Privacidad y seguridad** y use **Abrir de todos modos**. Apple explica este flujo y sus riesgos en [Abrir apps de forma segura en el Mac](https://support.apple.com/es-co/102445). No omita una alerta que indique que el archivo está dañado o contiene software malicioso: vuelva a descargarlo desde la publicación oficial.

### Ubuntu o Debian

Puede hacer doble clic en `betplaycito-nelson_1.1.0_all.deb`, abrirlo con el instalador de software y pulsar **Instalar**. El sistema solicitará la contraseña administrativa del computador.

También puede instalarlo desde una terminal ubicada en la carpeta de descarga:

```bash
sudo apt install ./betplaycito-nelson_1.1.0_all.deb
```

APT gestiona las dependencias del paquete local; consulte la [documentación de paquetes de Ubuntu](https://ubuntu.com/server/docs/tutorial/managing-software/#installing-a-deb-file). Al terminar, abra **BetPlaycito Nelson** desde el menú de aplicaciones. Una actualización con otro `.deb` reemplaza el programa, pero conserva los datos del usuario.

### Ejecución técnica desde el código fuente

Esta modalidad es opcional y requiere Python 3.10 o posterior:

```bash
PYTHONPATH=src python3 -m betplaycito
```

Para construir el zipapp y el paquete de Ubuntu desde el repositorio:

```bash
bash scripts/build.sh
bash scripts/build-deb.sh
```

`config.local.json`, las variables de entorno y las opciones `--config` o `--data-dir` permiten personalizar una instalación avanzada antes de crear su primera base. Las rutas deben quedar dentro del perfil del usuario o de la carpeta de la aplicación. No son necesarios para usar los instaladores normales.

## 3. Iniciar sesión

Una instalación nueva crea automáticamente esta cuenta:

```text
Usuario: NelsonRuiz
Contraseña: 1075271744
```

El campo de usuario ya aparece completado. Escriba la contraseña exactamente; distingue mayúsculas, minúsculas y números. La credencial es pública y está pensada únicamente para el primer acceso. Si otras personas pueden usar su sesión del computador, entre a **Seguridad** y cambie la contraseña.

La contraseña se valida localmente mediante una derivación PBKDF2 y no se guarda en texto plano en SQLite. Una actualización o reinstalación no restablece la cuenta: si esta base ya existía y usted cambió la contraseña, debe seguir usando la contraseña modificada.

Si varios intentos fallan, espere el periodo de protección indicado. Al terminar, pulse **Cerrar sesión**, especialmente en un computador compartido.

## 4. Dónde se guardan los datos

Los ejecutables nativos guardan la base fuera del programa y dentro del perfil del usuario actual:

| Sistema | Base y respaldos | Configuración avanzada opcional |
| --- | --- | --- |
| Windows | `%LOCALAPPDATA%\BetPlaycito Nelson\betplaycito.db` y `%LOCALAPPDATA%\BetPlaycito Nelson\respaldos\` | `%APPDATA%\BetPlaycito Nelson\config.local.json` |
| macOS | `~/Library/Application Support/BetPlaycito Nelson/betplaycito.db` y `respaldos/` en esa carpeta | `~/Library/Application Support/BetPlaycito Nelson/config.local.json` |
| Ubuntu/Debian | `~/.local/share/betplaycito-nelson/betplaycito.db` y `respaldos/` | `~/.config/betplaycito-nelson/config.local.json` |
| Código fuente o zipapp | `datos/betplaycito.db` y `respaldos/` junto al proyecto | `config.local.json` junto al proyecto |

Linux respeta `XDG_DATA_HOME` y `XDG_CONFIG_HOME` cuando contienen rutas absolutas. Cada cuenta del sistema operativo tiene su propia base. El ejecutable portable de Windows también usa `%LOCALAPPDATA%`; la base **no** queda incrustada en el `.exe` ni se guarda en Descargas.

Actualizar, reemplazar o desinstalar el programa conserva deliberadamente estas carpetas. Esto evita perder estadísticas, pero significa que desinstalar no equivale a borrar los datos. Para mover la información a otro computador, descargue un respaldo JSON desde **Datos y respaldos** y restáurelo en el equipo nuevo.

## 5. Abrir, cerrar y reconocer la vista real

Al abrir el aplicativo, este inicia un servicio privado en `127.0.0.1` y muestra el panel en el navegador predeterminado. Esa dirección local es normal: la aplicación no publica sus datos en Internet. Si ya estaba abierta, un segundo doble clic vuelve a mostrar la pestaña existente.

Para cerrar:

1. confirme que el indicador superior diga que todo está guardado;
2. abra el menú y pulse **Cerrar aplicación**;
3. confirme y cierre la pestaña cuando aparezca el mensaje final.

No apague el equipo durante una exportación, restauración o copia de seguridad.

Abrir `src/betplaycito/web/index.html` directamente produce una **Vista de demostración** mediante `file://`. Contiene datos ficticios, muestra un banner de solo lectura, no consulta la API y no guarda cambios. Sirve para revisar el diseño, no para trabajar. Para usar datos reales, abra el instalador, la aplicación o el ejecutable correspondiente.

## 6. Elegir el contexto

Los ajustes manuales pueden trabajar de dos maneras:

- **General:** cantidades que no necesita asociar a un equipo.
- **Por equipo:** estadísticas separadas para un equipo creado por usted.

Agregar un equipo no obliga a indicar rival. El nombre organiza ajustes y permite asociar partidos opcionales. Sin selección se muestra la vista global; también puede seleccionar varios equipos para un agregado y compararlos. Revise por separado “Guardar nuevos datos en”, porque cada ajuste se guarda en ese equipo o en Global, no necesariamente en el filtro visible.

Si deja de usar un equipo, archívelo. Sus estadísticas e historial se conservan.

## 7. Alimentar los sumadores

Cada tarjeta contiene opciones excluyentes dentro de su propio gráfico:

- `+` registra una unidad en la opción;
- `−` registra una corrección de una unidad;
- la carga por cantidad permite sumar o restar lotes sin repetir clics.

Ejemplo para Ambos marcan:

1. agregue 100 a Gol-Gol;
2. agregue 400 a No Gol;
3. el gráfico mostrará 20.0% y 80.0% sobre 500 registros.

Una resta no borra el incremento original: crea un movimiento compensatorio y nunca elimina ni modifica partidos detallados.

- Si “Guardar nuevos datos en” muestra un equipo, la corrección se limita al saldo manual de ese equipo.
- Si el destino es Global, la corrección compensa el total manual agregado, incluidos ajustes asociados a equipos, y solo aparece en la vista global.
- Los registros provenientes de partidos no están disponibles para restar.

La aplicación rechaza una cantidad mayor que el saldo manual aplicable y nunca deja bajo cero el total global ni el de un equipo.

Antes de confirmar una carga grande, revise:

- equipo o contexto seleccionado;
- variable y opción;
- signo y cantidad;
- tamaño de muestra que resultará.

## 8. Registrar un partido detallado opcional

“Nuevo partido” permite ingresar una observación coherente en varias tarjetas con una sola operación:

1. seleccione los equipos local y visitante o déjelos sin especificar;
2. ingrese los goles de ambos lados;
3. opcionalmente ingrese una nota;
4. si agrega córners, complete local y visitante;
5. si agrega tiros al arco, complete local y visitante;
6. revise y guarde.

El sistema deriva automáticamente Resultado, Goles 2.5, Gol-Gol y Local marcó. Solo deriva Córners 9.5 o Tiros al arco 9.5 cuando la pareja correspondiente está completa. El partido aparece como un registro detallado en el historial y suma una unidad a cada categoría derivada.

Use este módulo cuando conserva el detalle de una observación; use los sumadores para cantidades ya agregadas. No cargue el mismo dato por ambas vías salvo que quiera contarlo dos veces.

## 9. Interpretar las variables

| Tarjeta | Cómo clasificar un registro |
| --- | --- |
| Resultado | Local, Empate o Visitante según el marcador final |
| Goles 2.5 | Más = 3 o más goles totales; Menos = 0, 1 o 2 |
| Gol-Gol | Sí cuando ambos equipos marcaron; No cuando al menos uno no marcó |
| Esquinas 9.5 | Más = 10 o más esquinas totales; Menos = 0–9 |
| Tiros al arco 9.5 | Más = 10 o más tiros al arco totales; Menos = 0–9 |
| Local marcó | Sí cuando el local hizo al menos un gol; No cuando terminó en cero |

Cada tarjeta calcula su propio denominador. Que Goles tenga 500 registros y Esquinas 320 no es un error: significa que se ingresó distinta cantidad de información. Compare porcentajes junto con su tamaño de muestra.

## 10. Leer los gráficos y la explicación

La leyenda muestra cantidad y porcentaje de cada opción. El centro o resumen de la dona muestra la tendencia principal y el total analizado.

- “Puntos porcentuales” es la resta entre porcentajes, no un crecimiento relativo.
- Con total cero aparece “Sin datos”.
- Si dos opciones comparten el mayor porcentaje, no existe una líder única.
- Una muestra pequeña puede cambiar mucho con pocos registros.
- Los registros cargados manualmente pueden contener sesgos o errores.

El módulo explicativo resume lo almacenado; no conoce lesiones, alineaciones, cuotas, fecha, rival ni condiciones del partido. No use el porcentaje como garantía de un resultado futuro.

## 11. Revisar el historial

El historial combina ajustes y partidos en orden temporal y permite filtrarlos por tipo. Los filtros de variable y búsqueda se aplican a la página cargada en pantalla. Úselo para localizar una carga manual equivocada y aplicar la corrección opuesta. No espere que una corrección elimine el rastro anterior.

Al revisar un movimiento, confirme:

- fecha y hora;
- equipo/contexto;
- variable y opción;
- delta positivo o negativo;
- detalle y nota asociados.

## 12. Respaldos y exportaciones

Antes de cada arranque con una base existente, la aplicación crea automáticamente una copia SQLite fechada en la carpeta `respaldos/` de su perfil, indicada en la [sección 4](#4-dónde-se-guardan-los-datos). También puede usar **Crear copia ahora**. Descargue periódicamente los formatos de **Datos y respaldos** y guárdelos fuera del computador o en otra unidad.

- **JSON:** conserva estructura e historial y es el formato que la aplicación valida para restaurar.
- **CSV:** facilita revisar movimientos y totales en una hoja de cálculo.
- **XLSX:** facilita análisis en Excel o LibreOffice cuando está disponible.
- **SQLite:** es la base operativa; no la abra ni modifique mientras la aplicación está en uso.

El libro XLSX organiza la información en `Resumen`, `Equipos`, `Ajustes` y `Partidos`. CSV ofrece una tabla conjunta compatible con hojas de cálculo.

Una exportación CSV/XLSX no reemplaza el JSON integral ni una copia SQLite verificada. Restaurar un JSON **reemplaza** los equipos, ajustes y partidos actuales; no los combina. La cuenta administradora se conserva y el sistema crea primero una copia SQLite de seguridad. Aun así, descargue una copia actual adicional y confirme que eligió el archivo correcto.

No altere manualmente `betplaycito.db`, sus archivos `-wal` o `-shm`, ni copie una base activa de forma improvisada. Para detalles técnicos, consulte [Modelo de datos](MODELO-DE-DATOS.md#respaldo-y-exportación).

## 13. Solución de problemas

### No abre el aplicativo

- Confirme que descargó el artefacto correspondiente a Windows, Mac Apple Silicon, Mac Intel o Ubuntu; no cambie solo la extensión del archivo.
- En Windows, pruebe primero el instalador `Setup.exe`; revise si SmartScreen o el antivirus puso el archivo en cuarentena y continúe únicamente si verificó su procedencia.
- En macOS, confirme la arquitectura y revise **Privacidad y seguridad** después del primer intento de apertura.
- En Ubuntu/Debian, reinstale el `.deb` con `sudo apt install ./betplaycito-nelson_1.1.0_all.deb` para que APT informe cualquier dependencia pendiente.
- Si el proceso está abierto pero el navegador no apareció, visite `http://127.0.0.1:8765/`. Esa dirección solo responde mientras BetPlaycito está ejecutándose.
- Si usa código fuente, compruebe Python 3.10 o posterior y que `config.local.json`, si existe, sea JSON válido.

### No puedo iniciar sesión

- En una base nueva use `NelsonRuiz` y `1075271744`; ambos valores deben escribirse exactamente.
- Si ya había usado esta base o cambió la contraseña desde **Seguridad**, la credencial pública ya no la reemplaza.
- Recuerde que la contraseña distingue mayúsculas y minúsculas.
- Confirme que inició la aplicación con la misma cuenta del sistema operativo donde están sus datos.
- No publique cookies, bases, respaldos ni una contraseña nueva al pedir ayuda.

### Un porcentaje parece incorrecto

- Revise las cantidades de todas las opciones de esa misma tarjeta.
- Compruebe el equipo/contexto activo.
- Recuerde que cada tarjeta tiene su propio tamaño de muestra.
- Consulte el historial por cargas duplicadas o correcciones.

### Los datos no aparecen

- Si aparece el banner **Vista de demostración**, cerró o no inició el aplicativo real: abrió `index.html` directamente y esos números son ficticios.
- Verifique que abrió la aplicación con la misma cuenta de Windows, macOS o Linux; cada perfil tiene almacenamiento separado.
- El ejecutable portable de Windows también usa `%LOCALAPPDATA%`; mover el `.exe` no mueve la base.
- Si usa código fuente o zipapp, verifique que abrió el mismo proyecto y su mismo directorio `datos/`.
- Restaure únicamente con la función y el formato admitidos por la versión instalada.

Si reporta un problema, incluya la versión 1.1.0, el sistema operativo, el nombre exacto del archivo descargado, el mensaje y pasos reproducibles. Aunque la contraseña inicial es pública, quite del reporte contraseñas nuevas, cookies, bases y respaldos privados.
