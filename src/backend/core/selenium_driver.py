# ===================================================================
# Imports
# ===================================================================
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from config.logging import get_logger

# ===================================================================
# Helpers para resolver rutas a chromedriver y chrome binary, soportando ejecución frozen (PyInstaller) y desde código fuente.
# ===================================================================
def _backend_root_from_here() -> Path:
    """
    Resuelve el root '.../src/backend' desde este archivo.
    Soporta si el archivo está en src/backend/core/selenium_driver.py (caso actual)
    o si se mueve a otra subcarpeta.
    """
    here = Path(__file__).resolve()
    backend_root = here.parent
    if backend_root.name != "backend":
        backend_root = backend_root.parent
    return backend_root


def _get_chromedriver_path() -> Path:
    """
    Devuelve la ruta al chromedriver.exe ubicado en:
      src/backend/drivers/chromedriver.exe

    Soporta ejecución frozen (PyInstaller) y desde código fuente.
    """
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS) / "backend" / "drivers"
    else:
        base_path = _backend_root_from_here() / "drivers"

    driver_path = base_path / "chromedriver.exe"
    log_sel.info("[DEBUG] chromedriver path = %s exists=%s", str(driver_path), driver_path.exists())
    return driver_path


def _get_chrome_binary_path() -> Path:
    """
    Devuelve la ruta al chrome.exe ubicado en:
      src/backend/drivers/chrome/chrome.exe

    Soporta ejecución frozen (PyInstaller) y desde código fuente.
    """
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS) / "backend" / "drivers" / "chrome"
    else:
        base_path = _backend_root_from_here() / "drivers" / "chrome"

    chrome_binary = base_path / "chrome.exe"
    log_sel.info("[DEBUG] chrome binary = %s exists=%s", str(chrome_binary), chrome_binary.exists())
    return chrome_binary

# ===================================================================
# Definiciones
# ===================================================================
log_sel = get_logger("SELENIUM")

def build_chrome_driver(
    *,
    settings: Dict[str, Any],
    headless: bool,
    project_root: Path,
    page_load_timeout_s: int = 15,
) -> webdriver.Chrome:
    """
    Crea un Chrome WebDriver.
    Utiliza la configuración de selenium del settings:
      settings["selenium"]["chromedriver_path"]
      settings["selenium"]["chrome_binary_path"] (optional)
    """
    # Ruta Chrome WebDriver: src/backend/drivers
    selenium_cfg = settings.get("selenium", {}) if isinstance(settings, dict) else {}

    # Si settings trae paths, se respetan; si no, se calculan con la misma lógica del tester.
    chromedriver_path_cfg = str(selenium_cfg.get("chromedriver_path", "") or "").strip()
    chrome_binary_path_cfg = str(selenium_cfg.get("chrome_binary_path", "") or "").strip()

    driver_path = Path(chromedriver_path_cfg) if chromedriver_path_cfg else _get_chromedriver_path()
    chrome_bin_path = Path(chrome_binary_path_cfg) if chrome_binary_path_cfg else _get_chrome_binary_path()
    
    # Normalizar paths si vinieron relativos desde settings (pero sin salirnos del repo)
    if not driver_path.is_absolute():
        driver_path = (project_root / driver_path).resolve()

    if not chrome_bin_path.is_absolute():
        chrome_bin_path = (project_root / chrome_bin_path).resolve()

    if not driver_path.exists():
        raise FileNotFoundError(f"chromedriver.exe no encontrado: {driver_path}")

    chrome_options = Options()

    # Forzar chrome.exe del repo (si existe) para evitar mismatch con Chrome del sistema
    if chrome_bin_path and chrome_bin_path.exists():
        chrome_options.binary_location = str(chrome_bin_path)
        log_sel.info("Usando binario de Chrome: %s", str(chrome_bin_path))
    else:
        # Si esto pasa, Selenium usará Chrome del sistema y puede romper por mismatch.
        log_sel.warning("No se encontró chrome.exe en drivers; se usará Chrome del sistema.")

    if headless:
        chrome_options.add_argument("--headless=new")

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--log-level=3")

    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-insecure-localhost")

    service = Service(executable_path=str(driver_path))

    log_sel.info("Iniciando ChromeDriver: %s headless=%s", str(driver_path), headless)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(page_load_timeout_s)
    return driver