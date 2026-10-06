"""tools.py 工具箱：7个工具函数 + 菜单自动生成（tool_to_schema）+ TOOL_FUNCS 注册表"""

import subprocess
from pathlib import Path
import inspect

def _py_type_to_json(py_type):
    """Python 类型 → JSON Schema 类型"""
    return {str: "string", int: "integer", float: "number",
            bool: "boolean"}.get(py_type, "string")


def tool_to_schema(func):
    """从函数签名 + docstring 自动生成菜单（smolagents 同款思想）"""
    sig = inspect.signature(func)
    properties = {}
    required = []
    arg_docs = _parse_args_docs(func.__doc__)
    for name, param in sig.parameters.items():
        json_type = _py_type_to_json(param.annotation)
        prop = {"type": json_type}
        if name in arg_docs:  # 有说明就挂上
            prop["description"] = arg_docs[name]
        properties[name] = prop
        if param.default is inspect.Parameter.empty:   # 没默认值 = 必填
            required.append(name)
    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": (func.__doc__ or "").strip().split("\n")[0],  # docstring 首行
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }
def _parse_args_docs(docstring):
    """从 docstring 的 Args 段提取参数说明 → {"参数名": "描述"}
    识别格式：
        Args:
            path: 要读取的文件路径
            offset: 起始行号
    """
    docs = {}
    in_args = False
    for line in (docstring or "").splitlines():
        stripped = line.strip()
        if stripped.lower() == "args:":       # 进入 Args 段
            in_args = True
            continue
        if not in_args:
            continue
        if not stripped or ":" not in stripped:   # 空行或没有冒号 → 段落结束
            break
        name, _, desc = stripped.partition(":")   # 只按第一个冒号切（描述里可以有冒号）
        docs[name.strip()] = desc.strip()
    return docs
def read_file(path: str, offset: int = 1, limit: int = 0) -> str:
    """按行读取文件。
     Args:
        path: 要读取的文件路径，例如 README.md
        offset: 起始行号，从 1 开始
        limit: 读取行数，建议每次 20~30 行
        """
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        total = len(lines)
        if limit and limit > 0:      # 指定了行数：精准取段，不再截断
            picked = lines[offset - 1: offset - 1 + limit]
            return (f"[{path} 第{offset}-{min(offset + limit - 1, total)}行 / 共{total}行]\n"
                    + "\n".join(picked))
        return f"[{path} 共{total}行]\n" + "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        return f"读取失败: {e}"

def write_file(path: str, content: str) -> str:
    """把文本内容写入文件（整个覆盖，改局部内容请优先用 str_replace）。
    Args:
        path: 要写入的文件路径
        content: 要写入的完整内容
    """
    try:
        Path(path).write_text(content, encoding="utf-8")
        return f"已写入 {path}（{len(content)} 字符）"
    except Exception as e:  # noqa: BLE001
        return f"写入失败: {e}"


def list_dir(path: str = ".") -> str:
    """列出目录下的文件和子目录。
    Args:
        path: 目录路径，默认当前目录 '.'
    """
    try:
        p = Path(path)
        items = [f"{x.name}{'/' if x.is_dir() else ''}" for x in p.iterdir()]
        return "\n".join(items) or "(空目录)"
    except Exception as e:  # noqa: BLE001
        return f"列目录失败: {e}"
DANGEROUS = [
    # 你来判断哪些算危险，至少 6 个。起手提示：
    "del ", "rm ", "rmdir", "format", "shutdown", "reg ", "taskkill", "move", ">"
    # 想想：结束进程的？移动/覆盖文件的？重定向覆盖 ">" 算不算？
]

def is_dangerous(cmd: str) -> bool:
    c = cmd.lower()
    return any(p in c for p in DANGEROUS)

def run_command(cmd: str) -> str:
    """执行一条终端命令并返回输出（危险命令会先请求人工确认）。
    Args:
        cmd: 要执行的完整命令，例如 'python --version'
    """
    # ---- 确认门：危险命令先问人 ----
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
def now() -> str:
    """返回当前的日期和时间"""
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S")
def str_replace(path: str, old: str, new: str) -> str:
    """精确替换文件中的一段文本，old 必须恰好出现一次。
        Args:
            path: 目标文件路径
            old: 要被替换的原文，须含足够上下文使其唯一，空格缩进必须与文件完全一致
            new: 替换后的新文本
        """
    try:
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        count = text.count(old)
        if count == 0:
            return "未找到要替换的文本。请先 read_file 查看原文，注意空格和缩进必须完全一致。"
        if count > 1:
            return (f"该文本出现了 {count} 次，无法确定替换哪一处。"
                    "请把 old 写得更长（带上前后行）使其唯一。")
        p.write_text(text.replace(old, new), encoding="utf-8")
        return f"手术成功：替换 1 处（{len(old)} 字符 → {len(new)} 字符）"
    except Exception as e:  # noqa: BLE001
        return f"替换失败: {e}"


TODO_FILE = Path("todos.md")

def todo_write(todos: str) -> str:
    """更新当前任务清单（整体覆盖）。多步骤任务应先列清单、随进度更新状态。
    Args:
        todos: 每行一条任务，用前缀标记状态：[ ] 未开始 / [~] 进行中 / [x] 已完成
    """
    try:
        TODO_FILE.write_text(todos, encoding="utf-8")
        n = len(todos.strip().splitlines())
        return f"清单已更新（{n} 项）：\n{todos}"
    except Exception as e:  # noqa: BLE001
        return f"更新失败: {e}"
TOOLS = [tool_to_schema(f) for f in (read_file, write_file, list_dir, run_command, str_replace, now,todo_write)]

TOOL_FUNCS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_dir": list_dir,
    "run_command": run_command,
    "str_replace": str_replace,
    "now": now,
    "todo_write":todo_write
}