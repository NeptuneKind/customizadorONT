"""Tests for Step 4: Apply Flags with 3XML.bin via TFTP."""
import pytest


TFTP_SERVER = "192.168.100.15"
EXPECTED_RESPONSE = "Software Operation Successful!RetCode=0x0!"


@pytest.mark.full_locked
class TestStep4Apply3XML:
    """Step 4 connects after reboot, logs in with yet another credential set,
    and uploads 3XML.bin via TFTP. This is the final unlock step."""

    def test_step4_connect_after_reboot(self, mock_transport):
        """Telnet reconnects after Step 3 reboot."""
        mock_transport.connect(host="192.168.100.1", port=23, timeout_s=10)
        mock_transport.connect.assert_called_once()

    def test_step4_login_creds(self, telnet_creds_step4):
        """Step 4 uses credentials: root/adminHW → root/admin."""
        creds = telnet_creds_step4
        assert creds.username_1 == "root"
        assert creds.password_1 == "adminHW"
        assert creds.username_2 == "root"
        assert creds.password_2 == "admin"

    def test_step4_tftp_upload_3xml(self, mock_transport):
        """3XML.bin is uploaded and the expected RetCode=0x0 response is received."""
        mock_transport.load_pack_by_tftp.return_value = EXPECTED_RESPONSE
        result = mock_transport.load_pack_by_tftp(
            server_ip=TFTP_SERVER, remote_file="3XML.bin", expect=EXPECTED_RESPONSE
        )
        assert "RetCode=0x0" in result
        assert "Software Operation Successful" in result

    def test_step4_tftp_wrong_retcode(self, mock_transport):
        """If RetCode is not 0x0, the response indicates failure."""
        bad_response = "Software Operation Failed!RetCode=0x1!"
        mock_transport.load_pack_by_tftp.return_value = bad_response
        result = mock_transport.load_pack_by_tftp(
            server_ip=TFTP_SERVER, remote_file="3XML.bin", expect=EXPECTED_RESPONSE
        )
        assert "RetCode=0x0" not in result
