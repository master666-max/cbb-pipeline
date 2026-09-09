# library-bootstrap 通用建库 Skill（library-bootstrap · 完成于 2026-09-04）

> manifest 归档（D-001）：skill 本体在 knowledge/skills/library-bootstrap/（89 文件），发布包在根目录 library-bootstrap-v1.0-发布版/（78 文件）。测试脚本只在 skill 源目录。

## 一句话
可整目录拷到任何 agent harness 的一键建库 skill：8 档预设（L0 裸奔→L7 实验）+ 10 功能模块自由组合 + 6 特色包，模板复制式安装保证跨 harness 可复现。

## 复现
- 测试：`py -X utf8 knowledge/skills/library-bootstrap/run_tests.txt` → 13/13 PASS（T1-T7：L1/L6/L4+RP 安装、幂等、依赖拒绝、双入口、清单完备）
- 发布包：拷 `library-bootstrap-v1.0-发布版/` 到目标工作区，对 agent 说「按 library-bootstrap 建库」

## 数据流
任务书（用户五项裁决）→ Ph1 设计冻结 → Ph2 模块 → Ph3 特色包 → Ph4 适配器 → Ph5 预设+SKILL → Ph6 测试 → Ph7 发布

## 关键决策
- 可复现性三件套：模板复制+{{SLOT}}填槽 / install.md 清单式 / manifest sha1 哈希校验——不靠 agent 自由发挥。
- E-full/E-fallback/E-manual 三档环境降级（.py 被拦→.txt 形态→纯清单），P-001 坑变成 skill 内置免疫。
- L7 dream-fusion（梦境融合）：随机抽 3 条不相关条目强行联想——用户要的「更激进」，标注 ☆ 稳定性+逃生舱。

## 踩坑与经验
- 提炼到知识库：pitfalls.md#P-004（sed 批量文本生成翻车）
- 本次验证的范式：patterns.md#pt-004（第 4 次）

## 复用提示
- ★★★ 高：任何新工作区/新 harness 建库直接用发布包；模块模板按需抄。

## 未竟事项
- dream-fusion 尚未在本库实装（experimental 只随包分发，本库未启用）——下月体检时可考虑。
- 真机跨 harness 验证（Claude Code/Cursor 实机装一遍）待有环境时做。
