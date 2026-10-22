"""MCP integration test for 7CODE persistent project memory."""
import asyncio
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from seven_code_mcp.guard import Guard


def test_real_stdio_memory_lifecycle(tmp_path):
    project = tmp_path / "demo-project"
    project.mkdir()
    state = tmp_path / "memory-state"
    operator = Guard(state)
    operator.memory.configure_local(True)

    async def run():
        env = dict(os.environ, WINDOWS_LOCAL_MCP_STATE=str(state),
                   PYTHONIOENCODING="utf-8")
        params = StdioServerParameters(command=sys.executable,
                                      args=["-m", "seven_code_mcp"], env=env)
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = {tool.name for tool in (await session.list_tools()).tools}
                for expected in ("memory_status", "memory_project_create",
                                 "memory_project_list", "memory_project_context",
                                 "memory_checkpoint", "memory_search"):
                    assert expected in tools

                async def call(name, args=None):
                    result = await session.call_tool(name, args or {})
                    assert not result.isError, result
                    return json.loads(result.content[0].text)

                assert (await call("memory_status"))["enabled"]
                registered = await call("memory_project_create", {
                    "name": "Demo", "root_path": str(project), "objective": "keep progress"})
                pid = registered["project_id"]
                await call("memory_checkpoint", {"project_id": pid,
                    "summary": "Found an issue", "next_step": "Fix and test",
                    "details": "One tested issue", "status": "blocked"})
                changed = await call("write_file", {
                    "path": str(project / "hello.txt"), "content": "test"})
                assert changed["path"] == str(project / "hello.txt")
                listed = await call("memory_project_list")
                assert any(p["id"] == pid for p in listed["projects"])
                context = await call("memory_project_context", {"project_id": pid})
                assert context["project"]["next_step"] == "Fix and test"
                assert any(e["tool"] == "write_file" and e["result"] == "completed"
                           for e in context["recent_activity"])
                assert (await call("memory_search", {
                    "query": "tested issue", "project_id": pid}))["matches"]
    asyncio.run(run())
    operator.memory.configure_local(False)
