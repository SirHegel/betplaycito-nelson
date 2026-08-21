# Seguridad

[Volver al README](README.md)

## Alcance del modelo de seguridad

BetPlaycito Nelson es una herramienta personal, local y de una sola cuenta administradora. El servidor debe escuchar únicamente en la interfaz de bucle local. No ha sido diseñado ni auditado como un servicio público multiusuario.

La autenticación protege frente al acceso casual desde el mismo equipo; no puede proteger los datos si otra persona controla la cuenta del sistema operativo, puede leer los archivos locales o ha comprometido el dispositivo.

## Credencial predeterminada y secretos

Por decisión funcional, todas las bases nuevas reciben la cuenta pública `NelsonRuiz` con la contraseña inicial indicada en el README. Esa pareja es un valor de arranque, no un secreto ni una barrera frente a otra persona que conozca el proyecto. El servidor conserva únicamente su derivación PBKDF2 y permite reemplazarla desde **Seguridad**.

El repositorio público nunca debe contener otros secretos o datos privados, entre ellos:

- credenciales personales distintas de la cuenta pública de arranque;
- `config.local.json` con valores privados;
- cookies o identificadores de sesión;
- bases SQLite, archivos WAL o SHM;
- respaldos y exportaciones con datos privados;
- claves privadas, tokens o volcados de diagnóstico sensibles.

Para reemplazar la cuenta durante un despliegue controlado, use la plantilla:

```bash
cp config.example.json config.local.json
```

Defina valores propios en la copia. El archivo está cubierto por [`.gitignore`](.gitignore), pero esa exclusión no sustituye revisar lo que se confirma con Git. En una base ya creada, cambiar este archivo no cambia automáticamente el usuario almacenado: use la pantalla de Seguridad.

Recomendaciones:

- cambie la contraseña inicial pública en equipos compartidos;
- para una contraseña personal, use una frase larga, exclusiva y no basada en números de identificación;
- no codifique credenciales personales en Python, JavaScript, documentación, scripts o capturas;
- no entregue `config.local.json` junto al artefacto público;
- después de crear el administrador, retire del archivo cualquier contraseña inicial en texto plano o reemplácela por su hash;
- cambie la contraseña si el archivo se compartió por error;
- cierre sesión cuando termine en un equipo compartido.

La base almacena PBKDF2-HMAC-SHA-256 con sal y 600 000 iteraciones, y verifica con comparación resistente a temporización. La plantilla acepta una contraseña inicial para facilitar una configuración personalizada, pero es preferible generar `admin_password_hash` mediante `--hash-password`, limitar `config.local.json` a modo `600` y evitar conservar texto plano. Los secretos de sesión son aleatorios; SQLite guarda únicamente su SHA-256.

## Red y sesiones

- Mantenga la dirección de escucha en `127.0.0.1` o su equivalente de bucle local.
- No abra el puerto en el cortafuegos.
- No use túneles, reenvío de puertos ni un proxy público.
- Una cookie de sesión debe ser `HttpOnly`, `SameSite=Strict` y tener expiración; la sesión actual dura 12 horas.
- La aplicación debe validar sesión, método y origen esperado en cada escritura.
- El cierre de sesión debe invalidar la sesión en el servidor.
- Los intentos fallidos deben limitarse temporalmente sin revelar si el usuario existe.

El servidor actual valida `Host` y `Origin`, limita las escrituras al mismo origen y emite CSP, `X-Frame-Options: DENY`, `nosniff`, política de referente y restricciones de permisos. Estas defensas complementan, pero no amplían, su alcance estrictamente local.

HTTP sin TLS solo es aceptable mientras el tráfico permanezca dentro del dispositivo. Si se cambia el alcance de red, es obligatorio rediseñar autenticación, transporte, sesiones y protección CSRF antes de publicar.

## Protección de datos

Los datos se conservan en archivos locales. Aplique permisos de sistema operativo para que otros usuarios del equipo no puedan leer la configuración, la base o los respaldos.

- Mantenga copias cifradas si usa almacenamiento externo o nube.
- No envíe una base completa para diagnosticar un error.
- Exporte únicamente lo necesario.
- Elimine metadatos privados antes de compartir CSV, JSON o XLSX.
- Pruebe la recuperación de copias de seguridad con una copia aislada.

El backend intenta crear las carpetas privadas con modo `700` y la base y los respaldos con `600`. Verifique estos permisos si copia los archivos a otra ubicación o a un sistema de archivos que no conserva permisos POSIX.

El historial inmutable evita que una corrección ordinaria oculte movimientos, pero no evita que alguien con acceso al sistema de archivos borre o altere directamente la base. Los respaldos externos son necesarios.

## Dependencias y construcción

La aplicación de ejecución usa la biblioteca estándar de Python, lo que reduce dependencias externas, pero Python, el navegador, las acciones de CI y el sistema operativo deben mantenerse actualizados.

Antes de publicar un artefacto:

1. revise `git status` y el contenido de los archivos incluidos;
2. busque credenciales o rutas privadas accidentalmente agregadas;
3. ejecute las verificaciones del proyecto;
4. construya con [`scripts/build.sh`](scripts/build.sh);
5. compruebe que `dist/` solo contiene plantillas sin secretos;
6. publique el artefacto desde una revisión conocida.

El `.pyz` no cifra ni oculta su código. Nunca dependa del empaquetado para proteger un secreto.

## Despliegues públicos

No despliegue esta versión en Vercel ni en otro hosting como si fuera una aplicación estática. SQLite necesita almacenamiento persistente y el backend local no incorpora todas las defensas exigidas por Internet.

Una edición alojada requeriría una base remota administrada, gestor de secretos, HTTPS, protección CSRF, límites de solicitudes distribuidos, autorización, migraciones, registros seguros, copias de seguridad y una revisión independiente.

## Reportar una vulnerabilidad

No publique una vulnerabilidad explotable ni datos privados en una incidencia abierta. Contacte al responsable del repositorio por un canal privado y proporcione:

- versión o revisión afectada;
- descripción del impacto;
- pasos mínimos para reproducir;
- mitigación sugerida, si la conoce.

Quite credenciales, cookies, rutas personales, bases y respaldos. No pruebe una vulnerabilidad contra equipos o datos que no le pertenecen.
