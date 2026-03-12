from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.backend.customizer.context import CustomizationContext
from src.backend.customizer.models import CustomizationPlan
from src.backend.customizer.progress import ProgressCallback, ProgressEvent
from src.backend.customizer.models import WifiBand

from .huawei_navigator import HuaweiNavigator
from src.backend.customizer.product_map import resolve_product_name

@dataclass
class HuaweiCustomizationResult:
    ok: bool
    vendor: str
    ip: str
    model_code: str
    product: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)


class HuaweiAdapter:
    """
    Adaptador Huawei con la misma estructura base que ZTEAdapter.
    """

    supported_models = {"HUAWEI"}

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

    def _build_navigator(self, ctx: CustomizationContext) -> HuaweiNavigator:
        return HuaweiNavigator(
            driver=ctx.driver,
            base_url=f"http://{ctx.ip}",
            timeout_s=10,
        )

    def _do_login(
        self,
        navigator: HuaweiNavigator,
        ctx: CustomizationContext,
        progress: ProgressCallback,
    ) -> None:
        candidates = (ctx.settings.get("login_candidates") or {}).get("huawei") or []

        if not candidates:
            raise RuntimeError("No hay candidatos de login configurados para Huawei")

        self._emit(progress, "LOGIN", "Abriendo GUI Huawei", {"ip": ctx.ip})
        navigator._open_root()

        last_error: Optional[Exception] = None

        for c in candidates:
            user = str(c.get("user", "") or "")
            pwd = str(c.get("pass", "") or "")

            try:
                self._emit(
                    progress,
                    "LOGIN",
                    "Probando credenciales Huawei",
                    {"username": user},
                )
                navigator.login(username=user, password=pwd)
                self._emit(progress, "LOGIN", "Sesión Huawei iniciada", {"username": user})
                return
            except Exception as exc:
                last_error = exc

        raise RuntimeError(f"No fue posible iniciar sesión en Huawei: {last_error}")

    def _apply_wifi_plan(
        self,
        navigator: HuaweiNavigator,
        plan: CustomizationPlan,
        result: HuaweiCustomizationResult,
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
        navigator: HuaweiNavigator,
        band: WifiBand,
        desired_ssid: Optional[str],
        desired_password: Optional[str],
        result: HuaweiCustomizationResult,
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
                    "ssid": change_data.get("before", {}).get("ssid"),
                    "password": change_data.get("before", {}).get("password"),
                },
                "after": {
                    "ssid": change_data.get("after", {}).get("ssid"),
                    "password": change_data.get("after", {}).get("password"),
                },
            },
        })

    def _validate_wifi_band(
        self,
        band_label: str,
        after_data: Dict[str, Any],
        desired_ssid: Optional[str],
        desired_password: Optional[str],
        result: HuaweiCustomizationResult,
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
        navigator: HuaweiNavigator,
        plan: CustomizationPlan,
        result: HuaweiCustomizationResult,
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

        username = "root"

        old_password = self._normalize_optional_text(
            getattr(web_plan, "old_password", None)
            or getattr(web_plan, "current_password", None)
            or getattr(web_plan, "old_pass", None)
            or "admin"
        ) or "admin"

        new_password = self._normalize_optional_text(
            getattr(web_plan, "new_pass", None)
            or getattr(web_plan, "new_password", None)
            or getattr(web_plan, "password", None)
        )

        if new_password is None:
            result.steps.append({
                "step": "web_credentials_skip",
                "data": {"reason": "No se recibió nueva contraseña web a aplicar"},
            })
            return

        self._emit(progress, "WEB", "Leyendo credenciales web actuales Huawei", None)
        try:
            before_data = navigator.read_web_credentials()
        except Exception as e:
            raise RuntimeError(f"Error leyendo credenciales web actuales Huawei: {e}")

        self._emit(
            progress,
            "WEB",
            "Aplicando cambio de credenciales web Huawei",
            {
                "username": username,
                "old_password_used": True,
                "new_password_set": True,
            },
        )
        try:
            change_data = navigator.update_web_credentials(
                username=username,
                password=new_password,
            )
        except Exception as e:
            raise RuntimeError(f"Error aplicando credenciales web Huawei: {e}")

        self._emit(
            progress,
            "WEB",
            "Verificando login con nuevas credenciales Huawei",
            {
                "username": "root",
            },
        )
        verified = navigator.verify_web_credentials_login(
            username="root",
            password=new_password or "",
        )

        if not verified:
            result.errors.append(
                "No fue posible iniciar sesión con las nuevas credenciales web Huawei después del cambio"
            )

        result.steps.append({
            "step": "web_credentials",
            "data": {
                "username": username,
                "old_password": old_password,
                "new_password": new_password,
                "verified_login": True,
            },
        })

    def apply(
        self,
        plan: CustomizationPlan,
        ctx: CustomizationContext,
        progress: ProgressCallback,
    ) -> HuaweiCustomizationResult:
        result = HuaweiCustomizationResult(
            ok=True,
            vendor=ctx.vendor,
            ip=ctx.ip,
            model_code=ctx.model_code,
            product=resolve_product_name(ctx.model_code),
        )

        try:
            navigator = self._build_navigator(ctx)
            self._do_login(navigator=navigator, ctx=ctx, progress=progress)
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
        except Exception as exc:
            result.errors.append(str(exc))

        result.ok = len(result.errors) == 0
        return result