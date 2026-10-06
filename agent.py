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
        messages = [restored[0]]           # 新会话：只继承 system
        save_session(messages)
        print("🆕 已开启新会话")
    else:
        messages = restored
        messages.append({
            "role": "system",
            "content": "（会话已恢复。之前的任务均已结束，只需回应用户的最新消息，不要重做旧任务）",
        })
        print(f"↩️ 已继续上次会话（{len(messages)} 条消息）")
else:
    messages = [
        {"role": "system", "content": "你是文件管理助手，一律通过工具操作文件，完成后向用户简要汇报"},
    ]
print("Agent 已就绪（输入 exit 退出 / reset 清空记忆 / /think 切换思考流）")
seen_calls = {}
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

        msg = None
        for reask in range(3):        # 语义级重试：参数被坏节点抽走 → 重新点单（重摇骰子）
            msg = chat_stream(model=MODEL, messages=messages, tools=TOOLS,
                              show_thinking=show_thinking)
            lost = any(
                not tc["function"]["arguments"].strip()
                and required_params(tc["function"]["name"])     # 该工具确有必填参数
                for tc in (msg.get("tool_calls") or [])
            )
            if not lost:
                break
            print("⚠️ 检测到参数丢失（坏节点），重新点单...")

        if not msg.get("tool_calls"):             # 不点菜了 = 任务完成
            break

        messages.append(msg)                      # 点菜单入历史
        for tc in msg["tool_calls"]:
            args = json.loads(tc["function"]["arguments"] or "{}")
            print(f"模型点菜: {tc['function']['name']}({args})")
            func = TOOL_FUNCS[tc["function"]["name"]]

            key = f"{tc['function']['name']}:{tc['function']['arguments']}"  # 菜名:参数
            seen_calls[key] = seen_calls.get(key, 0) + 1                     # 计票（#169同款）
            if seen_calls[key] > 2:      # 同一调用第3次起：不执行，直接劝退
                result = (f"你已用完全相同的参数调用过 {seen_calls[key] - 1} 次，"
                          "结果都相同。请更换参数（如不同的 offset），"
                          "或直接基于已有结果回答。")
            else:
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
