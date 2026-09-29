"""
test_toolcall_relay.py — 探测"第二通请求"失败的原因：模型通道 or 请求大小

复现失败场景的请求形状：assistant(tool_calls) + tool(结果) 再调一次，
分别用不同模型、不同大小的工具结果测试。
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")
client = OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=os.environ["LLM_BASE_URL"])

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取一个文本文件的内容",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    }
]


def second_call(model: str, tool_content: str) -> str:
    """模拟'工具已执行、结果已回传'后的第二次请求"""
    messages = [
        {"role": "system", "content": "你是文件管理助手"},
        {"role": "user", "content": "我想看README.md的内容"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_test1",
                "type": "function",
                "function": {"name": "read_file", "arguments": '{"path":"README.md"}'},
            }],
        },
        {"role": "tool", "tool_call_id": "call_test1", "content": tool_content},
    ]
    try:
        r = client.chat.completions.create(
            model=model, messages=messages, tools=TOOLS, max_tokens=100,
        )
        return f"OK   回复{len(r.choices[0].message.content or '')}字"
    except Exception as e:  # noqa: BLE001
        return f"FAIL {type(e).__name__}: {str(e)[:60]}"


SMALL = "这是文件内容（100字）" * 4          # ~100 字符
BIG = "这是模拟的文件内容，用来测试大请求。" * 100   # ~2000 字符

print("== 变量一：工具结果大小（固定用当前模型）==")
cur = os.environ.get("LLM_MODEL", "?")
print(f"  小结果(~100字)  [{cur}]:", second_call(cur, SMALL))
print(f"  大结果(~2000字) [{cur}]:", second_call(cur, BIG))

print("\n== 变量二：换模型（固定用大结果）==")
for m in ["claude-haiku-4-6", "claude-sonnet-5", "deepseek-flash",
          "glm-5.3-flash", "kimi-k2.7-code", "gpt-5.3-codex"]:
    print(f"  [{m}]:", second_call(m, BIG))
