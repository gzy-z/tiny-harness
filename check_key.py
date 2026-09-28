"""
check_key.py — 供应商配置诊断（永不显示 Key 本身，可放心使用/提交）

用法：
    .venv\\Scripts\\python check_key.py

遇到 401 先跑它：看看三件套是否齐全、Key 是否混入脏字符、地址和 Key 是否同一家。
"""

from pathlib import Path

from dotenv import dotenv_values

v = dotenv_values(Path(__file__).resolve().parent / ".env")
key = v.get("LLM_API_KEY", "")

print("1. .env 存在且含 LLM_API_KEY:", bool(key))
if not key:
    raise SystemExit("→ 先把 .env.example 复制为 .env 并填好三件套")

print("2. Key 长度:", len(key))
print("3. 混入空格/引号/换行:", any(c in key for c in " \t\r\n'\""))
print("4. 接口地址:", v.get("LLM_BASE_URL") or "(未设置，默认 DeepSeek 官方)")
print("5. 模型名:", v.get("LLM_MODEL") or "(未设置，默认 deepseek-chat)")
print("6. Key 末4位（用于和报错信息比对）:", key[-4:])
