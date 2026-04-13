"""Unit tests for adapter registry."""
import pytest

from src.backend.customizer.registry import get_adapter
from src.backend.customizer.vendors.huawei.huawei_adapter import HuaweiAdapter
from src.backend.customizer.vendors.zte.zte_adapter import ZTEAdapter
from src.backend.customizer.vendors.fiber.fiber_adapter import FiberhomeAdapter


@pytest.mark.unit
class TestRegistry:
    def test_get_adapter_huawei(self):
        adapter = get_adapter("HUAWEI")
        assert isinstance(adapter, HuaweiAdapter)

    def test_get_adapter_zte(self):
        adapter = get_adapter("ZTE")
        assert isinstance(adapter, ZTEAdapter)

    def test_get_adapter_fiberhome(self):
        adapter = get_adapter("FIBERHOME")
        assert isinstance(adapter, FiberhomeAdapter)

    @pytest.mark.parametrize("vendor_str", ["huawei", "Huawei", "HUAWEI", " huawei "])
    def test_get_adapter_case_insensitive(self, vendor_str):
        adapter = get_adapter(vendor_str)
        assert isinstance(adapter, HuaweiAdapter)

    def test_get_adapter_unknown_raises(self):
        with pytest.raises(ValueError, match="Unsupported vendor"):
            get_adapter("NOKIA")

    def test_get_adapter_empty_raises(self):
        with pytest.raises(ValueError):
            get_adapter("")
