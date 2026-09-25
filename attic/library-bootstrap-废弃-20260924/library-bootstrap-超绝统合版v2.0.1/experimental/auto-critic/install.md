# EXP-auto-critic · 自动批评家（实验）

> ⚠ L7 实验模块。稳定性 ★。让每次 wrap-up 之后自动跑一个「批评家 pass」：换一个对抗视角挑本任务的毛病，写进 trajectory 供 reflect 取材。

## 做什么
在 wrap-up 之后追加一步：agent 切换到批评家人格，读本次 trajectory，专挑三类问题——①报喜不报忧 ②归因错误（表面现象当根因）③经验条目无据/过度概括。产出「批评家备忘」追加进 trajectory。

## 安装步骤
1. 复制 exp_auto_critic.md 到 knowledge/skills/（作为可选技能）。
2. wrap-up 第 6 步后追加：跑 auto-critic（用户说「跳过批评」可跳）。

## 已知风险
- 批评家输出可能过度挑刺打击效率——限 3 条以内，只挑有证据的。
- 无自反思能力的弱模型上效果差。

## 溯源
Reflexion（语言化自省）+ Memory-R1（记忆管理器 RL 思想的规则版）；本工作区 trajectory 修正「16发→14发」事件即人肉批评家实证。
