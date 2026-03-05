# SBSM — Contexto para Claude Code

## Qué es este proyecto
Script Python que respalda subtítulos `.srt` gestionados por Bazarr, enriqueciéndolos con metadata de calidad obtenida de Sonarr y Radarr. Genera manifiestos `.json` homónimos junto a cada `.srt`.

## Stack
- Python 3.10+, venv en `.venv/`
- `requests` para Bazarr (API REST nativa)
- `pyarr` para Sonarr y Radarr
- `python-dotenv` para configuración

## Scripts
| Archivo | Rol |
|---|---|
| `test_connections.py` | Valida conectividad con las 3 APIs |
| `phase2_aggregation.py` | Lee Bazarr + Sonarr/Radarr → genera `aggregated_data.json` |
| `phase3_backup.py` | Lee `aggregated_data.json` → copia `.srt` + escribe `.json` |

## Configuración clave (`.env`)
- `RUN_MODE`: `network` (SMB desde Windows) o `local` (en servidor)
- Paths de red: `SERIES_NETWORK`, `MOVIES_NETWORK`, `OUTPUT_NETWORK`
- Paths locales: `SERIES_LOCAL`, `MOVIES_LOCAL`, `OUTPUT_LOCAL`

## Decisiones de diseño
- Bazarr `/api/episodes` requiere el param `seriesid[]` (no `seriesId`)
- Los episodios usan dos llamadas: `get_episode(seriesId, series=True)` para el mapa de `episodeFileId`, luego `get_episode_file(id)` para calidad
- `bazarr_path: null` = subtítulo embebido en MKV, se omite sin error
- Nombres de carpeta sanitizados para Windows (`<>:"/\|?*` → `-`)
- Skip por tamaño de archivo para idempotencia (no reescribe si ya existe con mismo size)

## Infraestructura del servidor
- Servidor en `192.168.1.52`
- Shares SMB: `//192.168.1.52/Series`, `//192.168.1.52/Movies`
- Bazarr: puerto 6767 | Sonarr: 8989 | Radarr: 7878
