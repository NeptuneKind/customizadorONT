from __future__ import annotations

import time

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

    def _build_navigator_for_ip(self, driver, ip: str) -> FiberhomeNavigator:
        return FiberhomeNavigator(
            driver=driver,
            base_url=f"http://{ip}",
            timeout_s=12,
        )

    def _do_login(
        self,
        navigator: FiberhomeNavigator,
        ctx: CustomizationContext,
        progress: ProgressCallback,
    ) -> None:
        candidates = (ctx.settings.get("login_candidates") or {}).get("fiber") or []

        if not candidates:
            raise RuntimeError("No hay candidatos de login configurados para FiberHome")

        self._emit(progress, "LOGIN", "Abriendo GUI FiberHome", {"ip": ctx.ip})

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
        step_name = "wifi_24ghz" if band == WifiBand.B24 else "wifi_5ghz"

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
            "step": step_name,
            "data": {
                "before": {
                    "ssid": before_data.get("ssid"),
                    "password": before_data.get("password"),
                },
                "after": {
                    "ssid": after_data.get("ssid"),
                    "password": after_data.get("password"),
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

        old_username = "root"

        old_password = self._normalize_optional_text(
            getattr(web_plan, "old_password", None)
            or getattr(web_plan, "current_password", None)
            or getattr(web_plan, "old_pass", None)
            or "admin"
        ) or "admin"

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

        navigator.read_web_credentials()

        self._emit(
            progress,
            "WEB_CREDENTIALS",
            "Aplicando nuevas credenciales web",
            {
                "username": "root",
                "old_password_used": True,
                "new_password_set": True,
            },
        )

        navigator.update_web_credentials(
            username="root",
            password=new_password,
        )

        self._emit(
            progress,
            "WEB_CREDENTIALS",
            "Validando inicio de sesión con nuevas credenciales web",
            {"username": "root"},
        )

        verified = navigator.verify_web_credentials_login(
            username="root",
            password=new_password,
        )

        if not verified:
            raise RuntimeError("No fue posible validar el login FiberHome con las nuevas credenciales web")

        result.steps.append({
            "step": "web_credentials",
            "data": {
                "before": {
                    "username": "root",
                    "password": old_password,
                },
                "after": {
                    "username": "root",
                    "password": new_password,
                },
                "verified_login": verified,
            },
        })

    def _apply_ip_plan(
        self,
        navigator: FiberhomeNavigator,
        plan: CustomizationPlan,
        result: FiberhomeCustomizationResult,
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
            raise RuntimeError(f"Error leyendo IP actual FiberHome: {e}")

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
                "Cambio de IP aplicado; iniciando reboot manual FiberHome",
                {
                    "old_ip": old_ip,
                    "new_ip": new_ip,
                },
            )

            navigator.reboot()

            self._emit(
                progress,
                "IP",
                "Esperando 50 segundos antes de preparar pestaña de verificación",
                {
                    "new_ip": new_ip,
                    "wait_s": 50,
                },
            )
            time.sleep(50)

            self._emit(
                progress,
                "IP",
                "Abriendo pestaña secundaria de verificación FiberHome",
                {"new_ip": new_ip},
            )

            previous_handle = navigator.open_blank_verification_tab()
            verification_tab_handle = ctx.driver.current_window_handle

            verification_navigator = self._build_navigator_for_ip(ctx.driver, new_ip)
            verification_navigator.switch_to_window(verification_tab_handle)

            self._emit(
                progress,
                "IP",
                "Esperando 10 segundos adicionales antes del sondeo",
                {
                    "new_ip": new_ip,
                    "wait_s": 10,
                },
            )
            time.sleep(10)

            self._emit(
                progress,
                "IP",
                "Validando acceso en la nueva IP FiberHome",
                {
                    "old_ip": old_ip,
                    "new_ip": new_ip,
                    "mode": "verification_tab",
                    "retry_every_s": 5.0,
                },
            )

            verification_navigator.wait_until_login_accessible_on_new_ip(
                new_ip=new_ip,
                timeout_s=90,
                retry_every_s=5.0,
            )

            verification_navigator.login_for_verification(
                username="root",
                password="admin",
            )

            self._emit(
                progress,
                "IP",
                "Cerrando sesión de verificación FiberHome",
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

    def _validate_ip_change(
        self,
        old_ip: str,
        new_ip: str,
        after_data: Dict[str, Any],
        result: FiberhomeCustomizationResult,
    ) -> None:
        obtained_ip = str(after_data.get("ip", "") or "").strip()

        if obtained_ip != new_ip:
            result.errors.append(
                f"IP FiberHome no coincide. Esperado='{new_ip}' obtenido='{obtained_ip}'"
            )

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
        should_logout = True

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
            if should_logout:
                try:
                    self._emit(progress, "LOGOUT", "Cerrando sesión FiberHome", None)
                    navigator.logout()
                except Exception as logout_exc:
                    result.steps.append({
                        "step": "logout_warning",
                        "data": {
                            "warning": f"No fue posible cerrar sesión FiberHome: {logout_exc}"
                        },
                    })
        
        return result
    