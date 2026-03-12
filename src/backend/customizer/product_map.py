from __future__ import annotations


PRODUCT_BY_MODEL_CODE = {
    "MOD001": "HG6145F",
    "MOD002": "ZXHN F670L",
    "MOD003": "HG8145X6-10",
    "MOD004": "HG8145V5",
    "MOD005": "HG8145V5",
    "MOD007": "HG8145X6",
    "MOD008": "HG6145F1",
    "MOD009": "ZXHN F6600"
}


def resolve_product_name(model_code: str) -> str:
    return PRODUCT_BY_MODEL_CODE.get(model_code, model_code)