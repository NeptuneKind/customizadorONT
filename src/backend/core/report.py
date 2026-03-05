# ===================================================================
# Imports
# ===================================================================
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from config.logging import get_logger

# ===================================================================
# Definiciones
# ===================================================================
log_rep = get_logger("REPORT")

def write_json_report(
    *,
    reports_day_dir: Path,
    payload: Dict[str, Any],
    vendor: str,
    ip: str,
    model_code: str,
) -> Path:
    reports_day_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%H%M%S")
    safe_ip = ip.replace(".", "_")
    filename = f"{ts}_{vendor}_{model_code}_{safe_ip}.json"
    out_path = reports_day_dir / filename

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    log_rep.info("Reporte guardado en: %s", out_path)
    return out_path