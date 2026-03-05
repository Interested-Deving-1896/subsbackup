"""
Fase 1: Prueba de Concepto y Conectividad (PoC)
Valida la conexion y autenticacion contra Bazarr, Sonarr y Radarr.
"""

import os
import sys
import requests
from dotenv import load_dotenv
from pyarr import SonarrAPI, RadarrAPI

load_dotenv()

BAZARR_URL = os.getenv("BAZARR_URL", "http://localhost:6767")
BAZARR_API_KEY = os.getenv("BAZARR_API_KEY")
SONARR_URL = os.getenv("SONARR_URL", "http://localhost:8989")
SONARR_API_KEY = os.getenv("SONARR_API_KEY")
RADARR_URL = os.getenv("RADARR_URL", "http://localhost:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY")


def check_bazarr():
    if not BAZARR_API_KEY:
        print("[SKIP] BAZARR   - API key no configurada")
        return False
    try:
        resp = requests.get(
            f"{BAZARR_URL}/api/system/status",
            headers={"X-API-KEY": BAZARR_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        version = data.get("data", {}).get("bazarr_version", "desconocida")
        print(f"[ OK ] BAZARR   - Version: {version}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] BAZARR   - No se pudo conectar a {BAZARR_URL}")
    except requests.exceptions.HTTPError as e:
        print(f"[FAIL] BAZARR   - HTTP {e.response.status_code}: {e.response.text[:80]}")
    except Exception as e:
        print(f"[FAIL] BAZARR   - Error inesperado: {e}")
    return False


def check_sonarr():
    if not SONARR_API_KEY:
        print("[SKIP] SONARR   - API key no configurada")
        return False
    try:
        sonarr = SonarrAPI(SONARR_URL, SONARR_API_KEY)
        status = sonarr.get_system_status()
        version = status.get("version", "desconocida")
        print(f"[ OK ] SONARR   - Version: {version}")
        return True
    except Exception as e:
        print(f"[FAIL] SONARR   - {e}")
    return False


def check_radarr():
    if not RADARR_API_KEY:
        print("[SKIP] RADARR   - API key no configurada")
        return False
    try:
        radarr = RadarrAPI(RADARR_URL, RADARR_API_KEY)
        status = radarr.get_system_status()
        version = status.get("version", "desconocida")
        print(f"[ OK ] RADARR   - Version: {version}")
        return True
    except Exception as e:
        print(f"[FAIL] RADARR   - {e}")
    return False


def main():
    print("=" * 45)
    print("  SBSM - Test de Conectividad (Fase 1)")
    print("=" * 45)

    results = {
        "Bazarr":  check_bazarr(),
        "Sonarr":  check_sonarr(),
        "Radarr":  check_radarr(),
    }

    print("-" * 45)
    ok = sum(results.values())
    total = len(results)
    print(f"Resultado: {ok}/{total} servicios conectados")

    if ok < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
