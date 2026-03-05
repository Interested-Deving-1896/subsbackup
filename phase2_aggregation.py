"""
Fase 2: Motor de Agregación de Datos
Mapea subtítulos de Bazarr con metadata de calidad de Sonarr y Radarr.
"""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from pyarr import SonarrAPI, RadarrAPI

load_dotenv()

# ── Configuración ────────────────────────────────────────────────────────────
BAZARR_URL     = os.getenv("BAZARR_URL")
BAZARR_API_KEY = os.getenv("BAZARR_API_KEY")
SONARR_URL     = os.getenv("SONARR_URL")
SONARR_API_KEY = os.getenv("SONARR_API_KEY")
RADARR_URL     = os.getenv("RADARR_URL")
RADARR_API_KEY = os.getenv("RADARR_API_KEY")

_bz = {"X-API-KEY": BAZARR_API_KEY}
sonarr = SonarrAPI(SONARR_URL, SONARR_API_KEY)
radarr = RadarrAPI(RADARR_URL, RADARR_API_KEY)


# ── Caches ───────────────────────────────────────────────────────────────────
_episode_file_cache: dict = {}   # episodeFileId → file_data
_radarr_movie_cache: dict = {}   # radarrId      → movie_data


# ── Bazarr: fetchers ─────────────────────────────────────────────────────────
def get_bazarr_series() -> list:
    r = requests.get(f"{BAZARR_URL}/api/series", headers=_bz, timeout=15)
    r.raise_for_status()
    return r.json().get("data", [])


