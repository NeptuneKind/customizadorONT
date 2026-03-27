from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Dataclass para representar el estado de cada sección del plan (wifi, web_credentials, ip_plan)
@dataclass
class PlanState:
    enabled: bool = False
    fields_enabled: bool = False

# Dataclass para representar el estado de la sección de configuración estándar, con campos para SSID y contraseñas wifi, y contraseñas web
@dataclass
class StandardSettingsState:
    wifi_ssid_24: str = ""
    wifi_password_24: str = ""
    wifi_ssid_5: str = ""
    wifi_password_5: str = ""
    web_old_password: str = ""
    web_new_password: str = ""

# Dataclass para representar el estado de la ejecución, con campos para el proveedor, IP actual, código de modelo, slot seleccionado, IP calculada, estados de cada sección del plan, progreso de cada paso y logs de ejecución
@dataclass
class ExecutionState:
    vendor: str = "--"
    current_ip: str = "--"
    model_code: str = "--"
    selected_slot: Optional[int] = None
    calculated_ip: str = ""
    wifi: PlanState = field(default_factory=PlanState)
    web_credentials: PlanState = field(default_factory=PlanState)
    ip_plan: PlanState = field(default_factory=PlanState)
    progress: Dict[str, str] = field(
        default_factory=lambda: {
            "login": "pending",
            "wifi": "pending",
            "web_credentials": "pending",
            "ip": "pending",
        }
    )
    logs: List[str] = field(default_factory=list)

# Dataclass principal para representar el estado global de la aplicación, con campos para el estado de ejecución y el estado de configuración estándar, y métodos para agregar logs y sincronizar las reglas del plan
@dataclass
class AppState:
    execution: ExecutionState = field(default_factory=ExecutionState)
    standard_settings: StandardSettingsState = field(default_factory=StandardSettingsState)

    # Método para agregar un mensaje al log de ejecución
    def append_log(self, message: str) -> None:
        self.execution.logs.append(message)

    # Método para sincronizar las reglas de habilitación de campos en función de qué secciones del plan están activas
    def sync_plan_rules(self) -> None:
        wifi_enabled = self.execution.wifi.enabled
        web_enabled = self.execution.web_credentials.enabled
        ip_enabled = self.execution.ip_plan.enabled

        if ip_enabled:
            self.execution.wifi.enabled = False
            self.execution.web_credentials.enabled = False
            self.execution.wifi.fields_enabled = False
            self.execution.web_credentials.fields_enabled = False
            self.execution.ip_plan.fields_enabled = True
            return

        if wifi_enabled or web_enabled:
            self.execution.ip_plan.enabled = False
            self.execution.ip_plan.fields_enabled = False
            self.execution.wifi.fields_enabled = wifi_enabled
            self.execution.web_credentials.fields_enabled = web_enabled
            return

        self.execution.wifi.fields_enabled = False
        self.execution.web_credentials.fields_enabled = False
        self.execution.ip_plan.fields_enabled = False