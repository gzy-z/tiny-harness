"""test_mcp.py — MCP 集成测试：真启动服务器子进程、真调用（无网络依赖）"""
from mcp_client import call_mcp_tool, to_menu_item, list_mcp_tools


def test_get_weather_via_mcp():
    assert "晴" in call_mcp_tool("get_weather", {"city": "北京"})


def test_menu_item_shape():
    (t,) = [x for x in list_mcp_tools() if x.name == "project_stats"]
    item = to_menu_item(t)
    assert item["function"]["name"] == "mcp_project_stats"
    assert item["function"]["description"].startswith("[外部")