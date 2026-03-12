# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from selenium.webdriver.chrome.webdriver import WebDriver

from src.backend.core.monitoring import DetectedDevice

# ===================================================================
# Classes y Dataclasses
# ===================================================================
# Dataclass para almacenar el contexto completo del proceso de personalización
@dataclass
class CustomizationContext:
    project_root: Path
    settings: Dict[str, Any]
    detected: DetectedDevice
    headless: bool
    driver: Optional[WebDriver] = None

    # Getters de información clave para facilitar acceso
    @property
    def ip(self) -> str:
        return self.detected.ip

    @property
    def vendor(self) -> str:
        return self.detected.vendor

    @property
    def model_code(self) -> str:
        return self.detected.model_code