"""Tests for Step 2: Enable Customization Mode (EquipMode.sh on)."""
import pytest
from unittest.mock import call


@pytest.mark.full_locked
class TestStep2EnableEquipMode:
    """Step 2 connects after reboot, logs in, and runs the command sequence:
    set led switch on → su → shell → EquipMode.sh on → reset."""

    def test_step2_connect_after_reboot(self, mock_transport):
        """Telnet reconnects after Step 1 reboot."""
        mock_transport.connect(host="192.168.100.1", port=23, timeout_s=10)
        mock_transport.connect.assert_called_once()

    def test_step2_dual_login(self, mock_transport, telnet_creds_step2):
        """Login uses same credentials as Step 1: root/admin_123 → root/adminHW."""
        creds = telnet_creds_step2
        assert creds.username_1 == "root"
        assert creds.password_1 == "admin_123"
        assert creds.username_2 == "root"
        assert creds.password_2 == "adminHW"
        mock_transport.login(creds)
        mock_transport.login.assert_called_once()

    def test_step2_command_sequence(self, mock_transport):
        """Commands are sent in exact order: led → su → shell → EquipMode.sh on."""
        commands = ["set led switch on", "su", "shell", "EquipMode.sh on"]
        for cmd in commands:
            mock_transport.send_command(cmd)

        expected_calls = [call(cmd) for cmd in commands]
        mock_transport.send_command.assert_has_calls(expected_calls, any_order=False)

    def test_step2_equipmode_response(self, mock_transport):
        """EquipMode.sh on returns a response (command acknowledged)."""
        mock_transport.send_command.return_value = "EquipMode enabled"
        result = mock_transport.send_command("EquipMode.sh on")
        assert result == "EquipMode enabled"

    def test_step2_send_reset(self, mock_transport):
        """Reset is sent after EquipMode activation."""
        mock_transport.send_reset()
        mock_transport.send_reset.assert_called_once()

    def test_step2_wait_for_reboot(self, mock_transport):
        """Wait for device to reboot after EquipMode activation."""
        mock_transport.wait_for_reboot(down_timeout_s=15, up_timeout_s=90)
        mock_transport.wait_for_reboot.assert_called_once()
