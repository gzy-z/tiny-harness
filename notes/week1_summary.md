# 七日总结（Week 1 复盘）— tiny-harness 项目全景图

> 日期：2026-10-06 ｜ 用途：每周复盘 + 新会话的上下文锚点
> 一句话：**7 天从零造出了一个生产级韧性的编码 Agent，并领先原计划约 5 天**

## 一、旅程（每天一句话）

| 日 | 主题 | 里程碑 |
|---|---|---|
| D1 | 打通 API | 消息列表、流式、三件套配置（.env：KEY/BASE_URL/MODEL） |
| D2 | 函数调用 | 三步协议、工具注册表、Agent 循环（for+安全阀） |
| D3 | 权限与执行 | run_command+确认门、多轮 REPL、human-in-the-loop 闭环 |
| D4 | 项目化 | llm/tools/agent 三文件分层、流式+思考显示、上下文仪表盘 |
| D5 | 上下文三斧 | 截断(-84%)、整轮驱逐、LLM自摘要（421 tokens 装全场对话） |
| D6 | 质量体系 | context.py 分层、14 测试哨兵、smolagents 源码首读 |
| D7 | 手术刀 | str_replace、菜单自动生成、五层防御、A/B 评测(-38%) |

## 二、系统架构（当前形态）

```
agent.py（驾驶舱）
 ├─ REPL：exit/reset//think、会话恢复（选 new 或继续）
 ├─ 语义级重试：参数被坏节点抽走 → 自动重新点单 ×3
 ├─ Agent 循环：for 10圈安全阀 + for-else 超限警告
 ├─ 咽喉口三合一：防撞墙(TypeError→结果) + 截断(保头600/尾200)
 └─ save_session：JSONL 每轮落盘
tools.py（工具箱）
 ├─ tool_to_schema：inspect.signature+注解 → 菜单自动生成
 ├─ 工具：read_file(offset/limit) write_file list_dir run_command(确认门) str_replace(唯一匹配) now
 └─ DANGEROUS 黑名单 + is_dangerous
llm.py（发动机）
 ├─ chat/chat_stream：重试+指数退避+替补(glm-5.2,kimi)
 ├─ 流式碎片拼装：思考流显示 / 正文打字机 / 工具调用按 index 攒
 └─ 空流防御：not content and not calls → raise（触发重试）
context.py（记忆管理）
 ├─ estimate_tokens：中文1字/英文4字符 粗估
 ├─ evict_if_over：整轮驱逐（user边界下刀，不拆连体婴）+ 注入式摘要器
 └─ truncate_for_context / summarize_messages
```

**五层防御纵深**：传输层(重试+替补) → 流完整性(空流raise) → 语义层(参数丢失重问) → 执行层(防撞墙) → 行为层(10圈阀)

## 三、排障战史（方法论比结论值钱）

| 战役 | 手段 | 教训 |
|---|---|---|
| 401 无效 Key | 现场取证 | Key 与 base_url 必须同家配对 |
| 中转站空正文 | 对照实验(A/B) | HTTP 200 ≠ 成功；负载均衡节点轮盘赌 |
| 流式"打字机失灵" | 诊断脚本剥洋葱 | 思考藏在 reasoning 字段 → 反手做成功能 |
| 10圈死循环 | 复现+逐帧 | 提示词不许承诺工具做不到的事 → 加 offset/limit |
| 参数变空 read_file({}) | 分层对照+历史相关性+模型大逃杀 | glm-5.3-flash/sonnet-5 抽参数；deepseek-flash/glm-5.2/kimi/doubao 幸存 |
| 空流防御不生效 | 读代码 | 缩进一层=死代码；"有防御"≠"防御在工作" |
| confabulation | 对照日志 | 模型自述是故事（编"超时"），日志才是真相 |

## 四、LeetCode（9 题，台账 notes/leetcode_log.md）

- 套路卡：哈希通讯录(#1#169) / 栈(#20#155) / Kadane(#53#121) / 前缀和+哈希(#560) / 二分(#704#35)
- 制度：**隔天白纸盲写**（#169 盲写1过）；状态：照抄→半独立→盲写
- TLE 教训：O(n²) 在 10万级数据必死；嵌套for相乘

## 五、量化弹药（简历/面试直接用）

- 工具结果截断策略：单任务 token **8513→1394（-84%）**
- A/B 评测：str_replace 精确编辑比整文件重写**省 38%（生成端-60%）**
- 摘要压缩：整场对话压至 **421 tokens**（-90%+）
- 14 个测试哨兵；20+ commits；7 份日报

## 六、待办池（按优先级）

1. #155 补票（骨架已给）+ #232 用栈实现队列
2. v2 菜单：解析 docstring Args 段 → 参数描述回归
3. 重复调用检测（同 name+args 连续 3 次 → 干预）
4. todo 规划工具 / 子Agent（Week3 内容）
5. MCP 客户端 / RAG / 正式评测集（Week4）
6. mock 空流给防御补哨兵；修日报里的年份(2025→2026)

## 七、明日之后的路标

原计划 8 周 → 当前在 **Week 3 初**的位置。国庆后按：todo 工具 → 子Agent → MCP → RAG → 评测 → 毕业项目打磨。
