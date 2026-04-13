"""Unit tests for data models."""
import pytest

from src.backend.customizer.models import (
    CustomizationPlan,
    CustomizationResult,
    IPPlan,
    StepResult,
    WebCredentialsPlan,
    WifiBand,
    WifiPlan,
)


@pytest.mark.unit
class TestWifiBand:
    def test_band_24_value(self):
        assert WifiBand.B24.value == "2.4"

    def test_band_5_value(self):
        assert WifiBand.B5.value == "5"

    def test_band_is_str_enum(self):
        assert isinstance(WifiBand.B24, str)


@pytest.mark.unit
class TestWifiPlan:
    def test_defaults(self):
        plan = WifiPlan()
        assert plan.enabled is False
        assert plan.ssid_24 is None
        assert plan.pass_24 is None
        assert plan.ssid_5 is None
        assert plan.pass_5 is None

    def test_with_values(self):
        plan = WifiPlan(enabled=True, ssid_24="Net24", pass_24="pw24")
        assert plan.enabled is True
        assert plan.ssid_24 == "Net24"


@pytest.mark.unit
class TestWebCredentialsPlan:
    def test_defaults(self):
        plan = WebCredentialsPlan()
        assert plan.enabled is False
        assert plan.old_password == "admin"
        assert plan.new_password == ""


@pytest.mark.unit
class TestIPPlan:
    def test_defaults(self):
        plan = IPPlan()
        assert plan.enabled is False
        assert plan.new_ip == ""


@pytest.mark.unit
class TestCustomizationPlan:
    def test_defaults_all_disabled(self):
        plan = CustomizationPlan()
        assert plan.wifi.enabled is False
        assert plan.web_credentials.enabled is False
        assert plan.ip.enabled is False

    def test_sub_plans_are_independent_instances(self):
        p1 = CustomizationPlan()
        p2 = CustomizationPlan()
        p1.wifi.enabled = True
        assert p2.wifi.enabled is False


@pytest.mark.unit
class TestStepResult:
    def test_fields(self):
        sr = StepResult(step_id="wifi_24", ok=True, data={"ssid": "X"})
        assert sr.step_id == "wifi_24"
        assert sr.ok is True
        assert sr.data == {"ssid": "X"}
        assert sr.error is None
        assert sr.started_at == ""


@pytest.mark.unit
class TestCustomizationResult:
    def test_defaults(self):
        cr = CustomizationResult(
            ok=True, vendor="HUAWEI", model_code="MOD003", ip="192.168.100.1"
        )
        assert cr.ok is True
        assert cr.vendor == "HUAWEI"
        assert cr.product_name == ""
        assert isinstance(cr.steps, list)
        assert isinstance(cr.timestamp, str)
