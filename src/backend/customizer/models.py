# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# ===================================================================
# Classes y Dataclasses
# ===================================================================
# Clase para almacenar las bandas wifi
class WifiBand(str, Enum):
    B24 = "2.4"
    B5 = "5"

# Dataclass para representar el plan de wifi a configurar
@dataclass
class WifiPlan:
    enabled: bool = False
    ssid_24: str = None
    pass_24: str = None
    ssid_5: str = None
    pass_5: str = None

# Dataclass para representar el plan de credenciales web
@dataclass
class WebCredentialsPlan:
    enabled: bool = False
    old_password: str = "admin"
    new_password: str = ""

# Dataclass para representar el plan de firmware a configurar
@dataclass
class FirmwarePlan:
    enabled: bool = False
    mode: str = "selected"  # selected|all
    files: List[str] = field(default_factory=list)

# Dataclass para almacenar el plan completo de personalización
@dataclass
class CustomizationPlan:
    wifi: WifiPlan = field(default_factory=WifiPlan)
    web_credentials: WebCredentialsPlan = field(default_factory=WebCredentialsPlan)
    firmware: FirmwarePlan = field(default_factory=FirmwarePlan)

# Dataclass para almacenar el resultado de cada paso del proceso de personalización
@dataclass
class StepResult:
    step_id: str
    ok: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: str = ""
    finished_at: str = ""

# Dataclass para almacenar el resultado del proceso de personalización
@dataclass
class CustomizationResult:
    ok: bool
    vendor: str
    model_code: str
    ip: str
    product_name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    plan: Dict[str, Any] = field(default_factory=dict)
    steps: List[StepResult] = field(default_factory=list)