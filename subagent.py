"""subagent.py — 子Agent：用一次性的干净上下文，换回一份浓缩结论"""
import json

from context import truncate_for_context
from llm import MODEL, chat_stream
from tools import TOOLS, TOOL_FUNCS

# 最小权限：只读调研员（没有刀，就没有误伤；没有spawn，就没有递归）
SUB_TOOLS = [t for t in TOOLS if t["function"]["name"] in ("read_file", "list_dir")]
MAX_SUB_ROUNDS = 8


def spawn_agent(task: str) -> str:
    """派一个子Agent独立调研，返回浓缩结论（只读权限，最多8圈）"""
    messages = [
        {"role": "system", "content": "你是调研员，只调查不修改。预算有限（最多8圈）："
                                      "每圈尽量一次批量调用所有需要的工具，先广度后深度；"
                                      "信息够用就立即收尾给结论，不要恋战。"
                                      "最后用不超过150字总结。"},
        {"role": "user", "content": task},
    ]
    findings = []      # 每圈的阶段性发现（面包屑：圈数耗尽时打捞用）
    for _ in range(MAX_SUB_ROUNDS):
        msg = chat_stream(model=MODEL, messages=messages,
                          tools=SUB_TOOLS, show_thinking=False)
        if not msg.get("tool_calls"):
            return truncate_for_context(msg.get("content") or "(无结论)", limit=600)
        if msg.get("content"):                      # 模型每圈的进展自述，攒着
            findings.append(msg["content"])
        messages.append(msg)
        for tc in msg["tool_calls"]:
            args = json.loads(tc["function"]["arguments"] or "{}")
            print(f"    └─ 子Agent点菜: {tc['function']['name']}({args})")
            result = TOOL_FUNCS[tc["function"]["name"]](**args)
            result = truncate_for_context(str(result))
            messages.append({"role": "tool", "tool_call_id": tc["id"],
                             "content": result})
    # 打捞：圈数耗尽也把阶段性别发现带回，并劝主Agent别从零重做
    partial = "\n".join(findings)[-600:]
    return (f"(子Agent圈数耗尽。阶段性发现：\n{partial}\n"
            "建议：基于以上发现直接总结，或派一个范围更小的任务，不要从零重做)")