def get_bazarr_episodes(sonarr_series_id: int) -> list:
    r = requests.get(
        f"{BAZARR_URL}/api/episodes",
        headers=_bz,
        params={"seriesid[]": sonarr_series_id},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("data", []) if isinstance(data, dict) else []


def get_bazarr_movies(start: int = 0, length: int = 100) -> dict:
    r = requests.get(
        f"{BAZARR_URL}/api/movies",
        headers=_bz,
        params={"start": start, "length": length},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


# ── Sonarr: helpers con caché ────────────────────────────────────────────────
def build_sonarr_episode_file_map(sonarr_series_id: int) -> dict:
    """Devuelve {sonarrEpisodeId: episodeFileId} para la serie dada."""
    episodes = sonarr.get_episode(sonarr_series_id, series=True)
    return {
        ep["id"]: ep["episodeFileId"]
        for ep in episodes
        if ep.get("hasFile") and ep.get("episodeFileId")
    }


def get_episode_file(episode_file_id: int) -> dict | None:
    if episode_file_id not in _episode_file_cache:
        try:
            _episode_file_cache[episode_file_id] = sonarr.get_episode_file(episode_file_id)
        except Exception as e:
            print(f"    [WARN] episodeFile {episode_file_id}: {e}")
            _episode_file_cache[episode_file_id] = None
    return _episode_file_cache[episode_file_id]


# ── Radarr: helpers con caché ────────────────────────────────────────────────
def get_radarr_movie(radarr_id: int) -> dict | None:
    if radarr_id not in _radarr_movie_cache:
        try:
            _radarr_movie_cache[radarr_id] = radarr.get_movie(id_=radarr_id)
        except Exception as e:
            print(f"    [WARN] radarrId {radarr_id}: {e}")
            _radarr_movie_cache[radarr_id] = None
    return _radarr_movie_cache[radarr_id]


# ── Extractores de calidad ───────────────────────────────────────────────────
def extract_quality(media_file: dict) -> dict:
    """Campos de calidad comunes a episodeFile y movieFile."""
    q = media_file.get("quality", {}).get("quality", {})
    return {
        "quality":          q.get("name", "Unknown"),
        "resolution":       q.get("resolution"),
        "source":           q.get("source"),
        "release_group":    media_file.get("releaseGroup") or "",
        "original_filename": Path(media_file.get("path", "")).name,
        "video_path":       media_file.get("path", ""),
    }


# ── Procesadores ─────────────────────────────────────────────────────────────
def process_series() -> list:
    records = []
    all_series = get_bazarr_series()

    for series in all_series:
        title           = series["title"]
        sonarr_series_id = series["sonarrSeriesId"]
        print(f"\n  → {title}  (sonarrSeriesId={sonarr_series_id})")

        # Un solo GET para obtener todos los episodeFileIds de la serie
        ep_file_map = build_sonarr_episode_file_map(sonarr_series_id)

        episodes = get_bazarr_episodes(sonarr_series_id)
        eps_with_subs = [e for e in episodes if e.get("subtitles")]

        if not eps_with_subs:
            print("    [INFO] Sin episodios con subtítulos")
            continue

        for ep in eps_with_subs:
            sonarr_ep_id   = ep["sonarrEpisodeId"]
            ep_file_id     = ep_file_map.get(sonarr_ep_id)
            quality_fields = {}

            if ep_file_id:
                ef = get_episode_file(ep_file_id)
                if ef:
                    quality_fields = extract_quality(ef)
            else:
                print(f"    [ORPHAN] S{ep['season']:02d}E{ep['episode']:02d} "
                      f"'{ep['title']}' — sin episodeFile en Sonarr")

            for sub in ep["subtitles"]:
                records.append({
                    "type":             "episode",
                    "series_title":     title,
                    "series_path":      series["path"],
                    "season":           ep["season"],
                    "episode":          ep["episode"],
                    "episode_title":    ep["title"],
                    "sonarr_series_id": sonarr_series_id,
                    "sonarr_episode_id": sonarr_ep_id,
                    "bazarr_path":      sub["path"],
                    "language":         sub["name"],
                    "language_code":    sub["code2"],
                    "forced":           sub["forced"],
                    "hi":               sub["hi"],
                    **quality_fields,
                })
                q = quality_fields.get("quality", "?")
                rg = quality_fields.get("release_group", "?")
                print(f"    ✓ S{ep['season']:02d}E{ep['episode']:02d} "
                      f"[{sub['code2']}] {q} / {rg}")

    return records


def process_movies() -> list:
    records = []
    raw    = get_bazarr_movies(start=0, length=9999)
    movies = raw.get("data", [])

    for movie in movies:
        if not movie.get("subtitles"):
            print(f"  → {movie['title']} ({movie['year']})  [SIN SUBS — omitida]")
            continue

        radarr_id = movie["radarrId"]
        title     = movie["title"]
        print(f"\n  → {title} ({movie['year']})  (radarrId={radarr_id})")

        quality_fields = {}
        radarr_movie   = get_radarr_movie(radarr_id)
        if radarr_movie:
            movie_file = radarr_movie.get("movieFile")
            if movie_file:
                quality_fields = extract_quality(movie_file)
            else:
                print(f"    [ORPHAN] Sin movieFile en Radarr")
        else:
            print(f"    [ORPHAN] Película no encontrada en Radarr")

        for sub in movie["subtitles"]:
            records.append({
                "type":          "movie",
                "title":         title,
                "year":          movie["year"],
                "imdb_id":       movie.get("imdbId"),
                "radarr_id":     radarr_id,
                "bazarr_path":   sub["path"],
                "language":      sub["name"],
                "language_code": sub["code2"],
                "forced":        sub["forced"],
                "hi":            sub["hi"],
                **quality_fields,
            })
            q  = quality_fields.get("quality", "?")
            rg = quality_fields.get("release_group", "?")
            print(f"    ✓ [{sub['code2']}] {q} / {rg}")

    return records


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> list:
    print("=" * 55)
    print("  SBSM — Fase 2: Agregación de Datos")
    print("=" * 55)

    print("\n[SERIES]")
    series_records = process_series()

    print("\n[PELÍCULAS]")
    movie_records = process_movies()

    all_records = series_records + movie_records

    print(f"\n{'─'*55}")
    print(f"Total: {len(all_records)} registros  "
          f"({len(series_records)} episodios · {len(movie_records)} películas)")

    output_file = "aggregated_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2, ensure_ascii=False)
    print(f"Guardado en: {output_file}")

    return all_records


if __name__ == "__main__":
    main()
