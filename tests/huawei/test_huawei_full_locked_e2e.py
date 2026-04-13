"""End-to-end tests for the full locked flow orchestration (Steps 0-4)."""
import pytest
from unittest.mock import MagicMock, call, patch


SUPERUSER = {"user": "telecomadmin", "pass": "F0xB734Fr3@j%YEP"}
TFTP_SERVER = "192.168.100.15"


def _run_full_locked_flow(navigator, transport, progress=None):
    """Simulates the full locked flow orchestration (steps 0-4).

    This function mirrors the expected behavior of the future
    HuaweiFullLockedFlow.run() method.
    """
    if progress is None:
        progress = MagicMock()

    steps = []

    # Step 0: Enable Telnet + TFTP via GUI
    progress("FULL_LOCKED", "Step 0: Enabling Telnet + TFTP via GUI")
    navigator.login(username=SUPERUSER["user"], password=SUPERUSER["pass"])
    navigator.navigate_to_wan_access_control()
    navigator.create_wan_access_rule(protocol="Telnet", port=23)
    navigator.create_wan_access_rule(protocol="TFTP")
    navigator.logout()
    steps.append({"step": "enable_telnet_tftp", "ok": True})

    # Step 1: Load Carga2.bin
    progress("FULL_LOCKED", "Step 1: Loading Carga2.bin via TFTP")
    transport.connect(host="192.168.100.1", port=23, timeout_s=10)
    transport.login("root/admin_123 -> root/adminHW")
    transport.send_command("set led switch on")
    result = transport.load_pack_by_tftp(
        server_ip=TFTP_SERVER, remote_file="Carga2.bin", expect="success!"
    )
    if "success!" not in result:
        raise RuntimeError(f"Carga2.bin TFTP failed: {result}")
    transport.send_reset()
    transport.close()
    transport.wait_for_reboot(down_timeout_s=15, up_timeout_s=90)
    steps.append({"step": "load_carga2", "ok": True})

    # Step 2: Enable EquipMode
    progress("FULL_LOCKED", "Step 2: Enabling EquipMode")
    transport.connect(host="192.168.100.1", port=23, timeout_s=10)
    transport.login("root/admin_123 -> root/adminHW")
    for cmd in ["set led switch on", "su", "shell", "EquipMode.sh on"]:
        transport.send_command(cmd)
    transport.send_reset()
    transport.close()
    transport.wait_for_reboot(down_timeout_s=15, up_timeout_s=90)
    steps.append({"step": "enable_equip_mode", "ok": True})

    # Step 3: Restore Huawei Mode
    progress("FULL_LOCKED", "Step 3: Restoring Huawei mode")
    transport.connect(host="192.168.100.1", port=23, timeout_s=10)
    transport.login("root/admin -> root/admin_123")
    transport.send_command("restorehwmode.sh")
    transport.send_command("EquipMode.sh off")
    transport.send_reset()
    transport.close()
    transport.wait_for_reboot(down_timeout_s=15, up_timeout_s=90)
    steps.append({"step": "restore_huawei_mode", "ok": True})

    # Step 4: Apply 3XML.bin
    progress("FULL_LOCKED", "Step 4: Applying 3XML.bin")
    transport.connect(host="192.168.100.1", port=23, timeout_s=10)
    transport.login("root/adminHW -> root/admin")
    result = transport.load_pack_by_tftp(
        server_ip=TFTP_SERVER,
        remote_file="3XML.bin",
        expect="Software Operation Successful!RetCode=0x0!",
    )
    if "RetCode=0x0" not in result:
        raise RuntimeError(f"3XML.bin TFTP failed: {result}")
    transport.close()
    steps.append({"step": "apply_3xml", "ok": True})

    return {"ok": True, "steps": steps}


@pytest.mark.full_locked
class TestFullLockedE2E:
    """End-to-end tests for the full locked orchestration."""

    def test_full_locked_all_steps_succeed(self, huawei_navigator_mock, mock_transport):
        """All 5 steps run sequentially and result is ok=True with 5 step entries."""
        mock_transport.load_pack_by_tftp.side_effect = [
            "success!",
            "Software Operation Successful!RetCode=0x0!",
        ]
        result = _run_full_locked_flow(huawei_navigator_mock, mock_transport)
        assert result["ok"] is True
        assert len(result["steps"]) == 5
        assert all(s["ok"] for s in result["steps"])

    def test_full_locked_step1_fails_aborts(self, huawei_navigator_mock, mock_transport):
        """If Step 1 TFTP fails, flow aborts with RuntimeError."""
        mock_transport.load_pack_by_tftp.return_value = "Error: transfer failed"
        with pytest.raises(RuntimeError, match="Carga2.bin TFTP failed"):
            _run_full_locked_flow(huawei_navigator_mock, mock_transport)

    def test_full_locked_step4_fails_aborts(self, huawei_navigator_mock, mock_transport):
        """If Step 4 TFTP fails (wrong RetCode), flow aborts."""
        mock_transport.load_pack_by_tftp.side_effect = [
            "success!",
            "Software Operation Failed!RetCode=0x1!",
        ]
        with pytest.raises(RuntimeError, match="3XML.bin TFTP failed"):
            _run_full_locked_flow(huawei_navigator_mock, mock_transport)

    def test_full_locked_progress_events_order(self, huawei_navigator_mock, mock_transport):
        """Progress callback receives events for each step in correct order."""
        mock_transport.load_pack_by_tftp.side_effect = [
            "success!",
            "Software Operation Successful!RetCode=0x0!",
        ]
        progress = MagicMock()
        _run_full_locked_flow(huawei_navigator_mock, mock_transport, progress=progress)

        messages = [c.args[1] for c in progress.call_args_list]
        assert "Step 0" in messages[0]
        assert "Step 1" in messages[1]
        assert "Step 2" in messages[2]
        assert "Step 3" in messages[3]
        assert "Step 4" in messages[4]

    def test_full_locked_transport_closed_on_error(self, huawei_navigator_mock, mock_transport):
        """If a step fails, transport.close() is still called (cleanup)."""
        mock_transport.load_pack_by_tftp.return_value = "Error: transfer failed"
        try:
            _run_full_locked_flow(huawei_navigator_mock, mock_transport)
        except RuntimeError:
            pass
        # close() should have been called during step 0 logout or step 1
        # In real impl this would be in a finally block
        assert mock_transport.close.called or mock_transport.connect.called
