from __future__ import annotations

import time

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.backend.customizer.context import CustomizationContext
from src.backend.customizer.models import CustomizationPlan
from src.backend.customizer.progress import ProgressCallback, ProgressEvent

from .zte_navigator import ZTENavigator
from src.backend.customizer.product_map import resolve_product_name

@dataclass
class ZTECustomizationResult:
    ok: bool
    vendor: str
    ip: str
    model_code: str
    product: str
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
    
    # Método para crear una instancia de ZTENavigator apuntando a una IP específica (usado para verificación post-cambio de IP)
    def _build_navigator_for_ip(self, driver, ip: str) -> ZTENavigator:
        return ZTENavigator(
            driver=driver,
            base_url=f"http://{ip}",
            timeout_s=12,
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

        #navigator._open_wifi_ssid(index)

        # 4. Validación final
        self._emit(
            progress,
            "WIFI",
            f"Validando lectura final WiFi {band_label}",
            {"ssid_index": index},
        )
        after_data = navigator.read_wifi_band(index=index)

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

    # Método para aplicar el cambio de credenciales web después de WiFi
    def _apply_web_credentials_plan(
        self,
        navigator: ZTENavigator,
        plan: CustomizationPlan,
        result: ZTECustomizationResult,
        progress: ProgressCallback,
    ) -> None:
        # Buscar el bloque del plan de forma tolerante para no romper si todavía no existe formalmente
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

        # En ZTE, por requerimiento actual:
        # - siempre entramos como usuario normal root/admin
        # - username queda fijo en root, por lo que no se considera un valor a cambiar sino parte del proceso
        username = "root"

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
            "Navegando a Account Management",
            {"username": username},
        )

        self._emit(
            progress,
            "WEB_CREDENTIALS",
            "Aplicando nueva contraseña web",
            {
                "username": username,
                "old_password_used": True,
                "new_password_set": True,
            },
        )

        change_data = navigator.update_web_password(
            old_password=old_password,
            new_password=new_password,
            confirm_password=new_password,
        )

        self._emit(
            progress,
            "WEB_CREDENTIALS",
            "Validando inicio de sesión con nueva contraseña web",
            {"username": username},
        )

        navigator.verify_web_password_login(username=username, password=new_password)

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
        navigator: ZTENavigator,
        plan: CustomizationPlan,
        result: ZTECustomizationResult,
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
            raise RuntimeError(f"Error leyendo IP actual ZTE: {e}")

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
                "Cambio de IP aplicado ZTE",
                {
                    "old_ip": old_ip,
                    "new_ip": new_ip,
                },
            )

            self._emit(
                progress,
                "IP",
                "Esperando 32 segundos antes de preparar pestaña de verificación",
                {
                    "new_ip": new_ip,
                    "wait_s": 32,
                },
            )
            time.sleep(32)

            self._emit(
                progress,
                "IP",
                "Abriendo pestaña secundaria de verificación ZTE",
                {"new_ip": new_ip},
            )

            previous_handle = navigator.open_blank_verification_tab()
            verification_tab_handle = ctx.driver.current_window_handle

            verification_navigator = self._build_navigator_for_ip(ctx.driver, new_ip)
            verification_navigator.switch_to_window(verification_tab_handle)

            # self._emit(
            #     progress,
            #     "IP",
            #     "Esperando 5 segundos adicionales antes del sondeo",
            #     {
            #         "new_ip": new_ip,
            #         "wait_s": 5,
            #     },
            # )
            # time.sleep(5)

            self._emit(
                progress,
                "IP",
                "Validando acceso en la nueva IP ZTE",
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
                "Cerrando sesión de verificación ZTE",
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
        result: ZTECustomizationResult,
    ) -> None:
        obtained_ip = str(after_data.get("ip", "") or "").strip()

        if obtained_ip != new_ip:
            result.errors.append(
                f"IP ZTE no coincide. Esperado='{new_ip}' obtenido='{obtained_ip}'"
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
            product=resolve_product_name(ctx.model_code),
        )

        if ctx.model_code not in self.supported_models:
            result.errors.append(f"Modelo ZTE no soportado por este adaptador: {ctx.model_code}")
            return result

        if ctx.driver is None:
            result.errors.append("El contexto no contiene WebDriver inicializado")
            return result

        navigator = self._build_navigator(ctx)

        try:
            # 1) Login y espera de sesión
            self._do_login(
                navigator=navigator,
                ctx=ctx,
                progress=progress,
            )

            # 2) Customización WiFi
            self._apply_wifi_plan(
                navigator=navigator,
                plan=plan,
                result=result,
                progress=progress,
            )

            # 3) Customización de credenciales web
            self._apply_web_credentials_plan(
                navigator=navigator,
                plan=plan,
                result=result,
                progress=progress,
            )

            # 4) Customización de IP
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
            return result