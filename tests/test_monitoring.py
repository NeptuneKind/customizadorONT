"""Tests for device detection and monitoring."""
import pytest
from unittest.mock import patch, MagicMock

from src.backend.core.monitoring import (
    DetectedDevice,
    detect_vendor_and_model,
    ping_once_windows,
    wait_for_device_ip,
    _extract_title,
    _extract_js_productname,
)


@pytest.mark.unit
class TestPingOnceWindows:
    """Tests for the ping utility."""

    @patch("src.backend.core.monitoring.subprocess.run")
    def test_ping_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert ping_once_windows("192.168.100.1") is True

    @patch("src.backend.core.monitoring.subprocess.run")
    def test_ping_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert ping_once_windows("192.168.100.1") is False

    @patch("src.backend.core.monitoring.subprocess.run")
    def test_ping_exception(self, mock_run):
        mock_run.side_effect = OSError("Network error")
        assert ping_once_windows("192.168.100.1") is False


@pytest.mark.unit
class TestWaitForDeviceIP:
    """Tests for IP waiting logic."""

    @patch("src.backend.core.monitoring.ping_once_windows")
    def test_first_ip_responds(self, mock_ping):
        mock_ping.return_value = True
        result = wait_for_device_ip(["192.168.100.1", "192.168.1.1"])
        assert result == "192.168.100.1"

    @patch("src.backend.core.monitoring.ping_once_windows")
    def test_timeout_raises(self, mock_ping):
        mock_ping.return_value = False
        with pytest.raises(TimeoutError):
            wait_for_device_ip(
                ["192.168.100.1"], overall_timeout_s=0.1, sleep_s=0.01
            )


@pytest.mark.unit
class TestExtractTitle:
    """Tests for HTML title extraction."""

    def test_simple_title(self):
        html = "<html><head><title>HG8145X6-10</title></head></html>"
        assert _extract_title(html) == "HG8145X6-10"

    def test_no_title(self):
        html = "<html><head></head></html>"
        assert _extract_title(html) == ""

    def test_multiline_title(self):
        html = "<html><head><title>\n  HG8145V5  \n</title></head></html>"
        assert _extract_title(html) == "HG8145V5"


@pytest.mark.unit
class TestExtractJSProductName:
    """Tests for JS ProductName variable extraction."""

    def test_simple_productname(self):
        html = "var ProductName = 'HG8145X6';"
        assert _extract_js_productname(html) == "HG8145X6"

    def test_productname_with_escape(self):
        html = "var ProductName = 'HG8145X6\\x2d10';"
        result = _extract_js_productname(html)
        assert result == "HG8145X6\\x2d10"

    def test_no_productname(self):
        html = "var something = 'other';"
        assert _extract_js_productname(html) == ""


@pytest.mark.unit
class TestDetectVendorAndModel:
    """Tests for the main detection logic."""

    @patch("src.backend.core.monitoring._get_html")
    def test_detect_zte_by_ip(self, mock_html):
        """IP 192.168.1.1 is always detected as ZTE."""
        mock_html.return_value = "<title>F670L</title>"
        result = detect_vendor_and_model("192.168.1.1")
        assert result.vendor == "ZTE"
        assert result.model_code == "MOD002"

    @patch("src.backend.core.monitoring._get_html")
    def test_detect_zte_f6600(self, mock_html):
        """ZTE F6600 model detection."""
        mock_html.return_value = "<title>ZXHN F6600</title>"
        result = detect_vendor_and_model("192.168.1.1")
        assert result.vendor == "ZTE"
        assert result.model_code == "MOD009"

    @patch("src.backend.core.monitoring._get_html")
    def test_detect_huawei_x6_10_by_html(self, mock_html):
        """Huawei HG8145X6-10 detected by title."""
        mock_html.return_value = '<html><title>HG8145X6-10</title><input id="txt_username"></html>'
        result = detect_vendor_and_model("192.168.100.1")
        assert result.vendor == "HUAWEI"
        assert result.model_code == "MOD003"
        assert "HG8145X6-10" in result.product_name

    @patch("src.backend.core.monitoring._get_html")
    def test_detect_huawei_x6_by_js(self, mock_html):
        """Huawei HG8145X6 detected by JS ProductName."""
        mock_html.return_value = (
            '<html><title></title>'
            "<script>var ProductName = 'HG8145X6';</script>"
            '<input id="txt_username"></html>'
        )
        result = detect_vendor_and_model("192.168.100.1")
        assert result.vendor == "HUAWEI"
        assert result.model_code == "MOD007"

    @patch("src.backend.core.monitoring._get_html")
    def test_detect_huawei_v5(self, mock_html):
        """Huawei HG8145V5 detected by title."""
        mock_html.return_value = '<html><title>HG8145V5</title><input id="txt_password"></html>'
        result = detect_vendor_and_model("192.168.100.1")
        assert result.vendor == "HUAWEI"
        assert result.model_code == "MOD004"

    @patch("src.backend.core.monitoring._get_html")
    def test_detect_fiberhome_fallback(self, mock_html):
        """Non-Huawei, non-ZTE IP falls back to FiberHome."""
        mock_html.return_value = "<html><title>Unknown Device</title></html>"
        result = detect_vendor_and_model("192.168.100.1")
        assert result.vendor == "FIBERHOME"
        assert result.model_code == "MOD001"
        assert result.needs_post_login_model is True
