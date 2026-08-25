# Publicaciones nativas

El workflow `.github/workflows/release-native.yml` construye los artefactos al
publicar una etiqueta `vX.Y.Z`. La etiqueta debe coincidir con `__version__` en
`src/betplaycito/__init__.py`.

## Artefactos

- Windows x64: ejecutable portable de un archivo e instalador Inno Setup con UAC.
- macOS Apple Silicon y macOS Intel: bundle `.app` dentro de una imagen `.dmg`.
- Linux x86_64: ejecutable autónomo de un archivo construido en Ubuntu 22.04 para ampliar la compatibilidad de `glibc`.
- Debian/Ubuntu: paquete `.deb` generado por `scripts/build-deb.sh`.

Los ejecutables congelados incluyen `src/betplaycito/web`, por lo que no
dependen de archivos HTML, CSS o JavaScript ubicados junto al binario.

El ejecutable Linux autónomo se puede reproducir localmente con:

```bash
python3 -m venv .venv-build
.venv-build/bin/python -m pip install -r packaging/requirements-build.txt
BETPLAYCITO_BUILD_PYTHON=.venv-build/bin/python bash scripts/build-linux-native.sh
```

PyInstaller no es un compilador cruzado: Windows debe construirse en Windows y cada arquitectura de macOS en un ejecutor macOS compatible. El workflow aplica esa separación y valida los recursos incluidos antes de publicar.

## Firma opcional

Sin certificados los artefactos se construyen, pero Windows puede mostrar una
alerta de SmartScreen y macOS exigirá una apertura manual desde Privacidad y
seguridad. Para publicar con firma se admiten estos secretos del repositorio:

- `WINDOWS_CERTIFICATE_BASE64`: certificado Authenticode `.pfx` en base64.
- `WINDOWS_CERTIFICATE_PASSWORD`: contraseña del `.pfx`.
- `MACOS_CERTIFICATE_BASE64`: certificado Developer ID Application `.p12` en base64.
- `MACOS_CERTIFICATE_PASSWORD`: contraseña del `.p12`.
- `MACOS_SIGNING_IDENTITY`: nombre completo de la identidad Developer ID.
- `APPLE_API_KEY_P8_BASE64`: clave privada de App Store Connect en base64.
- `APPLE_API_KEY_ID`: identificador de la clave de notarización.
- `APPLE_API_ISSUER_ID`: identificador del emisor de la clave.

La firma de Windows se omite si falta cualquiera de sus dos secretos. La firma
y notarización de macOS se omiten si falta el grupo correspondiente. Ningún
certificado ni contraseña debe guardarse en el repositorio.
