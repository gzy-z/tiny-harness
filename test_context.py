"""test_context.py — 三斧的单元测试：把踩过的坑变成永久的哨兵"""
from context import SUMMARY_PREFIX, estimate_tokens, truncate_for_context, evict_if_over


def test_estimate_chinese():
    """纯中文：1 字 = 1 token"""
    msgs = [{"role": "user", "content": "你好世界"}]
    assert estimate_tokens(msgs) == 4


def test_estimate_english():
    """纯英文：4 字符 = 1 token"""
    msgs = [{"role": "user", "content": "abcd"}]
    assert estimate_tokens(msgs) == 1


def test_truncate_short_passthrough():
    """短文本不过刀，原样返回"""
    assert truncate_for_context("短文本") == "短文本"


def test_truncate_long_cuts_middle():
    """长文本保头保尾砍中间，且提示语在场"""
    text = "A" * 3000
    out = truncate_for_context(text)
    assert len(out) < 3000                # 确实变短了
    assert out.startswith("A")            # 头保住了
    assert out.endswith("A")              # 尾保住了
    assert "中间省略" in out               # 提示语在场（教模型自救的那句）

def test_evict_drops_old_round():


    msgs = [
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "旧问题" + "很" * 2000},  # 巨大的旧轮 → 必超预算
        {"role": "assistant", "content": "旧回答"},
        {"role": "user", "content": "新问题"},  # 小小的新轮
        {"role": "assistant", "content": "新回答"},
    ]

    def fake_summarizer(dropped):
        return "摘要OK"

    evict_if_over(msgs, budget=100, summarizer=fake_summarizer)
    assert msgs[0]["role"] == "system"  # ① 宪法永生
    assert any(str(m.get("content", "")).startswith(SUMMARY_PREFIX)  # ② 遗书塞回了开头
               for m in msgs)
    assert "新问题" in str(msgs)  # ③ 新轮幸存
    assert "旧问题" not in str(msgs)



"""test_tools.py — 把踩过的坑变成永久哨兵"""
import inspect

from tools import TOOLS, TOOL_FUNCS


def test_menu_and_registry_consistent():
    """哨兵1：菜单上的每道菜，厨房里必须真有
    （防 Day 4 的 tool.py 少个 s / 菜单注册错位）"""
    menu_names = {t["function"]["name"] for t in TOOLS}     # 菜单上的菜名集合
    kitchen_names = set(TOOL_FUNCS.keys())                  # 厨房里真有的菜集合
    assert menu_names == kitchen_names, f"菜单和厨房对不上: {menu_names ^ kitchen_names}"


def test_every_tool_schema_has_properties_wrapper():
    """哨兵2：parameters 必须有三层包装（type:object + properties 字典）
    （防 Day 4 惨案：缺 properties → 模型看到'没有参数' → 空手点菜 → 崩溃）"""
    for t in TOOLS:
        params = t["function"]["parameters"]
        assert params.get("type") == "object", f'{t["function"]["name"]} 缺 type:object'
        assert isinstance(params.get("properties"), dict), \
            f'{t["function"]["name"]} 缺 properties 包装'


def test_menu_params_match_function_signature():
    """哨兵3：菜单参数名必须和函数形参名完全一致
    （防 Day 3 车祸：菜单写 path、函数要 cmd → 模型按菜单点菜 → TypeError）"""
    for t in TOOLS:
        name = t["function"]["name"]
        menu_params = set(t["function"]["parameters"]["properties"].keys())
        real_params = set(inspect.signature(TOOL_FUNCS[name]).parameters.keys())
        assert menu_params == real_params, \
            f"{name} 菜单参数 {menu_params} ≠ 函数参数 {real_params}"

def test_is_dangerous():
    """哨兵4：危险名单要拦住删除、放行无害命令"""
    from tools import is_dangerous
    assert is_dangerous("del x.txt") is True          # 删除 → 必须拦
    assert is_dangerous("DEL x.txt") is True          # 大写变装也要拦
    assert is_dangerous("dir") is False               # 看目录 → 放行
    assert is_dangerous("python --version") is False  # 查版本 → 放行

def test_read_file_segments(tmp_path):
    """哨兵5：offset/limit 分段读不许退化（Day 5 修复的能力）"""
    from tools import read_file
    f = tmp_path / "sample.txt"
    f.write_text("\n".join(f"第{i}行" for i in range(1, 11)), encoding="utf-8")
    # ↑ 造了一个 10 行的临时文件：第1行、第2行……第10行

    out = read_file(str(f), offset=3, limit=2)        # 只取第 3~4 行

    assert "第3行" in out                             # 该在的在
    assert "第4行" in out
    assert "第2行" not in out                         # 不该在的不在
    assert "第5行" not in out
def test_required_params_have_descriptions():
    """v2 哨兵：必填参数必须有描述
    （事故记录：v1 时代模型因看不到参数说明而空手点菜）"""
    for t in TOOLS:
        params = t["function"]["parameters"]
        for name in params.get("required", []):
            desc = params["properties"][name].get("description", "")
            assert desc.strip(), f'{t["function"]["name"]} 的必填参数 {name} 缺描述'