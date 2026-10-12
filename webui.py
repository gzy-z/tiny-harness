"""webui.py — tiny-harness 的 Web 门面：FastAPI + SSE 流式聊天

用法：.venv\\Scripts\\python webui.py  →  浏览器开 http://127.0.0.1:8000
MVP 边界：单会话（全局 messages）/ 不挂 MCP / 不给 run_command（确认门在浏览器里没法玩）。
"""

import json
import queue
import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

from context import evict_if_over, estimate_tokens
from loop import run_loop
from tools import TOOLS

app = FastAPI(title="tiny-harness")

INDEX_HTML = Path(__file__).resolve().parent / "static" / "index.html"

# Web 版工具白名单：确认门（终端 input y/n）在浏览器里没有手，干脆不给这把刀
WEB_TOOLS = [t for t in TOOLS if t["function"]["name"] != "run_command"]

SYSTEM_PROMPT = (
    "你是 tiny-harness，一个运行在用户电脑上的编码助手。"
    "需要了解项目历史时用 search_memory 检索 notes/ 知识库。回答用中文，简洁。"
)

messages = [{"role": "system", "content": SYSTEM_PROMPT}]  # 单会话 MVP
busy = threading.Lock()  # 同一时刻只许一个任务进引擎（单会话的保镖）


def sse_error(text):
    """单条错误事件流——忙/空/崩统一出口（DRY）"""
    def gen():
        yield f'data: {json.dumps({"kind": "error", "text": text}, ensure_ascii=False)}\n\n'
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/")
def index():
    return FileResponse(INDEX_HTML)


@app.post("/chat")
def chat(body: dict):
    text = (body.get("message") or "").strip()
    if not text:                                    # 空消息不进历史不烧钱
        return sse_error("空消息")
    if not busy.acquire(blocking=False):            # 引擎正忙：也走 SSE，前端零分支
        return sse_error("Agent 正忙，等它说完再发")

    q = queue.Queue()

    def worker():
        try:
            answer = run_loop(
                messages, WEB_TOOLS,
                on_event=lambda kind, text: q.put({"kind": kind, "text": text}),
            )
            q.put({"kind": "final", "text": answer})
        except Exception as e:            # 引擎崩了也要给浏览器一个交代
            q.put({"kind": "error", "text": f"{type(e).__name__}: {e}"})
        finally:
            q.put(None)                   # 结束哨兵：流到此为止
            busy.release()

    messages.append({"role": "user", "content": text})
    evict_if_over(messages)          # 上下文管理：超预算驱逐+摘要（agent.py 同款三斧）
    print(f"[webui] {len(messages)} 条 | ≈{estimate_tokens(messages)} tokens")
    threading.Thread(target=worker, daemon=True).start()

    def gen():
        while (item := q.get()) is not None:   # := 海象：取值兼判断
            yield f'data: {json.dumps(item, ensure_ascii=False)}\n\n'
        yield 'data: {"kind": "done", "text": ""}\n\n'

    return StreamingResponse(gen(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
