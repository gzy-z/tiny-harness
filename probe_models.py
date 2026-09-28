"""
probe_models.py — 探测中转站上哪些模型真正可用（每次仅生成十几个 token）

用法：
    .venv\\Scripts\\python probe_models.py

背景：/v1/models 列出的模型 ≠ 你的套餐能用的模型，
     实测才是硬道理。想加候选就改下面的 MODELS 列表。
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=os.environ["LLM_BASE_URL"])

MODELS = [
    "claude-haiku-4-6",
    "claude-sonnet-5",
    "glm-5.2",
    "kimi-k2.7-code",
    "doubao-seed-2.1-pro",
    "deepseek-v4-flash",
    "deepseek-flash",
    "gpt-5.3-codex",
]

for m in MODELS:
    try:
        r = client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": "只回复两个字：OK"}],
            max_tokens=16,
        )
        print(f"可用   {m:24s} → {r.choices[0].message.content!r}")
    except Exception as e:  # noqa: BLE001 探针就是要抓住所有错误
        print(f"不可用 {m:24s} → {str(e)[:90]}")
