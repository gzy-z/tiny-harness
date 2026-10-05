# Day 07 学习日报

日期：2026-10-05

## 我今天学会了
1. **盲写制度开张**：#169 白纸盲写通过（卡在 .get(num,0)+1，拼出来后终身是我的了）
2. **菜单自动生成**（tool_to_schema）：inspect.signature + 类型注解 → 菜单从函数里"长"出来
3. **str_replace 精确编辑**：唯一匹配才动刀（count>1 拒绝）、错误消息教模型自救

## 今天的大戏：四字手术排障全链（值得完整复述）
现象：Agent 调工具时参数变空 `read_file({})` →
① 查生成菜单：发现 write_file/list_dir 描述为空（函数没写 docstring）→ 补上 + 新哨兵 →
② 碎片级解剖：单轮请求参数完好 → **问题精确出现在"带重建历史的请求"** →
③ 模型大逃杀：5 个候选模型跑同样的历史，**deepseek-flash / glm-5.2 / kimi / doubao 幸存**，glm-5.3-flash 和 sonnet-5 会抽参数，haiku 已下架(404) →
④ 换 deepseek-flash 当主力 → **手术成功，git diff 全场只改 4 个字**

结论：不是我的代码错，是通道对"多轮工具历史"的转换 bug——但发现它靠的是逐层对照实验。

## 今天的新认知（每条都值钱）
1. **新能力暴露旧账**×2：零参数工具暴露"arguments 永远非空"假设；自动生成暴露"没写 docstring"旧账
2. **空响应防御**：`if not content and not calls: raise`——把"成功的空"当错误，手动激活自家重试机制
3. **断言两课**：断言真实输出（不是手打的说明文字）；断言行为不ried断言措辞
4. **Confabulation**：模型说"第一次查询超时后换了命令"——超时是它编的（它看不见重试层）。**模型的自述是故事，日志才是真相**
5. `x or "{}"` 默认值戏法：空参数当空字典

## 数据
- 哨兵：14 个全绿（新增：菜单描述非空 + str_replace 三连）
- LeetCode：#35 Accepted（改编独立）；#169 盲写1过
- Agent 武器库：read_file(offset/limit) / write_file / list_dir / run_command(确认门) / str_replace / now()
- 主力模型：deepseek-flash（大逃杀冠军），替补 glm-5.2 / kimi

## 【你写】
1. 今天这场排障里，最让你有成就感的一步：
无数次修改之后成功了
2. 用一句话向不懂技术的人解释今天：
写作文的时候遇到错误的地方不用全部重写，只用改错误的地方