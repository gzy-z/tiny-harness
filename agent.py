"""agent.py — 驾驶舱：REPL + Agent 循环（程序入口，跑它就启动）"""

import json
from pathlib import Path

from context import estimate_tokens, evict_if_over, truncate_for_context
from llm import MODEL, chat_stream
from tools import TOOLS, TOOL_FUNCS

MAX_ITERATIONS = 10
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


# ---------------- 启动恢复 ----------------
restored = load_session()
if restored:
    messages = restored
    print(f"↩️ 已恢复上次会话（{len(messages)} 条消息）")
else:
    messages = [
        {"role": "system", "content": "你是文件管理助手，一律通过工具操作文件，完成后向用户简要汇报"},
    ]

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

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n———— 第 {iteration} 圈 ————")

        msg = chat_stream(model=MODEL, messages=messages, tools=TOOLS,
                          show_thinking=show_thinking)
        if not msg.get("tool_calls"):             # 不点菜了 = 任务完成
            break

        messages.append(msg)                      # 点菜单入历史
        for tc in msg["tool_calls"]:
            args = json.loads(tc["function"]["arguments"])
            print(f"模型点菜: {tc['function']['name']}({args})")
            func = TOOL_FUNCS[tc["function"]["name"]]
            try:
                result = func(**args)
            except TypeError as e:
                result = f"参数调用出错: {e}。请检查参数名和菜单 schema 是否一致。"
            result = truncate_for_context(str(result))
            print(f"执行结果: {result[:100]}")
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
    else:
        print("⚠️ 达到最大圈数，强制停止（防止无限点菜烧钱）")

    save_session(messages)                        # 每轮完成即存档，Ctrl+C 也不丢
