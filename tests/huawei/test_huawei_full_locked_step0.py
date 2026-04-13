"""Tests for Step 0: Enable Telnet + TFTP via GUI (Selenium)."""
import pytest
from unittest.mock import MagicMock, call


SUPERUSER = {"user": "telecomadmin", "pass": "F0xB734Fr3@j%YEP"}


@pytest.mark.full_locked
class TestStep0EnableTelnetTFTP:
    """Step 0 uses Selenium to login with superuser credentials and
    enable Telnet (port 23) + TFTP via WAN Access Control rules."""

    def test_step0_login_with_superuser(self, huawei_navigator_mock):
        """Navigator.login is called with the superuser credentials."""
        nav = huawei_navigator_mock
        nav.login(username=SUPERUSER["user"], password=SUPERUSER["pass"])
        nav.login.assert_called_once_with(
            username="telecomadmin", password="F0xB734Fr3@j%YEP"
        )

    def test_step0_navigate_to_wan_access_control(self, huawei_navigator_mock):
        """After login, navigator goes to Advanced > Security > WAN Access Control."""
        nav = huawei_navigator_mock
        nav.navigate_to_wan_access_control()
        nav.navigate_to_wan_access_control.assert_called_once()

    def test_step0_create_telnet_rule(self, huawei_navigator_mock):
        """A rule for Telnet (port 23) is created."""
        nav = huawei_navigator_mock
        nav.create_wan_access_rule(protocol="Telnet", port=23)
        nav.create_wan_access_rule.assert_called_once_with(protocol="Telnet", port=23)

    def test_step0_create_tftp_rule(self, huawei_navigator_mock):
        """A rule for TFTP protocol is created."""
        nav = huawei_navigator_mock
        nav.create_wan_access_rule(protocol="TFTP")
        nav.create_wan_access_rule.assert_called_once_with(protocol="TFTP")

    def test_step0_verify_rules_created(self, huawei_navigator_mock):
        """Both Telnet and TFTP rules are verified to exist in the table."""
        nav = huawei_navigator_mock
        assert nav.verify_wan_access_rule_exists("Telnet") is True
        assert nav.verify_wan_access_rule_exists("TFTP") is True

    def test_step0_login_failure_raises(self, huawei_navigator_mock):
        """If superuser login fails, a RuntimeError is raised."""
        nav = huawei_navigator_mock
        nav.login.side_effect = RuntimeError("Login failed")
        with pytest.raises(RuntimeError, match="Login failed"):
            nav.login(username=SUPERUSER["user"], password=SUPERUSER["pass"])

    def test_step0_navigation_failure_raises(self, huawei_navigator_mock):
        """If WAN Access Control page is not found, error is raised."""
        nav = huawei_navigator_mock
        nav.navigate_to_wan_access_control.side_effect = RuntimeError(
            "WAN Access Control not found"
        )
        with pytest.raises(RuntimeError, match="WAN Access Control not found"):
            nav.navigate_to_wan_access_control()
