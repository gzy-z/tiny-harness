"""llm.py — 发动机舱：模型客户端与带重试/替补的 chat() 调用"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
)
MODEL = os.environ["LLM_MODEL"]
FALLBACKS = ["glm-5.2", "kimi-k2.7-code"]   # 替补席：10-05 大逃杀幸存者（带工具历史·流式参数完好）

def chat(**kwargs):
    """生产级调用：先重试（指数退避 2s→4s），三连败就换替补模型"""
    candidates = [kwargs.pop("model", None) or MODEL] + FALLBACKS
    for i, m in enumerate(candidates):
        for attempt in range(3):
            try:
                return client.chat.completions.create(model=m, **kwargs)
            except Exception:
                if attempt < 2:
                    wait = 2 ** (attempt + 1)          # 2秒 → 4秒，指数退避
                    print(f"[{m} 第{attempt+1}次失败，{wait}秒后重试...]")
                    time.sleep(wait)
                elif i < len(candidates) - 1:
                    print(f"[{m} 三连败 → 换替补 {candidates[i+1]}]")
                else:
                    raise   # 三个模型都尽力了，真·全挂

def chat_stream(**kwargs):
    show_think = kwargs.pop("show_thinking", True)
    on_chunk = kwargs.pop("on_chunk", None)  # 字级回调：on_chunk("think"/"answer", text)

    # 终端打字机渲染器（默认回调）：前缀只打一次、end="" 续写——REPL 逐字兼容
    state = {"think": False, "answer": False}

    def term_render(kind, text):
        if kind == "think":
            if not state["think"]:
                print("〔思考〕", end="", flush=True)
                state["think"] = True
            if show_think:
                print(text, end="", flush=True)
        else:
            if not state["answer"]:
                print("\n〔回答〕", end="", flush=True)
                state["answer"] = True
            print(text, end="", flush=True)

    emit_chunk = on_chunk or term_render
    candidates = [kwargs.pop("model", None) or MODEL] + FALLBACKS
    for i, m in enumerate(candidates):
        for attempt in range(3):
            try:
                stream = client.chat.completions.create(model=m, stream=True, **kwargs)
                content = ""
                calls = {}      # 按序号收纳碎片：{序号: {"id","name","arguments"}}

                in_think = in_answer = False
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if not delta:
                        continue

                    # 碎片零：思考流（有的字段叫 reasoning，有的叫 reasoning_content，
                    # 两个都试 = 兼容层，多供应商世界的求生技能）
                    think = getattr(delta, "reasoning", None) or getattr(delta, "reasoning_content", None)
                    if think:
                        emit_chunk("think", think)

                    # 碎片一：正文（打字机本体）
                    if delta.content:
                        content += delta.content
                        emit_chunk("answer", delta.content)

                    # 碎片二：工具调用（只攒不打，原样保留）
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            slot = calls.setdefault(
                                tc.index, {"id": "", "name": "", "arguments": ""})
                            if tc.id:
                                slot["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    slot["name"] = tc.function.name
                                if tc.function.arguments:
                                    slot["arguments"] += tc.function.arguments
                if on_chunk is None:
                    print()   # 终端打字机收尾换行（Web 端不需要）
                msg = {"role": "assistant", "content": content or None}
                if calls:
                    msg["tool_calls"] = [
                        {"id": c["id"], "type": "function",
                         "function": {"name": c["name"], "arguments": c["arguments"]}}
                        for _, c in sorted(calls.items())
                    ]
                if not content and not calls:      # ← 挪出来：与 if calls 对齐
                    raise ValueError("空响应：疑似网关返回了空流")
                return msg

            except Exception:
                if attempt < 2:
                    wait = 2 ** (attempt + 1)
                    print(f"\n[-- 输出中断，{wait}秒后重试（上方残段可忽略）--]")
                    time.sleep(wait)
                elif i < len(candidates) - 1:
                    print(f"[{m} 三连败 → 换替补 {candidates[i+1]}]")
                else:
                    raise