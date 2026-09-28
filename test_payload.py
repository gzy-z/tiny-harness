"""
test_payload.py — 对照实验：找出哪种请求姿势会触发中转站返回空正文

用法：
    .venv\\Scripts\\python test_payload.py
"""

import time
from pathlib import Path

from dotenv import dotenv_values

try:
    import httpx2 as httpx
except ImportError:
    import httpx

v = dotenv_values(Path(__file__).resolve().parent / ".env")
BASE = v["LLM_BASE_URL"].rstrip("/")
KEY = v["LLM_API_KEY"]
MODEL = v["LLM_MODEL"]

SHORT = [{"role": "user", "content": "只回复两个字：OK"}]
DAY01 = [
    {"role": "system", "content": "你是一个简洁的技术助手，回答不超过两句话。"},
    {"role": "user", "content": "用一句话解释：什么是 Agent（智能体）？"},
]


def call(model, msgs, max_tokens=None):
    body = {"model": model, "messages": msgs}
    if max_tokens:
        body["max_tokens"] = max_tokens
    r = httpx.post(
        f"{BASE}/chat/completions",
        headers={"Authorization": f"Bearer {KEY}"},
        json=body,
        timeout=60,
    )
    return r.status_code, len(r.text)


CASES = [
    (f"短问题+max16      [{MODEL}]", MODEL, SHORT, 16),
    (f"day01同款         [{MODEL}]", MODEL, DAY01, None),
    ("day01同款         [claude-haiku-4-6]", "claude-haiku-4-6", DAY01, None),
]

for i in range(4):
    print(f"—— 第 {i + 1} 轮 ——")
    for name, model, msgs, mt in CASES:
        code, n = call(model, msgs, mt)
        flag = "  ← 空正文!" if n == 0 else ""
        print(f"  {name}  状态={code} 正文字符数={n}{flag}")
        time.sleep(1)
    print()
