# -*- coding: utf-8 -*-
"""portability_scan.py — 跨机通用性体检：扫新工具件的硬编码面。"""
import pathlib
import re

HERE = pathlib.Path(r"D:/zcode专用！！！！危险！！！！！！！！！/正典库构建系统/cbb/tools")
targets = ["lightrag_live.py", "lightrag_bridge.py", "lightrag_export.py", "lightrag_delta_sync.py",
           "graphiti_ingest.py", "graphiti_spike.py", "graphiti_dump.py", "graph_chain.py",
           "graph_audit.py", "web_supplement.py", "检索层.py", "环境自检.py", "neo4j_export.py",
           "build_evidence_index.py", "批次自检.py", "矛盾对生成.py", "连续性巡检.py", "诊断员.py",
           "检索层.py", "词表.py", "失效宣告.py", "抽样排序.py", "匹配建议.py", "捕获再捕获.py",
           "embedding_dedup" ]
targets = sorted(set(t for t in targets if (HERE / t).exists()))
pats = {
    "绝对盘符": re.compile("[\"'][A-Za-z]:[/\\\\]"),
    "实例名": re.compile("迷深实战"),
    "本地端点": re.compile(r"https?://(127\.0\.0\.1|localhost):\d+"),
    "模型名": re.compile("(deepseek-chat|tifa-deepsex|qwen3-embedding-8b|qwen3-reranker|text-embedding-qwen3)"),
    "winreg": re.compile("winreg"),
}
rows = []
for t in targets:
    s = (HERE / t).read_text(encoding="utf-8")
    hits = {name: len(pat.findall(s)) for name, pat in pats.items() if pat.search(s)}
    if hits:
        rows.append((t, hits))
for t, hits in rows:
    print(f"{t:26s} {hits}")
print(f"\n共 {len(rows)}/{len(targets)} 件含硬编码面（盘符=跨机必炸；端点/模型=建议 env 化；实例名=部署布局假设）")
