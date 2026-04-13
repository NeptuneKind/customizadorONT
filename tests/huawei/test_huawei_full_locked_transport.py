"""Tests for the FullLockedTransport interface contract."""
import pytest
from unittest.mock import MagicMock


@pytest.mark.full_locked
class TestFullLockedTransportInterface:
    """Validates that the transport mock (standing in for the future real
    implementation) exposes all required methods with correct signatures."""

    def test_transport_has_connect_method(self, mock_transport):
        assert callable(mock_transport.connect)
        mock_transport.connect(host="192.168.100.1", port=23, timeout_s=10)
        mock_transport.connect.assert_called_once()

    def test_transport_has_close_method(self, mock_transport):
        assert callable(mock_transport.close)
        mock_transport.close()
        mock_transport.close.assert_called_once()

    def test_transport_has_login_method(self, mock_transport):
        assert callable(mock_transport.login)

    def test_transport_has_send_command_method(self, mock_transport):
        assert callable(mock_transport.send_command)
        result = mock_transport.send_command("test_cmd")
        assert isinstance(result, str)

    def test_transport_has_load_pack_method(self, mock_transport):
        assert callable(mock_transport.load_pack_by_tftp)
        result = mock_transport.load_pack_by_tftp(
            server_ip="192.168.100.15", remote_file="test.bin", expect="ok"
        )
        assert isinstance(result, str)

    def test_transport_has_send_reset_method(self, mock_transport):
        assert callable(mock_transport.send_reset)
        mock_transport.send_reset()
        mock_transport.send_reset.assert_called_once()

    def test_transport_has_wait_for_reboot_method(self, mock_transport):
        assert callable(mock_transport.wait_for_reboot)
        mock_transport.wait_for_reboot(down_timeout_s=15, up_timeout_s=90)
        mock_transport.wait_for_reboot.assert_called_once()
