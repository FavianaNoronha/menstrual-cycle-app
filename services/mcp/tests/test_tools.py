import asyncio
from datetime import date

from companion_mcp import tools
from companion_mcp.server import DemoSource, build_server

TODAY = date(2026, 11, 8)


def test_status_trends_flags_brief_on_demo_record():
    rec = DemoSource(TODAY).get()
    status = tools.cycle_status(rec, TODAY)
    assert status["cycle_day"] is not None and status["not_a_diagnosis"] is True
    tr = tools.trends(rec, TODAY, months=6)
    assert tr["cycle_lengths_days"] == [29, 31, 28, 33]
    assert tr["peak_pain_by_period"] == [5, 6, 6, 7]
    assert tr["premenstrual_patterns"][0]["symptom"] == "cravings"
    assert "instruction_for_assistant" in tools.flags(rec, TODAY)
    assert tools.doctor_brief(rec, TODAY)["cycles_logged"] == 4


def test_server_exposes_four_read_only_tools():
    server = build_server(DemoSource(TODAY), today=lambda: TODAY)
    listed = asyncio.run(server.list_tools())
    names = {t.name for t in listed}
    assert names == {"get_cycle_status", "get_trends", "get_flags", "get_doctor_brief"}
    assert all(t.annotations.read_only_hint for t in listed)
