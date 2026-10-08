"""mcp_server.py — MCP 服务器：对外提供工具（stdio 传输，子进程方式被客户端启动）"""
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tiny-tools")     # 起个店名


@mcp.tool()
def get_weather(city: str) -> str:
    """查询指定城市的天气（教学假数据源）"""
    fake = {"北京": "晴 22°C", "上海": "多云 25°C", "广州": "雷阵雨 30°C"}
    return fake.get(city, f"{city}：暂无数据（教学假数据源）")


@mcp.tool()
def project_stats() -> str:
    """统计当前项目：py文件数、测试文件数、git提交数、代码总行数"""
    p = Path(".")
    py_files = list(p.glob("*.py"))
    test_files = [f for f in py_files if f.name.startswith("test_")]
    # stdin=DEVNULL：禁止 git 继承我们的协议管道，否则 stdio 通道会死锁（Windows 经典坑）
    r = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        capture_output=True, text=True, stdin=subprocess.DEVNULL)
    commits = r.stdout.strip() or f"git查询失败: {(r.stderr or '未知错误').strip()[:40]}"
    total_lines = sum(len(f.read_text(encoding="utf-8").splitlines())
                      for f in py_files if f.name != "mcp_server.py")
    return (f"py文件 {len(py_files)} 个｜测试文件 {len(test_files)} 个｜"
            f"git提交 {commits} 次｜总代码约 {total_lines} 行")


if __name__ == "__main__":
    mcp.run()       # stdio 模式启动：在这个进程的标准输入输出上讲 MCP 协议