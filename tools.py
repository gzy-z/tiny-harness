"""tools.py 工具箱：4个工具函数 + TOOLS 菜单 + TOOL_FUNCS 注册表"""

import subprocess
from pathlib import Path

def read_file(path: str) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8")
        return text if text else "(空文件)"
    except Exception as e:  # noqa: BLE001
        return f"读取失败: {e}"


def write_file(path: str, content: str) -> str:
    try:
        Path(path).write_text(content, encoding="utf-8")
        return f"已写入 {path}（{len(content)} 字符）"
    except Exception as e:  # noqa: BLE001
        return f"写入失败: {e}"


def list_dir(path: str = ".") -> str:
    try:
        p = Path(path)
        items = [f"{x.name}{'/' if x.is_dir() else ''}" for x in p.iterdir()]
        return "\n".join(items) or "(空目录)"
    except Exception as e:  # noqa: BLE001
        return f"列目录失败: {e}"
DANGEROUS = [
    # 你来判断哪些算危险，至少 6 个。起手提示：
    "del", "rm ", "rmdir", "format", "shutdown", "reg ","taskkill","move",">"
    # 想想：结束进程的？移动/覆盖文件的？重定向覆盖 ">" 算不算？
]

def is_dangerous(cmd: str) -> bool:
    c = cmd.lower()
    return any(p in c for p in DANGEROUS)

def run_command(cmd: str) -> str:
    """执行一条终端命令并返回输出（带确认门）"""
    # ---- 确认门（TODO B）：危险命令先问人 ----
    if is_dangerous(cmd):
        answer = input(f"\n⚠️  Agent 想执行可能有危险的命令:\n   {cmd}\n   输入 y 放行，其他任意键拒绝: ")
        if answer.strip().lower() != "y":
            return f"用户拒绝执行该命令: {cmd}。请不要再次尝试，直接向用户说明被拒了。"
    # ---- 真正的执行 ----
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=30, encoding="utf-8", errors="replace",
        )
        # shell=True：交给系统的命令行解释器（Windows 上是 cmd）
        # timeout=30：命令卡死 30 秒强制掐断——又一个安全阀
        out = (r.stdout or "") + (r.stderr or "")
        return f"[退出码 {r.returncode}]\n{out[:2000] or '(无输出)'}"
        # 只回传前 2000 字符：输出太长会撑爆上下文（下周"上下文管理"的伏笔）
    except subprocess.TimeoutExpired:
        return "命令超时（30秒），已被强制终止"
    except Exception as e:  # noqa: BLE001
        return f"执行失败: {e}"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "列出指定目录下的文件和子目录",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径，默认当前目录 '.'"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取一个文本文件的内容",
            "parameters": {
                "type": "object",
                "properties":{
                    "path": {"type": "string", "description" :"要读取的文件路径，比如：README.md'.'"},

                },
                "required":["path"],
            },
        },

    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "创建一个新的文本文件的内容",
            "parameters": {
                "type": "object",
                "properties":{
                    "path": {"type": "string", "description": "写入新的内容 '.'"},
                    "content": {"type":"string"}
                },
                "required": ["path","content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "在 Windows 终端执行一条命令并返回输出，适合查看版本、运行 python 脚本、pip 操作等任务",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "要执行的完整命令，例如 'python --version'"},
                },
                "required": ["cmd"],
            },
        },
    }

]
TOOL_FUNCS = {
    "list_dir":list_dir,
    "read_file":read_file,
    "write_file":write_file,
    "run_command":run_command
}