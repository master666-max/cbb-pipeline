# -*- coding: utf-8 -*-
"""g18_content.py — G18 v3.1 内容链：差异章+版本联动+考官契约附件+lens 快照+RELEASE-NOTES。"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cbb-v2"))
from cbb2 import lens  # noqa: E402

tree = ROOT / "cbb-pipeline-skill" / "cbb-pipeline"
store = ROOT / "迷深实战-本体库"

chapter = """

---

## v3.1 差异章（2026-09-29 · 含 v3.0 差异章欠账补记）

> v3.0 发布时 G05 差异章欠账未随包，本 v3.1 章合并补记。本差异章即 grep 证据（G05 判据）。

### v3.0 → v3.1 变更（判卷战役实证沉淀）

1. **判卷契约刻度**：提示词条款=行为学仪器参数——「从严倾向」条款+同向判例堆叠实测可压掉考官支持率 2/3（同批 A/B：v1 67.5% vs v2 22.5%，已知答案植株 8/8→0/8）。契约 v2.2（=v1 极简+claim 元数据防误读行）经五十件验证轮植株捕获 8/8 捕获门 PASS，**已验证待采纳**（量产默认仍 v2，切换由库属主裁决）。校准方法固化为 PT-026（同批 A/B 定位→植株考试定档→验证轮封顶）。
2. **编制 2/3+抽检审计**：主链判词=GLM×DEEPSEEK 双票一致（B13 need=2 双 support，against=0）；第三方考官退出主链，仅承担抽检审计（分歧带第三方支持率 45% 实测入巡检基线）。
3. **判卷面卫生双整改**：掺植株**随机穿插**全卷（替代末尾堆放——末堆对已判段零监控力）；期望字段（expected/is_plant）从判卷面剥离至特权映射文件，考官盲评。
4. **植株考试双角色**：考官上岗门（≥5/6）+ 提示词/契约变更定档——换考官、换契约、换端点一律先考试。
5. **令牌治理**：考官 key 注册表回读（ops.secret_from_registry，值不落盘），槽位 key 优先于平台默认 env（防默认键劫持新槽位发错端点）。
6. **新防线**：P-030（工作流修订后 world.run 按 argv 身份复放——改脚本必改 argv 轮次 tag）、P-031（修订不清理旧子进程→按代际标识清点格杀）、P-032（生成器内条件链禁令）。
"""

p = tree / "全流程说明书.md"
s = p.read_text(encoding="utf-8")
p.write_text(s + chapter, encoding="utf-8")
print("1 说明书差异章 appended")

p2 = tree / "SKILL.md"
s2 = p2.read_text(encoding="utf-8")
old = "v3.0 = 全量重构（失效记账制/契约v3/写入决策树/票数晋升，2026-09-27）"
assert old in s2, "SKILL 谱系锚未找到"
p2.write_text(s2.replace(old, old + "；v3.1 = 判卷契约刻度+严格双票编制(2/3)+第三方抽检审计通道（2026-09-29）"), encoding="utf-8")
print("2 SKILL 谱系 +v3.1")

p3 = tree / "README.md"
s3 = p3.read_text(encoding="utf-8")
anchor = "```mermaid\nflowchart TB"
assert anchor in s3, "README 锚未找到"
p3.write_text(s3.replace(
    anchor,
    "**当前版本 v3.1**（2026-09-29：判卷契约刻度+严格双票编制+第三方抽检审计；差异章见 全流程说明书.md v3.1 章）\n\n" + anchor, 1),
    encoding="utf-8")
print("3 README 版本行 +v3.1")

shutil.copyfile(ROOT / "考官契约.md", tree / "references" / "考官契约-20260929.md")
print("4 考官契约附件 → references/考官契约-20260929.md")

snap = lens.full_report(store)
(tree / "references" / "库况快照-v3.1.json").write_text(
    json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
print("5 lens 库况快照 → references/库况快照-v3.1.json:", json.dumps({k: snap[k] for k in snap if k != 'invalidation_chain'}, ensure_ascii=False)[:200])

notes = """# RELEASE-NOTES v3.1（2026-09-29）

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
"""
(tree / "RELEASE-NOTES-v3.1.md").write_text(notes, encoding="utf-8")
print("6 RELEASE-NOTES-v3.1.md 写入")
