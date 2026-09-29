# RELEASE-NOTES v3.1（2026-09-29）

> 迷深实战判卷战役（2,184 件三票满编 + 契约刻度定位）实证沉淀。差异章全文见 全流程说明书.md v3.1 章。

## 变更
- **判卷契约刻度**（v2→v2.1→v2.2 实测）：v2.2 = v1 极简 + claim 防误读行，五十件验证轮植株捕获 8/8 捕获门 PASS（晋升 35/hold 7，Wilson 95% [0.69,0.92]）；量产默认仍 v2，v2.2 为已验证待采纳态。
- **编制 2/3**：主链 GLM×DEEPSEEK 双票一致（双 support ∧ 零 against）；第三方仅抽检审计（分歧带支持率 45% 实测入 G17 CUSUM 基线）。
- **判卷面卫生**：植株随机穿插全卷 + 期望字段剥离至 manifest_priv（考官盲评）。
- **考官契约附件**：references/考官契约-20260929.md（编制史 v1.0→v1.14、令牌链、上岗考试记录）。
- **库况快照**：references/库况快照-v3.1.json（lens 机械复算）。

## 验证
- scripts/verify_release.py 逐位核对 HASHES.json；cbb2-tests 随包；契约 v2.2 上岗考试 8 株 8/8、验证轮 Wilson 区间在案。

## 已知限制
- 植株门在判卷契约 v2 下不可达（DS 弃权画像）——v2.2 采纳前，全量判卷轮结果为参考值。
- 2,184 件 hold 存量维持参考值判词 + 人工队列排序，不自动晋升。
- **库况（lens 快照 references/库况快照-v3.1.json）**：主库 6,278 件全部 provisional、confirmed=0——这是**纪律的诚实结果**：植株门 FAIL 的判卷轮不产生物料化晋升（G16b 时代报告中的"confirmed"为判卷台账口径，未写入记录状态位）；隔离区 quarantine_confirmed 743 为早期 Phase A 产物。物料化晋升等首个过门轮 + 库属主裁决。
