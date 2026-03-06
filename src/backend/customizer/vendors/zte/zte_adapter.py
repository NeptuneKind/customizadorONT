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

    def _normalize_optional_text(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        value = str(value).strip()
        return value if value else None

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

        navigator = ZTENavigator(
            driver=ctx.driver,
            base_url=f"http://{ctx.ip}",
            timeout_s=10,
        )

        try:
            self._emit(progress, "LOGIN", "Abriendo GUI ZTE", {"ip": ctx.ip})
            navigator.open_root()

            self._emit(progress, "LOGIN", "Iniciando sesión con credenciales por defecto", None)
            navigator.login_default(username="root", password="admin")

            self._emit(progress, "LOGIN", "Ensure session ready", None)
            navigator.wait_session_ready()

            wifi_plan = getattr(plan, "wifi", None)
            if wifi_plan is not None and getattr(wifi_plan, "enabled", False):
                self._emit(progress, "WIFI", "Abriendo SSID 2.4GHz", {"ssid_index": 0})
                navigator.open_wifi_ssid(0)

                self._emit(progress, "WIFI", "Leyendo estado actual de WiFi 2.4GHz", None)
                wifi24_before = navigator.read_wifi_band(index=0)
                result.steps.append({
                    "step": "wifi_24_before",
                    "data": wifi24_before,
                })

                desired_ssid_24 = self._normalize_optional_text(getattr(wifi_plan, "ssid_24", None))
                desired_pass_24 = self._normalize_optional_text(getattr(wifi_plan, "pass_24", None))

                desired_ssid_5 = self._normalize_optional_text(getattr(wifi_plan, "ssid_5", None))
                desired_pass_5 = self._normalize_optional_text(getattr(wifi_plan, "pass_5", None))

                changed_any = False

                if desired_ssid_24 is not None or desired_pass_24 is not None:
                    self._emit(
                        progress,
                        "WIFI",
                        "Aplicando cambios WiFi 2.4GHz",
                        {
                            "ssid_24": desired_ssid_24,
                            "pass_24_set": desired_pass_24 is not None,
                        },
                    )
                    wifi24_change = navigator.update_wifi_band(
                        index=0,
                        ssid=desired_ssid_24,
                        password=desired_pass_24,
                    )
                    result.steps.append({
                        "step": "wifi_24_change",
                        "data": wifi24_change,
                    })
                    changed_any = True

                # 5 GHz opcional
                if desired_ssid_5 is not None or desired_pass_5 is not None:
                    self._emit(
                        progress,
                        "WIFI",
                        "Preparando lectura/cambio de WiFi 5GHz",
                        {"ssid_index": 3},
                    )

                    try:
                        wifi5_before = navigator.read_wifi_band(index=3)
                        result.steps.append({
                            "step": "wifi_5_before",
                            "data": wifi5_before,
                        })

                        self._emit(
                            progress,
                            "WIFI",
                            "Intentando aplicar cambios WiFi 5GHz",
                            {
                                "ssid_5": desired_ssid_5,
                                "pass_5_set": desired_pass_5 is not None,
                            },
                        )

                        wifi5_change = navigator.update_wifi_band(
                            index=3,
                            ssid=desired_ssid_5,
                            password=desired_pass_5,
                        )
                        result.steps.append({
                            "step": "wifi_5_change",
                            "data": wifi5_change,
                        })
                        changed_any = True
                    except Exception as exc:
                        result.steps.append({
                            "step": "wifi_5_skip",
                            "data": {"reason": str(exc)},
                        })

                if changed_any:
                    self._emit(progress, "WIFI", "Validando lectura final WiFi 2.4GHz", None)
                    wifi24_after = navigator.read_wifi_band(index=0)

                    result.steps.append({
                        "step": "wifi_24_after",
                        "data": wifi24_after,
                    })

                    # Validación de 2.4 GHz
                    if desired_ssid_24 is not None and wifi24_after.get("ssid") != desired_ssid_24:
                        result.errors.append(
                            f"SSID 2.4GHz no coincide. Esperado='{desired_ssid_24}' obtenido='{wifi24_after.get('ssid')}'"
                        )

                    if desired_pass_24 is not None and wifi24_after.get("password") != desired_pass_24:
                        result.errors.append(
                            "Password 2.4GHz no coincide con el valor esperado"
                        )

                    # Validación opcional de 5 GHz
                    if desired_ssid_5 is not None or desired_pass_5 is not None:
                        try:
                            self._emit(progress, "WIFI", "Abriendo SSID 5GHz para validación final", {"ssid_index": 3})
                            wifi5_after = navigator.read_wifi_band(index=3)

                            result.steps.append({
                                "step": "wifi_5_after",
                                "data": wifi5_after,
                            })

                            if desired_ssid_5 is not None and wifi5_after.get("ssid") != desired_ssid_5:
                                result.errors.append(
                                    f"SSID 5GHz no coincide. Esperado='{desired_ssid_5}' obtenido='{wifi5_after.get('ssid')}'"
                                )

                            if desired_pass_5 is not None and wifi5_after.get("password") != desired_pass_5:
                                result.errors.append(
                                    "Password 5GHz no coincide con el valor esperado"
                                )
                        except Exception as exc:
                            result.steps.append({
                                "step": "wifi_5_validate_skip",
                                "data": {"reason": str(exc)},
                            })

                else:
                    result.steps.append({
                        "step": "wifi_skip",
                        "data": {"reason": "wifi.enabled=True pero no se recibieron valores a cambiar"},
                    })

            else:
                result.steps.append({
                    "step": "wifi_disabled",
                    "data": {"reason": "El plan no habilitó cambios WiFi"},
                })

            # TODO:
            # - web_credentials
            # - firmware
            # Se dejan fuera por ahora para no mezclar responsabilidades.

            result.ok = len(result.errors) == 0
            return result

        except Exception as exc:
            result.errors.append(str(exc))
            result.ok = False
            return result