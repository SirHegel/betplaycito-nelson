# Manual de uso

[Volver al README](../README.md)

## 1. Preparar el primer inicio

1. Compruebe que tiene Python 3.11 o posterior:

   ```bash
   python3 --version
   ```

2. Copie `config.example.json` como `config.local.json` en la carpeta de la aplicación.
3. Sustituya los valores de ejemplo por un usuario local y una contraseña larga y exclusiva.
4. Limite los permisos con `chmod 600 config.local.json` y no comparta el archivo.
5. Para no conservar la contraseña inicial en texto plano, genere un hash con `PYTHONPATH=src python3 -m betplaycito --hash-password` y use la clave `admin_password_hash` en vez de `admin_password`.
6. Si usa el código fuente, construya el aplicativo con:

   ```bash
   bash scripts/build.sh
   ```

El repositorio no contiene credenciales predeterminadas. Si inicia sin configuración y la base aún no tiene administrador, la consola muestra un código aleatorio de una sola vez. Ingréselo en el formulario “Configuración inicial” junto con su nuevo usuario y contraseña. El código deja de ser válido cuando se crea la cuenta.

## 2. Abrir y cerrar

En la carpeta `dist/`, abra `Iniciar BetPlaycito Nelson.sh`. También puede ejecutar `BetPlaycito-Nelson.pyz` con Python 3.

El aplicativo inicia un servidor accesible solo desde el mismo equipo y abre una pestaña del navegador. Mantenga abierta la ventana del proceso mientras usa el dashboard.

Para cerrar:

1. confirme que la pantalla indica que el último cambio fue guardado;
2. abra el menú y pulse “Cerrar aplicación”;
3. confirme la acción y cierre la pestaña cuando aparezca el mensaje final.

Si la interfaz no responde, termine el proceso desde su ventana con `Ctrl+C` como alternativa.

No apague el equipo en medio de una exportación o una operación de respaldo.

## 3. Iniciar sesión

Ingrese la cuenta creada durante la configuración inicial. No anote la contraseña en este manual ni la incluya en capturas de pantalla. Si luego la cambia desde “Seguridad”, use la nueva contraseña; el archivo de configuración inicial no actualiza la cuenta existente.

Si varios intentos fallan, espere el periodo de protección indicado por la aplicación. Al terminar, use “Cerrar sesión”, especialmente si comparte la cuenta del sistema operativo.

## 4. Elegir el contexto

Los ajustes manuales pueden trabajar de dos maneras:

- **General:** cantidades que no necesita asociar a un equipo.
- **Por equipo:** estadísticas separadas para un equipo creado por usted.

Agregar un equipo no obliga a indicar rival. El nombre organiza ajustes y permite asociar partidos opcionales. Sin selección se muestra la vista global; también puede seleccionar varios equipos para un agregado y compararlos. Revise por separado “Guardar nuevos datos en”, porque cada ajuste se guarda en ese equipo o en Global, no necesariamente en el filtro visible.

Si deja de usar un equipo, archívelo. Sus estadísticas e historial se conservan.

## 5. Alimentar los sumadores

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

## 6. Registrar un partido detallado opcional

“Nuevo partido” permite ingresar una observación coherente en varias tarjetas con una sola operación:

1. seleccione los equipos local y visitante o déjelos sin especificar;
2. ingrese los goles de ambos lados;
3. opcionalmente ingrese una nota;
4. si agrega córners, complete local y visitante;
5. si agrega tiros al arco, complete local y visitante;
6. revise y guarde.

El sistema deriva automáticamente Resultado, Goles 2.5, Gol-Gol y Local marcó. Solo deriva Córners 9.5 o Tiros al arco 9.5 cuando la pareja correspondiente está completa. El partido aparece como un registro detallado en el historial y suma una unidad a cada categoría derivada.

Use este módulo cuando conserva el detalle de una observación; use los sumadores para cantidades ya agregadas. No cargue el mismo dato por ambas vías salvo que quiera contarlo dos veces.

## 7. Interpretar las variables

| Tarjeta | Cómo clasificar un registro |
| --- | --- |
| Resultado | Local, Empate o Visitante según el marcador final |
| Goles 2.5 | Más = 3 o más goles totales; Menos = 0, 1 o 2 |
| Gol-Gol | Sí cuando ambos equipos marcaron; No cuando al menos uno no marcó |
| Esquinas 9.5 | Más = 10 o más esquinas totales; Menos = 0–9 |
| Tiros al arco 9.5 | Más = 10 o más tiros al arco totales; Menos = 0–9 |
| Local marcó | Sí cuando el local hizo al menos un gol; No cuando terminó en cero |

