"""Tests for the Huawei normal customization flow (WiFi, WebCreds, IP)."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from src.backend.customizer.models import (
    CustomizationPlan,
    IPPlan,
    WebCredentialsPlan,
    WifiBand,
    WifiPlan,
)
from src.backend.customizer.vendors.huawei.huawei_adapter import HuaweiAdapter


@pytest.mark.normal
class TestHuaweiAdapterWiFi:
    """Tests for WiFi plan application."""

    def test_apply_wifi_disabled_skip(self, huawei_adapter, fake_ctx, mock_progress):
        """When wifi.enabled=False, step is recorded as wifi_disabled."""
        plan = CustomizationPlan(wifi=WifiPlan(enabled=False))
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder:
            nav = MagicMock()
            nav.login.return_value = None
            nav.logout.return_value = None
            nav._open_root.return_value = None
            mock_nav_builder.return_value = nav

            result = huawei_adapter.apply(plan, fake_ctx, mock_progress)

        wifi_steps = [s for s in result.steps if "wifi" in s.get("step", "")]
        assert any("disabled" in s["step"] for s in wifi_steps)

    def test_apply_wifi_24_only(self, huawei_adapter, fake_ctx, mock_progress):
        """When only 2.4GHz values are set, only B24 band is updated."""
        plan = CustomizationPlan(
            wifi=WifiPlan(enabled=True, ssid_24="Net24", pass_24="Pw24")
        )
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder:
            nav = MagicMock()
            nav._open_root.return_value = None
            nav.read_wifi_band.return_value = {"ssid": "Net24", "password": "Pw24"}
            nav.update_wifi_band.return_value = {
                "before": {"ssid": "Old", "password": "OldPw"},
                "after": {"ssid": "Net24", "password": "Pw24"},
            }
            mock_nav_builder.return_value = nav

            result = huawei_adapter.apply(plan, fake_ctx, mock_progress)

        nav.update_wifi_band.assert_called_once()
        call_kwargs = nav.update_wifi_band.call_args
        assert call_kwargs[1]["band"] == WifiBand.B24 or call_kwargs.kwargs.get("band") == WifiBand.B24

    def test_apply_wifi_5_only(self, huawei_adapter, fake_ctx, mock_progress):
        """When only 5GHz values are set, only B5 band is updated."""
        plan = CustomizationPlan(
            wifi=WifiPlan(enabled=True, ssid_5="Net5G", pass_5="Pw5G")
        )
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder:
            nav = MagicMock()
            nav._open_root.return_value = None
            nav.read_wifi_band.return_value = {"ssid": "Net5G", "password": "Pw5G"}
            nav.update_wifi_band.return_value = {
                "before": {"ssid": "Old5", "password": "OldPw5"},
                "after": {"ssid": "Net5G", "password": "Pw5G"},
            }
            mock_nav_builder.return_value = nav

            result = huawei_adapter.apply(plan, fake_ctx, mock_progress)

        nav.update_wifi_band.assert_called_once()

    def test_apply_wifi_both_bands(self, huawei_adapter, fake_ctx, mock_progress):
        """When both bands are set, both are updated."""
        plan = CustomizationPlan(
            wifi=WifiPlan(
                enabled=True,
                ssid_24="Net24", pass_24="Pw24",
                ssid_5="Net5G", pass_5="Pw5G",
            )
        )
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder:
            nav = MagicMock()
            nav._open_root.return_value = None
            nav.read_wifi_band.side_effect = [
                {"ssid": "Net24", "password": "Pw24"},
                {"ssid": "Net24", "password": "Pw24"},
                {"ssid": "Net5G", "password": "Pw5G"},
                {"ssid": "Net5G", "password": "Pw5G"},
            ]
            nav.update_wifi_band.side_effect = [
                {"before": {"ssid": "O", "password": "O"}, "after": {"ssid": "Net24", "password": "Pw24"}},
                {"before": {"ssid": "O", "password": "O"}, "after": {"ssid": "Net5G", "password": "Pw5G"}},
            ]
            mock_nav_builder.return_value = nav

            result = huawei_adapter.apply(plan, fake_ctx, mock_progress)

        assert nav.update_wifi_band.call_count == 2

    def test_apply_wifi_validation_mismatch(self, huawei_adapter, fake_ctx, mock_progress):
        """If read-after-write SSID doesn't match, error is appended."""
        plan = CustomizationPlan(
            wifi=WifiPlan(enabled=True, ssid_24="Expected", pass_24="Pw")
        )
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder:
            nav = MagicMock()
            nav._open_root.return_value = None
            # First read (before), then read (after) returns wrong value
            nav.read_wifi_band.side_effect = [
                {"ssid": "Old", "password": "OldPw"},
                {"ssid": "WRONG_SSID", "password": "Pw"},
            ]
            nav.update_wifi_band.return_value = {
                "before": {"ssid": "Old", "password": "OldPw"},
                "after": {"ssid": "WRONG_SSID", "password": "Pw"},
            }
            mock_nav_builder.return_value = nav

            result = huawei_adapter.apply(plan, fake_ctx, mock_progress)

        assert len(result.errors) > 0
        assert any("SSID" in e for e in result.errors)


