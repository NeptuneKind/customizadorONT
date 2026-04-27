from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from PySide6.QtCore import QThread, Signal

from src.backend.customizer.models import CustomizationPlan
from src.backend.customizer.progress import ProgressEvent


class CustomizationWorker(QThread):
    event_received = Signal(object)      # ProgressEvent
    run_finished = Signal(bool, object)  # (ok: bool, errors: list[str])

    def __init__(
        self,
        plan: CustomizationPlan,
        settings: Dict[str, Any],
        ips: List[str],
        project_root: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.plan = plan
        self.settings = settings
        self.ips = ips
        self.project_root = project_root

    def run(self) -> None:
        from src.backend.customizer.orquestador import run_customization

        errors: List[str] = []
        ok = False

        try:
            reports_dir = (
                self.project_root
                / "reports"
                / "customizations"
                / datetime.now().strftime("%d-%m-%Y")
            )
            reports_dir.mkdir(parents=True, exist_ok=True)

            exit_code = run_customization(
                settings=self.settings,
                project_root=self.project_root,
                reports_day_dir=reports_dir,
                ips=self.ips,
                headless=False,
                plan=self.plan,
                progress=lambda evt: self.event_received.emit(evt),
            )
            ok = exit_code == 0

        except Exception as exc:
            self.event_received.emit(ProgressEvent(phase="ERROR", message=str(exc)))
            errors = [str(exc)]

        self.run_finished.emit(ok, errors)
