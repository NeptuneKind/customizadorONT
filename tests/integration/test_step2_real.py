"""
Step 2 - Tests de integracion real: habilitar modo de customizacion.

Secuencia Step 2 (post-reboot de Step 1):
  1. Reconectar TCP al :23
  2. Dual login (admin_123 -> adminHW)
  3. set led switch on
  4. su          -> prompt 'SU_WAP'
  5. shell       -> prompt 'WAP(Dopra Linux)' (BusyBox)
  6. EquipMode.sh on  -> dentro del shell BusyBox
  7. send reset
  8. esperar reboot (device back up) - Step 2 termina aqui

Como correr:

  pytest tests/integration/test_step2_real.py::test_01_reconectar_socket -s
  pytest tests/integration/test_step2_real.py::test_02_login_telnet -s
  pytest tests/integration/test_step2_real.py::test_03_comando_led -s
  pytest tests/integration/test_step2_real.py::test_04_escalar_su -s
  pytest tests/integration/test_step2_real.py::test_05_entrar_shell -s
  pytest tests/integration/test_step2_real.py::test_06_equipmode_on -s
  pytest tests/integration/test_step2_real.py::test_07_reset -s
  pytest tests/integration/test_step2_real.py::test_08_esperar_reboot -s
  pytest tests/integration/test_step2_real.py -s -v
"""
import pytest

from src.backend.core.huawei_full_locked_transport import infer_step_from_credentials
from tests.integration.conftest import debug_acumulado

pytestmark = pytest.mark.integration

PREFIX = "STEP 2"


def test_01_reconectar_socket(socket_abierto_step2, settings, ont_ip):
    """Abre conexion TCP fresca al :23 (Step 2 inicia aqui)."""
    print(f"\n[{PREFIX}] test_01 - reconectar socket TCP al {ont_ip}:23")
    debug_acumulado(socket_abierto_step2, settings, PREFIX, label="post-connect")

    assert socket_abierto_step2._sock is not None, "El socket no quedo conectado"
    peer = socket_abierto_step2._sock.getpeername()
    assert peer[0] == ont_ip, f"IP remota incorrecta: {peer[0]} (esperaba {ont_ip})"
    assert peer[1] == 23, f"Puerto remoto incorrecto: {peer[1]}"
    print(f"[{PREFIX}] [OK] TCP establecido a {peer[0]}:{peer[1]}")


def test_02_login_telnet(socket_logueado_step2, settings):
    """Dual login (admin_123 -> adminHW). Imprime inferencia de estado por credencial."""
    print(f"\n[{PREFIX}] test_02 - dual login Telnet")
    debug_acumulado(socket_logueado_step2, settings, PREFIX, label="post-login")

    inferred = infer_step_from_credentials(socket_logueado_step2)
    print(f"[{PREFIX}] Inferencia de estado del ONT:")
    print(f"[{PREFIX}]   likely_step : {inferred['likely_step']}")
    print(f"[{PREFIX}]   confidence  : {inferred['confidence']}")
    print(f"[{PREFIX}]   note        : {inferred['note']}")

    assert socket_logueado_step2._sock is not None, "Conexion perdida durante login"
    assert socket_logueado_step2._credentials_used is not None, \
        "login() no registro que credencial funciono - revisar _do_login"
    _, _, pair = socket_logueado_step2._credentials_used
    print(f"[{PREFIX}] [OK] Login exitoso con par {pair}")


def test_03_comando_led(socket_con_led_step2, settings):
    """Envia 'set led switch on' y verifica que el ONT responde."""
    print(f"\n[{PREFIX}] test_03 - set led switch on")
    debug_acumulado(socket_con_led_step2, settings, PREFIX, label="post-LED")

    resp = (socket_con_led_step2._last_response or "").strip()
    assert resp, "El ONT no respondio nada al comando 'set led switch on'"
    print(f"[{PREFIX}] [OK] ONT respondio al LED command")


