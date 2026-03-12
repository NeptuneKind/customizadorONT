# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

# ===================================================================
# Classes y Dataclasses
# ===================================================================
# Dataclass para representar un evento de progreso
@dataclass
class ProgressEvent:
    phase: str          # e.g. DETECT, LOGIN, WIFI_24, WIFI_5, WEB_CREDS, DONE
    message: str
    data: Optional[Dict[str, Any]] = None

# Tipo para la función callback de progreso
ProgressCallback = Callable[[ProgressEvent], None]