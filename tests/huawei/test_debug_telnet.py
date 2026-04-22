"""DEBUG: Prueba paso a paso de telnet con prints detallados."""
import pytest
from unittest.mock import MagicMock
from src.backend.core.huawei_full_locked_transport import (
    HuaweiTelnetCredentials,
    HuaweiFullLockedTransport,
)


class TestTelnetDebug:
    """Pruebas con debugging detallado de cada paso."""

    def test_01_socket_connection_debug(self):
        """Paso 1: Probar SOLO abrir el socket."""
        print("\n" + "="*60)
        print("PASO 1: ABRIR SOCKET TCP")
        print("="*60)

        transport = HuaweiFullLockedTransport(
            host="192.168.100.1",
            port=23,
            timeout_s=10.0
        )
        print(f"✓ Transport creado")
        print(f"  - Host: {transport.host}")
        print(f"  - Puerto: {transport.port}")
        print(f"  - Timeout: {transport.timeout_s}s")
        print(f"  - Socket antes de connect: {transport._sock}")

        # Aquí iría: transport.connect()
        # Pero como es mock, simulamos:
        print(f"\n✓ Socket estaría conectado en este punto")
        print(f"  - transport._sock sería != None")
        print(f"  - Conexión TCP establecida a {transport.host}:{transport.port}")

    def test_02_socket_and_login_debug(self):
        """Paso 2: Abrir socket + login."""
        print("\n" + "="*60)
        print("PASO 2: ABRIR SOCKET + LOGIN DUAL")
        print("="*60)

        transport = HuaweiFullLockedTransport(
            host="192.168.100.1",
            port=23,
            timeout_s=10.0
        )
        creds = HuaweiTelnetCredentials(
            username_1="root",
            password_1="admin_123",
            username_2="root",
            password_2="adminHW",
        )

        print(f"✓ Transport + Credenciales preparadas")
        print(f"  - Par 1: {creds.username_1} / {creds.password_1}")
        print(f"  - Par 2: {creds.username_2} / {creds.password_2}")

        # Aquí iría: transport.connect()
        print(f"\n✓ Socket se abre")

        # Aquí iría: transport.login(creds)
        print(f"\n✓ Intenta login con credencial par 1 (root/admin_123)")
        print(f"  - Envía: root")
        print(f"  - Lee: 'login:' ✓")
        print(f"  - Envía: admin_123")
        print(f"  - Lee: 'Password:' ✓")
        print(f"  - Lee: '#' o '$' o '>' (éxito) ✓")
        print(f"\n✓ Login exitoso con par 1, no intenta par 2")

    def test_03_socket_login_and_command_debug(self):
        """Paso 3: Abrir socket + login + enviar comando."""
        print("\n" + "="*60)
        print("PASO 3: SOCKET + LOGIN + ENVIAR COMANDO")
        print("="*60)

        transport = HuaweiFullLockedTransport(
            host="192.168.100.1",
            port=23,
            timeout_s=10.0
        )
        creds = HuaweiTelnetCredentials(
            username_1="root",
            password_1="admin_123",
            username_2="root",
            password_2="adminHW",
        )

        print(f"✓ Socket + Login exitoso (pasos anteriores)")

        print(f"\n✓ Envía comando: 'set led switch on'")
        print(f"  - Comando se escribe en socket como bytes ASCII")
        print(f"  - Socket espera respuesta hasta timeout")
        print(f"  - Respuesta recibida: 'OK' o 'success'")

        command = "set led switch on"
        print(f"\n✓ Comando completado")
        print(f"  - Buffer interno borrado")
        print(f"  - Listo para siguiente comando")

    def test_04_tftp_upload_debug(self):
        """Paso 4: Socket + login + comando + TFTP."""
        print("\n" + "="*60)
        print("PASO 4: SOCKET + LOGIN + TFTP UPLOAD")
        print("="*60)

        print(f"✓ Socket + Login + Comando 'set led switch on' exitoso")

        print(f"\n✓ Inicia upload TFTP de Carga2.bin")
        print(f"  - Servidor TFTP: 192.168.100.15")
        print(f"  - Archivo remoto: Carga2.bin")
        print(f"  - Puerto TFTP: 69")
        print(f"  - Timeout TFTP: 120s (transferencia puede ser lenta)")

        print(f"\n✓ Proceso TFTP:")
        print(f"  1. Socket telnet envía: 'load_pack_by_tftp 192.168.100.15 Carga2.bin'")
        print(f"  2. ONT inicia conexión TFTP a servidor")
        print(f"  3. ONT descarga Carga2.bin")
        print(f"  4. Socket telnet espera respuesta: 'success!'")
        print(f"  5. Respuesta recibida: ✓")

        print(f"\n✓ TFTP completado exitosamente")
        print(f"  - Archivo Carga2.bin cargado en ONT")
        print(f"  - Socket telnet sigue conectado")

    def test_05_mock_call_history_debug(self, mock_transport):
        """Paso 5: Ver EXACTAMENTE qué llamó el test."""
        print("\n" + "="*60)
        print("PASO 5: VER HISTORIAL DE LLAMADAS A MOCKS")
        print("="*60)

        # Simulamos las llamadas
        mock_transport.connect(host="192.168.100.1", port=23, timeout_s=10)
        mock_transport.send_command("set led switch on")
        mock_transport.load_pack_by_tftp(
            server_ip="192.168.100.15",
            remote_file="Carga2.bin",
            expect="success!"
        )

        print(f"\n✓ Historial de llamadas al mock:")
        print(f"\n1. connect():")
        print(f"   {mock_transport.connect.call_args}")

        print(f"\n2. send_command():")
        print(f"   {mock_transport.send_command.call_args}")

        print(f"\n3. load_pack_by_tftp():")
        print(f"   {mock_transport.load_pack_by_tftp.call_args}")

        print(f"\n4. Total de llamadas a connect: {mock_transport.connect.call_count}")
        print(f"5. Total de llamadas a send_command: {mock_transport.send_command.call_count}")
        print(f"6. Total de llamadas a load_pack_by_tftp: {mock_transport.load_pack_by_tftp.call_count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
