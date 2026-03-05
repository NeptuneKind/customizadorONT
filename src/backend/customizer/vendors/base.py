# ===================================================================
# Imports
# ===================================================================
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from src.backend.customizer.context import CustomizationContext
from src.backend.customizer.models import CustomizationPlan, CustomizationResult
from src.backend.customizer.progress import ProgressCallback

# ===================================================================
# Classes y Dataclasses
# ===================================================================
# Class para definir la interfaz común de los adaptadores de marca
class BrandAdapter(ABC):

    # Cada adaptador debe definir su marca (vendor) y cómo aplicar el plan de personalización
    @property
    @abstractmethod
    def vendor(self) -> str:
        raise NotImplementedError

    # Aplicar el plan de personalización al dispositivo usando el contexto y reportando progreso
    @abstractmethod
    def apply(
        self,
        plan: CustomizationPlan,
        ctx: CustomizationContext,
        progress: ProgressCallback,
    ) -> CustomizationResult:
        raise NotImplementedError