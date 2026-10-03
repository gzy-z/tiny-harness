"""agent.py 驾驶舱：REPL + Agent 循环（程序入口，跑它就启动）"""

import json
from llm import chat,chat_stream, MODEL
from tools import TOOLS, TOOL_FUNCS
show_thinking = True
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

CONTEXT_BUDGET = 3000   # 实验用小预算，方便触发；生产按窗口设（如 32000）


def evict_if_over(messages, budget=CONTEXT_BUDGET):
    """超预算：先摘要、再驱逐整轮，永远保留 system 和历史摘要"""
    while estimate_tokens(messages) > budget and len(messages) > 3:
        start = next(i for i, m in enumerate(messages) if m["role"] == "user")
        end = next(
            (i for i in range(start + 1, len(messages)) if messages[i]["role"] == "user"),
            len(messages),
        )
        dropped = messages[start:end]

        memo = summarize_messages(dropped)  # ← 写遗书
        del messages[start:end]  # ← 再扔

        # 把纸条塞回开头：已有摘要就合并，没有就插在 system 后面
        old = next((m for m in messages
                    if str(m.get("content", "")).startswith(SUMMARY_PREFIX)), None)
        if old:
            old["content"] += "\n" + SUMMARY_PREFIX + memo
        else:
            messages.insert(1, {"role": "assistant", "content": SUMMARY_PREFIX + memo})

        print(f"🗑️ 驱逐 {len(dropped)} 条消息，留摘要：{memo[:60]}...")

SUMMARY_PREFIX = "【历史摘要】"

def summarize_messages(dropped) -> str:
    """调用模型把要被扔的轮次压成小纸条（约100字）"""
    try:
        text = "\n".join(
            str(m.get("content") or "")
            for m in dropped if m.get("content"))
        resp = chat(
            model=MODEL,
            messages=[
                {"role": "system",
                 "content": "你是记忆压缩器。把对话历史压缩成100字以内的摘要，"
                            "必须保留：用户要求过什么、做了什么、关键结论。直接输出摘要正文。"},
                {"role": "user", "content": text[:4000]},
            ],
            max_tokens=300,
        )
        return resp.choices[0].message.content or "(摘要失败)"
    except Exception:  # noqa: BLE001 摘要失败也不能耽误驱逐
        return "(摘要生成失败，已直接丢弃)"

MAX_TOOL_OUTPUT = 1000  # 工具结果进入上下文的最大字符数
def truncate_for_context(text: str, limit: int = MAX_TOOL_OUTPUT) -> str:
    """太长的工具结果：保头保尾、砍中间"""
    if len(text) <= limit:
        return text
    head, tail = text[:600], text[-200:]
    omitted = len(text) - len(head) - len(tail)
    return (f"{head}\n\n...[中间省略约{omitted}字符，"
            f"如需中间内容，请用 read_file 的 offset/limit 参数分段读取]...\n\n{tail}")
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
    if user_input.lower() == "/think":
        show_thinking = not show_thinking
        print(f"思考流显示：{'开' if show_thinking else '关'}")
        continue
    messages.append({"role": "user", "content": user_input})
    evict_if_over(messages)
    context_meter(messages)
    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n———— 第 {iteration} 圈 ————")


        msg = chat_stream(model=MODEL, messages=messages, tools=TOOLS, show_thinking=show_thinking)
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
            result = truncate_for_context(str(result))
            print(f"执行结果: {result[:100]}")
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
    else:
        print("⚠️ 达到最大圈数，强制停止（防止无限点菜烧钱）")
