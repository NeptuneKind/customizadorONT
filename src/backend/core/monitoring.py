# ===================================================================
# Imports
# ===================================================================
import subprocess
import sys
import time
import re
import html as html_lib
from dataclasses import dataclass
from typing import Optional, List, Tuple

import requests
import urllib3

from config.logging import get_logger

# ===================================================================
# Definiciones
# ===================================================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log_ping = get_logger("PING")
log_detect = get_logger("DETECT")

@dataclass
class DetectedDevice:
    ip: str
    vendor: str            # "HUAWEI" | "ZTE" | "FIBERHOME"
    model_code: str        # "MOD001".."MOD00X"
    product_name: str      # Mejor esfuerzo (title / JS var)
    needs_post_login_model: bool # True para FiberHome cuando el modelo se confirma tras login

# Mantener MOD00X para cada modelo
# - FiberHome: MOD001 HG6145F, MOD008 HG6145F1
# - ZTE: MOD002 F670L, MOD009 F6600
# - Huawei: MOD003 X6-10, MOD007 X6, MOD004 V5 "Big", MOD005 V5 "Small"
# MODEL_DEFAULTS = {
#     "FIBERHOME": "MOD001",
#     "HUAWEI": "MOD004",
#     "ZTE": "MOD002",
# }

# ===================================================================
# Métodos de monitoreo
# ===================================================================
def ping_once_windows(ip: str, timeout_ms: int = 800) -> bool:
    """
    Hace un ping de Windows a la IP dada con un timeout específico.
      -n 1 : one echo
      -w ms: timeout per reply in ms
    """
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout_ms), ip],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception as e:
        log_ping.error("Ping failed ip=%s err=%s", ip, e)
        return False
    
def wait_for_device_ip(
    ips: List[str],
    overall_timeout_s: Optional[float] = None,
    per_ping_timeout_ms: int = 800,
    sleep_s: float = 0.25,
) -> str:
    """
    Hace pings a las IPs hasta que una responda.
    """
    start = time.time()
    attempt = 0

    while True:
        for ip in ips:
            attempt += 1
            if ping_once_windows(ip, timeout_ms=per_ping_timeout_ms):
                sys.stdout.write(f"\r[PING] Conectado IP={ip} intento={attempt}        \n")
                sys.stdout.flush()
                log_ping.info("Conectado IP=%s intento=%d", ip, attempt)
                return ip
            else:
                sys.stdout.write(f"\r[PING] Buscando dispositivo... intento={attempt}")
                sys.stdout.flush()

            if overall_timeout_s is not None and (time.time() - start) >= overall_timeout_s:
                sys.stdout.write("\n")
                raise TimeoutError("Esperando IP del dispositivo")

            time.sleep(sleep_s)

def detect_vendor_and_model(ip: str, timeout_s: float = 3.0) -> DetectedDevice:
    """
    Detección de vendor y modelo basada en lógica similar a ONTTester.
    1) Si ip == 192.168.1.1 => ZTE
    2) Si no => intentar Huawei por HTML (title/ProductName)
    3) Si no detecta Huawei => asumir FiberHome (modelo se confirma tras login)
    """
    # 1) ZTE por IP (primero)
    if ip.strip() == "192.168.1.1":
        return _detect_zte_by_html(ip, timeout_s=timeout_s)
    
    # 2) No es 192.168.1.1 => intentar Huawei por HTML
    huawei = _try_detect_huawei(ip, timeout_s=timeout_s)
    if huawei is not None:
        return huawei
    
    # 3) Si no es Huawei => FiberHome (confirmar modelo tras login)
    log_detect.info("No se detectó Huawei => es un FiberHome con IP=%s", ip)
    return DetectedDevice(
        ip=ip,
        vendor="FIBERHOME",
        model_code="MOD001",          # default base para FiberHome
        product_name="",
        needs_post_login_model=True,  # se confirmara tras login
    )

def _get_html(ip: str, timeout_s: float) -> str:
    """
    Hace una petición HTTP GET a la IP dada y devuelve el HTML como texto.
    """
    base_url = f"http://{ip}/"
    session = requests.Session()
    resp = session.get(base_url, timeout=timeout_s, verify=False, allow_redirects=True)
    return resp.text or ""

def _detect_zte_by_html(ip: str, timeout_s: float) -> DetectedDevice:
    raw_html = _get_html(ip, timeout_s)
    title = _extract_title(raw_html)
    zte_model = html_lib.unescape(title).upper().strip() if title else ""

    # MOD mapping
    if "F6600" in zte_model:
        model_code = "MOD009"
    else:
        # fallback ZTE
        model_code = "MOD002"

    log_detect.info("ZTE detectado ip=%s model=%s title=%s", ip, model_code, zte_model)
    return DetectedDevice(
        ip=ip,
        vendor="ZTE",
        model_code=model_code,
        product_name=zte_model,
        needs_post_login_model=False,
    )

def _try_detect_huawei(ip: str, timeout_s: float) -> Optional[DetectedDevice]:
    raw_html = _get_html(ip, timeout_s)
    html_lower = raw_html.lower()
    html_normalized = html_lower.replace(" ", "").replace("\n", "").replace("\t", "")

    # mismos indicadores que ONTTester para Huawei
    if not any(k in html_normalized for k in ["huawei", "hg8145", "txt_username", "txt_password"]):
        return None

    product_name = ""

    # Paso A: title
    title = _extract_title(raw_html)
    if title:
        product_name = title.upper().strip()

    # Paso B: JS var ProductName con fix del guion \x2d (X6-10)
    if "HG8145" not in product_name:
        js_product = _extract_js_productname(raw_html)
        if js_product:
            raw_js = js_product.upper()
            product_name = raw_js.replace("\\X2D", "-").replace("\\x2d", "-").strip()

    # Paso C: asignacion modelo (sin cambios)
    if "HG8145X6-10" in product_name:
        model_code = "MOD003"
    elif "HG8145X6" in product_name:
        model_code = "MOD007"
    elif "HG8145V5" in product_name:
        if "SMALL" in product_name:
            model_code = "MOD005"
        else:
            model_code = "MOD004"
    else:
        # fallback Huawei
        model_code = "MOD004"

    log_detect.info("Huawei detectado ip=%s model=%s product=%s", ip, model_code, product_name)
    return DetectedDevice(
        ip=ip,
        vendor="HUAWEI",
        model_code=model_code,
        product_name=product_name,
        needs_post_login_model=False,
    )

def _extract_title(raw_html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
    if not m:
        return ""
    return m.group(1).strip()


def _extract_js_productname(raw_html: str) -> str:
    m = re.search(r"var\s+ProductName\s*=\s*['\"]([^'\"]+)['\"]", raw_html, re.IGNORECASE)
    if not m:
        return ""
    return m.group(1).strip()