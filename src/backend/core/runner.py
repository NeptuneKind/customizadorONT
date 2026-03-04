from typing import List, Dict, Any

from config.logging import get_logger
from backend.core.monitoring import wait_for_device_ip, detect_vendor_and_model
from backend.core.report import write_json_report


log_run = get_logger("RUN")


def run_monitoring_only(
    *,
    settings: Dict[str, Any],
    reports_day_dir,
    ips: List[str],
    overall_timeout_s: float = 60.0,
) -> int:
    ip = wait_for_device_ip(ips, overall_timeout_s=overall_timeout_s)
    detected = detect_vendor_and_model(ip)

    payload = {
        "ok": True,
        "step": "monitoring_only",
        "ip": detected.ip,
        "vendor": detected.vendor,
        "model_code": detected.model_code,
        "product_name": detected.product_name,
    }

    write_json_report(
        reports_day_dir=reports_day_dir,
        payload=payload,
        vendor=detected.vendor,
        ip=detected.ip,
        model_code=detected.model_code,
    )

    log_run.info("Monitoring test finished vendor=%s model=%s ip=%s", detected.vendor, detected.model_code, detected.ip)
    return 0