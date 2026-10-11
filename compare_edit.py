"""compare_edit.py — A/B 对决：Day2全身换血派 vs 手术刀派（同题同数据）

用法：.venv\\Scripts\\python compare_edit.py
流式通道（对 tools 更友好）+ stream_options 拿官方 usage；在副本上操作，自动清理。
"""

import json
import random
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


def call_llm(messages, tools, candidates=CANDIDATES, attempts=3, sabotage=0.0):
    """流式调用（带重试/替补），返回 (msg_dict, usage)
    candidates=[MODEL] + attempts=1 即为裸奔模式；sabotage>0 在 try 内注入
    故障——病毒打进防线内部，重试才接得住（评测 A/B 用）"""
    for m in candidates:
        for attempt in range(attempts):
            try:
                if random.random() < sabotage:
                    raise ConnectionError("节点病（模拟）：请求失败")
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
                if attempt < attempts -1:
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
    # 裁判：检查改对了没
    final = Path("tmp_compare.py").read_text(encoding="utf-8")
    ok = (new in final[:200]) and (old not in final[:200])
    print(f"{label:14s} {'✅ 成功' if ok else '❌ 失败（但没人知道文件坏没坏过的日子结束了）'}")
    return {"ok": ok, "tokens": p_total + c_total, "rounds": rounds}

if __name__ == "__main__":
    print("=" * 62)
    a = run_once(TOOLS_A, "A·全身换血派")
    b = run_once(TOOLS_B, "B·手术刀派")
    print("=" * 62)
    print(f"手术刀节省: {a['tokens'] - b['tokens']} tokens（{(a['tokens'] - b['tokens']) / a['tokens']:.0%}）")
