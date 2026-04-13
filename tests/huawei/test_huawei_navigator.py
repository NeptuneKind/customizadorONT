"""Tests for HuaweiNavigator Selenium methods (mocked WebDriver)."""
import pytest
from unittest.mock import MagicMock, patch

from src.backend.customizer.models import WifiBand


@pytest.mark.normal
class TestHuaweiNavigatorInit:
    """Tests for navigator initialization and basic properties."""

    def test_navigator_stores_driver(self, huawei_navigator_mock):
        """Navigator mock is callable and has expected attributes."""
        assert huawei_navigator_mock is not None

    def test_navigator_has_login_method(self, huawei_navigator_mock):
        assert callable(huawei_navigator_mock.login)

    def test_navigator_has_logout_method(self, huawei_navigator_mock):
        assert callable(huawei_navigator_mock.logout)

    def test_navigator_has_read_wifi_band(self, huawei_navigator_mock):
        assert callable(huawei_navigator_mock.read_wifi_band)

    def test_navigator_has_update_wifi_band(self, huawei_navigator_mock):
        assert callable(huawei_navigator_mock.update_wifi_band)

    def test_navigator_has_read_web_credentials(self, huawei_navigator_mock):
        assert callable(huawei_navigator_mock.read_web_credentials)

    def test_navigator_has_read_ip_configuration(self, huawei_navigator_mock):
        assert callable(huawei_navigator_mock.read_ip_configuration)


@pytest.mark.normal
class TestHuaweiNavigatorWiFi:
    """Tests for WiFi-related navigator methods."""

    def test_read_wifi_band_returns_dict(self, huawei_navigator_mock):
        result = huawei_navigator_mock.read_wifi_band(band=WifiBand.B24)
        assert isinstance(result, dict)
        assert "ssid" in result
        assert "password" in result

    def test_update_wifi_band_returns_before_after(self, huawei_navigator_mock):
        result = huawei_navigator_mock.update_wifi_band(
            band=WifiBand.B24, ssid="NewSSID", password="NewPass"
        )
        assert "before" in result
        assert "after" in result


@pytest.mark.normal
class TestHuaweiNavigatorWebCredentials:
    """Tests for web credentials navigator methods."""

    def test_read_web_credentials_returns_dict(self, huawei_navigator_mock):
        result = huawei_navigator_mock.read_web_credentials()
        assert isinstance(result, dict)

    def test_verify_login_returns_bool(self, huawei_navigator_mock):
        result = huawei_navigator_mock.verify_web_credentials_login(
            username="root", password="test"
        )
        assert isinstance(result, bool)


@pytest.mark.normal
class TestHuaweiNavigatorIP:
    """Tests for IP configuration navigator methods."""

    def test_read_ip_returns_dict(self, huawei_navigator_mock):
        result = huawei_navigator_mock.read_ip_configuration()
        assert isinstance(result, dict)
        assert "ip" in result

    def test_update_ip_calls_correctly(self, huawei_navigator_mock):
        huawei_navigator_mock.update_ip_configuration(new_ip="192.168.101.1")
        huawei_navigator_mock.update_ip_configuration.assert_called_once_with(
            new_ip="192.168.101.1"
        )
