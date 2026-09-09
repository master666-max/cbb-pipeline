# -*- coding: utf-8 -*-
"""论文实现核对：总表 vs REGISTRY vs 安装器代码 vs bodies 内容体。"""
import re, json, io, importlib.util
from pathlib import Path

ROOT = Path(r"D:\zcode专用！！！！危险！！！！！！！！！")
SRC = ROOT / "library-bootstrap-v3.0" / "bootstrap_v3.py"
TABLE = ROOT / "引用论文总表.md"
BODIES = ROOT / "library-bootstrap-v3.0" / "bootstrap_data" / "bodies.json"

spec = importlib.util.spec_from_file_location("bsv3", SRC)
bs = importlib.util.module_from_spec(spec); spec.loader.exec_module(bs)

table = TABLE.read_text(encoding="utf-8")
code = SRC.read_text(encoding="utf-8")
bodies = json.loads(BODIES.read_text(encoding="utf-8"))

# 总表条目
tbl_entries = dict(re.findall(r"^### (A\d+) — (.+)$", table, re.M))
tbl_blocks = {m.group(1): m.group(0) for m in re.finditer(r"^### (A\d+) — .+?(?=^### |\Z)", table, re.M | re.S)}
print("总表正文条目数:", len(tbl_entries))
print("REGISTRY 条目数:", len(bs.REGISTRY))
miss_in_table = sorted(set(bs.REGISTRY) - set(tbl_entries), key=lambda x: int(x[1:]))
miss_in_reg = sorted(set(tbl_entries) - set(bs.REGISTRY), key=lambda x: int(x[1:]))
print("REGISTRY 有而总表无正文:", miss_in_table)
print("总表有而 REGISTRY 无:", miss_in_reg)

# arXiv 编号一致性
print("\n--- arXiv 编号/年份 总表 vs REGISTRY ---")
for aid in sorted(tbl_entries, key=lambda x: int(x[1:])):
    m = re.search(r"arXiv:(\d{4}\.\d{4,5})", tbl_blocks[aid])
    rid = bs.REGISTRY.get(aid, {}).get("arxiv_id")
    if m and rid and m.group(1) != rid:
        print(f"  [不一致] {aid}: 表={m.group(1)} REGISTRY={rid}")
print("(无输出=全部一致)")

# 标题形态差异（REGISTRY 标题 vs 总表标题主名）
print("\n--- 标题形态差异（经典/doc 型） ---")
for aid in sorted(tbl_entries, key=lambda x: int(x[1:])):
    t_title = tbl_entries[aid]
    r_title = bs.REGISTRY.get(aid, {}).get("title", "")
    # 粗略：REGISTRY 标题关键英文词是否出现在总表标题
    rw = set(re.findall(r"[A-Za-z]{4,}", r_title))
    tw = set(re.findall(r"[A-Za-z]{4,}", t_title))
    if rw and not (rw & tw):
        print(f"  [形态不同] {aid}: 表='{t_title[:70]}' | REG='{r_title[:70]}'")

# bodies 全文聚合
body_texts = {}
for slot, items in bodies.items():
    if not isinstance(items, dict): continue
    for k, v in items.items():
        body_texts[f"{slot}/{k}"] = v.get("body", "")
print("\nbodies 内容体文件数:", len(body_texts))

def grep_all(keywords):
    """返回 (代码命中行, bodies 命中文件列表)"""
    ch = []
    for i, l in enumerate(code.splitlines(), 1):
        if any(k.lower() in l.lower() for k in keywords):
            ch.append((i, l.strip()[:90]))
    bh = [k for k, t in body_texts.items() if any(kw.lower() in t.lower() for kw in keywords)]
    return ch, bh

# 每篇论文的机制证据探针
probes = {
 "A1":  (["分页", "虚拟内存", "自编辑", "中断"], None),
 "A14": (["热温冷", "热度", "逐出", "页调度", "hot_budget"], None),
 "A16": (["MemCube", "激活记忆", "参数记忆", "版本元数据"], None),
 "A18": (["六类", "Core", "Episodic", "Procedural", "Knowledge Vault", "Vault"], None),
 "A12": (["去重", "合并", "整合", "增量更新"], None),
 "A27": (["keywords", "属性标注", "语义标签"], None),
 "A20": (["LightMem", "感官", "睡眠时更新", "三级记忆"], None),
 "A6":  (["Ebbinghaus", "艾宾浩斯", "遗忘曲线", "锦标赛", "半衰期"], None),
 "A8":  (["PageRank", "PPR", "扩散激活", "Personalized"], None),
 "A9":  (["HippoRAG 2", "非参数持续", "段落级"], None),
 "A11": (["双时态", "superseded", "t_invalid", "失效打标"], None),
 "A15": (["G-Memory", "多 agent 触发", "雷达触发", "m-radar"], None),
 "A17": (["固定长度记忆覆写", "长文触发", "分段读取"], None),
 "A2":  (["反思", "importance_accum", "reflect", "recency"], None),
 "A3":  (["Reflexion", "批评家", "critic", "根因"], None),
 "A23": (["议会", "四席位", "Debate", "辩论", "心智议会"], None),
 "A5":  (["Voyager", "技能库", "技能固化", "自动课程"], None),
 "A21": (["objective hacking", "豁免", "不可见", "MUTATION", "黑名单"], None),
 "A22": (["自进化", "Self-Evolving", "分类学"], None),
 "A19": (["ADD", "UPDATE", "DELETE", "NOOP"], None),
 "A13": (["Sleep-time", "睡眠时计算", "空闲期", "sleep"], None),
 "A29": (["互补学习", "CLS", "双速率", "海马"], None),
 "A30": (["GWT", "全局工作空间", "广播总线", "广播"], None),
 "A31": (["躯体标记", "Somatic", "valence", "arousal", "certainty", "stakes"], None),
 "A32": (["DMN", "默认模式", "Default Mode"], None),
 "A33": (["心境一致", "mood-congruent", "情绪唤起", "唤起度", "检索重排"], None),
 "A25": (["Context Rot", "预算", "200", "150 行", "常驻"], None),
 "A4":  (["CoALA", "Cognitive Architectures"], None),
 "A10": (["A-MEM", "agentic memory", "m-evolve", "演化"], None),
}
print("\n--- 机制证据：代码层(C) / 内容体层(B) ---")
for aid, (kws, _) in probes.items():
    ch, bh = grep_all(kws)
    code_hits = sorted({i for i, _ in ch})[:6]
    print(f"{aid:4s} 代码命中行 {len(ch):3d} {str(code_hits):40s} 内容体文件 {len(bh):2d} {bh[:3]}")
