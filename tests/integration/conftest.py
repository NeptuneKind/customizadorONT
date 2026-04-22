"""
Fixtures de integración reales — conectan al ONT de verdad.
Sigue el mismo camino que main.py → run_customization() → HuaweiAdapter.

Configuración de IPs:
  pytest tests/integration/ --ip=192.168.100.1 --tftp-ip=192.168.100.15
"""
from __future__ import annotations

import pytest
from pathlib import Path

from config.settings import load_or_init_settings
from src.backend.core.monitoring import detect_vendor_and_model, wait_for_device_ip
from src.backend.core.selenium_driver import build_chrome_driver
from src.backend.customizer.context import CustomizationContext
from src.backend.customizer.vendors.huawei.huawei_adapter import HuaweiAdapter
from src.backend.core.huawei_full_locked_transport import (
    HuaweiFullLockedTransport,
    HuaweiTelnetCredentials,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ──────────────────────────────────────────────────────────────────────────────
# Flags CLI
# ──────────────────────────────────────────────────────────────────────────────

def pytest_addoption(parser):
    parser.addoption("--ip",      default="192.168.100.1",  help="IP del ONT")
    parser.addoption("--tftp-ip", default="192.168.100.15", help="IP servidor TFTP")
    parser.addoption("--headless", action="store_true",     help="Selenium sin ventana")


@pytest.fixture(scope="session")
def bins_dir():
    return PROJECT_ROOT / "BINS"


@pytest.fixture(scope="session")
def ont_ip(request):
    return request.config.getoption("--ip")


@pytest.fixture(scope="session")
def tftp_ip(request):
    return request.config.getoption("--tftp-ip")


@pytest.fixture(scope="session")
def headless(request):
    return request.config.getoption("--headless")


@pytest.fixture(scope="session")
def settings():
    return load_or_init_settings(
        PROJECT_ROOT=PROJECT_ROOT,
        CONFIG_DIR=PROJECT_ROOT / "config",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Contexto de producción — idéntico a run_customization()
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def ctx(settings, ont_ip, headless):
    """
    CustomizationContext completo, construido igual que run_customization().
    Espera al dispositivo (hasta 60s), detecta vendor/modelo, abre Chrome.
    """
    ip = wait_for_device_ip([ont_ip], overall_timeout_s=60)
    detected = detect_vendor_and_model(ip)
    driver = build_chrome_driver(
        settings=settings,
        headless=headless,
        project_root=PROJECT_ROOT,
    )
    context = CustomizationContext(
        project_root=PROJECT_ROOT,
        settings=settings,
        detected=detected,
        headless=headless,
        driver=driver,
    )
    yield context
    try:
        driver.quit()
    except Exception:
        pass


@pytest.fixture(scope="module")
def adapter():
    return HuaweiAdapter()


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures de Step 0 — GUI Selenium
# Cada uno es un nivel más avanzado del anterior.
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def gui_abierta(adapter, ctx):
    """
    Navigator con Chrome abierto y la página del ONT cargada.
    Usa adapter._build_navigator() exactamente igual que en producción.
    """
    nav = adapter._build_navigator(ctx)
    nav._open_root()
    return nav


@pytest.fixture(scope="module")
def gui_logueada(gui_abierta, settings):
    """
    Navigator con sesión superuser iniciada.
    Lee las credenciales de la segunda entrada de settings["login_candidates"]["huawei"]
    (índice 1 = superuser, índice 0 = credenciales default).
    """
    superuser = settings["login_candidates"]["huawei"][1]
    gui_abierta.login(username=superuser["user"], password=superuser["pass"])
    return gui_abierta


@pytest.fixture(scope="module")
def gui_lan_telnet_habilitado(gui_logueada):
    """LAN Telnet habilitado en Device Access Control (Advanced → Security → Device Access Control)."""
    gui_logueada.enable_lan_telnet()
    return gui_logueada


@pytest.fixture(scope="module")
def gui_en_wan(gui_lan_telnet_habilitado):
    """Navigator navegado hasta WAN Access Control."""
    gui_lan_telnet_habilitado.navigate_to_wan_access_control()
    return gui_lan_telnet_habilitado


@pytest.fixture(scope="module")
def gui_telnet_habilitado(gui_en_wan):
    """Regla Telnet (puerto 23) creada en WAN Access Control.
    Nota: TFTP no aparece en la GUI — el ONT actúa como cliente TFTP (no servidor).
    """
    gui_en_wan.create_wan_access_rule("TELNET")
    return gui_en_wan


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures de Step 1 — Telnet real
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def telnet_creds_step1(settings):
    creds_list = settings["login_telnet_candidates"]["huawei"]
    return HuaweiTelnetCredentials(
        username_1=creds_list[0]["user"],
        password_1=creds_list[0]["pass"],
        username_2=creds_list[1]["user"],
        password_2=creds_list[1]["pass"],
    )


@pytest.fixture(scope="module")
def socket_abierto(ont_ip):
    """Conexión TCP al puerto 23 establecida."""
    transport = HuaweiFullLockedTransport(host=ont_ip, port=23, timeout_s=10.0)
    transport.connect()
    yield transport
    transport.close()
    print(f"\n[STEP 1] Socket TCP cerrado (teardown fixture)")


@pytest.fixture(scope="module")
def socket_logueado(socket_abierto, telnet_creds_step1):
    """Sesión Telnet autenticada (dual login completado)."""
    socket_abierto.login(telnet_creds_step1)
    return socket_abierto


@pytest.fixture(scope="module")
def socket_con_led(socket_logueado):
    """Post-login con 'set led switch on' enviado."""
    socket_logueado.send_command("set led switch on")
    return socket_logueado
