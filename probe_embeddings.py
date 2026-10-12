"""probe_embeddings.py — 排雷：中转站有没有 embedding API（RAG 路线抉择）

用法：.venv\\Scripts\\python probe_embeddings.py
先拉 models 列表找 embedding 类候选，再逐个真调 /v1/embeddings 验明正身。
"""

from dotenv import dotenv_values
from openai import OpenAI
from pathlib import Path

v = dotenv_values(Path(__file__).resolve().parent / ".env")
client = OpenAI(api_key=v["LLM_API_KEY"], base_url=v["LLM_BASE_URL"])

# 常见 embedding 模型名（OpenAI / 智谱 / 开源系）
KNOWN = ["text-embedding-3-small", "text-embedding-3-large",
         "text-embedding-ada-002", "embedding-2", "bge-m3", "text-embedding-v3"]

candidates = []
try:
    models = [m.id for m in client.models.list().data]
    found = [m for m in models if any(k in m.lower() for k in ("embed", "bge"))]
    print(f"models 列表共 {len(models)} 个，embedding 类候选: {found or '无'}")
    candidates = found + [k for k in KNOWN if k not in found]
except Exception as e:
    print("models 列表拉取失败（不少中转站不实现它，不代表没 embedding）:", type(e).__name__)
    candidates = KNOWN

print("-" * 56)
ok = None
for name in candidates:
    try:
        r = client.embeddings.create(model=name, input="tiny-harness 排雷测试")
        dim = len(r.data[0].embedding)
        print(f"✅ {name}: 维度={dim}")
        if ok is None:
            ok = (name, dim)
    except Exception as e:
        msg = str(e).replace("\n", " ")[:90]
        print(f"❌ {name}: {type(e).__name__} {msg}")

print("-" * 56)
if ok:
    print(f"判定：走向量路线，主力模型 {ok[0]}（维度 {ok[1]}）")
else:
    print("判定：向量路线不通 → 启用 Plan B：BM25 关键词检索（纯本地）")
