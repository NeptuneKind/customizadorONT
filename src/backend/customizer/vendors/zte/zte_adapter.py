from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.backend.customizer.context import CustomizationContext
from src.backend.customizer.models import CustomizationPlan
from src.backend.customizer.progress import ProgressCallback, ProgressEvent

from .zte_navigator import ZTENavigator


@dataclass
class ZTECustomizationResult:
    ok: bool
    vendor: str
    ip: str
    model_code: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)


class ZTEAdapter:
    """
    Adaptador ZTE para aplicar el plan de customización.
    """

    supported_models = {"MOD002", "MOD009"}

    def _emit(self, progress: ProgressCallback, phase: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        progress(ProgressEvent(phase=phase, message=message, data=data))

    # Método helper para normalizar valores de texto opcionales: None, strings vacíos o solo espacios se consideran None
    def _normalize_optional_text(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        value = str(value).strip()
        return value if value else None

    # Método para crear una instancia de ZTENavigator
    def _build_navigator(self, ctx: CustomizationContext) -> ZTENavigator:
        return ZTENavigator(
            driver=ctx.driver,
            base_url=f"http://{ctx.ip}",
            timeout_s=10,
        )
    
    # Método que encapsula el login y espera sesión lista
    def _do_login(
        self,
        navigator: ZTENavigator,
        ctx: CustomizationContext,
        progress: ProgressCallback,
    ) -> None:
        self._emit(progress, "LOGIN", "Abriendo GUI ZTE", {"ip": ctx.ip})
        navigator._open_root()

        self._emit(progress, "LOGIN", "Iniciando sesión con credenciales por defecto", None)
        navigator._zte_login(username="root", password="admin")

        self._emit(progress, "LOGIN", "Sesión iniciada, esperando menú principal", None)
        navigator.wait_session_ready()
    
    # Método que aplica la parte de WiFi del plan, pero delega cada banda a _process_wifi_band()
    def _apply_wifi_plan(
        self,
        navigator: ZTENavigator,
        plan: CustomizationPlan,
        result: ZTECustomizationResult,
        progress: ProgressCallback,
    ) -> None:
        wifi_plan = getattr(plan, "wifi", None)
        if wifi_plan is None or not getattr(wifi_plan, "enabled", False):
            result.steps.append({
                "step": "wifi_disabled",
                "data": {"reason": "El plan no habilitó cambios WiFi"},
            })
            return

        desired_ssid_24 = self._normalize_optional_text(getattr(wifi_plan, "ssid_24", None))
        desired_pass_24 = self._normalize_optional_text(getattr(wifi_plan, "pass_24", None))
        desired_ssid_5 = self._normalize_optional_text(getattr(wifi_plan, "ssid_5", None))
        desired_pass_5 = self._normalize_optional_text(getattr(wifi_plan, "pass_5", None))

        if (
            desired_ssid_24 is None and desired_pass_24 is None and
            desired_ssid_5 is None and desired_pass_5 is None
        ):
            result.steps.append({
                "step": "wifi_skip",
                "data": {"reason": "wifi.enabled=True pero no se recibieron valores a cambiar"},
            })
            return

        if desired_ssid_24 is not None or desired_pass_24 is not None:
            self._process_wifi_band(
                navigator=navigator,
                index=0,
                desired_ssid=desired_ssid_24,
                desired_password=desired_pass_24,
                result=result,
                progress=progress,
            )

        if desired_ssid_5 is not None or desired_pass_5 is not None:
            try:
                self._process_wifi_band(
                    navigator=navigator,
                    index=3,
                    desired_ssid=desired_ssid_5,
                    desired_password=desired_pass_5,
                    result=result,
                    progress=progress,
                )
            except Exception as exc:
                result.steps.append({
                    "step": "wifi_5_skip",
                    "data": {"reason": str(exc)},
                })

    # Método que: navega a la banda -> lee estado actual -> aplica cambios -> lee estado final -> valida resultados
    def _process_wifi_band(
        self,
        navigator: ZTENavigator,
        index: int,
        desired_ssid: Optional[str],
        desired_password: Optional[str],
        result: ZTECustomizationResult,
        progress: ProgressCallback,
    ) -> None:
        band_label = "2.4GHz" if index == 0 else "5GHz" if index == 3 else f"index_{index}"
        band_key = "24" if index == 0 else "5" if index == 3 else str(index)

        # 1. Navegación
        self._emit(
            progress,
            "WIFI",
            f"Navegando a sección WiFi {band_label}",
            {"ssid_index": index},
        )
        #navigator._open_wifi_ssid(index) # Se abre el toggle de la banda

        # 2. Lectura inicial
        self._emit(
            progress,
            "WIFI",
            f"Leyendo estado actual WiFi {band_label}",
            {"ssid_index": index},
        )
        before_data = navigator.read_wifi_band(index=index)
        result.steps.append({
            "step": f"wifi_{band_key}_before",
            "data": before_data,
        })

        # 3. Cambio
        self._emit(
            progress,
            "WIFI",
            f"Aplicando cambios WiFi {band_label}",
            {
                "ssid_index": index,
                "ssid": desired_ssid,
                "password_set": desired_password is not None,
            },
        )
        change_data = navigator.update_wifi_band(
            index=index,
            ssid=desired_ssid,
            password=desired_password,
        )
        result.steps.append({
            "step": f"wifi_{band_key}_change",
            "data": change_data,
        })

        #navigator._open_wifi_ssid(index)

        # 4. Validación final
        self._emit(
            progress,
            "WIFI",
            f"Validando lectura final WiFi {band_label}",
            {"ssid_index": index},
        )
        after_data = navigator.read_wifi_band(index=index)
        result.steps.append({
            "step": f"wifi_{band_key}_after",
            "data": after_data,
        })

        self._validate_wifi_band(
            band_label=band_label,
            after_data=after_data,
            desired_ssid=desired_ssid,
            desired_password=desired_password,
            result=result,
        )
    
    # Método para lectura comparando con los valores finales contra los deseados y agregando errores al resultado si no coinciden
    def _validate_wifi_band(
        self,
        band_label: str,
        after_data: Dict[str, Any],
        desired_ssid: Optional[str],
        desired_password: Optional[str],
        result: ZTECustomizationResult,
    ) -> None:
        if desired_ssid is not None and after_data.get("ssid") != desired_ssid:
            result.errors.append(
                f"SSID {band_label} no coincide. Esperado='{desired_ssid}' obtenido='{after_data.get('ssid')}'"
            )

        if desired_password is not None and after_data.get("password") != desired_password:
            result.errors.append(
                f"Password {band_label} no coincide con el valor esperado"
            )

    # Método principal que aplica el plan completo usando el ZTENavigator y devuelve un resultado estructurado con toda la información relevante
    def apply(
        self,
        plan: CustomizationPlan,
        ctx: CustomizationContext,
        progress: ProgressCallback,
    ) -> ZTECustomizationResult:
        result = ZTECustomizationResult(
            ok=False,
            vendor=ctx.vendor,
            ip=ctx.ip,
            model_code=ctx.model_code,
        )

        if ctx.model_code not in self.supported_models:
            result.errors.append(f"Modelo ZTE no soportado por este adaptador: {ctx.model_code}")
            return result

        if ctx.driver is None:
            result.errors.append("El contexto no contiene WebDriver inicializado")
            return result

        navigator = self._build_navigator(ctx)

        try:
            self._do_login(
                navigator=navigator,
                ctx=ctx,
                progress=progress,
            )

            self._apply_wifi_plan(
                navigator=navigator,
                plan=plan,
                result=result,
                progress=progress,
            )

            result.ok = len(result.errors) == 0
            return result

        except Exception as exc:
            result.errors.append(str(exc))
            result.ok = False
            return result