@pytest.mark.normal
class TestHuaweiAdapterWebCredentials:
    """Tests for web credentials plan application."""

    def test_apply_web_credentials_disabled_skip(self, huawei_adapter, fake_ctx, mock_progress):
        """When enabled=False, step is web_credentials_disabled."""
        plan = CustomizationPlan(
            web_credentials=WebCredentialsPlan(enabled=False)
        )
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder:
            nav = MagicMock()
            nav._open_root.return_value = None
            mock_nav_builder.return_value = nav

            result = huawei_adapter.apply(plan, fake_ctx, mock_progress)

        web_steps = [s for s in result.steps if "web_credentials" in s.get("step", "")]
        assert len(web_steps) > 0

    def test_apply_web_credentials_success(self, huawei_adapter, fake_ctx, mock_progress):
        """Full flow: update + verify login succeeds."""
        plan = CustomizationPlan(
            web_credentials=WebCredentialsPlan(
                enabled=True, old_password="admin", new_password="NewPw"
            )
        )
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder:
            nav = MagicMock()
            nav._open_root.return_value = None
            nav.read_web_credentials.return_value = {"username": "root"}
            nav.update_web_credentials.return_value = {}
            nav.verify_web_credentials_login.return_value = True
            mock_nav_builder.return_value = nav

            result = huawei_adapter.apply(plan, fake_ctx, mock_progress)

        nav.verify_web_credentials_login.assert_called_once()
        assert result.ok is True

    def test_apply_web_credentials_verify_fails(self, huawei_adapter, fake_ctx, mock_progress):
        """If verification login fails, error is appended."""
        plan = CustomizationPlan(
            web_credentials=WebCredentialsPlan(
                enabled=True, old_password="admin", new_password="NewPw"
            )
        )
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder:
            nav = MagicMock()
            nav._open_root.return_value = None
            nav.read_web_credentials.return_value = {"username": "root"}
            nav.update_web_credentials.return_value = {}
            nav.verify_web_credentials_login.return_value = False
            mock_nav_builder.return_value = nav

            result = huawei_adapter.apply(plan, fake_ctx, mock_progress)

        assert len(result.errors) > 0


@pytest.mark.normal
class TestHuaweiAdapterIP:
    """Tests for IP plan application."""

    def test_apply_ip_disabled_skip(self, huawei_adapter, fake_ctx, mock_progress):
        """When ip.enabled=False, step is ip_disabled."""
        plan = CustomizationPlan(ip=IPPlan(enabled=False))
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder:
            nav = MagicMock()
            nav._open_root.return_value = None
            mock_nav_builder.return_value = nav

            result = huawei_adapter.apply(plan, fake_ctx, mock_progress)

        ip_steps = [s for s in result.steps if "ip" in s.get("step", "")]
        assert len(ip_steps) > 0

    def test_apply_ip_success(self, huawei_adapter, fake_ctx, mock_progress):
        """IP change flow: update + verification tab + login."""
        plan = CustomizationPlan(ip=IPPlan(enabled=True, new_ip="192.168.101.1"))
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder, \
             patch.object(huawei_adapter, "_build_navigator_for_ip") as mock_nav_ip:
            nav = MagicMock()
            nav._open_root.return_value = None
            nav.read_ip_configuration.return_value = {"ip": "192.168.100.1"}
            nav.update_ip_configuration.return_value = None
            nav.open_blank_verification_tab.return_value = "main_window"
            mock_nav_builder.return_value = nav

            verify_nav = MagicMock()
            verify_nav.wait_until_login_accessible_on_new_ip.return_value = None
            verify_nav.login_for_verification.return_value = None
            verify_nav.logout.return_value = None
            verify_nav.switch_to_window.return_value = None
            verify_nav.close_current_tab_and_switch_back.return_value = None
            mock_nav_ip.return_value = verify_nav

            fake_ctx.driver.current_window_handle = "main_window"
            fake_ctx.driver.window_handles = ["main_window", "verify_tab"]

            result = huawei_adapter.apply(plan, fake_ctx, mock_progress)

        ip_steps = [s for s in result.steps if s.get("step") == "ip_configuration"]
        assert len(ip_steps) == 1


