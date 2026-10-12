"""test_memory.py — RAG 记忆系统哨兵：分词 / 切块 / 检索命中"""

from pathlib import Path

from memory import bm25_search, chunk_file, tokenize

NOTES = Path(__file__).resolve().parent / "notes"

def test_tokenize():
    # bigram：相邻两字一组，三个字出两个词——最小可证伪事实
    assert tokenize("上下文") == ["上下", "下文"]


def test_chunk():
    # 切块：结果非空，每段是非空字符串
    parts = chunk_file(NOTES / "day10.md")
    assert parts, "day10 至少该切出一块"
    assert all(isinstance(p, str) and p.strip() for p in parts)


def test_search_hit():
    # 检索：搜 MCP 挂载，第一名应来自 day10（那是 MCP 的正主）
    hits = bm25_search("MCP 挂载")
    assert hits, "应有命中"
    assert "day10" in hits[0][1]["source"]