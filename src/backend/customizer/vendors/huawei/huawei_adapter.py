from __future__ import annotations

import time
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

    def _build_navigator_for_ip(self, driver, ip: str) -> HuaweiNavigator:
        return HuaweiNavigator(
            driver=driver,
            base_url=f"http://{ip}",
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

    def _apply_ip_plan(
    self,
    navigator: HuaweiNavigator,
    plan: CustomizationPlan,
    result: HuaweiCustomizationResult,
    progress: ProgressCallback,
    ctx: CustomizationContext,
) -> None:
        ip_plan = getattr(plan, "ip", None)

        if ip_plan is None:
            result.steps.append({
                "step": "ip_skip",
                "data": {"reason": "El plan no contiene bloque de IP"},
            })
            return

        enabled = getattr(ip_plan, "enabled", False)
        if not enabled:
            result.steps.append({
                "step": "ip_disabled",
                "data": {"reason": "El plan no habilitó cambio de IP"},
            })
            return

        new_ip = self._normalize_optional_text(getattr(ip_plan, "new_ip", None))

        if new_ip is None:
            result.steps.append({
                "step": "ip_skip",
                "data": {"reason": "No se recibió nueva IP a aplicar"},
            })
            return

        old_ip = ctx.ip

        self._emit(
            progress,
            "IP",
            "Leyendo configuración actual de IP",
            {"current_ip": old_ip},
        )

        try:
            before_data = navigator.read_ip_configuration()
        except Exception as e:
            raise RuntimeError(f"Error leyendo IP actual Huawei: {e}")

        self._emit(
            progress,
            "IP",
            "Aplicando nueva IP",
            {
                "old_ip": old_ip,
                "new_ip": new_ip,
            },
        )

        previous_handle = ctx.driver.current_window_handle
        verification_tab_handle: Optional[str] = None

        try:
            navigator.update_ip_configuration(new_ip=new_ip)
            self._emit(
                progress,
                "IP",
                "Esperando estabilización post-Apply Huawei",
                {
                    "new_ip": new_ip,
                    "wait_s": 2.0,
                },
            )
            time.sleep(2.0)

            self._emit(
                progress,
                "IP",
                "Abriendo pestaña secundaria de verificación Huawei",
                {"new_ip": new_ip},
            )

            previous_handle = navigator.open_blank_verification_tab()
            verification_tab_handle = ctx.driver.current_window_handle

            self._emit(
                progress,
                "IP",
                "Verificando acceso en la nueva IP Huawei",
                {
                    "old_ip": old_ip,
                    "new_ip": new_ip,
                    "mode": "verification_tab",
                },
            )

            verification_navigator = self._build_navigator_for_ip(ctx.driver, new_ip)
            verification_navigator.switch_to_window(verification_tab_handle)

            self._emit(
                progress,
                "IP",
                "Esperando acceso a la GUI en la nueva IP Huawei",
                {
                    "new_ip": new_ip,
                    "retry_every_s": 0.75,
                    "tab": "secondary",
                },
            )

            verification_navigator.wait_until_login_accessible_on_new_ip(
                new_ip=new_ip,
                timeout_s=20,
                retry_every_s=0.75,
            )

            verification_navigator.login_for_verification(
                username="root",
                password="admin",
            )

            self._emit(
                progress,
                "IP",
                "Cerrando sesión de verificación Huawei",
                {"new_ip": new_ip},
            )

            verification_navigator.logout()

        finally:
            try:
                if verification_tab_handle is not None:
                    verification_navigator = self._build_navigator_for_ip(ctx.driver, new_ip)
                    verification_navigator.switch_to_window(verification_tab_handle)
                    verification_navigator.close_current_tab_and_switch_back(previous_handle)
            except Exception:
                pass

        result.ip = new_ip

        result.steps.append({
            "step": "ip_configuration",
            "data": {
                "before": {
                    "ip": before_data.get("ip", old_ip),
                },
                "applied": {
                    "ip": new_ip,
                },
                "verified_change": True,
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

        navigator: Optional[HuaweiNavigator] = None
        should_logout = True

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

            ip_plan = getattr(plan, "ip", None)
            ip_enabled = bool(ip_plan and getattr(ip_plan, "enabled", False))
            requested_new_ip = self._normalize_optional_text(
                getattr(ip_plan, "new_ip", None) if ip_plan is not None else None
            )

            if ip_enabled and requested_new_ip:
                should_logout = False

            self._apply_ip_plan(
                navigator=navigator,
                plan=plan,
                result=result,
                progress=progress,
                ctx=ctx,
            )

            result.ok = len(result.errors) == 0
            return result

        except Exception as exc:
            result.errors.append(str(exc))
            result.ok = False

        finally:
            if should_logout and navigator is not None:
                try:
                    self._emit(progress, "LOGOUT", "Cerrando sesión Huawei", None)
                    navigator.logout()
                except Exception as logout_exc:
                    result.steps.append({
                        "step": "logout_warning",
                        "data": {
                            "warning": f"No fue posible cerrar sesión Huawei: {logout_exc}"
                        },
                    })

        return result