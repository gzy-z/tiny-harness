"""eval.py — 正式评测集：任务集 + 裁判 + 跑批统计

用法：.venv\\Scripts\\python eval.py [N]
每任务跑 N 次（默认 3），统计成功率/平均token/平均圈数/平均耗时，输出 markdown 表。
沙盒 tmp_eval/ 操作，不碰真项目。教训链：单次数字=抽签（33%→44%）→ 跑批才有统计意义。
"""
import json
import shutil
import time
from pathlib import Path

from compare_edit import SYSTEM, call_llm
from tools import TOOLS, TOOL_FUNCS
from llm import MODEL
SANDBOX = Path("tmp_eval")
RUNS = 3
# 评测模式菜单：去掉 run_command（确认门卡无人值守）——最小够用原则
EVAL_TOOLS = [t for t in TOOLS if t["function"]["name"] != "run_command"]


def setup_sandbox():
    """每轮开考前：清空沙盒，拷材料进来"""
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    SANDBOX.mkdir()
    shutil.copy("check_key.py", SANDBOX / "check_key.py")
    shutil.copy("llm.py", SANDBOX / "llm.py")   # 给 read_answer 当靶子
    (SANDBOX / "buggy.py").write_text(
        'def multiply(a, b):\n'
        '    """返回 a 和 b 的乘积"""\n'
        '    return a + b\n',
        encoding="utf-8")

def check_edit_surgical():
    text = (SANDBOX / "check_key.py").read_text(encoding="utf-8")
    return ("永不显示" in text[:200]) != ("绝不显示" in text[:200])  # 恰好一个在


def check_read_answer(messages):
    final = next(m for m in reversed(messages) if m["role"] == "assistant")
    answer = (final.get("content") or "").strip()
    return any(k in answer for k in ["2", "两", "俩"])

def check_create_file():
    # 裁判：文件存在 + 内容含关键词（生成类任务的最低标准）
    p = SANDBOX / "summary.md"
    return p.exists() and "tiny-harness" in p.read_text(encoding="utf-8")


def check_multi_edit():
    # 裁判：两处都改到（新词在、旧词不在）——两处都验了唯一性，str_replace 不会撞墙
    text = (SANDBOX / "check_key.py").read_text(encoding="utf-8")
    ok1 = ("供应商配置体检" in text) and ("供应商配置诊断" not in text)
    ok2 = ("先跑这个" in text) and ("先跑它" not in text)
    return ok1 and ok2


def check_find_bug(messages):
    # 裁判（查对话型）：最后回答点出"加"或"+"（把乘法写成加法）
    final = next(m for m in reversed(messages) if m["role"] == "assistant")
    answer = final.get("content") or ""
    return ("+" in answer) or ("加" in answer)

TASKS = [
    {"name": "edit_surgical", "prompt": None, "check": check_edit_surgical},
    {"name": "read_answer",
     "prompt": "读 tmp_eval/llm.py，告诉我 FALLBACKS 列表里有几个替补模型？只回答数字。",
     "check": check_read_answer},
    {"name": "create_file","prompt":"在 tmp_eval/ 里创建 summary.md，用两三句话介绍 tiny-harness 项目，内容必须包含 tiny-harness 这个词。",
     "check": check_create_file},
    {"name":"multi_edit" ,"prompt":"对 tmp_eval/check_key.py 做两处修改：①把'供应商配置诊断'改成'供应商配置体检'；②把'先跑它'改成'先跑这个'。",
     "check":check_multi_edit},
    {"name":"find_bug", "prompt":"tmp_eval/buggy.py 的 multiply 函数有 bug。读文件找出 bug 在哪一行、错在哪，简要说明。","check":check_find_bug}
]


def run_task(task, **llm_kw):
    """跑一个任务一次，返回战报；**llm_kw 原样转交 call_llm（透传惯用法）"""
    setup_sandbox()
    if task["name"] == "edit_surgical":  # 现场定改词方向（防背答案）
        text = (SANDBOX / "check_key.py").read_text(encoding="utf-8")[:200]
        old, new = ("绝不显示", "永不显示") if "绝" in text else ("永不显示", "绝不显示")
        prompt = f"把 tmp_eval/check_key.py 的 docstring 里 {old} 四个字改成 {new}"
    else:
        prompt = task["prompt"]
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt}]
    p_total = c_total = rounds = 0
    t0 = time.time()
    for _ in range(10):
        rounds += 1
        msg, usage = call_llm(messages, EVAL_TOOLS, **llm_kw)
        p_total += getattr(usage, "prompt_tokens", 0) or 0
        c_total += getattr(usage, "completion_tokens", 0) or 0
        messages.append(msg)
        if not msg.get("tool_calls"):
            break
        for tc in msg["tool_calls"]:
            args = json.loads(tc["function"]["arguments"] or "{}")
            result = TOOL_FUNCS[tc["function"]["name"]](**args)
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": str(result)})
    ok = task["check"](messages) if task["check"].__code__.co_varnames[:1] == ("messages",) else task["check"]()
    if not ok:  # 黑匣子：失败的现场完整封存，供事后验尸
        Path(f"failed_{task['name']}_{int(time.time())}.json").write_text(
            json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ⚠️ {task['name']} 失败，现场已存 failed_{task['name']}_*.json")
    return {"ok": ok, "tokens": p_total + c_total, "rounds": rounds, "sec": round(time.time() - t0)}


def main(**llm_kw):
    print("| 任务 | 成功率 | 平均token | 平均圈数 | 平均耗时 |")
    print("|---|---|---|---|---|")
    for task in TASKS:
        reports = []
        for _ in range(RUNS):
            try:
                reports.append(run_task(task, **llm_kw))
            except Exception as e:  # 防御关：故障击穿 = 该次失败（留遗言，不吞异常）
                print(f"  ⚠️ {task['name']} 被击穿: {type(e).__name__}")
                reports.append({"ok": False, "tokens": 0, "rounds": 0, "sec": 0})
        n_ok = sum(r["ok"] for r in reports)
        avg = lambda k: round(sum(r[k] for r in reports) / len(reports))
        print(f"| {task['name']} | {n_ok}/{RUNS} | {avg('tokens')} | {avg('rounds')} | {avg('sec')}s |")
    shutil.rmtree(SANDBOX, ignore_errors=True)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "ab":
        print("== A组：防御关 + 30% 故障 ==")
        main(sabotage=0.3, attempts=1, candidates=[MODEL])
        print("== B组：防御开 + 30% 故障 ==")
        main(sabotage=0.3)
    else:
        main()