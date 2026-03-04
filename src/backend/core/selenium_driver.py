# ===================================================================
# Imports
# ===================================================================
from pathlib import Path
from typing import Optional, Dict, Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from config.logging import get_logger

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
    chromedriver_path = str(selenium_cfg.get("chromedriver_path", "") or "").strip()
    chrome_binary_path = str(selenium_cfg.get("chrome_binary_path", "") or "").strip()

    if not chromedriver_path:
        raise ValueError("Falta selenium.chromedriver_path en settings")
    
    # Resolver ruta relativa contra project_root
    driver_path = Path(chromedriver_path)
    if not driver_path.is_absolute():
        driver_path = (project_root / driver_path).resolve()

    chrome_options = Options()

    if chrome_binary_path:
        chrome_options.binary_location = chrome_binary_path
        log_sel.info("Usando binario de Chrome: %s", chrome_binary_path)

    if headless:
        chrome_options.add_argument("--headless=new")

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--log-level=3")

    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-insecure-localhost")

    service = Service(chromedriver_path)

    log_sel.info("Iniciando ChromeDriver: %s headless=%s", chromedriver_path, headless)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(page_load_timeout_s)
    return driver