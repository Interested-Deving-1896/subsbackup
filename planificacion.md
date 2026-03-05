# Arquitectura y Plan de Desarrollo: Sistema de Backup de Subtítulos y Metadata (SBSM)

## 1. Visión General del Proyecto
Desarrollo de un script automatizado para la extracción, enriquecimiento y respaldo de subtítulos (`.srt`) gestionados por Bazarr, cruzando información con las bases de datos de Sonarr y Radarr mediante sus respectivas APIs REST. El objetivo es preservar el archivo físico del subtítulo junto con un manifiesto JSON que contenga su metadata de origen (resolución, release group, etc.) para facilitar futuras restauraciones.

## 2. Stack Tecnológico Sugerido
* **Lenguaje:** Python 3.10+ (Ideal para manejo de diccionarios, I/O de archivos y peticiones HTTP).
* **Gestión de Dependencias y Entorno:** `pipenv` o `poetry`.
* **Librerías Core:**
    * `requests`: Para comunicación nativa con la API de Bazarr.
    * `pyarr`: Wrapper oficial (recomendado) para interactuar con las APIs v3 de Sonarr y Radarr.
    * `python-dotenv`: Para manejo seguro de API Keys y URLs en un archivo `.env`.
    * `pathlib` y `shutil`: Para operaciones de sistema de archivos seguras y multiplataforma.
* **Sincronización Cloud:** `Rclone` (ejecutado vía `subprocess`).

---

## 3. Fases de Desarrollo

### Fase 1: Prueba de Concepto y Conectividad (PoC)
**Objetivo:** Validar la conexión y autenticación contra las 3 APIs.
**Tareas:**
1.  Configurar archivo `.env` con las variables: `BAZARR_URL`, `BAZARR_API_KEY`, `SONARR_URL`, `SONARR_API_KEY`, `RADARR_URL`, `RADARR_API_KEY`.
2.  Implementar scripts de test básicos que realicen un `GET` simple.
    * *Bazarr:* Petición a `/api/system/status`.
    * *Sonarr/Radarr:* Instanciar cliente `PyArr` y ejecutar `get_system_status()`.
**Entregable:** Script `test_connections.py` que imprima un log de OK/FAIL para cada servicio.

### Fase 2: Motor de Agregación de Datos
**Objetivo:** Mapear los IDs de Bazarr con los IDs de Sonarr/Radarr para unificar la metadata.
**Flujo Lógico:**
1.  Obtener lista completa de subtítulos desde Bazarr (`GET /api/episodes` y `GET /api/movies`).
2.  Iterar sobre cada elemento e identificar su origen (Serie o Película).
3.  Extraer el identificador puente (`sonarrEpisodeId` o `radarrMovieId`).
4.  Consultar la API correspondiente (ej. `GET /api/v3/episode/{id}` en Sonarr).
5.  Construir un diccionario de Python unificado que contenga:
    * `bazarr_path`: Ruta actual del `.srt`.
    * `language`: Idioma del subtítulo.
    * `quality`: Resolución y fuente (ej. `WEBDL-1080p`).
    * `release_group`: Grupo de release (ej. `NTb`, `YIFY`).
    * `original_filename`: Nombre original del archivo de video (útil para re-sincronización).
**Consideraciones:** Manejar excepciones (`try/except`) para "registros huérfanos" (subtítulos en Bazarr cuyo video ya fue eliminado de Sonarr/Radarr).

### Fase 3: Procesamiento Batch y Sistema de Archivos
**Objetivo:** Copiar los archivos físicos y generar los manifiestos JSON.
**Flujo Lógico:**
1.  Definir un `OUTPUT_DIR` principal.
2.  Por cada subtítulo procesado en la Fase 2:
    * Crear la estructura de directorios dinámicamente usando `pathlib`. Se sugiere: `OUTPUT_DIR/Series/NombreSerie/Season XX/`.
    * Copiar el archivo `.srt` original usando `shutil.copy2()` para preservar los timestamps.
    * Volcar el diccionario de metadata de la Fase 2 en un archivo `.json` homónimo.
**Optimización:** Implementar validación de hashes (MD5/SHA1) o chequeo de fecha de modificación para evitar copiar archivos que ya existen en el backup y no han cambiado.

### Fase 4: Sincronización en la Nube
**Objetivo:** Subir el backup local a un proveedor cloud (Google Drive, OneDrive, etc.).
**Implementación Sugerida:** No utilizar las APIs nativas de las nubes (para evitar lidiar con refresco de tokens y rate limits).
1.  Configurar un *remote* en Rclone a nivel sistema operativo.
2.  Desde Python, utilizar la librería `subprocess` para invocar:
    `rclone sync /ruta/al/OUTPUT_DIR remote_name:/Backup_Subtitulos --transfers=4 --checkers=8`
**Beneficios:** El comando `sync` garantiza que el destino sea un espejo exacto del origen, manejando subidas paralelas y reintentos automáticamente.

### Fase 5: Automatización y Despliegue
**Objetivo:** Ejecución desatendida del sistema completo.
**Estrategias:**
* **Enfoque Pull (Basado en Cron/Scheduled Task):** Empaquetar el script en un contenedor Docker (opcional) o configurarlo en el crontab del servidor para que se ejecute diariamente de madrugada (ej. `0 3 * * * python main.py`).
* **Enfoque Push (Event-driven):** Configurar Bazarr (Settings -> Custom Scripts) para disparar el script pasando argumentos específicos cada vez que un nuevo subtítulo sea descargado exitosamente (recomendado para la Fase 2 del proyecto).

---

## 4. Estructura de Salida Esperada (Ejemplo)
```text
/Backup_Subtitulos/
├── Movies/
│   └── The Matrix (1999)/
│       ├── The.Matrix.1999.es.srt
│       └── The.Matrix.1999.es.json
└── Series/
    └── Severance/
        └── Season 01/
            ├── Severance.S01E01.es.srt
            └── Severance.S01E01.es.json
