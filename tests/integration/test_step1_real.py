"""
Step 1 — Tests de integración real: cargar Carga2.bin via TFTP + reset.

Cada test llega UN PASO MÁS LEJOS que el anterior.
El fixture de cada test hace automáticamente todo lo anterior.

Cómo correr:

  # Solo abrir el socket TCP al ONT
  pytest tests/integration/test_step1_real.py::test_01_abrir_socket -s

  # Hasta el login Telnet (dual credentials)
  pytest tests/integration/test_step1_real.py::test_02_login_telnet -s

  # Hasta enviar el primer comando
  pytest tests/integration/test_step1_real.py::test_03_comando_led -s

  # Step 1 completo: TFTP + reset (tarda ~3 min)
  pytest tests/integration/test_step1_real.py::test_04_tftp_carga2 -s
  pytest tests/integration/test_step1_real.py::test_05_reset -s
  pytest tests/integration/test_step1_real.py::test_06_esperar_reboot -s

  # Todo el step 1 de una vez
  pytest tests/integration/test_step1_real.py -s -v
"""
import pytest

pytestmark = pytest.mark.integration


def test_01_abrir_socket(socket_abierto, ont_ip):
    """Abre la conexión TCP al puerto 23 del ONT."""
    print(f"\n[STEP 1] Socket TCP abierto a {ont_ip}:23")
    assert socket_abierto._sock is not None, "El socket no quedó conectado"
    print(f"[STEP 1] socket._sock = {socket_abierto._sock}")


def test_02_login_telnet(socket_logueado):
    """Autenticación Telnet con dual credentials (root/admin_123 → root/adminHW)."""
    print(f"\n[STEP 1] Login Telnet completado")
    print(f"[STEP 1] Credenciales probadas: root/admin_123, root/adminHW")
    assert socket_logueado._sock is not None, "Conexión perdida durante login"


def test_03_comando_led(socket_con_led):
    """Envía 'set led switch on' y verifica que el ONT responde."""
    print(f"\n[STEP 1] Comando 'set led switch on' enviado")
    assert socket_con_led._sock is not None, "Conexión perdida al enviar comando"
    print(f"[STEP 1] Conexión sigue activa tras el comando")


def test_04_tftp_carga2(socket_con_led, tftp_ip):
    """
    Inicia la carga de Carga2.bin via TFTP.
    Tarda varios minutos — no cancelar.
    """
    print(f"\n[STEP 1] Iniciando TFTP: load_pack_by_tftp {tftp_ip} Carga2.bin")
    print(f"[STEP 1] Timeout: 120s — esperando respuesta 'success!'...")

    response = socket_con_led.load_pack_by_tftp(
        server_ip=tftp_ip,
        remote_file="Carga2.bin",
        expect="success!",
    )

    print(f"[STEP 1] Respuesta recibida: {response[:300]}")
    assert "success!" in response, \
        f"TFTP no retornó 'success!'. Respuesta: {response[:300]}"
    print(f"[STEP 1] Carga2.bin cargado exitosamente")


def test_05_reset(socket_con_led):
    """Envía el comando de reset al ONT. El socket puede cerrarse en cualquier momento."""
    print(f"\n[STEP 1] Enviando 'send reset'...")
    socket_con_led.send_reset()
    print(f"[STEP 1] Reset enviado (el dispositivo comenzará a reiniciarse)")


def test_06_esperar_reboot(socket_con_led, ont_ip):
    """
    Espera a que el dispositivo se caiga y vuelva a responder.
    Fase DOWN: hasta 15s
    Fase UP:   hasta 90s
    """
    print(f"\n[STEP 1] Esperando que {ont_ip} caiga (fase DOWN, max 15s)...")
    print(f"[STEP 1] Luego esperando que vuelva (fase UP, max 90s)...")

    socket_con_led.wait_for_reboot(down_timeout_s=15, up_timeout_s=90)

    print(f"[STEP 1] Dispositivo reiniciado y accesible")
    print(f"[STEP 1] Step 1 completado — Carga2.bin aplicado")
