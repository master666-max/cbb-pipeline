# -*- coding: utf-8 -*-
"""verify_gold.py — 金标三轮自审机械核查
用法: py -X utf8 verify_gold.py  → 输出 结果/gold-verify-report.md
轮1 逐项核对: 每个实体/关系的证据行原文对照（名字是否在行内、行号是否越界）
轮2 漏标扫描: 『』《》【】引号术语清单（未覆盖者标出）+ 每实体的全文提及行 + 数字行清单
轮3 语料对账: 按行号重切语料并 sha256 对比切样文件 + JSON 合法性 + 计数
"""
import json, os, re, hashlib

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
CORPUS = r"D:\zcode专用！！！！危险！！！！！！！！！\语料分析\corpus\clean_full.txt"
GOLDS = {"excerpt1": (5516, 5700), "excerpt2": (14388, 14560),
         "excerpt3": (47485, 47688), "excerpt4": (1, 26)}

corpus = open(CORPUS, encoding="utf-8").read().splitlines()
report = ["# 金标三轮自审核查报告（机械部分）\n"]

def norm(s):
    return re.sub(r"[\s『』「」·•]+", "", s or "")

for name, (a, b) in GOLDS.items():
    gpath = os.path.join(ROOT, "金标", f"gold-{name}.json")
    epath = os.path.join(ROOT, "材料", f"{name}-" + ("CHAPTER0014.md" if name == "excerpt1" else
                          "CHAPTER0038.md" if name == "excerpt2" else
                          "CHAPTER0114.md" if name == "excerpt3" else "CHAPTER0001-序章型.md"))
    gold = json.load(open(gpath, encoding="utf-8"))
    ext_lines = open(epath, encoding="utf-8").read().splitlines()
    corpus_slice = corpus[a - 1: b]
    report.append(f"\n---\n## {name}（语料行 {a}-{b}）\n")
    # ---------- 轮3 语料对账 ----------
    sha_ext = hashlib.sha256(("\n".join(ext_lines) + "\n").encode("utf-8")).hexdigest()[:16]
    sha_cor = hashlib.sha256(("\n".join(corpus_slice) + "\n").encode("utf-8")).hexdigest()[:16]
    ok = sha_ext == sha_cor
    report.append(f"### 轮3 语料对账\n- 切样文件 sha16={sha_ext} | 语料重切 sha16={sha_cor} | {'PASS' if ok else '**FAIL 切样与语料不一致**'}")
    report.append(f"- 计数: 实体 {len(gold['entities'])} | 关系 {len(gold['edges'])} | 时间 {len(gold['time_expressions'])} | 声明口径: {gold.get('annotation_rules_note', '')[:0]}{gold.get('annotation_rules', {}).get('计数口径', '见rules') if isinstance(gold.get('annotation_rules'), dict) else '见note'}")
    # ---------- 轮1 逐项核对 ----------
    report.append(f"\n### 轮1 逐项取证\n")
    maxline = len(ext_lines)
    for e in gold["entities"]:
        lines = re.findall(r"L(\d+)", e.get("evidence", ""))
        bad = [l for l in lines if int(l) < 1 or int(l) > maxline]
        texts = [f"L{l}:{ext_lines[int(l)-1][:50]}" for l in lines[:2] if 1 <= int(l) <= maxline]
        namehit = norm(e["name"]) in norm("".join(ext_lines[int(l)-1] for l in lines if 1 <= int(l) <= maxline)) if lines else None
        report.append(f"- 实体 `{e['name']}` 证据 {e.get('evidence')} {'⚠越界'+str(bad) if bad else ''} | 行文: {' || '.join(texts)}")
    for ed in gold["edges"]:
        lines = re.findall(r"L(\d+)", ed.get("evidence", ""))
        texts = [f"L{l}:{ext_lines[int(l)-1][:50]}" for l in lines[:1] if 1 <= int(l) <= maxline]
        report.append(f"- 关系 `{ed['source']} -{ed['relation']}-> {ed['target']}` {ed.get('evidence')} | 行文: {' || '.join(texts)}")
    # ---------- 轮2 漏标扫描 ----------
    report.append(f"\n### 轮2 漏标扫描\n")
    text_all = "\n".join(ext_lines)
    quoted = {}
    for m in re.finditer(r"[『《【]([^』》】]{1,20})[』》】]", text_all):
        quoted[m.group(1)] = quoted.get(m.group(1), 0) + 1
    covered = " | ".join(norm(e["name"]) for e in gold["entities"])
    uncovered = {q: c for q, c in quoted.items() if norm(q) not in covered}
    report.append(f"- 引号术语总览: {quoted}")
    report.append(f"- **未被金标实体覆盖的引号术语: {uncovered if uncovered else '无'}**")
    # 每实体提及行
    for e in gold["entities"]:
        names = [norm(e["name"])] + [norm(re.sub(r"\(.*?\)", "", a)) for a in e.get("aliases", [])]
        hits = [str(i + 1) for i, ln in enumerate(ext_lines) if any(n and n in norm(ln) for n in names)]
        report.append(f"- `{e['name']}` 提及行: {','.join(hits) if hits else '（别名形式出现，未见字面）'}")
    # 数字行（时间/等级审计用）
    numlines = [f"L{i+1}:{ln[:40]}" for i, ln in enumerate(ext_lines) if re.search(r"\d+", ln)][:12]
    report.append(f"- 含数字行(前12, 时间/等级审计用): {numlines}")

out = os.path.join(ROOT, "结果", "gold-verify-report.md")
open(out, "w", encoding="utf-8").write("\n".join(report))
print("written:", out, "| sections:", len(report))
