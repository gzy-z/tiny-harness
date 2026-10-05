"""test_schema.py — 菜单质量哨兵（防"空描述"事故复发）"""
from tools import TOOLS


def test_every_tool_has_description():
    """每个工具的 description 必须非空
    （事故记录：自动生成 v1 上线当天，write_file/list_dir 因没写 docstring
      导致菜单描述为空、模型不知道何时该用——本哨兵让它永不复发）"""
    for t in TOOLS:
        desc = t["function"]["description"].strip()
        assert desc, f'{t["function"]["name"]} 的 description 是空的——模型看不见这道菜!'