@pytest.mark.normal
class TestHuaweiAdapterLogin:
    """Tests for login credential handling."""

    def test_apply_login_all_fail(self, huawei_adapter, fake_ctx, mock_progress):
        """If all login candidates fail, RuntimeError is captured."""
        plan = CustomizationPlan()
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder:
            nav = MagicMock()
            nav._open_root.return_value = None
            nav.login.side_effect = RuntimeError("Login failed")
            mock_nav_builder.return_value = nav

            result = huawei_adapter.apply(plan, fake_ctx, mock_progress)

        assert result.ok is False
        assert len(result.errors) > 0

    def test_apply_login_second_succeeds(self, huawei_adapter, fake_ctx, mock_progress):
        """First candidate fails, second succeeds."""
        plan = CustomizationPlan()
        call_count = 0

        def login_side_effect(username, password):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("First login failed")

        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder:
            nav = MagicMock()
            nav._open_root.return_value = None
            nav.login.side_effect = login_side_effect
            mock_nav_builder.return_value = nav

            result = huawei_adapter.apply(plan, fake_ctx, mock_progress)

        assert result.ok is True
        assert nav.login.call_count == 2


@pytest.mark.normal
class TestHuaweiAdapterFullPlan:
    """Tests for combined plan execution."""

    def test_apply_full_plan_wifi_webcreds(self, huawei_adapter, fake_ctx, mock_progress, full_plan):
        """WiFi + WebCreds both execute, IP is disabled (mutual exclusion)."""
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder:
            nav = MagicMock()
            nav._open_root.return_value = None
            # read_wifi_band is called: before_24, after_24, before_5, after_5
            nav.read_wifi_band.side_effect = [
                {"ssid": "Old24", "password": "OldPw24"},
                {"ssid": "TestSSID24", "password": "TestPass24"},
                {"ssid": "Old5", "password": "OldPw5"},
                {"ssid": "TestSSID5", "password": "TestPass5"},
            ]
            nav.update_wifi_band.side_effect = [
                {"before": {"ssid": "Old24", "password": "OldPw24"}, "after": {"ssid": "TestSSID24", "password": "TestPass24"}},
                {"before": {"ssid": "Old5", "password": "OldPw5"}, "after": {"ssid": "TestSSID5", "password": "TestPass5"}},
            ]
            nav.read_web_credentials.return_value = {"username": "root"}
            nav.update_web_credentials.return_value = {}
            nav.verify_web_credentials_login.return_value = True
            mock_nav_builder.return_value = nav

            result = huawei_adapter.apply(full_plan, fake_ctx, mock_progress)

        assert result.ok is True
        step_names = [s["step"] for s in result.steps]
        assert any("wifi" in s for s in step_names)
        assert any("web_credentials" in s for s in step_names)
        assert any("ip" in s and "disabled" in s for s in step_names)

    def test_apply_ip_only_plan(self, huawei_adapter, fake_ctx, mock_progress, ip_only_plan):
        """Only IP executes, WiFi and WebCreds are disabled."""
        with patch.object(huawei_adapter, "_build_navigator") as mock_nav_builder, \
             patch.object(huawei_adapter, "_build_navigator_for_ip") as mock_nav_ip:
            nav = MagicMock()
            nav._open_root.return_value = None
            nav.read_ip_configuration.return_value = {"ip": "192.168.100.1"}
            nav.update_ip_configuration.return_value = None
            nav.open_blank_verification_tab.return_value = "main_window"
            mock_nav_builder.return_value = nav

            verify_nav = MagicMock()
            mock_nav_ip.return_value = verify_nav
            fake_ctx.driver.current_window_handle = "main_window"

            result = huawei_adapter.apply(ip_only_plan, fake_ctx, mock_progress)

        step_names = [s["step"] for s in result.steps]
        assert any("wifi" in s and ("disabled" in s or "skip" in s) for s in step_names)
        assert any("ip_configuration" in s for s in step_names)
