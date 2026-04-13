"""Tests for JSON report generation."""
import json

import pytest

from src.backend.core.report import write_json_report


@pytest.mark.unit
class TestWriteJsonReport:
    """Tests for the report writer."""

    def test_creates_file(self, tmp_path):
        """Report file is created in the specified directory."""
        payload = {"ok": True, "vendor": "HUAWEI"}
        path = write_json_report(
            reports_day_dir=tmp_path,
            payload=payload,
            vendor="HUAWEI",
            ip="192.168.100.1",
            model_code="MOD003",
        )
        assert path.exists()
        assert path.suffix == ".json"

    def test_filename_format(self, tmp_path):
        """Filename matches HHMMSS_VENDOR_MODELCODE_IP.json pattern."""
        path = write_json_report(
            reports_day_dir=tmp_path,
            payload={"ok": True},
            vendor="HUAWEI",
            ip="192.168.100.1",
            model_code="MOD003",
        )
        name = path.name
        assert "HUAWEI" in name
        assert "MOD003" in name
        assert "192_168_100_1" in name
        assert name.endswith(".json")

    def test_content_matches_payload(self, tmp_path):
        """JSON content matches the payload dict."""
        payload = {
            "ok": True,
            "vendor": "HUAWEI",
            "ip": "192.168.100.1",
            "steps": [{"step": "wifi_24", "data": {"ssid": "Test"}}],
        }
        path = write_json_report(
            reports_day_dir=tmp_path,
            payload=payload,
            vendor="HUAWEI",
            ip="192.168.100.1",
            model_code="MOD003",
        )
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["ok"] is True
        assert loaded["vendor"] == "HUAWEI"
        assert len(loaded["steps"]) == 1
