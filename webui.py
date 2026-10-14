"""webui.py — tiny-harness 的 Web 门面：FastAPI + SSE 流式聊天

用法：.venv\\Scripts\\python webui.py  →  浏览器开 http://127.0.0.1:8000
边界：单会话（全局 messages，/reset 开新会话）/ 已挂 MCP / 不给 run_command（确认门在浏览器里没法玩）。
"""

import json
import queue
import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from tools import TOOLS, TOOL_FUNCS
from mcp_client import call_mcp_tool, list_mcp_tools, to_menu_item
from context import evict_if_over, estimate_tokens
from loop import run_loop

from datetime import date    # 顶部 import 区


app = FastAPI(title="tiny-harness")

INDEX_HTML = Path(__file__).resolve().parent / "static" / "index.html"

# Web 版工具白名单：确认门（终端 input y/n）在浏览器里没有手，干脆不给这把刀
WEB_TOOLS = [t for t in TOOLS if t["function"]["name"] != "run_command"]
# ---- 组合根：挂载 MCP 外部工具（仿 agent.py，挂了也不熄火）----
try:
    _mounted = []
    for _t in list_mcp_tools():
        WEB_TOOLS.append(to_menu_item(_t))
        TOOL_FUNCS[f"mcp_{_t.name}"] = (
            lambda _n=_t.name, **kw: call_mcp_tool(_n, kw))
        _mounted.append("mcp_" + _t.name)
    print(f"🔌 [webui] 已挂载 MCP: {', '.join(_mounted) or '无'}")
except Exception as e:
    print(f"⚠️ [webui] MCP 挂载失败（Web 仍可运行）: {e}")

SYSTEM_PROMPT = (
    "你是 tiny-harness，一个运行在用户电脑上的编码助手。"
    "需要了解项目历史时用 search_memory 检索 notes/ 知识库。回答用中文，简洁。"
    "用户请你记住关于他的信息时，直接用 write_file 更新 notes/user_profile.md"
    "（先读旧档案再合并，不必先询问）。"
    f"今天是 {date.today().isoformat()}。涉及日期时间以此为准，不确定就调 now 工具查。"
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


@app.post("/reset")
def reset():
    """开新会话：清历史只留 system；引擎正忙时不许动刀"""
    if not busy.acquire(blocking=False):
        return {"ok": False, "msg": "Agent 正忙，等它说完再开新会话"}
    try:
        messages[:] = [messages[0]]   # 就地改内容，全局引用不动
        return {"ok": True, "msg": "已开新会话"}
    finally:
        busy.release()


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
            put = lambda kind, text: q.put({"kind": kind, "text": text})
            answer = run_loop(
                messages, WEB_TOOLS,
                on_event=put,      # 引擎事件（round/tool_call/...）
                on_chunk=put,      # 字级碎片（think/answer）——同一条 SSE 管道
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
