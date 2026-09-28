"""
Day 01 · 第一次调用大模型 API
=============================
今天只学一件事，但是是整个 Agent 体系里最重要的一件事：

    「消息列表（messages）」—— Agent 的一切都围绕这个数据结构转。

Agent 没有任何魔法：你把一段对话历史（消息列表）发给模型，
模型返回一段回复，你把回复追加进列表，再发给模型……
所谓"记忆"，就是这个列表还没被删掉而已。

运行前的准备（看 README.md）：
    1. 把 .env.example 复制为 .env，填好"供应商三件套"（KEY/接口地址/模型名）
    2. 安装依赖：.venv\\Scripts\\pip install -r requirements.txt
    3. 运行：.venv\\Scripts\\python day01_first_call.py
"""

import os
from http.client import responses
from pathlib import Path


from dotenv import load_dotenv
from openai import OpenAI


# ---------------------------------------------------------------
# 1. 加载 .env 文件里的环境变量
#    为什么不把 Key 写死在代码里？——因为代码要上传 GitHub，
#    密钥一旦泄露，别人就能花光你账户里的钱（真实事故每天都在发生）。
# ---------------------------------------------------------------
# 把 .env 的位置锚定在"脚本所在目录"：无论从哪个目录启动，都只读本项目的 .env。
# （Day 01 的教训：程序从哪个目录启动，就会去哪个目录找 .env，这是新手大坑）
load_dotenv(Path(__file__).resolve().parent / ".env")

# ---------------------------------------------------------------
# 2. 创建客户端
#    DeepSeek 的 API 完全兼容 OpenAI SDK，只需要把 base_url 换掉。
#    这意味着你以后换成任何兼容模型（GLM、Qwen、本地 Ollama）都只改这一行。
# ---------------------------------------------------------------
# 供应商三件套：KEY / BASE_URL / MODEL，全部从 .env 读取。
# OpenAI 兼容接口的世界里：换供应商 = 只改 .env 三行，代码一行不动。
# .env 没配置时，默认用 DeepSeek 官方。
api_key = os.environ.get("LLM_API_KEY", "")
if not api_key:
    # 报一句人话，而不是让新手对着 KeyError 的堆栈发呆
    raise SystemExit("没读到 LLM_API_KEY：请检查 tiny-harness/.env 是否已填写")

client = OpenAI(
    api_key=api_key,
    base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
)

MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

# ---------------------------------------------------------------
# 3. 核心：消息列表
#    每条消息是一个 dict，只有两个关键字段：
#      - role:    system(设定) / user(用户) / assistant(模型) / tool(工具结果)
#      - content: 文本内容
#    整个 Agent 的"上下文管理"，本质就是管理这个列表的长度和内容。
# ---------------------------------------------------------------
messages = [
    {"role": "system", "content": "你是没素质的杠精，回答四到五句话。"},
    {"role": "user", "content": "跟女朋友分手了怎么办"},
]

# ---------------------------------------------------------------
# 4. 发起请求
#    这个函数就是 Agent 的"心脏"——之后无论项目长到多复杂，
#    最终都是调用它，只是 messages 越来越长、tools 越来越多。
# ---------------------------------------------------------------

reply = ""
stream  = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    stream=True
)
for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        reply += delta
        print(delta, end="", flush=True)
# ---------------------------------------------------------------
# 5. 取出回复
#    注意：模型返回的是一整个对象，回复文本藏在
#    response.choices[0].message.content —— 这个嵌套结构要记熟。
# ---------------------------------------------------------------
print("第1轮",reply)
messages.append({"role": "assistant", "content": reply})
messages.append({"role": "user", "content": "想跟她复合怎么办"})
response2 = client.chat.completions.create(model=MODEL, messages=messages)
reply2 = response2.choices[0].message.content
print("第2轮：",reply2)




# ---------------------------------------------------------------
# 6. 观察 token 用量
#    prompt_tokens = 发出去多少 token（你的输入也要花钱！）
#    completion_tokens = 模型生成多少 token
#    第 2 周做"上下文管理"时，就要靠这些数字决定何时截断历史。
# ---------------------------------------------------------------
print(f"\n--- 本次消耗: prompt={response2.usage.prompt_tokens} "
      f"completion={response2.usage.completion_tokens} tokens ---")


# ================================================================
# 今日练习（做完才算完成 Day 01）
#
# 练习 1（多轮对话雏形）：
#   把 reply 以 {"role": "assistant", "content": reply} 追加进 messages，
#   再追加一条新的 user 消息（比如"再举个例子"），再次调用 create()。
#   观察：模型为什么"记得"上一轮说了什么？
#
# 练习 2（流式输出，必做）：
#   给 create() 加参数 stream=True，返回值变成一个迭代器：
#       stream = client.chat.completions.create(..., stream=True)
#       for chunk in stream:
#           delta = chunk.choices[0].delta.content
#           if delta:   # 注意有些 chunk 的 content 是 None
#               print(delta, end="", flush=True)
#   这就是你日常用的 ChatGPT/DeepSeek 网页"打字机效果"的全部原理。
#
# 练习 3（理解 system prompt）：
#   把 system 消息改成三种不同人设（严苛的代码审查者/热情的老师/杠精），
#   问同一个问题，对比回复差异。
# ================================================================
