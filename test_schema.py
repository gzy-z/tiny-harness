"""test_schema.py — 菜单质量哨兵（防"空描述"事故复发）"""
from tools import TOOLS


def test_every_tool_has_description():
    """每个工具的 description 必须非空
    （事故记录：自动生成 v1 上线当天，write_file/list_dir 因没写 docstring
      导致菜单描述为空、模型不知道何时该用——本哨兵让它永不复发）"""
    for t in TOOLS:
        desc = t["function"]["description"].strip()
        assert desc, f'{t["function"]["name"]} 的 description 是空的——模型看不见这道菜!'


def test_subagent_is_readonly():
    """子Agent 只许只读：调研员不许带刀上岗
    （没有写/删/执行 → 根本不存在'没人按y'的确认门难题；
      没有 spawn → 结构上不可能递归繁殖）"""
    from subagent import SUB_TOOLS
    names = {t["function"]["name"] for t in SUB_TOOLS}
    forbidden = {"write_file", "str_replace", "run_command",
                 "spawn_agent", "todo_write", "now"}
    assert not (names & forbidden), f"调研员偷带违禁品: {names & forbidden}"
    assert names, "SUB_TOOLS 不能为空"
