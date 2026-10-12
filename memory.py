"""memory.py — RAG 长期记忆：notes/ 知识库 + BM25 检索（字符 bigram 分词）

RAG 三步的本地实现：切块 → 索引 → top-k 检索。
embedding 路线不通（中转站 83 模型无 embedding，6 名全 404）→ BM25 上位。
"""

import math
import re
from collections import Counter
from pathlib import Path

NOTES = Path(__file__).resolve().parent / "notes"
K1, B = 1.5, 0.75  # BM25 经典参数：词频饱和度 / 长度归一化强度


def tokenize(text):
    """字符 bigram：'上下文管理' → ['上下','下文','文管','管理']
    中文无空格，bigram 零依赖且对检索意外地好用（生产会换 jieba/向量）。"""
    text = re.sub(r"\s+", "", text)
    return [text[i:i + 2] for i in range(len(text) - 1)]


def chunk_file(path):
    """按 '## ' 节标题切块——日报的章节天然是语义边界"""
    parts = re.split(r"\n(?=## )", path.read_text(encoding="utf-8"))
    return [p.strip() for p in parts if p.strip()]


def build_index():
    """建库：所有日报切块 → [{source, text, tf(词频表)}]"""
    index = []
    for f in sorted(NOTES.glob("*.md")):
        for chunk in chunk_file(f):
            index.append({"source": f.name, "text": chunk,
                          "tf": Counter(tokenize(chunk))})
    return index


_INDEX = None  # 模块级缓存：检索不再每次重建（知识库更新后重启进程或手动置空）


def get_index():
    """惰性单例：第一次检索才建库，之后复用"""
    global _INDEX
    if _INDEX is None:
        _INDEX = build_index()
    return _INDEX


def bm25_search(query, k=3):
    """BM25 打分取 top-k：返回 [(分数, 命中块dict), ...]"""
    index = get_index()
    q_terms = tokenize(query)
    N = len(index)
    avgdl = sum(len(i["tf"]) for i in index) / N or 1
    df = Counter()  # 每个词出现在多少块（越常见越不值钱）
    for i in index:
        df.update(i["tf"].keys())
    scored = []
    for doc in index:
        dl = len(doc["tf"])
        s = 0.0
        for t in q_terms:
            if t not in doc["tf"]:
                continue
            idf = math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1)
            tf = doc["tf"][t]
            s += idf * (tf * (K1 + 1)) / (tf + K1 * (1 - B + B * dl / avgdl))
        if s > 0:
            scored.append((s, doc))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


if __name__ == "__main__":
    for s, doc in bm25_search("MCP 挂载 外部工具"):
        print(f"[{s:6.2f} | {doc['source']}] {doc['text'][:80]}")