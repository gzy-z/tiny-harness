"""agent.py 驾驶舱：REPL + Agent 循环（程序入口，跑它就启动）"""

import json
from llm import chat, MODEL
from tools import TOOLS, TOOL_FUNCS
messages = [
    {"role": "system", "content": "你是文件管理助手，一律通过工具操作文件，完成后向用户简要汇报"},
]
MAX_ITERATIONS = 10

print("Agent 已就绪（输入 exit 退出 / reset 清空记忆）")

while True:
    user_input = input("\n你> ").strip()
    if not user_input:
        continue                                  # 空回车，重新等
    if user_input.lower() in ("exit", "quit", "退出"):
        print("再见！")
        break
    if user_input.lower() == "reset":
        messages = [messages[0]]                  # 记忆清零，只留 system
        print("（已清空记忆）")
        continue

    messages.append({"role": "user", "content": user_input})

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n———— 第 {iteration} 圈 ————")

        # ★ 心脏在这里：每圈开头【重新请求、更新 msg】
        response = chat(model=MODEL, messages=messages, tools=TOOLS)
        msg = response.choices[0].message

        if not msg.tool_calls:        # 不点菜了 = 任务完成
            print("最终回答:", msg.content)
            break

        messages.append(msg)          # 点菜单入历史
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            print(f"模型点菜: {tc.function.name}({args})")
            func = TOOL_FUNCS[tc.function.name]
            result = func(**args)
            print(f"执行结果: {result[:100]}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    else:
        # for-else：只有循环【没 break、跑满】才会执行 = 安全阀触发
        print("⚠️ 达到最大圈数，强制停止（防止无限点菜烧钱）")