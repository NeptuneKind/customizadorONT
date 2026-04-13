"""Shared fixtures for all tests."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure project root is on sys.path so imports like "config.settings" work.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.core.monitoring import DetectedDevice
from src.backend.customizer.models import (
    CustomizationPlan,
    IPPlan,
    WebCredentialsPlan,
    WifiPlan,
)
from src.backend.customizer.context import CustomizationContext
from src.backend.customizer.progress import ProgressEvent


# ── Settings ────────────────────────────────────────────────────────

@pytest.fixture()
def fake_settings():
    return {
        "headless": True,
        "targets": {
            "wifi_24_ssid": "",
            "wifi_24_pass": "",
            "wifi_5_ssid": "",
            "wifi_5_pass": "",
        },
        "web_credentials": {
            "change_web_credentials": False,
            "new_user": "",
            "new_pass": "",
        },
        "login_candidates": {
            "huawei": [
                {"user": "root", "pass": "admin"},
                {"user": "telecomadmin", "pass": "F0xB734Fr3@j%YEP"},
            ],
            "huawei_superuser": [
                {"user": "telecomadmin", "pass": "F0xB734Fr3@j%YEP"},
            ],
            "zte": [
                {"user": "root", "pass": "admin"},
                {"user": "admin", "pass": "Zgs12O5TSa2l3o9"},
            ],
            "fiber": [
                {"user": "root", "pass": "admin"},
                {"user": "admin", "pass": "z#Wh46QN@52Rm%j5"},
            ],
        },
        "selenium": {
            "chromedriver_path": "src/backend/drivers/chromedriver.exe",
            "chrome_binary_path": "",
        },
    }


# ── Detected devices ───────────────────────────────────────────────

@pytest.fixture()
def fake_detected_huawei():
    return DetectedDevice(
        ip="192.168.100.1",
        vendor="HUAWEI",
        model_code="MOD003",
        product_name="HG8145X6-10",
        needs_post_login_model=False,
    )


@pytest.fixture()
def fake_detected_zte():
    return DetectedDevice(
        ip="192.168.1.1",
        vendor="ZTE",
        model_code="MOD002",
        product_name="ZXHN F670L",
        needs_post_login_model=False,
    )


@pytest.fixture()
def fake_detected_fiber():
    return DetectedDevice(
        ip="192.168.100.1",
        vendor="FIBERHOME",
        model_code="MOD001",
        product_name="",
        needs_post_login_model=True,
    )


# ── Mocks ───────────────────────────────────────────────────────────

@pytest.fixture()
def mock_driver():
    driver = MagicMock()
    driver.current_window_handle = "main_window"
    driver.window_handles = ["main_window"]
    driver.current_url = "http://192.168.100.1/"
    return driver


@pytest.fixture()
def mock_progress():
    return MagicMock()


# ── Context ─────────────────────────────────────────────────────────

@pytest.fixture()
def fake_ctx(tmp_path, fake_settings, fake_detected_huawei, mock_driver):
    return CustomizationContext(
        project_root=tmp_path,
        settings=fake_settings,
        detected=fake_detected_huawei,
        headless=True,
        driver=mock_driver,
    )


# ── Plans ───────────────────────────────────────────────────────────

@pytest.fixture()
def wifi_plan_enabled():
    return WifiPlan(
        enabled=True,
        ssid_24="TestSSID24",
        pass_24="TestPass24",
        ssid_5="TestSSID5",
        pass_5="TestPass5",
    )


@pytest.fixture()
def web_creds_plan_enabled():
    return WebCredentialsPlan(
        enabled=True,
        old_password="admin",
        new_password="NewPass123",
    )


@pytest.fixture()
def ip_plan_enabled():
    return IPPlan(enabled=True, new_ip="192.168.101.1")


@pytest.fixture()
def full_plan(wifi_plan_enabled, web_creds_plan_enabled):
    """WiFi + WebCreds enabled, IP disabled (mutual exclusion rule)."""
    return CustomizationPlan(
        wifi=wifi_plan_enabled,
        web_credentials=web_creds_plan_enabled,
        ip=IPPlan(enabled=False),
    )


@pytest.fixture()
def ip_only_plan(ip_plan_enabled):
    """Only IP enabled, WiFi + WebCreds disabled (mutual exclusion rule)."""
    return CustomizationPlan(
        wifi=WifiPlan(enabled=False),
        web_credentials=WebCredentialsPlan(enabled=False),
        ip=ip_plan_enabled,
    )


@pytest.fixture()
def disabled_plan():
    return CustomizationPlan()
