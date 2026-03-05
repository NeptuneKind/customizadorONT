from datetime import datetime
from typing import Any, Dict, List, Optional

from ...context import CustomizationContext
from ...models import CustomizationPlan, CustomizationResult, StepResult, WifiBand
from ...progress import ProgressCallback, ProgressEvent

from .navigator import FiberhomeNavigator


class FiberhomeAdapter:
    vendor = "FIBERHOME"

    def apply(self, plan: CustomizationPlan, ctx: CustomizationContext, progress: ProgressCallback) -> CustomizationResult:
        nav = FiberhomeNavigator(base_url=f"http://{ctx.ip}/")
        steps: List[StepResult] = []

        def run_step(step_id: str, fn) -> Optional[Dict[str, Any]]:
            started = datetime.now().isoformat(timespec="seconds")
            try:
                ret = fn()
                data = ret if isinstance(ret, dict) else {}
                steps.append(
                    StepResult(
                        step_id=step_id,
                        ok=True,
                        data=data,
                        started_at=started,
                        finished_at=datetime.now().isoformat(timespec="seconds"),
                    )
                )
                return data
            except Exception as e:
                steps.append(
                    StepResult(
                        step_id=step_id,
                        ok=False,
                        error=str(e),
                        started_at=started,
                        finished_at=datetime.now().isoformat(timespec="seconds"),
                    )
                )
                return None

        # 1) Home + Login
        progress(ProgressEvent(phase="LOGIN", message="Open home"))
        run_step("open_home", lambda: nav.open_home(ctx.driver))

        progress(ProgressEvent(phase="LOGIN", message="Login"))
        run_step("login", lambda: self._login_with_candidates(nav, ctx))

        progress(ProgressEvent(phase="LOGIN", message="Ensure session ready"))
        run_step("ensure_logged_in", lambda: nav.ensure_logged_in(ctx.driver))

        # 2) WiFi (lectura + escritura + lectura)
        if plan.wifi.enabled:
            if plan.wifi.ssid_24 or plan.wifi.pass_24:
                progress(ProgressEvent(phase="WIFI_24", message="Navigate WiFi 2.4"))
                run_step("wifi_24_nav", lambda: nav.go_to_wifi_basic(ctx.driver, WifiBand.B24))

                progress(ProgressEvent(phase="WIFI_24", message="Read WiFi 2.4 (before)"))
                run_step("wifi_24_read_before", lambda: nav.read_wifi_basic(ctx.driver, WifiBand.B24))

                progress(ProgressEvent(phase="WIFI_24", message="Apply WiFi 2.4"))
                run_step("wifi_24_set", lambda: nav.set_wifi_basic(ctx.driver, WifiBand.B24, plan.wifi.ssid_24, plan.wifi.pass_24))

                progress(ProgressEvent(phase="WIFI_24", message="Read WiFi 2.4 (after)"))
                run_step("wifi_24_read_after", lambda: nav.read_wifi_basic(ctx.driver, WifiBand.B24))

            if plan.wifi.ssid_5 or plan.wifi.pass_5:
                progress(ProgressEvent(phase="WIFI_5", message="Navigate WiFi 5"))
                run_step("wifi_5_nav", lambda: nav.go_to_wifi_basic(ctx.driver, WifiBand.B5))

                progress(ProgressEvent(phase="WIFI_5", message="Read WiFi 5 (before)"))
                run_step("wifi_5_read_before", lambda: nav.read_wifi_basic(ctx.driver, WifiBand.B5))

                progress(ProgressEvent(phase="WIFI_5", message="Apply WiFi 5"))
                run_step("wifi_5_set", lambda: nav.set_wifi_basic(ctx.driver, WifiBand.B5, plan.wifi.ssid_5, plan.wifi.pass_5))

                progress(ProgressEvent(phase="WIFI_5", message="Read WiFi 5 (after)"))
                run_step("wifi_5_read_after", lambda: nav.read_wifi_basic(ctx.driver, WifiBand.B5))

        # 3) Web credentials (stub)
        if plan.web_credentials.enabled:
            progress(ProgressEvent(phase="WEB_CREDS", message="Navigate web credentials"))
            run_step("web_creds_nav", lambda: nav.go_to_web_credentials(ctx.driver))

            progress(ProgressEvent(phase="WEB_CREDS", message="Apply web credentials"))
            run_step("web_creds_set", lambda: nav.set_web_credentials(ctx.driver, plan.web_credentials.new_user, plan.web_credentials.new_pass))

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

    def _login_with_candidates(self, nav: FiberhomeNavigator, ctx: CustomizationContext) -> None:
        candidates = (ctx.settings.get("login_candidates") or {}).get("fiberhome") or []
        if not candidates:
            raise RuntimeError("No login candidates for fiberhome in settings")

        for c in candidates:
            user = str(c.get("user", "") or "")
            pwd = str(c.get("pass", "") or "")
            try:
                nav.login(ctx.driver, user, pwd, timeout_s=12)
                return
            except Exception:
                continue

        raise RuntimeError("All login candidates failed (fiberhome)")