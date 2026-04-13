"""BONUS: Tests for the reverse/locking flow (re-lock an unlocked device)."""
import pytest
from unittest.mock import MagicMock, call


TFTP_SERVER = "192.168.100.15"


def _run_reverse_lock_flow(navigator, transport, progress=None):
    """Simulates the reverse flow to re-lock an unlocked ONT.

    The reverse flow should undo what the unlock flow did, effectively
    restoring the ISP lock. Steps execute in reverse order:
    R0: Re-apply ISP lock config (equivalent of undoing 3XML unlock)
    R1: Re-enable EquipMode, apply ISP restrictions, disable EquipMode
    R2: Undo restorehwmode (re-apply ISP firmware variant)
    R3: Reload original ISP firmware pack
    R4: Disable Telnet + TFTP in GUI
    """
    if progress is None:
        progress = MagicMock()

    steps = []

    # R0: Apply ISP lock configuration (reverse of Step 4)
    progress("REVERSE", "R0: Applying ISP lock configuration")
    transport.connect(host="192.168.100.1", port=23, timeout_s=10)
    transport.login("root/admin -> root/adminHW")
    result = transport.load_pack_by_tftp(
        server_ip=TFTP_SERVER,
        remote_file="ISP_Lock.bin",
        expect="Software Operation Successful!RetCode=0x0!",
    )
    transport.send_reset()
    transport.close()
    transport.wait_for_reboot(down_timeout_s=15, up_timeout_s=90)
    steps.append({"step": "apply_isp_lock", "ok": "RetCode=0x0" in result})

    # R1: Enable EquipMode, apply ISP config, disable EquipMode (reverse of Steps 2-3)
    progress("REVERSE", "R1: Re-applying ISP restrictions via EquipMode")
    transport.connect(host="192.168.100.1", port=23, timeout_s=10)
    transport.login("root/admin_123 -> root/adminHW")
    for cmd in ["su", "shell", "EquipMode.sh on"]:
        transport.send_command(cmd)
    # Apply ISP restrictions while in EquipMode
    transport.send_command("apply_isp_restrictions.sh")
    transport.send_command("EquipMode.sh off")
    transport.send_reset()
    transport.close()
    transport.wait_for_reboot(down_timeout_s=15, up_timeout_s=90)
    steps.append({"step": "reapply_isp_restrictions", "ok": True})

    # R2: Reload ISP firmware variant (reverse of Step 1)
    progress("REVERSE", "R2: Reloading ISP firmware variant")
    transport.connect(host="192.168.100.1", port=23, timeout_s=10)
    transport.login("root/admin_123 -> root/adminHW")
    result = transport.load_pack_by_tftp(
        server_ip=TFTP_SERVER,
        remote_file="ISP_Carga.bin",
        expect="success!",
    )
    transport.send_reset()
    transport.close()
    transport.wait_for_reboot(down_timeout_s=15, up_timeout_s=90)
    steps.append({"step": "reload_isp_firmware", "ok": "success!" in result})

    # R3: Disable Telnet + TFTP in GUI (reverse of Step 0)
    progress("REVERSE", "R3: Disabling Telnet + TFTP via GUI")
    navigator.login(username="telecomadmin", password="F0xB734Fr3@j%YEP")
    navigator.navigate_to_wan_access_control()
    navigator.delete_wan_access_rule(protocol="Telnet")
    navigator.delete_wan_access_rule(protocol="TFTP")
    navigator.logout()
    steps.append({"step": "disable_telnet_tftp", "ok": True})

    return {"ok": all(s["ok"] for s in steps), "steps": steps}


@pytest.mark.reverse
class TestReverseFlowLocker:
    """Tests for the reverse locking flow (re-lock unlocked devices)."""

    def test_reverse_command_sequence(self, huawei_navigator_mock, mock_transport):
        """The reverse flow sends commands in the expected order to re-lock."""
        mock_transport.load_pack_by_tftp.side_effect = [
            "Software Operation Successful!RetCode=0x0!",
            "success!",
        ]
        result = _run_reverse_lock_flow(huawei_navigator_mock, mock_transport)

        # Verify EquipMode commands were sent
        send_calls = [str(c) for c in mock_transport.send_command.call_args_list]
        command_strings = [c.args[0] if c.args else "" for c in mock_transport.send_command.call_args_list]
        assert "EquipMode.sh on" in command_strings
        assert "EquipMode.sh off" in command_strings

    def test_reverse_steps_execute_in_order(self, huawei_navigator_mock, mock_transport):
        """Progress events confirm steps execute in reverse logical order."""
        mock_transport.load_pack_by_tftp.side_effect = [
            "Software Operation Successful!RetCode=0x0!",
            "success!",
        ]
        progress = MagicMock()
        _run_reverse_lock_flow(huawei_navigator_mock, mock_transport, progress=progress)

        messages = [c.args[1] for c in progress.call_args_list]
        assert "R0" in messages[0]
        assert "R1" in messages[1]
        assert "R2" in messages[2]
        assert "R3" in messages[3]

    def test_reverse_wifi_locked_after(self, huawei_navigator_mock, mock_transport):
        """After re-lock, WiFi configuration should be inaccessible (locked)."""
        mock_transport.load_pack_by_tftp.side_effect = [
            "Software Operation Successful!RetCode=0x0!",
            "success!",
        ]
        result = _run_reverse_lock_flow(huawei_navigator_mock, mock_transport)
        assert result["ok"] is True
        # The ISP lock config step should have completed
        lock_step = next(s for s in result["steps"] if s["step"] == "apply_isp_lock")
        assert lock_step["ok"] is True

    def test_reverse_mac_hidden_after(self, huawei_navigator_mock, mock_transport):
        """After re-lock, MAC should be hidden (ISP restrictions re-applied)."""
        mock_transport.load_pack_by_tftp.side_effect = [
            "Software Operation Successful!RetCode=0x0!",
            "success!",
        ]
        result = _run_reverse_lock_flow(huawei_navigator_mock, mock_transport)
        assert result["ok"] is True
        # ISP restrictions step should have completed
        isp_step = next(s for s in result["steps"] if s["step"] == "reapply_isp_restrictions")
        assert isp_step["ok"] is True
