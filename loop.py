"""loop.py — 通用 Agent 循环引擎：主 Agent 和子 Agent 共用的唯一实现。
防御纵深（语义重试/重复检测/防撞墙/截断）都在这里，谁调用谁受益。"""
import json

from context import truncate_for_context
from llm import MODEL, chat_stream
from tools import TOOL_FUNCS


def required_params(name, tools):
    """从菜单查某工具的必填参数集合"""
    for t in tools:
        if t["function"]["name"] == name:
            return set(t["function"]["parameters"].get("required", []))
    return set()

def run_loop(messages, tools, max_rounds=10, show_thinking=True, indent="", on_event=None):
    """跑完一个任务……返回最终回答；预算耗尽时打捞阶段性发现。
    契约：收工的最终回答由引擎统一 append 进 messages，调用方只管展示。
    on_event(kind, text)：事件回调，默认 print——REPL 不变，Web 端接 SSE。"""
    emit = on_event or (lambda kind, text: print(f"{indent}{text}"))
    seen = {}          # 重复调用计票器（每次调用 run_loop 自动重置）
    findings = []      # 各圈的进展自述（预算耗尽时打捞）

    for i in range(max_rounds):
        emit("round", f"———— 第 {i + 1} 圈 ————")
        msg = None
        for _reask in range(3):        # 语义级重试：参数被坏节点抽走就重问
            msg = chat_stream(model=MODEL, messages=messages, tools=tools,
                              show_thinking=show_thinking)
            lost = any(
                not tc["function"]["arguments"].strip()
                and required_params(tc["function"]["name"], tools)
                for tc in (msg.get("tool_calls") or [])
            )
            if not lost:
                break
            emit("warn", "⚠️ 参数丢失（坏节点），重新点单...")

        if not msg.get("tool_calls"):                    # 收工
            messages.append(msg)                         # 最终回答也进历史（修复悬空复读）
            return msg.get("content") or "(无内容)"

        if msg.get("content"):
            findings.append(msg["content"])              # 攒面包屑
        messages.append(msg)

        for tc in msg["tool_calls"]:
            args = json.loads(tc["function"]["arguments"] or "{}")
            emit("tool_call", f"模型点菜: {tc['function']['name']}({args})")
            func = TOOL_FUNCS[tc["function"]["name"]]

            key = f"{tc['function']['name']}:{tc['function']['arguments']}"
            seen[key] = seen.get(key, 0) + 1
            if seen[key] > 2:                            # 同调用第3次起劝退
                result = (f"你已用完全相同的参数调用过 {seen[key] - 1} 次，"
                          "结果都相同。请更换参数或基于已有结果回答。")
            else:
                try:
                    result = func(**args)
                except TypeError as e:
                    result = f"参数调用出错: {e}。请检查参数名和菜单 schema 是否一致。"
            result = truncate_for_context(str(result))
            emit("tool_result", f"执行结果: {result[:100]}")
            messages.append({"role": "tool", "tool_call_id": tc["id"],
                             "content": result})
    # 预算耗尽：打捞而不是空手而归
    partial = "\n".join(findings)[-600:]
    return f"(圈数耗尽。阶段性发现：\n{partial}\n建议：基于以上直接总结，勿从零重做)"