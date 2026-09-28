"""
diag_relay.py — 绕过 SDK 直连中转站，查看原始 HTTP 响应（排障专用）

用法：
    .venv\\Scripts\\python diag_relay.py

当 SDK 报 JSONDecodeError 时用它：能看到服务器真正返回了什么
（状态码、Content-Type、正文字符数、正文前 120 字符）。
"""

from pathlib import Path

from dotenv import dotenv_values

try:
    import httpx2 as httpx  # openai 3.x 内部用的分支版
except ImportError:
    import httpx

v = dotenv_values(Path(__file__).resolve().parent / ".env")
base = v["LLM_BASE_URL"].rstrip("/")
key = v["LLM_API_KEY"]

CANDIDATES = [
    v.get("LLM_MODEL", "deepseek-v4-flash"),  # 当前配置的模型
    "deepseek-flash",
    "claude-haiku-4-6",
    "glm-5.3-flash",
]

for model in CANDIDATES:
    r = httpx.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": "只回复两个字：OK"}],
            "max_tokens": 16,
        },
        timeout=60,
    )
    body = r.text
    print(f"[{model}]")
    print(f"  状态码={r.status_code}  正文字符数={len(body)}  "
          f"Content-Type={r.headers.get('content-type')}")
    print(f"  正文前120字符: {body[:120]!r}")
    print()
