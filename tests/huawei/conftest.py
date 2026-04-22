"""Huawei-specific fixtures for full locked and normal flow tests."""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from src.backend.customizer.vendors.huawei.huawei_adapter import HuaweiAdapter


# ── Telnet credentials dataclass (mirrors future transport interface) ──

@dataclass
class HuaweiTelnetCredentials:
    username_1: str
    password_1: str
    username_2: str
    password_2: str


# ── Adapter ─────────────────────────────────────────────────────────

@pytest.fixture()
def huawei_adapter():
    return HuaweiAdapter()


# ── Navigator mock ──────────────────────────────────────────────────

@pytest.fixture()
def huawei_navigator_mock():
    nav = MagicMock()
    nav.login.return_value = None
    nav.logout.return_value = None
    nav.read_wifi_band.return_value = {"ssid": "OldSSID", "password": "OldPass"}
    nav.update_wifi_band.return_value = {
        "before": {"ssid": "OldSSID", "password": "OldPass"},
        "after": {"ssid": "NewSSID", "password": "NewPass"},
    }
    nav.read_web_credentials.return_value = {"username": "root"}
    nav.update_web_credentials.return_value = {}
    nav.verify_web_credentials_login.return_value = True
    nav.read_ip_configuration.return_value = {"ip": "192.168.100.1"}
    nav.update_ip_configuration.return_value = None
    nav.open_blank_verification_tab.return_value = "main_window"
    nav.wait_until_login_accessible_on_new_ip.return_value = None
    nav.login_for_verification.return_value = None
    nav.switch_to_window.return_value = None
    nav.close_current_tab_and_switch_back.return_value = None
    nav._open_root.return_value = None
    # Step 0 methods (Device Access Control + WAN Access Control)
    nav.enable_lan_telnet.return_value = None
    nav.navigate_to_wan_access_control.return_value = None
    nav.create_wan_access_rule.return_value = None
    nav.verify_wan_access_rule_exists.return_value = True
    nav.enable_telnet.return_value = None
    return nav


# ── Transport mock ──────────────────────────────────────────────────

@pytest.fixture()
def mock_transport():
    transport = MagicMock()
    transport.connect.return_value = None
    transport.close.return_value = None
    transport.login.return_value = None
    transport.send_command.return_value = "OK"
    transport.load_pack_by_tftp.return_value = "success!"
    transport.send_reset.return_value = None
    transport.wait_for_reboot.return_value = None
    return transport


# ── Telnet credentials per step ─────────────────────────────────────

@pytest.fixture()
def telnet_creds_step1():
    return HuaweiTelnetCredentials(
        username_1="root", password_1="admin_123",
        username_2="root", password_2="adminHW",
    )


@pytest.fixture()
def telnet_creds_step2():
    return HuaweiTelnetCredentials(
        username_1="root", password_1="admin_123",
        username_2="root", password_2="adminHW",
    )


@pytest.fixture()
def telnet_creds_step3():
    return HuaweiTelnetCredentials(
        username_1="root", password_1="admin",
        username_2="root", password_2="admin_123",
    )


@pytest.fixture()
def telnet_creds_step4():
    return HuaweiTelnetCredentials(
        username_1="root", password_1="adminHW",
        username_2="root", password_2="admin",
    )
