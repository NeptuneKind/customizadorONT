# ===================================================================
# Imports
# ===================================================================
import os
import sys
import json
import argparse
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Callable

from config.settings import load_or_init_settings, resolve_headless
from config.logging import setup_logging, get_logger

from src.backend.core.monitoring import wait_for_device_ip, detect_vendor_and_model
from src.backend.core.report import write_json_report

# ===================================================================
# Paths del proyecto e IPs por defecto
# ===================================================================
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config"
SRC_DIR = PROJECT_ROOT / "src"
BACKEND_DIR = SRC_DIR / "backend"
FRONTEND_DIR = SRC_DIR / "frontend"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_CUSTOM_DIR = REPORTS_DIR / "customizations"
LOGS_DIR = PROJECT_ROOT / "logs"

DEFAULT_IPS = ["192.168.100.1", "192.168.1.1"]

# ===================================================================
# Métodos de proyecto
# ===================================================================
def add_src_to_sys_path() -> None:
    """
    Permite imports tipo: from backend.core.ping import ...
    sin depender de instalación como paquete.
    """
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

def ensure_directories() -> None:
    """
    Crea los directorios necesarios si no existen.
    """
    for directory in [CONFIG_DIR, REPORTS_DIR, REPORTS_CUSTOM_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True) # Crea el directorio si no existe

def today_reports_dir() -> Path:
    """
    Devuelve el path del directorio de reportes para el día actual.
    reports/DD-MM-YYYY/
    """
    date = datetime.now().strftime("%d-%m-%Y")
    path = REPORTS_CUSTOM_DIR / date
    path.mkdir(parents=True, exist_ok=True)
    return path

# ===================================================================
# Parser
# ===================================================================
def build_parser() -> argparse.ArgumentParser:
    """
    Parser de argumentos CLI (opcional).
    Permite ejecutar: python main.py --debug --headless
    """
    p = argparse.ArgumentParser(prog="ONT Customizador")
    p.add_argument("--debug", action="store_true", help="Logging detallado.")
    p.add_argument("--headless", action="store_true", help="Forzar Selenium headless.")
    p.add_argument("--no-headless", action="store_true", help="Forzar Selenium visible.")
    return p

# ===================================================================
# Main
# ===================================================================
def main() -> int:
    add_src_to_sys_path()
    ensure_directories()

    parser = build_parser()
    args = parser.parse_args()

    setup_logging(debug=bool(args.debug), logs_dir=LOGS_DIR)
    print("LOGGING SETUP DONE") # debug

    settings = load_or_init_settings(PROJECT_ROOT = PROJECT_ROOT, CONFIG_DIR = CONFIG_DIR)
    headless = resolve_headless(settings, args)

    ip = wait_for_device_ip(DEFAULT_IPS, overall_timeout_s=60)
    det = detect_vendor_and_model(ip)

    payload = {"ok": True, "ip": det.ip, "vendor": det.vendor, "model_code": det.model_code, "product_name": det.product_name}
    write_json_report(reports_day_dir=today_reports_dir(), payload=payload, vendor=det.vendor, ip=det.ip, model_code=det.model_code)

    log = get_logger("MAIN")
    log.info("Boot OK")
    log.info("headless=%s", headless)
    log.info("settings_path=%s", (CONFIG_DIR / "settings.json"))
    log.info("reports_today=%s", today_reports_dir())

    # Temporary default behavior for debug runs:
    # Later this will start UI or run customization flow.
    return 0

if __name__ == "__main__":
    raise SystemExit(main())