# Cómo contribuir

[Volver al README](README.md)

Gracias por ayudar a mejorar BetPlaycito Nelson. Mantenga los cambios pequeños, verificables y compatibles con su enfoque local.

## Preparar el entorno

Requisitos: Git, Bash y Python 3.11 o posterior.

```bash
git clone URL_DEL_REPOSITORIO
cd betplaycito-nelson
cp config.example.json config.local.json
```

Use credenciales ficticias solo para desarrollo. `config.local.json`, bases, respaldos y artefactos están ignorados por Git.

## Principios del proyecto

- Biblioteca estándar de Python en tiempo de ejecución.
- Persistencia principal en SQLite.
- Servidor limitado al equipo local.
- Historial por eventos inmutables; las correcciones son movimientos compensatorios.
- Ningún contador puede quedar negativo.
- Equipos opcionales, sin convertirlos implícitamente en partidos o rivales.
- Partidos detallados opcionales con categorías derivadas dentro de la misma transacción.
- Cálculos descritos como frecuencias históricas, no garantías predictivas.
- Interfaz utilizable con teclado y mensajes claros además del color.
- Ninguna credencial, base o respaldo real en código, pruebas o documentación.

## Flujo sugerido

1. Cree una rama para un cambio concreto.
2. Añada o actualice pruebas cuando cambie una regla.
3. Mantenga estables las claves almacenadas de variables y opciones.
4. Documente cambios de esquema y proporcione una migración segura.
5. Construya el artefacto:

   ```bash
   bash scripts/build.sh
   ```

6. Revise el diff y confirme que no contiene secretos.
7. Abra una solicitud de cambios explicando problema, solución y comprobaciones.

## Cambios en datos

Una modificación del esquema debe:

- tener una versión explícita;
- ejecutarse dentro de una transacción;
- crear o requerir un respaldo coherente;
- preservar movimientos e identificadores existentes;
- incluir una prueba de migración desde la versión anterior.

No cambie claves persistidas únicamente para mejorar una etiqueta visual. Cambie la etiqueta de presentación o incluya una migración deliberada.

## Cambios en seguridad

Lea [SECURITY.md](SECURITY.md). No adjunte un `config.local.json`, hash real, cookie, base o respaldo a una solicitud de cambios. Use valores claramente ficticios en pruebas y ejemplos.

Los problemas de seguridad explotables deben reportarse por un canal privado, no en una incidencia pública.

## Documentación

Use español claro, enlaces relativos y ejemplos sin información personal. Si cambia comportamiento, actualice como mínimo:

- [README](README.md);
- [Arquitectura](docs/ARQUITECTURA.md);
- [Modelo de datos](docs/MODELO-DE-DATOS.md);
- [Manual de uso](docs/MANUAL-DE-USO.md), cuando afecte la operación.
