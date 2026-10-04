"""context.py — 上下文管理三板斧：估token / 截断 / 驱逐+摘要（纯逻辑，可独立测试）"""

from llm import chat, MODEL

CONTEXT_BUDGET = 3000       # 实验用小预算，方便触发；生产按窗口设（如 32000）
MAX_TOOL_OUTPUT = 1000      # 工具结果进入上下文的最大字符数
SUMMARY_PREFIX = "【历史摘要】"


def estimate_tokens(messages):
    """粗估 token：中文 1 字 ≈ 1 token，英文等 ≈ 4 字符 / token（够用，不精确）"""
    parts = []
    for m in messages:
        parts.append(str(m.get("content") or ""))
        for tc in (m.get("tool_calls") or []):
            parts.append(str(tc.get("function", {}).get("arguments", "")))
    text = "".join(parts)
    cn = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return int(cn + (len(text) - cn) / 4)


def truncate_for_context(text: str, limit: int = MAX_TOOL_OUTPUT) -> str:
    """太长的工具结果：保头保尾、砍中间"""
    if len(text) <= limit:
        return text
    head, tail = text[:600], text[-200:]
    omitted = len(text) - len(head) - len(tail)
    return (f"{head}\n\n...[中间省略约{omitted}字符，"
            f"如需中间内容，请用 read_file 的 offset/limit 参数分段读取]...\n\n{tail}")


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


def evict_if_over(messages, budget=CONTEXT_BUDGET, summarizer=None):
    """超预算：先摘要、再按"整轮"驱逐。永远保留 system 和历史摘要。
    summarizer 不传用真摘要；测试时可注入假摘要（依赖注入）。"""
    if summarizer is None:
        summarizer = summarize_messages
    while estimate_tokens(messages) > budget and len(messages) > 3:
        start = next(i for i, m in enumerate(messages) if m["role"] == "user")
        end = next(
            (i for i in range(start + 1, len(messages)) if messages[i]["role"] == "user"),
            len(messages),
        )
        dropped = messages[start:end]

        memo = summarizer(dropped)               # 写遗书
        del messages[start:end]                  # 再扔

        # 把纸条塞回开头：已有摘要就合并，没有就插在 system 后面
        old = next((m for m in messages
                    if str(m.get("content", "")).startswith(SUMMARY_PREFIX)), None)
        if old:
            old["content"] += "\n" + SUMMARY_PREFIX + memo
        else:
            messages.insert(1, {"role": "assistant", "content": SUMMARY_PREFIX + memo})

        print(f"🗑️ 驱逐 {len(dropped)} 条消息，留摘要：{memo[:60]}...")
