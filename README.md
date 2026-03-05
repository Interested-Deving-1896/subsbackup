# SBSM — Subtitle Backup & Metadata System

Script automatizado para extraer, enriquecer y respaldar subtítulos (`.srt`) gestionados por **Bazarr**, cruzando información con **Sonarr** y **Radarr** para preservar metadata de calidad y origen junto a cada archivo.

## Qué hace

Por cada subtítulo externo (`.srt`) registrado en Bazarr:
1. Obtiene metadata de calidad desde Sonarr/Radarr (resolución, source, release group).
2. Copia el `.srt` a una carpeta de backup estructurada.
3. Genera un manifiesto `.json` homónimo con toda la metadata para facilitar restauraciones futuras.

### Estructura de salida
```
Backup_Subtitulos/
├── Movies/
│   └── Apocalypto (2006)/
│       ├── Apocalypto (2006).srt
│       └── Apocalypto (2006).json
└── Series/
    └── Star Trek- Starfleet Academy/
        └── Season 01/
            ├── Star.Trek...S01E01...es.srt
            └── Star.Trek...S01E01...es.json
```

## Requisitos

- Python 3.10+
- Bazarr, Sonarr y Radarr accesibles por red
- (Para modo red) Shares SMB montados o credenciales en el Administrador de Credenciales de Windows

## Instalación

```bash
python -m venv .venv
.venv/Scripts/pip install requests pyarr python-dotenv   # Windows
# .venv/bin/pip install ...                               # Linux/macOS
```

Copiar `.env.example` a `.env` y completar los valores:

```bash
cp .env.example .env
```

## Configuración (`.env`)

| Variable | Descripción |
|---|---|
| `BAZARR_URL` / `BAZARR_API_KEY` | URL y API key de Bazarr |
| `SONARR_URL` / `SONARR_API_KEY` | URL y API key de Sonarr |
| `RADARR_URL` / `RADARR_API_KEY` | URL y API key de Radarr |
| `RUN_MODE` | `network` (Windows via SMB) \| `local` (en el servidor) |
| `SERIES_NETWORK` / `MOVIES_NETWORK` | Roots SMB de series y películas (modo network) |
| `OUTPUT_NETWORK` | Carpeta destino del backup (modo network) |
| `SERIES_LOCAL` / `MOVIES_LOCAL` | Paths locales de series y películas (modo local) |
| `OUTPUT_LOCAL` | Carpeta destino del backup (modo local) |

## Uso

### 1. Verificar conectividad
```bash
.venv/Scripts/python test_connections.py
```
Valida la conexión y autenticación contra las 3 APIs.

### 2. Agregar datos
```bash
.venv/Scripts/python phase2_aggregation.py
```
Consulta Bazarr, Sonarr y Radarr, genera `aggregated_data.json` con todos los subtítulos enriquecidos con metadata de calidad.

### 3. Ejecutar backup
```bash
.venv/Scripts/python phase3_backup.py
```
Lee `aggregated_data.json`, copia los `.srt` y escribe los manifiestos `.json` en la carpeta de destino configurada. Los subtítulos embebidos (sin archivo `.srt` externo) se omiten silenciosamente. Las ejecuciones sucesivas son idempotentes: si el archivo ya existe con el mismo tamaño, se salta.

## Despliegue en el servidor (modo local)

1. Copiar el proyecto al servidor.
2. Crear el entorno virtual e instalar dependencias (igual que arriba con `pip`).
3. En `.env`, cambiar `RUN_MODE=local` y ajustar `OUTPUT_LOCAL` al path de destino.
4. Ejecutar en orden: `phase2_aggregation.py` → `phase3_backup.py`.
5. Para ejecución desatendida, agregar al crontab:
   ```
   0 3 * * * cd /path/al/proyecto && .venv/bin/python phase2_aggregation.py && .venv/bin/python phase3_backup.py
   ```

## Notas

- **Subtítulos embebidos**: Bazarr rastrea subtítulos dentro de archivos MKV que no tienen `.srt` externo. Estos registros (`bazarr_path: null`) son ignorados en el backup ya que no hay archivo físico que copiar.
- **Caracteres inválidos en Windows**: Los títulos con `:` u otros caracteres especiales se sanitizan automáticamente en los nombres de carpeta.
- **Registros huérfanos**: Si un subtítulo existe en Bazarr pero su video fue eliminado de Sonarr/Radarr, se registra como `[ORPHAN]` en el log sin interrumpir el proceso.
- **Idempotencia**: Ejecutar el backup múltiples veces es seguro. Los archivos con el mismo tamaño no se reescriben.
