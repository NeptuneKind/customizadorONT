# ===================================================================
# Imports
# ===================================================================
import json
from pathlib import Path
from typing import Any, Dict

# ===================================================================
# Declaración de diccionario de settings
# ===================================================================
DEFAULT_SETTINGS: Dict[str, Any] = {
    "headless": False,
    "targets": {
        "wifi_24_ssid": "",
        "wifi_24_pass": "",
        "wifi_5_ssid": "",
        "wifi_5_pass": ""
    },
    "web_credentials": {
        "change_web_credentials": False,
        "new_user": "",
        "new_pass": ""
    },
    "login_candidates": {
        "huawei": [{"user": "root", "pass": "admin"}, {"user": "telecomadmin", "pass": "F0xB734Fr3@j%YEP"}],
        "zte": [{"user": "root", "pass": "admin"}, {"user": "admin", "pass": "Zgs12O5TSa2l3o9"}],
        "fiber": [{"user": "root", "pass": "admin"}, {"user": "admin", "pass": "z#Wh46QN@52Rm%j5"}],
    },
    "selenium": {
        "chromedriver_path": "",
        "chrome_binary_path": ""
    }
}

# ===================================================================
# Métodos de settings
# ===================================================================
def get_settings_path(CONFIG_DIR: Path) -> Path:
    """
    Settings persistentes dentro del repo: ./config/settings.json
    """
    return CONFIG_DIR / "settings.json"

def load_or_init_settings(*, PROJECT_ROOT: Path, CONFIG_DIR: Path) -> Dict[str, Any]:
    """
    Carga ./config/settings.json.
    Si no existe, lo crea con DEFAULT_SETTINGS.
    Hace merge para garantizar claves.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    settings_path = get_settings_path(CONFIG_DIR)

    if not settings_path.exists():
        # Set defaults con chromedriver relativo (solo si no viene definido)
        defaults = dict(DEFAULT_SETTINGS)
        defaults["selenium"] = dict(DEFAULT_SETTINGS["selenium"])
        defaults["selenium"]["chromedriver_path"] = str(
            PROJECT_ROOT / "src" / "backend" / "drivers" / "chromedriver.exe"
        )

        with settings_path.open("w", encoding="utf-8") as f:
            json.dump(defaults, f, ensure_ascii=False, indent=2)
        return defaults

    try:
        with settings_path.open("r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        # Si está corrupto, regresamos defaults sin sobreescribir.
        defaults = dict(DEFAULT_SETTINGS)
        defaults["selenium"] = dict(DEFAULT_SETTINGS["selenium"])
        defaults["selenium"]["chromedriver_path"] = str(
            PROJECT_ROOT / "src" / "backend" / "drivers" / "chromedriver.exe"
        )
        return defaults

    # Merge top-level + sub-dicts
    merged: Dict[str, Any] = dict(DEFAULT_SETTINGS)
    merged.update(data)

    for k in ("targets", "web_credentials", "login_candidates", "selenium"):
        base = DEFAULT_SETTINGS.get(k, {})
        incoming = data.get(k, {}) if isinstance(data, dict) else {}
        if isinstance(base, dict) and isinstance(incoming, dict):
            merged[k] = {**base, **incoming}
        else:
            merged[k] = incoming or base

    # Fallback de chromedriver si quedó vacío
    if not merged.get("selenium", {}).get("chromedriver_path"):
        merged["selenium"]["chromedriver_path"] = str(
            PROJECT_ROOT / "src" / "backend" / "drivers" / "chromedriver.exe"
        )

    return merged

def save_settings(*, CONFIG_DIR: Path, settings: Dict[str, Any]) -> None:
    """
    Guarda ./config/settings.json
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    settings_path = get_settings_path(CONFIG_DIR)
    with settings_path.open("w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def resolve_headless(settings: Dict[str, Any], args: Any) -> bool:
    """
    Prioridad: flags CLI -> settings.json
    args debe tener: headless, no_headless (bool)
    """
    headless_cli = bool(getattr(args, "headless", False))
    no_headless_cli = bool(getattr(args, "no_headless", False))

    if headless_cli and no_headless_cli:
        return True
    if headless_cli:
        return True
    if no_headless_cli:
        return False
    return bool(settings.get("headless", False))