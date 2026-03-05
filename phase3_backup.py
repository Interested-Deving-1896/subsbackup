"""
Fase 3: Procesamiento Batch y Sistema de Archivos
Copia los .srt y genera manifiestos .json con metadata de origen.
"""
import json
import os
import shutil
from pathlib import Path, PurePosixPath

from dotenv import load_dotenv

load_dotenv()

# ── Configuración ────────────────────────────────────────────────────────────
RUN_MODE = os.getenv("RUN_MODE", "network").lower()  # local | network

if RUN_MODE == "local":
    SERIES_ROOT = os.getenv("SERIES_LOCAL", "/series")
    MOVIES_ROOT = os.getenv("MOVIES_LOCAL", "/movies")
    OUTPUT_DIR  = Path(os.getenv("OUTPUT_LOCAL", "/backup/subtitulos"))
else:
    SERIES_ROOT = os.getenv("SERIES_NETWORK", "//192.168.1.52/Series")
    MOVIES_ROOT = os.getenv("MOVIES_NETWORK", "//192.168.1.52/Movies")
    OUTPUT_DIR  = Path(os.getenv("OUTPUT_NETWORK", "C:/dev_backup/Subtitulos"))

INPUT_FILE = "aggregated_data.json"


# ── Path resolver ─────────────────────────────────────────────────────────────
def resolve_source(bazarr_path: str) -> Path:
    """Traduce un path de Bazarr (/series/... o /movies/...) al path real accesible."""
    posix = PurePosixPath(bazarr_path)
    parts = posix.parts  # ('/', 'series', 'Show', ...)

    if len(parts) < 2:
        return Path(bazarr_path)

    prefix = parts[1].lower()  # 'series' | 'movies'
    relative = str(posix.relative_to(f"/{parts[1]}"))

    if prefix == "series":
        return Path(SERIES_ROOT) / relative
    elif prefix == "movies":
        return Path(MOVIES_ROOT) / relative
    else:
        return Path(bazarr_path)


# ── Sanitizador de nombres de carpeta (chars inválidos en Windows) ────────────
_INVALID_WIN_CHARS = str.maketrans({c: "-" for c in r'<>:"/\|?*'})

def sanitize(name: str) -> str:
    return name.translate(_INVALID_WIN_CHARS).strip()


# ── Destination builder ───────────────────────────────────────────────────────
def build_dest_dir(record: dict) -> Path:
    """Construye la carpeta destino según el tipo de registro."""
    if record["type"] == "episode":
        season_str = f"Season {record['season']:02d}"
        return OUTPUT_DIR / "Series" / sanitize(record["series_title"]) / season_str
    else:
        folder = f"{sanitize(record['title'])} ({record['year']})"
        return OUTPUT_DIR / "Movies" / folder


# ── Processors ───────────────────────────────────────────────────────────────
def process_record(record: dict, stats: dict) -> None:
    bazarr_path = record.get("bazarr_path")

    # ── Subtítulos embebidos (sin archivo físico) ──
    if bazarr_path is None:
        stats["skipped_embedded"] += 1
        return

    src = resolve_source(bazarr_path)

    # ── Verificar que el origen existe ────────────
    if not src.exists():
        label = _record_label(record)
        print(f"  [MISSING] {label}  →  {src}")
        stats["missing"] += 1
        return

    dest_dir  = build_dest_dir(record)
    dest_srt  = dest_dir / src.name
    dest_json = dest_srt.with_suffix(".json")

    dest_dir.mkdir(parents=True, exist_ok=True)

    # ── Saltar si ya existe y tiene el mismo tamaño ──
    if dest_srt.exists() and dest_srt.stat().st_size == src.stat().st_size:
        stats["skipped_unchanged"] += 1
        return

    # ── Copiar .srt ────────────────────────────────
    try:
        shutil.copy2(src, dest_srt)
    except Exception as e:
        print(f"  [ERROR] Copia fallida: {src.name}  →  {e}")
        stats["errors"] += 1
        return

    # ── Escribir manifiesto .json ──────────────────
    with open(dest_json, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    label = _record_label(record)
    print(f"  ✓ {label}  [{record.get('language_code','?')}]  →  {dest_srt.name}")
    stats["copied"] += 1


def _record_label(record: dict) -> str:
    if record["type"] == "episode":
        return (f"{record['series_title']} "
                f"S{record['season']:02d}E{record['episode']:02d} "
                f"'{record['episode_title']}'")
    return f"{record['title']} ({record['year']})"


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 55)
    print(f"  SBSM — Fase 3: Backup  [{RUN_MODE.upper()}]")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 55)

    with open(INPUT_FILE, encoding="utf-8") as f:
        records: list[dict] = json.load(f)

    stats = {
        "copied":            0,
        "skipped_unchanged": 0,
        "skipped_embedded":  0,
        "missing":           0,
        "errors":            0,
    }

    # Agrupar por tipo para mejor legibilidad del log
    episodes = [r for r in records if r["type"] == "episode"]
    movies   = [r for r in records if r["type"] == "movie"]

    if episodes:
        print(f"\n[SERIES]  ({len(episodes)} registros)")
        for record in episodes:
            process_record(record, stats)

    if movies:
        print(f"\n[PELÍCULAS]  ({len(movies)} registros)")
        for record in movies:
            process_record(record, stats)

    print(f"\n{'─'*55}")
    print(f"  Copiados:          {stats['copied']}")
    print(f"  Sin cambios:       {stats['skipped_unchanged']}")
    print(f"  Embebidos (skip):  {stats['skipped_embedded']}")
    print(f"  Faltantes:         {stats['missing']}")
    print(f"  Errores:           {stats['errors']}")
    print(f"{'─'*55}")


if __name__ == "__main__":
    main()
