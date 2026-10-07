"""subagent.py — 子Agent：用一次性的干净上下文，换回一份浓缩结论"""
from loop import run_loop
from tools import TOOLS

# 最小权限：只读调研员（没有刀，就没有误伤；没有spawn，就没有递归）
SUB_TOOLS = [t for t in TOOLS if t["function"]["name"] in ("read_file", "list_dir")]


def spawn_agent(task: str) -> str:
    """派一个子Agent独立调研，返回浓缩结论（只读权限，最多8圈）"""
    messages = [
        {"role": "system", "content": "你是调研员，只调查不修改。"
                                      "每圈尽量批量调用工具，信息够用就收尾。"
                                      "最后用不超过150字总结。"},
        {"role": "user", "content": task},
    ]
    return run_loop(messages, SUB_TOOLS, max_rounds=8,
                    show_thinking=False, indent="    ")
