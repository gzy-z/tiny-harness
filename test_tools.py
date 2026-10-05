def test_str_replace_success(tmp_path):
    from tools import str_replace
    f = tmp_path / "t.txt"
    f.write_text("第一行\n第二行\n第三行", encoding="utf-8")
    out = str_replace(str(f), "第二行", "SECOND")
    assert "手术成功" in out
    assert "SECOND" in f.read_text(encoding="utf-8")
    assert "第二行" not in f.read_text(encoding="utf-8")

def test_str_replace_not_found(tmp_path):
    from tools import str_replace
    f = tmp_path / "t.txt"
    f.write_text("hello", encoding="utf-8")
    out = str_replace(str(f), "不存在的文本", "x")
    assert "未找到" in out                    # 拒绝 + 指引
    assert f.read_text(encoding="utf-8") == "hello"   # 文件毫发无损
def test_str_replace_ambiguous(tmp_path):
    from tools import str_replace
    f = tmp_path / "t.txt"
    f.write_text("aa\naa\n", encoding="utf-8")
    out = str_replace(str(f), "aa", "SECOND")

    assert "2 次" in out                                   # 拒绝原因里报了次数
    assert f.read_text(encoding="utf-8") == "aa\naa\n"     # 文件毫发无损