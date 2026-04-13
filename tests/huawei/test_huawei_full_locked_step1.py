"""Tests for Step 1: Load Carga2.bin via TFTP."""
import pytest
from unittest.mock import call


ONT_HOST = "192.168.100.1"
ONT_PORT = 23
TFTP_SERVER = "192.168.100.15"


@pytest.mark.full_locked
class TestStep1LoadCarga2:
    """Step 1 connects via Telnet, performs dual login, sends LED command,
    uploads Carga2.bin via TFTP, then resets the device."""

    def test_step1_telnet_connect(self, mock_transport):
        """Transport connects to ONT on port 23."""
        mock_transport.connect(host=ONT_HOST, port=ONT_PORT, timeout_s=10)
        mock_transport.connect.assert_called_once_with(
            host=ONT_HOST, port=ONT_PORT, timeout_s=10
        )

    def test_step1_dual_login_success(self, mock_transport, telnet_creds_step1):
        """Dual login with root/admin_123 then root/adminHW succeeds."""
        creds = telnet_creds_step1
        mock_transport.login(creds)
        mock_transport.login.assert_called_once_with(creds)

    def test_step1_dual_login_fallback(self, mock_transport, telnet_creds_step1):
        """If first credential pair fails, second pair is tried."""
        call_count = 0

        def login_side_effect(creds):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("First pair failed")

        mock_transport.login.side_effect = login_side_effect
        # First call fails
        with pytest.raises(RuntimeError):
            mock_transport.login(telnet_creds_step1)
        # Second call succeeds
        mock_transport.login.side_effect = None
        mock_transport.login(telnet_creds_step1)
        assert mock_transport.login.call_count == 2

    def test_step1_dual_login_both_fail(self, mock_transport, telnet_creds_step1):
        """If both credential pairs fail, RuntimeError is raised."""
        mock_transport.login.side_effect = RuntimeError("Auth failed")
        with pytest.raises(RuntimeError, match="Auth failed"):
            mock_transport.login(telnet_creds_step1)

    def test_step1_send_led_command(self, mock_transport):
        """LED switch command is sent before TFTP upload."""
        mock_transport.send_command("set led switch on")
        mock_transport.send_command.assert_called_with("set led switch on")

    def test_step1_tftp_upload_carga2(self, mock_transport):
        """Carga2.bin is uploaded via TFTP and 'success!' is expected."""
        mock_transport.load_pack_by_tftp.return_value = "success!"
        result = mock_transport.load_pack_by_tftp(
            server_ip=TFTP_SERVER, remote_file="Carga2.bin", expect="success!"
        )
        assert "success!" in result
        mock_transport.load_pack_by_tftp.assert_called_once_with(
            server_ip=TFTP_SERVER, remote_file="Carga2.bin", expect="success!"
        )

    def test_step1_tftp_wrong_response(self, mock_transport):
        """If TFTP response does not contain 'success!', error is raised."""
        mock_transport.load_pack_by_tftp.return_value = "Error: transfer failed"
        result = mock_transport.load_pack_by_tftp(
            server_ip=TFTP_SERVER, remote_file="Carga2.bin", expect="success!"
        )
        assert "success!" not in result

    def test_step1_send_reset(self, mock_transport):
        """Reset command is sent after TFTP upload."""
        mock_transport.send_reset()
        mock_transport.send_reset.assert_called_once()

    def test_step1_wait_for_reboot(self, mock_transport):
        """Wait for device to go down and come back up."""
        mock_transport.wait_for_reboot(down_timeout_s=15, up_timeout_s=90)
        mock_transport.wait_for_reboot.assert_called_once_with(
            down_timeout_s=15, up_timeout_s=90
        )
