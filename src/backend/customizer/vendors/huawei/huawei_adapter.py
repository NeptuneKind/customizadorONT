# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from src.backend.customizer.context import CustomizationContext
from src.backend.customizer.models import (
    CustomizationPlan,
    CustomizationResult,
    StepResult,
    WifiBand,
)
from src.backend.customizer.progress import ProgressCallback, ProgressEvent
from src.backend.customizer.vendors.base import BrandAdapter
from .huawei_navigator import HuaweiNavigator

# ===================================================================
# Clase y métodos
# ===================================================================
# Adaptador específico para dispositivos Huawei (encargado de aplicar el plan de personalización usando HuaweiNavigator)
class HuaweiAdapter(BrandAdapter):
    # Getter para la marca (vendor) que maneja este adaptador
    @property
    def vendor(self) -> str:
        return "HUAWEI"
    
    # Método para aplicar el plan de personalización al dispositivo Huawei usando el contexto y reportando progreso
    def apply(self, plan: CustomizationPlan, ctx: CustomizationContext, progress: ProgressCallback) -> CustomizationResult:
        steps = []
        nav = HuaweiNavigator(base_url=f"http://{ctx.ip}/")

        # Helper para ejecutar cada paso del proceso, capturar su resultado y tiempos, y acumularlo en la lista de steps
        def run_step(step_id: str, fn):
            started = datetime.now().isoformat(timespec="seconds")
            try:
                fn()
                steps.append(StepResult(step_id=step_id, ok=True, started_at=started, finished_at=datetime.now().isoformat(timespec="seconds")))
            except Exception as e:
                steps.append(StepResult(step_id=step_id, ok=False, error=str(e), started_at=started, finished_at=datetime.now().isoformat(timespec="seconds")))

        # Fase de login (abrir home, intentar login con candidatos, asegurar que estamos logeados)
        progress(ProgressEvent(phase="LOGIN", message="Opening home"))
        run_step("open_home", lambda: nav.open_home(ctx.driver))

        # TODO: refactorizar para intentar cada candidato de login y reportar cuál funcionó (o si fallaron todos)
        progress(ProgressEvent(phase="LOGIN", message="Login"))
        run_step("login", lambda: self._login_with_candidates(nav, ctx))

        if plan.wifi.enabled:
            if plan.wifi.ssid_24 or plan.wifi.pass_24:
                progress(ProgressEvent(phase="WIFI_24", message="Applying WiFi 2.4"))
                run_step("wifi_24", lambda: self._apply_wifi(nav, ctx, WifiBand.B24, plan.wifi.ssid_24, plan.wifi.pass_24))

            if plan.wifi.ssid_5 or plan.wifi.pass_5:
                progress(ProgressEvent(phase="WIFI_5", message="Applying WiFi 5"))
                run_step("wifi_5", lambda: self._apply_wifi(nav, ctx, WifiBand.B5, plan.wifi.ssid_5, plan.wifi.pass_5))

        if plan.web_credentials.enabled:
            progress(ProgressEvent(phase="WEB_CREDS", message="Applying web credentials"))
            run_step("web_credentials", lambda: self._apply_web_credentials(nav, ctx, plan.web_credentials.new_user, plan.web_credentials.new_pass))

        ok = all(s.ok for s in steps)
        return CustomizationResult(
            ok=ok,
            vendor=ctx.vendor,
            model_code=ctx.model_code,
            ip=ctx.ip,
            product_name=ctx.detected.product_name,
            plan={
                "wifi": vars(plan.wifi),
                "web_credentials": vars(plan.web_credentials),
                "firmware": vars(plan.firmware),
            },
            steps=steps,
        )
    
    # Método para intentar con todos los candidatos de login configurados para Huawei
    def _login_with_candidates(self, nav: HuaweiNavigator, ctx: CustomizationContext) -> None:
        candidates = (ctx.settings.get("login_candidates") or {}).get("huawei") or []
        if not candidates:
            raise RuntimeError("No hay candidatos de login configurados para Huawei")

        for c in candidates:
            user = str(c.get("user", "") or "")
            pwd = str(c.get("pass", "") or "")
            try:
                nav.login(ctx.driver, user, pwd, timeout_s=10)
                nav.ensure_logged_in(ctx.driver, timeout_s=10)
                return
            except Exception:
                continue

        raise RuntimeError("All login candidates failed (huawei)")
    
    # Método para aplicar la configuración de WiFi (SSID y contraseña) para la banda indicada usando el HuaweiNavigator
    def _apply_wifi(self, nav: HuaweiNavigator, ctx: CustomizationContext, band: WifiBand, ssid: str, password: str) -> None:
        nav.go_to_wifi_basic(ctx.driver, band)
        nav.set_wifi_basic(ctx.driver, band, ssid, password)

    # Método para aplicar la configuración de credenciales web (nuevo usuario y contraseña para el panel) usando el HuaweiNavigator
    def _apply_web_credentials(self, nav: HuaweiNavigator, ctx: CustomizationContext, new_user: str, new_pass: str) -> None:
        nav.go_to_web_credentials(ctx.driver)
        nav.set_web_credentials(ctx.driver, new_user, new_pass)