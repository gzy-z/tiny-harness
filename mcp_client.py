"""mcp_client.py — 把外部 MCP 服务器的工具桥接进本地工具体系"""
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = StdioServerParameters(
    command=".venv/Scripts/python.exe",
    args=["mcp_server.py"],
)


def to_menu_item(t):
    """MCP 工具 → 我们 TOOLS 的菜单格式（注意 inputSchema 天生就是 JSON Schema）"""
    schema = t.inputSchema or {"type": "object", "properties": {}, "required": []}
    return {
        "type": "function",
        "function": {
            "name": f"mcp_{t.name}",                      # 加前缀防撞名
            "description": f"[外部·tiny-tools] {t.description}",
            "parameters": schema,
        },
    }


def list_mcp_tools():
    """拉取外部菜单（异步内核 + 同步外壳）"""
    async def _inner():
        async with stdio_client(SERVER) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return (await session.list_tools()).tools
    return asyncio.run(_inner())


def call_mcp_tool(name, arguments):
    """调用外部工具，返回文本"""
    async def _inner():
        async with stdio_client(SERVER) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                return result.content[0].text if result.content else "(空结果)"
    return asyncio.run(_inner())