Cada tarjeta calcula su propio denominador. Que Goles tenga 500 registros y Esquinas 320 no es un error: significa que se ingresó distinta cantidad de información. Compare porcentajes junto con su tamaño de muestra.

## 8. Leer los gráficos y la explicación

La leyenda muestra cantidad y porcentaje de cada opción. El centro o resumen de la dona muestra la tendencia principal y el total analizado.

- “Puntos porcentuales” es la resta entre porcentajes, no un crecimiento relativo.
- Con total cero aparece “Sin datos”.
- Si dos opciones comparten el mayor porcentaje, no existe una líder única.
- Una muestra pequeña puede cambiar mucho con pocos registros.
- Los registros cargados manualmente pueden contener sesgos o errores.

El módulo explicativo resume lo almacenado; no conoce lesiones, alineaciones, cuotas, fecha, rival ni condiciones del partido. No use el porcentaje como garantía de un resultado futuro.

## 9. Revisar el historial

El historial combina ajustes y partidos en orden temporal y permite filtrarlos por tipo. Los filtros de variable y búsqueda se aplican a la página cargada en pantalla. Úselo para localizar una carga manual equivocada y aplicar la corrección opuesta. No espere que una corrección elimine el rastro anterior.

Al revisar un movimiento, confirme:

- fecha y hora;
- equipo/contexto;
- variable y opción;
- delta positivo o negativo;
- detalle y nota asociados.

## 10. Respaldos y exportaciones

Antes de cada arranque con una base existente, la aplicación crea automáticamente una copia SQLite fechada en `respaldos/`. También puede usar “Crear copia ahora”. Descargue periódicamente los formatos de la pantalla “Datos y respaldos” y guárdelos fuera de la carpeta del aplicativo.

- **JSON:** conserva estructura e historial y es el formato que la aplicación valida para restaurar.
- **CSV:** facilita revisar movimientos y totales en una hoja de cálculo.
- **XLSX:** facilita análisis en Excel o LibreOffice cuando está disponible.
- **SQLite:** es la base operativa; no la abra ni modifique mientras la aplicación está en uso.

El libro XLSX organiza la información en `Resumen`, `Equipos`, `Ajustes` y `Partidos`. CSV ofrece una tabla conjunta compatible con hojas de cálculo.

Una exportación CSV/XLSX no reemplaza el JSON integral ni una copia SQLite verificada. Restaurar un JSON **reemplaza** los equipos, ajustes y partidos actuales; no los combina. La cuenta administradora se conserva y el sistema crea primero una copia SQLite de seguridad. Aun así, descargue una copia actual adicional y confirme que eligió el archivo correcto.

No altere archivos dentro de `datos/` ni copie una base activa de forma improvisada. Para detalles técnicos, consulte [Modelo de datos](MODELO-DE-DATOS.md#respaldo-y-exportación).

## 11. Solución de problemas

### No abre el aplicativo

- Confirme que `BetPlaycito-Nelson.pyz` y el lanzador estén juntos.
- Compruebe Python 3.11 o posterior.
- Verifique que el lanzador tenga permiso de ejecución.
- Revise que `config.local.json` sea JSON válido y tenga los campos de la plantilla.

### No puedo iniciar sesión

- Recuerde que la contraseña distingue mayúsculas y minúsculas.
- Compruebe que editó el archivo de configuración de la carpeta que está ejecutando.
- No publique el contenido del archivo al pedir ayuda.

### Un porcentaje parece incorrecto

- Revise las cantidades de todas las opciones de esa misma tarjeta.
- Compruebe el equipo/contexto activo.
- Recuerde que cada tarjeta tiene su propio tamaño de muestra.
- Consulte el historial por cargas duplicadas o correcciones.

### Los datos no aparecen

- Verifique que abrió la misma copia de la aplicación y el mismo directorio de datos.
- No cree varias carpetas `dist/` con bases independientes sin identificarlas.
- Restaure únicamente con la función y el formato admitidos por la versión instalada.

Si reporta un problema, incluya la versión, el mensaje exacto y pasos reproducibles, pero quite usuarios, contraseñas, cookies, bases y respaldos privados.
