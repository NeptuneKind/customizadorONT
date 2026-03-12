# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

from src.backend.customizer.vendors.base import BrandAdapter
from src.backend.customizer.vendors.huawei.huawei_adapter import HuaweiAdapter
from src.backend.customizer.vendors.zte.zte_adapter import ZTEAdapter
from src.backend.customizer.vendors.fiber.fiber_adapter import FiberhomeAdapter

# ===================================================================
# Métodos de registry
# ===================================================================
# Método para obtener el adaptador de marca correspondiente al vendor detectado
def get_adapter(vendor: str) -> BrandAdapter:
    v = (vendor or "").upper().strip()
    if v == "HUAWEI": return HuaweiAdapter()
    if v == "ZTE": return ZTEAdapter()
    if v == "FIBERHOME": return FiberhomeAdapter()
    raise ValueError(f"Unsupported vendor: {vendor}")