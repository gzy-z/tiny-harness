# Day 10 学习日报

日期：2026-10-08

## 我今天学会了
1. **MCP 双面工程**：FastMCP 写服务器（@装饰器自动注册）+ 客户端三步协议（initialize → tools/list → tools/call）
2. **stdio 死锁坑**：服务器内 subprocess 继承协议管道句柄 → 死锁；`stdin=subprocess.DEVNULL` 一针两病（死锁 + git 空输出）
3. **版本钉扎**：mcp 2.x 改名 FastMCP→MCPServer，错误信息建议 pin 'mcp<2' —— requirements.txt 写版本范围防"一觉醒来 API 变了"
4. **lambda 语法课**：默认参数不能排在 **kwargs 后面（可变关键字必须垫底）
5. **async/await 初见**：等待时让出 CPU，先照抄后专题

## 里程碑：作品集上线
- github.com/gzy-z/tiny-harness **公开上线**（24 颗 commit）
- 推送前安检：**.env 从未进过历史**（0 次）——十天 gitignore 纪律的完美验收
- README 公开版（特性/防御表/架构/数据/怎么读）已 commit，**待网络恢复推送**（Connection was reset，深夜/清晨重试或挂代理）

## 今天最戏剧的一幕
Agent 启动即插电：`🔌 已挂载 MCP 外部工具: mcp_get_weather, mcp_project_stats`——
这两道菜**不在 tools.py 里，在另一个进程里**。todo → 外部菜并行 → 打勾 → 汇报，全部规矩照常生效。
**Agent 从"自带工具箱"进化为"即插即用平台"。**

## 数据
- 哨兵：18 全绿（新增 MCP 集成测试 2 个）
- #35 盲写首过（LeetCode 累计 12 题）
- 新模块：mcp_server.py / mcp_client.py

## 【你写】
1. 用自己的话解释"MCP 的 inputSchema 和我的 TOOLS 菜单天生同构"意味着什么：

2. 一句话向不懂技术的人解释今天：

## 明日菜单
GitHub README 补推（网络择机）→ 评测课起步（compare_edit 升级为正式 eval 集）→ RAG 记忆 或 Web UI 起步
