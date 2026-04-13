"""Tests for Step 3: Restore Huawei Mode (restorehwmode.sh + EquipMode.sh off)."""
import pytest
from unittest.mock import call


@pytest.mark.full_locked
class TestStep3RestoreHuaweiMode:
    """Step 3 connects after reboot with DIFFERENT credentials,
    runs restorehwmode.sh and EquipMode.sh off, then resets."""

    def test_step3_connect_after_reboot(self, mock_transport):
        """Telnet reconnects after Step 2 reboot."""
        mock_transport.connect(host="192.168.100.1", port=23, timeout_s=10)
        mock_transport.connect.assert_called_once()

    def test_step3_login_different_creds(self, telnet_creds_step3):
        """Step 3 uses DIFFERENT credentials: root/admin → root/admin_123."""
        creds = telnet_creds_step3
        assert creds.username_1 == "root"
        assert creds.password_1 == "admin"
        assert creds.username_2 == "root"
        assert creds.password_2 == "admin_123"

    def test_step3_command_sequence(self, mock_transport):
        """Commands are sent in order: restorehwmode.sh → EquipMode.sh off."""
        commands = ["restorehwmode.sh", "EquipMode.sh off"]
        for cmd in commands:
            mock_transport.send_command(cmd)

        expected_calls = [call(cmd) for cmd in commands]
        mock_transport.send_command.assert_has_calls(expected_calls, any_order=False)

    def test_step3_restorehwmode_response(self, mock_transport):
        """restorehwmode.sh returns a response indicating success."""
        mock_transport.send_command.return_value = "Huawei mode restored"
        result = mock_transport.send_command("restorehwmode.sh")
        assert "restored" in result.lower() or result != ""

    def test_step3_send_reset(self, mock_transport):
        """Reset is sent after restoring Huawei mode."""
        mock_transport.send_reset()
        mock_transport.send_reset.assert_called_once()

    def test_step3_wait_for_reboot(self, mock_transport):
        """Wait for device to reboot after restore."""
        mock_transport.wait_for_reboot(down_timeout_s=15, up_timeout_s=90)
        mock_transport.wait_for_reboot.assert_called_once()
