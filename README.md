# tiny-harness 🔌

> 从零自研的迷你 Agent Harness —— 不依赖任何 Agent 框架，10 天从第一次 API 调用长成即插即用的 Agent 平台。

一个能**列计划、派子 Agent、执行命令（带人工确认门）、精准编辑文件、动态挂载 MCP 外部工具、跨会话记忆检索（RAG）**的命令行 Agent，以及支撑它的整套工程质量体系（六层防御、21 个测试哨兵、上下文三层管理、自建评测集）。

![demo](docs/demo_hd.gif)

## ✨ 特性

- **Agent 循环引擎**（`loop.py`）：点菜→执行→回传，主/子 Agent 共用唯一实现
- **子 Agent**（`subagent.py`）：独立上下文干调研，只回传浓缩结论——主上下文零污染
- **MCP 客户端**（`mcp_client.py` + `mcp_server.py`）：动态挂载 Model Context Protocol 生态服务器，换服务器零代码
- **工具系统**（`tools.py`）：菜单由函数签名+docstring 自动生成（inspect 反射），手写 Schema 的 bug 类结构上不可能
- **权限门**：危险命令黑名单 + 人工 y/n 确认；子 Agent 最小权限（只读）
- **上下文管理三板斧**：工具结果截断（-84% token）、整轮驱逐（不拆散 tool_calls 连体婴）、LLM 自压缩摘要
- **流式体验**：打字机输出 + 思考流显示（兼容 reasoning/reasoning_content 双字段）
- **会话持久化**：JSONL 逐轮落盘，重启可选择恢复或开新
- **评测系统**（`eval.py`）：任务集 + 机器裁判 + 跑批统计 + 故障注入 A/B——单次数字=抽签，跑批才有统计意义
- **长期记忆 / RAG**（`memory.py`）：notes/ 知识库 + BM25 检索（字符 bigram 分词，指纹感知缓存）——`search_memory` 让 Agent 跨会话记忆、回答可溯源，Agent 甚至自发用 `write_file` 写用户档案，涌现出记忆的写入端；embedding 通道 404 后的零依赖工业标准实现
- **Web UI**（`webui.py` + `static/`）：FastAPI + SSE 流式聊天——字级打字机（思考/回答分色逐字流出）、MCP 外部工具可点、一键新会话，点开链接即可试玩

## 🛡️ 六层防御纵深

| 层 | 防什么 | 机制 |
|---|---|---|
| 传输层 | 超时/坏网关 | 重试 + 指数退避 + 替补模型 |
| 流完整性 | "成功"的空响应 | 空流 raise → 自动重试 |
| 语义层 | 参数被网关抽走 | 必填参数空缺检测 → 重新点单 |
| 重复行为 | 同调用死循环 | 计票器第 3 次起劝退 |
| 执行层 | 调用参数出错 | 防撞墙：错误变工具结果 |
| 行为上限 | 无限点菜 | 圈数安全阀 + 阶段性发现打捞 |

## 📐 架构

```
agent.py     驾驶舱：REPL / 会话恢复 / 上下文仪表盘 / 组合根接线
loop.py      引擎：通用 Agent 循环（全部防御的唯一实现）
tools.py     工具箱：7 个本地工具 + 菜单自动生成 + 注册表
subagent.py  子 Agent：只读调研员，一次性上下文
mcp_*.py     MCP 双面：服务器（FastMCP）+ 客户端桥
llm.py       发动机：流式碎片拼装 / 思考流 / 重试与替补
context.py   记忆管理：token 估算 / 截断 / 驱逐+摘要
memory.py    长期记忆：notes/ 切块索引 + BM25 top-k 检索（RAG，零依赖）
webui.py     Web 门面：FastAPI + SSE + 线程队列中转（on_event 回调接浏览器）
static/      极简前端：终端风聊天界面，引擎事件分色滚动
eval.py      评测集：6 任务×N 次跑批 / 机器裁判 / 故障注入 A/B（给防御定价）
test_*.py    21 个测试哨兵（含"每个 bug 一个哨兵"的回归传统）
notes/       10 天开发日志（learning in public）
```

## 🚀 快速上手

```bash
git clone https://github.com/gzy-z/tiny-harness.git
cd tiny-harness
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env    # 填入你的 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
.venv\Scripts\python agent.py     # 命令行试玩
.venv\Scripts\python webui.py     # 或浏览器试玩 → http://127.0.0.1:8000
```

> 任意 OpenAI 兼容接口（DeepSeek / GLM / 中转站均可），改三行配置即换供应商。

## 📊 实测数据

- 工具结果截断：单任务 token **8513 → 1394（-84%）**
- str_replace vs 整文件重写：7 次抽样均值 **≈-24%**（单次区间 -30% ~ +58%，方差本身就说明了为什么要跑批）
- **故障注入 A/B**（30% 节点故障模拟）：防御关 **4/15（27%）** vs 防御开 **15/15（100%）** 成功率——代价是 2× 延迟，token 持平（失败请求发出前即被拦截）
- 评测任务集基准：6 任务 × 3 次 **18/18**，含 RAG 检索任务（memory_recall 3/3）；成本分层：读（1.9k~2.9k）< 改（4.6k~5.6k）< 生成（8.4k）
- 历史压缩：整场对话压至 **421 tokens**
- RAG 闭环：Agent 自发 write_file 写用户档案 + 指纹感知缓存自动重建 → 跨会话记住用户
- 测试：21 绿 2.5s（pytest 收集优化 182s→2.5s）

## 📖 这个仓库怎么读

`day01_*.py ~ day09_*.py` 是按天保留的进化化石（每一步都能跑）；`notes/dayXX.md` 是当天的开发日志，记录了每个 bug 的发现、定位与修复过程——包括中转站的"节点轮盘赌"、流式参数丢失之谜、被锁死在会话存档里的 system prompt 等。**Bug 图鉴比功能列表更有料。**

## License

MIT
