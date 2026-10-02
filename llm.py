"""llm.py — 发动机舱：模型客户端与带重试/替补的 chat() 调用"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
)
MODEL = os.environ["LLM_MODEL"]
FALLBACKS = ["claude-sonnet-5", "deepseek-flash"]   # 替补席：实测今天都健康

def chat(**kwargs):
    """生产级调用：先重试（指数退避 2s→4s），三连败就换替补模型"""
    candidates = [kwargs.pop("model", None) or MODEL] + FALLBACKS
    for i, m in enumerate(candidates):
        for attempt in range(3):
            try:
                return client.chat.completions.create(model=m, **kwargs)
            except Exception:
                if attempt < 2:
                    wait = 2 ** (attempt + 1)          # 2秒 → 4秒，指数退避
                    print(f"[{m} 第{attempt+1}次失败，{wait}秒后重试...]")
                    time.sleep(wait)
                elif i < len(candidates) - 1:
                    print(f"[{m} 三连败 → 换替补 {candidates[i+1]}]")
                else:
                    raise   # 三个模型都尽力了，真·全挂
