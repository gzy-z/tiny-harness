"""compare_edit.py — A/B 对决：Day2全身换血派 vs 手术刀派（同题同数据）

用法：.venv\\Scripts\\python compare_edit.py
流式通道（对 tools 更友好）+ stream_options 拿官方 usage；在副本上操作，自动清理。
"""

import json
import shutil
import time
from pathlib import Path

from context import truncate_for_context
from llm import MODEL, client
from tools import TOOLS, TOOL_FUNCS

SYSTEM = "你是文件管理助手，一律通过工具操作文件，完成后向用户简要汇报"
CORE = ["read_file", "write_file", "list_dir"]
TOOLS_A = [t for t in TOOLS if t["function"]["name"] in CORE]                    # Day 2 阵容
TOOLS_B = [t for t in TOOLS if t["function"]["name"] in CORE + ["str_replace"]]  # +手术刀
CANDIDATES = [MODEL, "glm-5.2", "kimi-k2.7-code"]


def call_llm(messages, tools):
    """流式调用（带重试/替补），返回 (msg_dict, usage)"""
    for m in CANDIDATES:
        for attempt in range(3):
            try:
                stream = client.chat.completions.create(
                    model=m, messages=messages, tools=tools,
                    max_tokens=2000, stream=True,
                    stream_options={"include_usage": True})
                content, calls, usage = "", {}, None
                for ch in stream:
                    if ch.usage:
                        usage = ch.usage
                    if not ch.choices:
                        continue
                    d = ch.choices[0].delta
                    if d and d.content:
                        content += d.content
                    if d and d.tool_calls:
                        for tc in d.tool_calls:
                            s = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                            if tc.id:
                                s["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    s["name"] = tc.function.name
                                if tc.function.arguments:
                                    s["arguments"] += tc.function.arguments
                msg = {"role": "assistant", "content": content or None}
                if calls:
                    msg["tool_calls"] = [
                        {"id": c["id"], "type": "function",
                         "function": {"name": c["name"], "arguments": c["arguments"]}}
                        for _, c in sorted(calls.items())]
                return msg, usage
            except Exception:  # noqa: BLE001
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
    raise RuntimeError("所有通道尝试失败")


def run_once(tools, label):
    shutil.copy("check_key.py", "tmp_compare.py")
    text = Path("tmp_compare.py").read_text(encoding="utf-8")[:200]
    old, new = ("绝不显示", "永不显示") if "绝" in text else ("永不显示", "绝不显示")
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"把 tmp_compare.py 的 docstring 里 {old} 四个字改成 {new}"},
    ]
    p_total = c_total = rounds = 0
    for _ in range(10):
        rounds += 1
        msg, usage = call_llm(messages, tools)
        p_total += getattr(usage, "prompt_tokens", 0) or 0
        c_total += getattr(usage, "completion_tokens", 0) or 0
        messages.append(msg)
        if not msg.get("tool_calls"):
            break
        for tc in msg["tool_calls"]:
            args = json.loads(tc["function"]["arguments"] or "{}")
            result = TOOL_FUNCS[tc["function"]["name"]](**args)
            messages.append({"role": "tool", "tool_call_id": tc["id"],
                             "content": truncate_for_context(str(result))})
    Path("tmp_compare.py").unlink()
    print(f"{label:14s} 圈数={rounds}  发送={p_total:5d}  生成={c_total:5d}  合计={p_total + c_total}")
    return p_total + c_total


print("=" * 62)
a = run_once(TOOLS_A, "A·全身换血派")
b = run_once(TOOLS_B, "B·手术刀派")
print("=" * 62)
print(f"手术刀节省: {a - b} tokens（{(a - b) / a:.0%}）")
