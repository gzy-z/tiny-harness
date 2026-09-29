"""
Day 02 动手课 · 三个真实工具 —— 第一次真正操作你的硬盘
=======================================================
和上一课的区别：get_weather 是"假"的（返回写死的数据），
今天的三个工具是真的会读写你的文件系统。

【你的任务】填完 TODO 1 ~ 4 才能运行：
    TODO 1: 给 read_file 写菜单
    TODO 2: 给 write_file 写菜单
    TODO 3: 建工具注册表（本文件最核心的概念！）
    TODO 4: 用注册表分发执行

运行：
    .venv\\Scripts\\python day02b_real_tools.py
"""
import time
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
)
MODEL = os.environ["LLM_MODEL"]
FALLBACKS = ["claude-sonnet-5", "deepseek-flash"]   # 替补席：实测今天都健康

def chat(**kwargs):
    """生产级调用：先重试（指数退避 2s→4s），三连败就换替补模型"""
    candidates = [kwargs.pop("model", None) or MODEL] + FALLBACKS
    for i, m in enumerate(candidates):
        for attempt in range(3):
            try:
                return client.chat.completions.create(model=m, **kwargs)
            except Exception:
                if attempt < 2:
                    wait = 2 ** (attempt + 1)          # 2秒 → 4秒，指数退避
                    print(f"[{m} 第{attempt+1}次失败，{wait}秒后重试...]")
                    time.sleep(wait)
                elif i < len(candidates) - 1:
                    print(f"[{m} 三连败 → 换替补 {candidates[i+1]}]")
                else:
                    raise   # 三个模型都尽力了，真·全挂

# ---------------------------------------------------------------
# 真实工具（完整提供）：注意错误处理的方式——
# 出错不 raise 崩掉程序，而是把错误信息【当作结果回传给模型】，
# 让模型自己决定怎么办（换个路径？告诉用户？）。
# 真实 harness 在这里还会做路径安全检查（限制只能碰项目目录）——下周的内容。
# ---------------------------------------------------------------
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


# ---------------------------------------------------------------
# 菜单：list_dir 我写好了当范例；
# read_file 和 write_file 的菜单由你照葫芦画瓢（TODO 1、2）
# ---------------------------------------------------------------
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
                "path": {"type": "string", "description" :"要读取的文件路径，比如：README.md'.'"},

            },
            "required":["path"],
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "创建一个新的文本文件的内容",
            "parameters": {
                "path": {"type": "string", "description": "写入新的内容 '.'"},
                "content": {"type":"string"}
            },
            "required": ["path","content"],
        },
    },
    # TODO 1: 给 read_file 写菜单
    #   提示：结构完全照抄上面；name="read_file"；
    #   description 写清楚"读取一个文本文件的内容"；
    #   一个参数 path（string），required 里放 "path"
    #
    # TODO 2: 给 write_file 写菜单
    #   提示：两个参数 path、content（都是 string），required 里两个都要
]


# TODO 3: 工具注册表 —— 把"菜名"映射到"真函数"的字典
#   这是每个 Agent harness 的心脏：执行不再写一堆 if/else，
#   而是查表分发。所有大项目（包括 Claude Code）都是这个思路。
#   提示：
#   TOOL_FUNCS = {
#       "list_dir": list_dir,
#       ...把三个都填上...
#   }
TOOL_FUNCS = {
    "list_dir":list_dir,
    "read_file":read_file,
    "write_file":write_file
}

messages = [
    {"role": "system", "content": "你是文件管理助手，一律通过工具操作文件，完成后向用户简要汇报"},
    # 实验时换这条 user 消息：
    {"role": "user", "content": "看看目录里有什么，然后创建 hello.txt，内容写'这是Agent创建的'"},
]
MAX_ITERATIONS = 10

for iteration in range(1, MAX_ITERATIONS + 1):
    print(f"\n———— 第 {iteration} 圈 ————")

    # ★ 心脏在这里：每圈开头【重新请求、更新 msg】
    response = chat(model=MODEL, messages=messages, tools=TOOLS)
    msg = response.choices[0].message

    if not msg.tool_calls:        # 不点菜了 = 任务完成
        print("最终回答:", msg.content)
        break

    messages.append(msg)          # 点菜单入历史
    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)
        print(f"模型点菜: {tc.function.name}({args})")
        func = TOOL_FUNCS[tc.function.name]
        result = func(**args)
        print(f"执行结果: {result[:100]}")
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
else:
    # for-else：只有循环【没 break、跑满】才会执行 = 安全阀触发
    print("⚠️ 达到最大圈数，强制停止（防止无限点菜烧钱）")
# ================================================================
# 跑通后做三个实验（改 user 消息重跑）：
#
# 实验 1【今天的重头戏】：
#   "看看目录里有什么，然后创建 hello.txt，内容写'这是Agent创建的'"
#   → 观察它点完第一道菜就被"掐断"了（链式任务做不完）
#   → 这就是明天"Agent 循环"存在的意义！
#
# 实验 2【并行点菜】：
#   "当前目录有哪些文件？另外读一下 PLAN.md 的内容"
#   → 观察一轮里可能点两道菜
#
# 实验 3【安全边界】：
#   "把我目录里的文件全删了"
#   → 观察它没这道菜可点，只能如实汇报
#   → 领悟：菜单之外，模型寸步难行——安全是"设计"出来的
# ================================================================
