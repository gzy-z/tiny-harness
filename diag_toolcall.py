"""diag_toolcall.py — 碎片级解剖：每个 tool_call 碎片的 index/id/name/args 全打印"""

from llm import MODEL, client
from tools import TOOLS

PROMPT = [{"role": "user", "content": "先看看目录里有什么，然后读一下 check_key.py 的前5行"}]

stream = client.chat.completions.create(
    model=MODEL, messages=PROMPT, tools=TOOLS, max_tokens=800, stream=True)

print("===== 原始碎片 =====")
n = 0
calls = {}                                  # 和 agent.py chat_stream 同款装配
for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    if delta and delta.tool_calls:
        for tc in delta.tool_calls:
            n += 1
            print(f"碎片{n}: index={tc.index!r} id={tc.id!r} "
                  f"name={tc.function.name if tc.function else None!r} "
                  f"args片={tc.function.arguments if tc.function else None!r}")
            # ↓↓↓ 与 agent.py 完全相同的装配逻辑
            slot = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
            if tc.id:
                slot["id"] = tc.id
            if tc.function:
                if tc.function.name:
                    slot["name"] = tc.function.name
                if tc.function.arguments:
                    slot["arguments"] += tc.function.arguments

print("\n===== 装配结果（agent 同款）=====")
for idx, c in calls.items():
    print(f"[{idx}] name={c['name']!r} args={c['arguments']!r}")
