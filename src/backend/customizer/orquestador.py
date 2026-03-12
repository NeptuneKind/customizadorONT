# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.backend.core.monitoring import wait_for_device_ip, detect_vendor_and_model
from src.backend.core.selenium_driver import build_chrome_driver
from src.backend.core.report import write_json_report

from src.backend.customizer.context import CustomizationContext
from src.backend.customizer.models import CustomizationPlan
from src.backend.customizer.progress import ProgressCallback, ProgressEvent
from src.backend.customizer.registry import get_adapter

# ===================================================================
# Métodos de orquestador
# ===================================================================
# Método para ejecutar la personalización completa: detectar dispositivo, aplicar plan y generar reporte
def run_customization(
    *,
    settings: Dict[str, Any],
    project_root: Path,
    reports_day_dir: Path,
    ips: List[str],
    headless: bool,
    plan: CustomizationPlan,
    progress: ProgressCallback,
    overall_timeout_s: float = 60.0,
) -> int:
    # Fase de detección: esperar a que el dispositivo responda en la red y detectar su vendor/modelo
    progress(ProgressEvent(phase="DETECT", message="Esperando dispositivo en la red..."))
    ip = wait_for_device_ip(ips, overall_timeout_s=overall_timeout_s)
    detected = detect_vendor_and_model(ip)

    # Fase de personalización: construir el driver, crear el contexto y aplicar el plan con el adaptador correspondiente
    driver = build_chrome_driver(settings=settings, headless=headless, project_root=project_root)

    ctx = CustomizationContext(
        project_root=project_root,
        settings=settings,
        detected=detected,
        headless=headless,
        driver=driver,
    )

    interrupted = False

    try:
        # Obtener el adaptador de marca y aplicar el plan
        adapter = get_adapter(detected.vendor)
        result = adapter.apply(plan, ctx, progress)

        # Fase de reporte: escribir el resultado en un JSON con toda la información relevante
        write_json_report(
            reports_day_dir=reports_day_dir,
            payload=result.__dict__,
            vendor=detected.vendor,
            ip=detected.ip,
            model_code=detected.model_code,
        )
        progress(ProgressEvent(phase="DONE", message="Customización finalizada", data={"ok": result.ok}))
        return 0 if result.ok else 2

    except KeyboardInterrupt:
        interrupted = True
        raise

    finally:
        if interrupted:
            # Cierre rapido al abortar con Ctrl+C
            try:
                service = getattr(driver, "service", None)
                if service is not None:
                    service.stop()
            except Exception:
                pass

            try:
                proc = getattr(getattr(driver, "service", None), "process", None)
                if proc is not None:
                    proc.kill()
            except Exception:
                pass
        else:
            try:
                # Cierre normal en flujo sin interrupcion
                driver.quit()
            except Exception:
                pass