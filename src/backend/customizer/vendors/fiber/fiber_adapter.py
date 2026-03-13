from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.backend.customizer.context import CustomizationContext
from src.backend.customizer.models import CustomizationPlan
from src.backend.customizer.progress import ProgressCallback, ProgressEvent
from src.backend.customizer.models import WifiBand

from .fiber_navigator import FiberhomeNavigator
from src.backend.customizer.product_map import resolve_product_name

@dataclass
class FiberhomeCustomizationResult:
    ok: bool
    vendor: str
    ip: str
    model_code: str
    product: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)

class FiberhomeAdapter:
    """
    Adaptador FiberHome alineado a la estructura de Huawei/ZTE.
    """

    supported_models = {"MOD001"}

    def _emit(
        self,
        progress: ProgressCallback,
        phase: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        progress(ProgressEvent(phase=phase, message=message, data=data))

    def _normalize_optional_text(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        value = str(value).strip()
        return value if value else None

    def _build_navigator(self, ctx: CustomizationContext) -> FiberhomeNavigator:
        return FiberhomeNavigator(
            driver=ctx.driver,
            base_url=f"http://{ctx.ip}",
            timeout_s=12,
        )

    def _do_login(
        self,
        navigator: FiberhomeNavigator,
        ctx: CustomizationContext,
        progress: ProgressCallback,
    ) -> None:
        candidates = (ctx.settings.get("login_candidates") or {}).get("fiberhome") or []

        if not candidates:
            raise RuntimeError("No hay candidatos de login configurados para FiberHome")

        self._emit(progress, "LOGIN", "Abriendo GUI FiberHome", {"ip": ctx.ip})
        navigator.open_home()

        last_error: Optional[Exception] = None

        for c in candidates:
            user = str(c.get("user", "") or "")
            pwd = str(c.get("pass", "") or "")

            try:
                self._emit(
                    progress,
                    "LOGIN",
                    "Probando credenciales FiberHome",
                    {"username": user},
                )
                navigator.login(username=user, password=pwd)
                navigator.ensure_logged_in()
                self._emit(progress, "LOGIN", "Sesión FiberHome iniciada", {"username": user})
                return
            except Exception as exc:
                last_error = exc

        raise RuntimeError(f"No fue posible iniciar sesión en FiberHome: {last_error}")

    def _apply_wifi_plan(
        self,
        navigator: FiberhomeNavigator,
        plan: CustomizationPlan,
        result: FiberhomeCustomizationResult,
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
                band=WifiBand.B24,
                desired_ssid=desired_ssid_24,
                desired_password=desired_pass_24,
                result=result,
                progress=progress,
            )

        if desired_ssid_5 is not None or desired_pass_5 is not None:
            self._process_wifi_band(
                navigator=navigator,
                band=WifiBand.B5,
                desired_ssid=desired_ssid_5,
                desired_password=desired_pass_5,
                result=result,
                progress=progress,
            )

    def _process_wifi_band(
        self,
        navigator: FiberhomeNavigator,
        band: WifiBand,
        desired_ssid: Optional[str],
        desired_password: Optional[str],
        result: FiberhomeCustomizationResult,
        progress: ProgressCallback,
    ) -> None:
        band_label = "2.4GHz" if band == WifiBand.B24 else "5GHz"
        band_key = "24" if band == WifiBand.B24 else "5"

        self._emit(
            progress,
            "WIFI",
            f"Navegando a sección WiFi {band_label}",
            {"band": band.name},
        )

        self._emit(
            progress,
            "WIFI",
            f"Leyendo estado actual WiFi {band_label}",
            {"band": band.name},
        )
        try:
            before_data = navigator.read_wifi_band(band=band)
        except Exception as e:
            raise RuntimeError(
                f"Error leyendo WiFi {band_label} antes de aplicar: {e}"
            )

        self._emit(
            progress,
            "WIFI",
            f"Aplicando cambios WiFi {band_label}",
            {
                "band": band.name,
                "ssid": desired_ssid,
                "password_set": desired_password is not None,
            },
        )
        try:
            change_data = navigator.update_wifi_band(
                band=band,
                ssid=desired_ssid,
                password=desired_password,
            )
        except Exception as e:
            raise RuntimeError(
                f"Error aplicando WiFi {band_label}: {e}"
            )

        self._emit(
            progress,
            "WIFI",
            f"Validando lectura final WiFi {band_label}",
            {"band": band.name},
        )
        try:
            after_data = navigator.read_wifi_band(band=band)
        except Exception as e:
            raise RuntimeError(
                f"Error leyendo WiFi {band_label} después de aplicar: {e}"
            )

        self._validate_wifi_band(
            band_label=band_label,
            after_data=after_data,
            desired_ssid=desired_ssid,
            desired_password=desired_password,
            result=result,
        )

        result.steps.append({
            "step": f"wifi_{band_key}",
            "data": {
                "band": band_label,
                "before": {
                    "ssid": before_data.get("ssid"),
                    "password": before_data.get("password"),
                },
                "after": {
                    "ssid": after_data.get("ssid"),
                    "password": after_data.get("password"),
                },
                "apply_result": {
                    "before": change_data.get("before", {}),
                    "after": change_data.get("after", {}),
                },
            },
        })

    def _validate_wifi_band(
        self,
        band_label: str,
        after_data: Dict[str, Any],
        desired_ssid: Optional[str],
        desired_password: Optional[str],
        result: FiberhomeCustomizationResult,
    ) -> None:
        if desired_ssid is not None and after_data.get("ssid") != desired_ssid:
            result.errors.append(
                f"SSID {band_label} no coincide. Esperado='{desired_ssid}' obtenido='{after_data.get('ssid')}'"
            )

        if desired_password is not None and after_data.get("password") != desired_password:
            result.errors.append(
                f"Password {band_label} no coincide con el valor esperado"
            )

    def _apply_web_credentials_plan(
        self,
        navigator: FiberhomeNavigator,
        plan: CustomizationPlan,
        result: FiberhomeCustomizationResult,
        progress: ProgressCallback,
    ) -> None:
        web_plan = (
            getattr(plan, "web", None)
            or getattr(plan, "web_credentials", None)
            or getattr(plan, "login", None)
        )

        if web_plan is None:
            result.steps.append({
                "step": "web_credentials_skip",
                "data": {"reason": "El plan no contiene bloque de credenciales web"},
            })
            return

        enabled = getattr(web_plan, "enabled", False)
        if not enabled:
            result.steps.append({
                "step": "web_credentials_disabled",
                "data": {"reason": "El plan no habilitó cambio de credenciales web"},
            })
            return

        old_username = self._normalize_optional_text(
            getattr(web_plan, "old_username", None)
            or getattr(web_plan, "current_username", None)
            or getattr(web_plan, "old_user", None)
            or "root"
        ) or "root"

        old_password = self._normalize_optional_text(
            getattr(web_plan, "old_password", None)
            or getattr(web_plan, "current_password", None)
            or getattr(web_plan, "old_pass", None)
            or "admin"
        ) or "admin"

        new_username = self._normalize_optional_text(
            getattr(web_plan, "new_username", None)
            or getattr(web_plan, "username", None)
            or getattr(web_plan, "user", None)
            or old_username
        ) or old_username

        new_password = self._normalize_optional_text(
            getattr(web_plan, "new_password", None)
            or getattr(web_plan, "password", None)
            or getattr(web_plan, "pass", None)
            or getattr(web_plan, "web_password", None)
        )

        if new_password is None:
            result.steps.append({
                "step": "web_credentials_skip",
                "data": {"reason": "No se recibió nueva contraseña web a aplicar"},
            })
            return

        self._emit(
            progress,
            "WEB_CREDENTIALS",
            "Navegando a sección de credenciales web",
            {"username": old_username},
        )

        before_data = navigator.read_web_credentials()

        self._emit(
            progress,
            "WEB_CREDENTIALS",
            "Aplicando nuevas credenciales web",
            {
                "old_username": old_username,
                "new_username": new_username,
                "old_password_used": True,
                "new_password_set": True,
            },
        )

        change_data = navigator.update_web_credentials(
            old_username=old_username,
            old_password=old_password,
            new_username=new_username,
            new_password=new_password,
        )

        self._emit(
            progress,
            "WEB_CREDENTIALS",
            "Validando inicio de sesión con nuevas credenciales web",
            {"username": new_username},
        )

        navigator.verify_web_credentials_login(
            username=new_username,
            password=new_password,
        )

        result.steps.append({
            "step": "web_credentials",
            "data": {
                "before": before_data,
                "after": change_data.get("after", {}),
                "verified_login": True,
            },
        })

    def apply(
        self,
        plan: CustomizationPlan,
        ctx: CustomizationContext,
        progress: ProgressCallback,
    ) -> FiberhomeCustomizationResult:
        result = FiberhomeCustomizationResult(
            ok=False,
            vendor=ctx.vendor,
            ip=ctx.ip,
            model_code=ctx.model_code,
            product=resolve_product_name(ctx.model_code),
        )

        if ctx.model_code not in self.supported_models:
            result.errors.append(f"Modelo FiberHome no soportado por este adaptador: {ctx.model_code}")
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

            self._apply_web_credentials_plan(
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