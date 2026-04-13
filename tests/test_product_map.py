"""Unit tests for product_map module."""
import pytest

from src.backend.customizer.product_map import PRODUCT_BY_MODEL_CODE, resolve_product_name


@pytest.mark.unit
class TestProductMap:
    @pytest.mark.parametrize(
        "code, expected",
        [
            ("MOD001", "HG6145F"),
            ("MOD002", "ZXHN F670L"),
            ("MOD003", "HG8145X6-10"),
            ("MOD004", "HG8145V5"),
            ("MOD005", "HG8145V5"),
            ("MOD007", "HG8145X6"),
            ("MOD008", "HG6145F1"),
            ("MOD009", "ZXHN F6600"),
        ],
    )
    def test_known_model_codes(self, code, expected):
        assert resolve_product_name(code) == expected

    def test_unknown_model_code_returns_code(self):
        assert resolve_product_name("MOD999") == "MOD999"

    def test_all_known_codes_are_in_map(self):
        expected_codes = {"MOD001", "MOD002", "MOD003", "MOD004", "MOD005", "MOD007", "MOD008", "MOD009"}
        assert set(PRODUCT_BY_MODEL_CODE.keys()) == expected_codes
