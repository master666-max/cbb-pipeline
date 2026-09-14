# cbb-extract（本体版 v2 · 四面防御）

> P2 抽取器。前置：cbb-coordinate（manifest 切片=章节边界真值）、cbb-anchor（伪锚点）。产出：candidate 记录（Record v2.0，allow_candidate 态）。

## 四面防御（并配；R6 独有性经 16 仓复核确认——四层组合为 CBB 独有）

| 面 | 机制 | 来源 |
|----|------|------|
| ①读入侧 | R6 元文本规则（`R6_CUSTOM_EXTRACTION_INSTRUCTIONS`，逐字照抄 Step0 Tier2 已验证文本，勿改动措辞）+ stub 启发闸 `is_metatext`（元文本章零抽取） | Step 0 |
| ②输出侧 | 禁词八类 `scan_banned`（对**抽取产物字段值**扫描，非原文）：比喻→白描(transform)/万能修饰删/默认特征删/叙事禁词删/性格标签→行为依据(transform)/主观评价删/解释性描写删/语气修饰删 | worldbook 禁词剔除八类表 |
| ③模型侧 | 防先验 `no_prior_fill`：「AI 已知信息不入档」——默认特征（黑发黑眼/尖耳/年轻）在 canonical 值中且证据引文无原文出处 → 判先验补全，处置=`// 原文未提及` 占位（绝不默认填充） | worldbook 错误 5 判据 |
| ④安全侧 | 注入防御 `has_embedded_instruction`：untrusted narrative text 条款——正文内嵌指令样模式（ignore previous/系统提示词/shell 片段/代码围栏）→ **整块拒抽**（宁可漏抽不可执行） | graphify-novel 输入防御先例 |

## 吸收项（U-A17 §3）
- **证据式抽取条款**：每断言须原文引+章号（B4 无证据不入库，make_candidate 构造期强制；Bad/Good 例句见 docstring）——claude-book。
- **`//原文未提及`占位+"反推"标注**：字段级置信三态（未提及=占位/推断=（反推）/直证=原文）——worldbook 四规则。
- **别名四分类**（`alias_merge_policy`）：proper_name=可合并／nickname=须同指证据且置信≥0.85／descriptor·title=永不合并／存疑=分开建（宁可分裂不可误合）——oh-story 规则层（算法层在 cbb-store/U-B07）。
- **长篇施工参数**（`CONSTRUCTION_PARAMS`+`plan_batches`+`merge_plan`，迷深 517 章直接可用）：章节边界以 manifest 切片为真值；5-8 章/批新上下文子代理（no accumulation；**尾批允许 <5——尾批不摊薄不凑数**）；降维聚合 15KB/章→≤8K 回传→√N 合并——oh-story。
- **机械硬检查**（`verify_evidence`）：落盘后证据引文回原文坐标 grep 复核+计数核对，**不依赖抽取器自报**——oh-story。
- **编写前重读纪律**：`reread_before_write` 施工条款（生成条目前重读对应章节原文）——worldbook Step 4。

## 保留面（v1.0）
stub 离线确定性抽取（词典实体+关键词事件）；record_id 内容哈希幂等；`build_episode_kwargs`（伪锚点 reference_time 禁墙钟 + R6 注入，Step0 Tier2 已验证形态）；`env_probe` 只探存在性布尔（D-004）。

## 移出
三态写入桩 → cbb-store（U-B07）。

## 用法
```bash
py -X utf8 cbb/cbb-extract/cbb_extract.py --manifest .cache/<键>.json --lexicon 缇达,迷宫 --events 拔出了剑 --out cands.json
py -X utf8 cbb/cbb-extract/cbb_extract.py --manifest x --r6-check   # 只验 R6 标配在位
```
