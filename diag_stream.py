"""diag_stream.py — 抓流式碎片的原始 JSON，看正文到底藏在哪个字段"""

import time

from llm import MODEL, client

TOOLS = [{
    "type": "function",
    "function": {
        "name": "echo",
        "description": "把文字原样返回（测试用）",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
}]

stream = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "写一首关于秋天的两行小诗（不需要用工具）"}],
    tools=TOOLS,
    stream=True,
    max_tokens=500,
)

t0 = time.time()
n = 0
cc = 0
raw_samples = []

for chunk in stream:
    n += 1
    if len(raw_samples) < 4:      # 抓前4个碎片存档
        raw_samples.append(chunk.model_dump_json()[:300])
    if not chunk.choices:
        continue
    d = chunk.choices[0].delta
    if d and d.content:
        cc += len(d.content)

print(f"chunks={n}, content字数={cc}, 全程={time.time() - t0:.2f}s\n")
for i, s in enumerate(raw_samples):
    print(f"--- 碎片{i} 原文 ---")
    print(s, "\n")
