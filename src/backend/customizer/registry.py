# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

from src.backend.customizer.vendors.base import BrandAdapter
from src.backend.customizer.vendors.huawei.adapter import HuaweiAdapter
#from src.backend.customizer.vendors.zte.adapter import ZTEAdapter
from src.backend.customizer.vendors.fiber.adapter import FiberhomeAdapter
# TODO: add ZteAdapter, FiberhomeAdapter

# ===================================================================
# Métodos de registry
# ===================================================================
# Método para obtener el adaptador de marca correspondiente al vendor detectado
def get_adapter(vendor: str) -> BrandAdapter:
    v = (vendor or "").upper().strip()
    if v == "HUAWEI":
        return HuaweiAdapter()
    #if v == "ZTE": return ZteAdapter()
    if v == "FIBERHOME": return FiberhomeAdapter()
    raise ValueError(f"Unsupported vendor: {vendor}")