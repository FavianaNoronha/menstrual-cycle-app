"""Ritu MCP server.

Local dev (stdio, demo data):   ritu-mcp
Claude Desktop config:          {"mcpServers": {"ritu": {"command": "ritu-mcp"}}}

Production plan: remote streamable-HTTP server behind OAuth 2.1, where each
access token maps to exactly one consenting user and a set of scopes
(cycle:read, flags:read, brief:read, log:write). Until that is built, this
server only serves the demo record.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Protocol

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ritu_engine import CycleRecord, PainLog, Period, Profile, SymptomLog

from . import tools

IST = timezone(timedelta(hours=5, minutes=30))
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


class RecordSource(Protocol):
    def get(self) -> CycleRecord: ...


class DemoSource:
    """A made-up record for trying the connector. Never real user data."""

    def __init__(self, today: date) -> None:
        start = today - timedelta(days=4 * 30 + 5)
        periods, symptoms, pain = [], [], []
        for i, length in enumerate([29, 31, 28, 33]):
            periods.append(Period(start, start + timedelta(days=4)))
            pain.append(PainLog(start, [5, 6, 6, 7][i]))
            for back in range(1, 7):
                symptoms.append(SymptomLog(start + timedelta(days=length - back), {"cravings": 5}, {"sweet"}))
            for cd in range(4, 11):
                symptoms.append(SymptomLog(start + timedelta(days=cd - 1), {"cravings": 1}))
            start += timedelta(days=length)
        periods.append(Period(start, start + timedelta(days=4)))
        self._record = CycleRecord(periods=periods, symptoms=symptoms, pain=pain, profile=Profile(age=29))

    def get(self) -> CycleRecord:
        return self._record


def build_server(source: RecordSource, today=lambda: datetime.now(IST).date()) -> MCPServer:
    server = MCPServer(
        name="ritu",
        title="Ritu cycle record",
        instructions=(
            "Ritu holds one woman's self-logged menstrual cycle record. Use these tools to answer questions "
            "about her cycle, symptoms and what to discuss with a doctor. Never diagnose. If get_flags returns "
            "urgent or soon items, tell her the guidance exactly as written before anything else."
        ),
    )

    @server.tool(annotations=READ_ONLY)
    def get_cycle_status() -> dict:
        """Today's cycle day, an estimated phase, and the next period as a date range with confidence."""
        return tools.cycle_status(source.get(), today())

    @server.tool(annotations=READ_ONLY)
    def get_trends(months: int = 6) -> dict:
        """Cycle lengths, flow scores (PBAC), peak pain per period, and symptoms that rise before periods."""
        return tools.trends(source.get(), today(), months)

    @server.tool(annotations=READ_ONLY)
    def get_flags() -> dict:
        """Findings from fixed clinical rules (not AI), most severe first, with the guidance to relay."""
        return tools.flags(source.get(), today())

    @server.tool(annotations=READ_ONLY)
    def get_doctor_brief() -> dict:
        """The structured one-page summary she can show her gynaecologist, with suggested questions."""
        return tools.doctor_brief(source.get(), today())

    return server


def main() -> None:
    build_server(DemoSource(datetime.now(IST).date())).run("stdio")


if __name__ == "__main__":
    main()
