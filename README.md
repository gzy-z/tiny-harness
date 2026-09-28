# tiny-harness — 从零造一个 Agent

这是一个**学习型项目**：8 周内，不用任何 Agent 框架，从 0 写出一个对标 Claude Code / Codex 的
迷你 Agent Harness（智能体运行框架），模型后端使用 DeepSeek API。

## 为什么这么学？

Agent 的本质只有一句话：

> **LLM + 工具调用 + 循环 + 上下文管理 + 权限控制**

先用 100 行代码把这个循环亲手写出来，再回头读 smolagents / Aider / Gemini CLI 的源码，
你才知道该看什么。这就是"以造代读"。

## 环境准备（Day 01 第一节课）

1. **获取 API Key**：打开 https://platform.deepseek.com → 注册 → 创建 API Key → 充值 10 元
   （学习期足够用很久）
2. **配置密钥**：把本目录下的 `.env.example` 复制一份命名为 `.env`，把你的 Key 填进去
3. **安装依赖**：
   ```bash
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```
4. **运行第一个程序**：
   ```bash
   .venv\Scripts\python day01_first_call.py
   ```

## 目录约定

- `dayXX_xxx.py` — 每天的练习代码，一个文件讲一个概念，保留下来就是你的成长记录
- `PLAN.md` — 8 周作战计划，每天打开打卡
- 后期会重构成 `src/` 包结构（这本身就是一堂课）

## 学习路线总览

| 阶段 | 周 | 产出 |
|---|---|---|
| 地基 + 最小 Agent | W1 | 流式聊天客户端 → 100 行 mini-agent |
| 玩具变工具 | W2 | 上下文管理、权限、持久化、测试 |
| 编辑与规划 | W3 | 精确编辑、todo 规划、子 Agent |
| 生态与评测 | W4 | MCP、RAG 记忆、评测报告 |
| 毕业项目 | W5-6 | 完整开源项目 + Web UI |
| 打磨 | W7 | 博客、性能、第二亮点 |
| 求职冲刺 | W8 | 简历、面试话术、投递 |

详细计划见 **[PLAN.md](PLAN.md)**。
