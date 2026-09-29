"""
Day 02 · 函数调用（Function Calling）—— Agent 的"关节"
=======================================================
Agent 三大件：LLM（会想）+ 工具（会动手）+ 循环（会坚持）。
昨天你搞定了"会想"，今天打通"会动手"。

核心认知（先背下来再看代码）：
    模型永远不能直接执行任何东西！
    它只能返回一张结构化的"点菜单"（tool_calls），
    真正动手执行的是你的 Python 代码，
    执行完把结果回传，模型再据此说话。

三步协议：
    ① 声明工具（JSON Schema 写"菜单"）
    ② 模型点菜（返回 tool_calls，自己不执行）
    ③ 你执行 + 回传（结果以 role="tool" 塞回消息列表，再问一次）

运行：
    .venv\\Scripts\\python day02_tool_call.py
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
)
MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")


# ---------------------------------------------------------------
# 0. 真正的函数：一个普通的 Python 函数
#    注意：模型完全看不见这个函数的代码！
#    它能看到的只有下面 TOOLS 里你写的"说明书"。
# ---------------------------------------------------------------
def get_weather(city: str) -> str:
    """教学环境用假数据；真实产品里这里会去调天气 API"""
    fake = {"北京": "晴，25°C，湿度40%", "上海": "多云，28°C", "广州": "雷阵雨，31°C"}
    return fake.get(city, f"{city}：暂无数据（这是教学假数据）")


# ---------------------------------------------------------------
# ① 声明工具：用 JSON Schema 描述"有哪些工具、怎么用"
#    - name:        函数名，模型点菜时报这个名字
#    - description: 最重要的一行！模型靠它判断"什么时候该点这道菜"
#    - parameters:  参数的格式说明书
# ---------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市当前的天气情况",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，例如：北京"},
                },
                "required": ["city"],
            },
        },
    }
]

messages = [
    {"role": "system", "content": "你是天气助手，需要天气信息时必须使用工具查询，不要编造。"},
    {"role": "user", "content": "北京的天气怎么样"},
]

# ---------------------------------------------------------------
# ② 第一次请求：模型看到"菜单"，决定是否"点菜"
#    判断依据 = finish_reason：
#      "tool_calls" = 模型想调工具（点菜了）
#      "stop"       = 不需要工具，直接回答
# ---------------------------------------------------------------
print("=" * 50)
response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
msg = response.choices[0].message
print("finish_reason:", response.choices[0].finish_reason)

if msg.tool_calls:
    # 关键细节 1：assistant 的"点菜单"必须先存入历史，
    # 否则第二轮模型不知道自己点过什么（对话就断片了）
    messages.append(msg)

    for tc in msg.tool_calls:
        # 关键细节 2：arguments 是【JSON 字符串】，不是 dict，要解析
        args = json.loads(tc.function.arguments)
        print(f"模型点菜: {tc.function.name}({args})")

        # 关键细节 3：执行的是你自己写的函数——模型只动了嘴
        result = get_weather(**args)
        print(f"本地执行结果: {result}")

        # 关键细节 4：结果以 role="tool" 回传，
        # tool_call_id 像餐厅的"取餐号"，把结果和点菜单配对
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })

    # -------------------------------------------------------
    # ③ 第二次请求：模型拿着工具结果，生成给人看的最终回答
    #    （明天这里会变成 while 循环——模型可能还要再点菜）
    # -------------------------------------------------------
    print("=" * 50)
    final = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
    print("最终回答:", final.choices[0].message.content)
else:
    print("模型没点菜，直接回答了:", msg.content)


# ================================================================
# 今日练习
#
# 练习 1（观察"不点菜"）：
#   把 user 消息换成 "你好，介绍一下你自己"，重跑。
#   观察 finish_reason 变成 "stop"，model 一道菜都没点——
#   点不点菜是【模型自己判断】的，依据是工具的 description。
#
# 练习 2（加第二道菜）：
#   自己写一个 get_time() 返回当前时间字符串（import time），
#   照葫芦画瓢加进 TOOLS，然后问"现在几点了？北京天气如何？"
#   观察模型可能在【一轮里点两道菜】。
#
# 练习 3（看原始结构）：
#   在 for 循环前打印 print(msg.tool_calls)，
#   亲眼看看"点菜单"长什么样。
# ================================================================