def test_04_escalar_su(socket_en_su_step2, settings):
    """Ejecuta 'su' - prompt cambia a 'SU_WAP' (sin pedir password)."""
    print(f"\n[{PREFIX}] test_04 - su (escalar privilegios)")
    debug_acumulado(socket_en_su_step2, settings, PREFIX, label="post-su")

    response = socket_en_su_step2._last_response or ""
    assert "SU_WAP" in response, \
        f"Prompt 'SU_WAP' no encontrado. Respuesta: {repr(response[-400:])}"
    print(f"[{PREFIX}] [OK] Prompt SU_WAP alcanzado")


def test_05_entrar_shell(socket_en_shell_step2, settings):
    """Ejecuta 'shell' desde SU_WAP - prompt cambia a 'WAP(Dopra Linux)' (BusyBox)."""
    print(f"\n[{PREFIX}] test_05 - shell (entrar Dopra Linux BusyBox)")
    debug_acumulado(socket_en_shell_step2, settings, PREFIX, label="post-shell")

    response = socket_en_shell_step2._last_response or ""
    assert "WAP(Dopra Linux)" in response, \
        f"Prompt 'WAP(Dopra Linux)' no encontrado. Respuesta: {repr(response[-400:])}"
    print(f"[{PREFIX}] [OK] Shell Dopra Linux alcanzado")


def test_06_equipmode_on(socket_equipmode_step2, settings):
    """
    Ejecuta 'EquipMode.sh on' dentro del shell BusyBox.
    Captura la respuesta cruda - el marcador expect= se fijara tras esta corrida.
    """
    print(f"\n[{PREFIX}] test_06 - EquipMode.sh on (dentro del shell BusyBox)")
    debug_acumulado(socket_equipmode_step2, settings, PREFIX, label="post-EquipMode.sh on")

    response = socket_equipmode_step2._last_response or ""
    print(f"[{PREFIX}] Respuesta cruda completa:")
    for line in response.split("\n"):
        if line.strip():
            print(f"[{PREFIX}]   {repr(line)}")

    assert response.strip(), "El ONT no respondio nada a 'EquipMode.sh on'"

    lower = response.lower()
    for err in ("not found", "command is not existed", "permission denied"):
        assert err not in lower, \
            f"EquipMode.sh on reporto error ({err!r}): {repr(response[:300])}"

    print(f"[{PREFIX}] [OK] EquipMode.sh on ejecutado sin errores detectados")


def test_07_reset(socket_equipmode_step2, settings):
    """Envia 'send reset'. El socket puede cerrarse inmediatamente."""
    print(f"\n[{PREFIX}] test_07 - send reset")
    socket_equipmode_step2.send_reset()
    debug_acumulado(socket_equipmode_step2, settings, PREFIX, label="post-reset")
    print(f"[{PREFIX}] [OK] send reset enviado - dispositivo reiniciandose")


def test_08_esperar_reboot(socket_equipmode_step2, settings, ont_ip):
    """
    Espera a que el dispositivo caiga y vuelva a responder.
    DOWN: hasta 15s / UP: hasta 90s. Step 2 termina aqui.
    """
    print(f"\n[{PREFIX}] test_08 - esperar reboot ({ont_ip})")
    print(f"[{PREFIX}]   Fase DOWN: esperando que {ont_ip} caiga (max 15s)...")
    print(f"[{PREFIX}]   Fase UP  : esperando que {ont_ip} vuelva (max 90s)...")

    socket_equipmode_step2.wait_for_reboot(down_timeout_s=15, up_timeout_s=90)

    debug_acumulado(socket_equipmode_step2, settings, PREFIX, label="post-reboot")
    print(f"[{PREFIX}] [OK] Dispositivo de vuelta - Step 2 completado")
    print(f"[{PREFIX}]   Proximo paso: login con root/admin (pair 1 de Step 3)")
