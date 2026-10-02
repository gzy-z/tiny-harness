"""agent.py 驾驶舱：REPL + Agent 循环（程序入口，跑它就启动）"""

import json
from llm import chat,chat_stream, MODEL
from tools import TOOLS, TOOL_FUNCS

messages = [
    {"role": "system", "content": "你是文件管理助手，一律通过工具操作文件，完成后向用户简要汇报"},
]
def estimate_tokens(messages):
    """粗估 token：中文 1 字 ≈ 1 token，英文等 ≈ 4 字符 / token（够用，不精确）"""
    parts = []
    for m in messages:
        parts.append(str(m.get("content") or ""))
        for tc in (m.get("tool_calls") or []):
            parts.append(str(tc.get("function", {}).get("arguments", "")))
    text = "".join(parts)
    cn = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
    return int(cn + (len(text) - cn) / 4)

def context_meter(messages, window=128000):
    """上下文仪表盘：条数 + 估算 token + 进度条"""
    est = estimate_tokens(messages)
    filled = min(20, round(est / window * 20))
    bar = "█" * filled + "░" * (20 - filled)
    print(f"\n📊 上下文: {len(messages)} 条消息 | ≈{est} tokens | "
          f"{bar} {est / window:.1%}")
MAX_ITERATIONS = 10

print("Agent 已就绪（输入 exit 退出 / reset 清空记忆）")

while True:
    user_input = input("\n你> ").strip()
    if not user_input:
        continue                                  # 空回车，重新等
    if user_input.lower() in ("exit", "quit", "退出"):
        print("再见！")
        break
    if user_input.lower() == "reset":
        messages = [messages[0]]                  # 记忆清零，只留 system
        print("（已清空记忆）")
        continue

    messages.append({"role": "user", "content": user_input})
    context_meter(messages)
    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n———— 第 {iteration} 圈 ————")


        msg = chat_stream(model=MODEL, messages=messages, tools=TOOLS)
        if not msg.get("tool_calls"):       # 不点菜了 = 任务完成
            break

        messages.append(msg)          # 点菜单入历史
        for tc in msg["tool_calls"]:
            args = json.loads(tc["function"]["arguments"])
            print(f"模型点菜: {tc['function']['name']}({args})")
            func = TOOL_FUNCS[tc["function"]["name"]]
            try:
                result = func(**args)
            except TypeError as e:
                result = f"参数调用出错: {e}。请检查参数名和菜单 schema 是否一致。"
            print(f"执行结果: {result[:100]}")
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
    else:
        print("⚠️ 达到最大圈数，强制停止（防止无限点菜烧钱）")
