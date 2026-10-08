"""mcp_client_test.py — 第一个 MCP 客户端：连服务器、看菜单、买东西"""
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 告诉协议层：用哪个程序、什么参数启动服务器（它会帮我们 spawn 子进程）
SERVER = StdioServerParameters(
    command=".venv/Scripts/python.exe",
    args=["mcp_server.py"],
)


async def main():
    async with stdio_client(SERVER) as (read, write):      # ① 启动并连接服务器
        async with ClientSession(read, write) as session:
            await session.initialize()                     # ② 握手：报家门、对版本

            tools = await session.list_tools()             # ③ 要菜单
            print("== 服务器菜单 ==")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")

            result = await session.call_tool("project_stats", {})   # ④ 点菜
            print("\n== 调用 project_stats ==")
            print(result.content[0].text)


asyncio.run(main())