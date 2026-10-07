"""agent.py — 驾驶舱：REPL + Agent 循环（程序入口，跑它就启动）"""
SYSTEM_PROMPT = (
    "你是文件管理助手，遵守以下规则：\n"
    "1. 一律通过工具操作文件，完成后向用户简要汇报。\n"
    "2. 当任务包含 2 件及以上独立子任务时，必须先调用 todo_write 列出计划；"
    "每完成一项立即更新状态标记；全部完成后输出最终清单并总结。\n"
    "3. 遇到调研、搜索、了解现状类任务（如'看看有哪些''查一下情况'），"
    "优先派 spawn_agent 完成，基于其结论回答。"
)
import json
from pathlib import Path

from context import estimate_tokens, evict_if_over, truncate_for_context
from llm import MODEL, chat_stream
from tools import TOOLS, TOOL_FUNCS
from loop import run_loop
from subagent import spawn_agent
from tools import tool_to_schema
MAX_ITERATIONS = 10

# ---- 组合根：子Agent 接线（模块加载时执行一次，而不是在循环里反复执行）----
TOOL_FUNCS["spawn_agent"] = spawn_agent
TOOLS.append(tool_to_schema(spawn_agent))
SESSION_FILE = Path("session.jsonl")
show_thinking = True


# ---------------- 会话持久化 ----------------
def save_session(messages):
    """全量快照：一行一条消息"""
    SESSION_FILE.write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in messages),
        encoding="utf-8",
    )
    # ensure_ascii=False：让中文以本来面目存盘，打开文件能直接读


def load_session():
    """启动时恢复：文件存在且每行都合法就载入"""
    if not SESSION_FILE.exists():
        return None
    try:
        lines = SESSION_FILE.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(line) for line in lines if line.strip()] or None
    except Exception:  # noqa: BLE001 文件坏了就当没有，绝不耽误启动
        return None


# ---------------- 仪表盘 ----------------
def context_meter(messages, window=128000):
    """上下文仪表盘：条数 + 估算 token + 进度条"""
    est = estimate_tokens(messages)
    filled = min(20, round(est / window * 20))
    bar = "█" * filled + "░" * (20 - filled)
    print(f"\n📊 上下文: {len(messages)} 条消息 | ≈{est} tokens | "
          f"{bar} {est / window:.1%}")


def required_params(name):
    """查某工具的必填参数集合（从自动生成的菜单里读）"""
    for t in TOOLS:
        if t["function"]["name"] == name:
            return set(t["function"]["parameters"].get("required", []))
    return set()


# ---------------- 启动恢复 ----------------
restored = load_session()
if restored:
    print(f"↩️ 检测到上次会话（{len(restored)} 条消息）")
    while True:      # 答非所问就重问，绝不瞎猜
        choice = input("回车 = 继续上次会话 / 输入 new = 开新会话： ").strip().lower()
        if choice == "" or choice == "new":
            break
        print("没听懂。请【直接回车】继续，或输入【new】开新会话")
    if choice == "new":
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]   # 宪法永远来自代码
        save_session(messages)
        print("🆕 已开启新会话")
    else:
        messages = restored
        messages[0] = {"role": "system", "content": SYSTEM_PROMPT}
        print(f"↩️ 已继续上次会话（{len(messages)} 条消息）")
else:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
print("Agent 已就绪（输入 exit 退出 / reset 清空记忆 / /think 切换思考流）")

while True:
    user_input = input("\n你> ").strip()
    if not user_input:
        continue                                  # 空回车，重新等
    if user_input.lower() in ("exit", "quit", "退出"):
        print("再见！")
        save_session(messages)                    # 退场前存档
        break
    if user_input.lower() == "reset":
        messages = [messages[0]]                  # 记忆清零，只留 system
        save_session(messages)                    # 清空也要落盘（防诈尸）
        print("（已清空记忆）")
        continue
    if user_input.lower() == "/think":
        show_thinking = not show_thinking
        print(f"思考流显示：{'开' if show_thinking else '关'}")
        continue

    messages.append({"role": "user", "content": user_input})
    evict_if_over(messages)
    context_meter(messages)

    # —— 引擎启动：循环逻辑与全部防御都在 loop.py 的唯一实现里 ——
    answer = run_loop(messages, TOOLS, max_rounds=MAX_ITERATIONS,
                      show_thinking=show_thinking)
    if answer.startswith("("):   # 引擎的说明性返回（打捞文本等）没走打字机，补印
        print(answer)

    save_session(messages)                        # 每轮完成即存档，Ctrl+C 也不丢
