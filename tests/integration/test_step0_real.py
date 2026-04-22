"""
Step 0 — Tests de integración real: habilitar Telnet via GUI Selenium.

Flujo:
  1. Abrir browser
  2. Login superuser (telecomadmin)
  3. Device Access Control → habilitar "LAN-side Telnet"  ← habilita Telnet desde el LAN
  4. Navegar a WAN Access Control
  5. Crear regla Telnet en WAN Access Control
  6. Verificar regla y logout

Nota: TFTP no aparece en WAN Access Control GUI porque el ONT actúa como
cliente TFTP (él descarga desde el PC), no como servidor — no necesita regla entrante.

Cómo correr:

  # Solo abrir el browser
  pytest tests/integration/test_step0_real.py::test_01_abrir_browser -s

  # Hasta login
  pytest tests/integration/test_step0_real.py::test_02_login -s

  # Hasta habilitar LAN Telnet en Device Access Control
  pytest tests/integration/test_step0_real.py::test_03_habilitar_lan_telnet -s

  # Hasta navegar a WAN Access Control
  pytest tests/integration/test_step0_real.py::test_04_navegar_wan -s

  # Step 0 completo (crear regla Telnet en WAN Access Control)
  pytest tests/integration/test_step0_real.py::test_05_crear_regla_telnet -s

  # Verificar que la regla quedó creada
  pytest tests/integration/test_step0_real.py::test_06_verificar_regla_telnet -s

  # Todo el step 0 de una vez
  pytest tests/integration/test_step0_real.py -s -v
"""
import pytest

pytestmark = pytest.mark.integration


def test_01_abrir_browser(gui_abierta, ctx):
    """
    Abre Chrome y carga la GUI del ONT.
    El fixture ctx ya esperó al dispositivo (wait_for_device_ip) y detectó vendor/modelo.
    """
    print(f"\n[STEP 0] Dispositivo: {ctx.vendor} {ctx.model_code} en {ctx.ip}")
    print(f"[STEP 0] Browser abierto en {gui_abierta.base_url}")
    print(f"[STEP 0] URL actual: {gui_abierta.driver.current_url}")
    assert gui_abierta.driver.current_url != ""


def test_02_login(gui_logueada, ctx):
    """
    Login con superuser telecomadmin — requerido para acceder a configuración avanzada.
    """
    url = gui_logueada.driver.current_url
    print(f"\n[STEP 0] Login superuser (telecomadmin) completado en {ctx.ip}")
    print(f"[STEP 0] URL post-login: {url}")
    assert ctx.ip in url or "index" in url.lower() or gui_logueada.driver.title != ""


def test_03_habilitar_lan_telnet(gui_lan_telnet_habilitado):
    """
    Habilita 'LAN-side PC to access via Telnet' en Device Access Control.
    Este es el checkbox que realmente abre el puerto 23 desde el LAN.
    """
    print(f"\n[STEP 0] Device Access Control: LAN Telnet habilitado")
    print(f"[STEP 0] URL: {gui_lan_telnet_habilitado.driver.current_url}")
    assert gui_lan_telnet_habilitado.driver.current_url != ""


def test_04_navegar_wan(gui_en_wan):
    """Navega hasta Advanced → Security → WAN Access Control."""
    print(f"\n[STEP 0] Navegación a WAN Access Control exitosa")
    print(f"[STEP 0] URL en WAN: {gui_en_wan.driver.current_url}")
    assert gui_en_wan.driver.current_url != ""


def test_05_crear_regla_telnet(gui_telnet_habilitado):
    """Crea la regla Telnet (puerto 23) en WAN Access Control — Step 0 completo."""
    print(f"\n[STEP 0] Regla Telnet creada en WAN Access Control")
    rules = gui_telnet_habilitado.read_wan_access_control_rules()
    print(f"[STEP 0] Reglas presentes: {rules}")
    assert any("telnet" in str(r).lower() for r in rules), \
        f"Regla Telnet no encontrada en: {rules}"


def test_06_verificar_regla_telnet(gui_en_wan):
    """
    Verifica que la regla Telnet existe en WAN Access Control.
    Si no existe la crea; si ya existe pasa directo al logout.
    """
    rules = gui_en_wan.read_wan_access_control_rules()
    print(f"\n[STEP 0] Reglas en la tabla: {rules}")

    telnet_ok = any("telnet" in str(r).lower() for r in rules)
    print(f"[STEP 0]   Telnet (23): {'✓' if telnet_ok else '✗ — creando regla...'}")

    if not telnet_ok:
        gui_en_wan.create_wan_access_rule("TELNET")
        rules = gui_en_wan.read_wan_access_control_rules()
        telnet_ok = any("telnet" in str(r).lower() for r in rules)
        print(f"[STEP 0]   Telnet (23) tras crear: {'✓' if telnet_ok else '✗'}")

    assert telnet_ok, f"Regla Telnet no encontrada tras crear: {rules}"
    print(f"[STEP 0] Step 0 completado — LAN Telnet + regla WAN habilitados")

    print(f"[STEP 0] Haciendo logout...")
    try:
        gui_en_wan.logout()
        print(f"[STEP 0] Logout exitoso")
    except Exception as e:
        print(f"[STEP 0] ⚠ Logout falló (no crítico): {e}")
