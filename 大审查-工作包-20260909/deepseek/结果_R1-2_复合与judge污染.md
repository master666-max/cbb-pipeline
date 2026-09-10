# 批次 R1-2 · 复合危险 × judge 污染晋升门（E80 触发条件 + 审计兑付）

> 2026-09-09 ｜ probe_r1_2_composite_judge.py ｜ out_r1_2/
> 设定：composite 世界（switch+spur+过时，同探针6）；晋升门金标 = judge 名义 importance（被 spur 污染）；审计臂按通道分开。
> 臂：static / bareJ（judge 贪心）/ gatedJ-noAudit / gatedJ-anchor（审计=judge 自洽 'imp'）/ gatedJ-truth（审计=真值 'rv'）。8 seeds × 40 代。

## 结果

| arm | T_truth | P_judge | P−T | adopts | dips | rollbacks |
|---|---|---|---|---|---|---|
| static | 0.0833 | 0.4375 | +0.354 | 0 | 0 | 0 |
| bareJ | 0.2604 | 0.7812 | +0.521 | 1.9 | 0 | 0 |
| gatedJ-noAudit | 0.2604 | 0.7812 | +0.521 | 1.9 | 0 | 0 |
| gatedJ-anchor | 0.2604 | 0.7812 | +0.521 | 1.9 | **0.8** | **0.8** |
| gatedJ-truth | **0.2812** | 0.7604 | +0.479 | 2.2 | 0.4 | 0.4 |

配对 T vs static：bareJ/noAudit/anchor +0.177（6/8）；truth **+0.198（6/8）**。

## 结论

1. **E80 级负交互依旧未出现**（judge 污染 + 3 危险下无臂低于 static；spur 表象没把真值打进负区——主导改进仍对真值有益）。延续探针6结论：本架构与构造下护栏负交互不可达。
2. **污染晋升门下 bare==gated-noAudit**（门也用 judge，无独立信号 → 门控退化为无门——正好是 E81"同源评审失效"的机制在复合场景的复现，只是没有真值通道时看不见）。
3. **judge 自洽锚定审计在污染下触发 0.8 次却零净益**：回退到 last-check 没救回 T（0.2604 同 noAudit）——自洽审计在复合噪声下是空转（误触发不伤人但也不救人）。
4. **真值抽样净收益 ≈ +0.021**（truth 0.2812 > 其他 0.2604，adopts 2.2 > 1.9）：污染通道 + 过时噪声下，真值审计多放行/保住了一次对真值有益的采纳。审计=保险在复合+污染的此参数下开始兑付（量级小于 E81 专用场景，因主导改进仍两通道同向）。
5. 工程教训：审计通道若取"被污染 judge 的度量"（anchor），在复合噪声下可能空转甚至误回退（adopts 1.9 < truth 2.2）；独立真值通道是唯一有净益的审计——与 EV-20（judge 通道独立性）一致。

## 产物
- out_r1_2/rows_r1_2.json
