# exp9-emotion · 情绪状态向量（BCA 3.1 · 公理 3 stakes 是生死线）

## 装什么
soul/STATE.md（4 维连续向量）+ 更新脚本 + 调制指令规则表。依赖 exp9-instrumentation。

## install.md 步骤
1. 复制 template/soul/STATE.md → soul/STATE.md（初始中性向量）。
2. 复制 scripts/state_update.txt → tools/。
3. 会话入口追加一行：「读到 soul/STATE.md 的调制指令就执行」（v1 前缀注入）。
4. wrap-up 第 3 步后追加：「跑 tools/state_update.txt --verdict passed/failed/corrected 更新情绪向量」。
5. **stakes 红线**：Δ 只由 ①任务完成质量（verdict）②长期利益信号（复用/采纳遥测）驱动；用户即时夸赞文本禁止进入 Δ（物理隔离）。
6. 校验点：STATE.md 含 4 维与更新史；`state_intervene.txt --set arousal=0.8` 可写且写后校验。

## 调制规则表（写入 STATE.md 生成器）
| 维度 | 低值 | 高值 |
|---|---|---|
| valence | 措辞保守 | 措辞开放 |
| arousal | 检索收敛慢/响应长 | 响应短/检索激进 |
| certainty | 强制先检索+降置信 | 可直接作答 |
| interest | 话题浅尝 | 延长探索 |

更新公式：s_t = 0.7·s_{t-1} + 0.3·Δ（半衰期显式化）。消融/干预走 state_intervene（A1/A2 验收）。

## 溯源
BCA 3.1 情绪状态向量（躯体标记假说：情绪=压缩的价值缓存）；措辞一律"情绪式调制器"非"情绪"（公理 1）。
