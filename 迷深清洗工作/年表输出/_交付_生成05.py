# -*- coding: utf-8 -*-
"""交付④b 全量 Word(1568 条事件全量) + 伏笔链 + 反转节点
结构:
- 封面/说明
- 目录页(书签超链接): 伏笔链总览 / 反转轴速查 / 五层 × 子时段
- 正文:
  一、伏笔链总览(89 链全列: topic + 伏笔端→回收端 + status + notes)
  二、反转轴速查(按轴列 181 节点: before→after)
  三、五层全量事件: 每子时段下 1568 条完整事件(标题/时间/锚点/类型/置信度/人物/地点/描述全文/台词)
     每条事件追加伏笔链参与标注(FC)与反转节点标注(RV)
"""
import os, json, re
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
DELIVER = os.path.join(BASE, "交付四件套")
fl = json.load(open(os.path.join(BASE, "final_output", "full_event_list.json"), encoding="utf-8"))
agg = json.load(open(os.path.join(DELIVER, "_agg.json"), encoding="utf-8"))
fc = json.load(open(os.path.join(BASE, "final_output", "foreshadow_chains.json"), encoding="utf-8"))
rn = json.load(open(os.path.join(BASE, "final_output", "reversal_nodes.json"), encoding="utf-8"))
by_id = {e["event_id"]: e for e in fl}

# 索引
fs_map, cb_map = {}, {}
for c in fc:
    if "chain_id" not in c: continue
    fs_map.setdefault(c["foreshadow_event_id"], []).append(c)
    cb_map.setdefault(c["callback_event_id"], []).append(c)
rv_map = {}
for n in rn:
    if "event_id" not in n: continue
    rv_map.setdefault(n["event_id"], []).append(n)

LAYER_META = {
    "T0": ("段0 · 原世界(现代日本)", "58 事件 ｜ 原生家庭·英才教育·妹妹病倒·病床前救赎"),
    "T1": ("段1 · 千年前·战争期(T-1000~T-995)", "123 事件 ｜ 召唤·圣人救世·阳滝异化·始祖复仇"),
    "T2": ("段2 · 千年前·建造期(T-995~T-990)", "119 事件 ｜ 十理就位·诺斯菲诞生·形式婚姻·涡波休眠"),
    "T4": ("段3 · 千年间(T-990~T-0)", "45 事件 ｜ 拉丝缇娅拉培育·守护者就位·攻略至23层"),
    "T3": ("段4 · 千年后主线(T-0~终章)", "1223 事件 ｜ 一层苏醒·逐层攻略·守护者战·终局"),
}
AXIS_NAME = {0: "通用/未归轴", 1: "涡波=千年前迷宫/莱文教始祖", 2: "迷宫本质=魔力污水处理厂", 3: "诺斯菲=涡波之女/妻·首个魔石人类",
             4: "缇亚=使徒西斯转世(独立个体)", 5: "技能???=使徒植入木马", 6: "阳滝=100层水之理盗窃者"}

def set_ea(run, ea="微软雅黑"):
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    rf.set(qn("w:eastAsia"), ea)

def add_bookmark(paragraph, bookmark_id, bookmark_name):
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bookmark_id)); start.set(qn("w:name"), bookmark_name)
    paragraph._p.append(start)
    end = OxmlElement("w:bookmarkEnd"); end.set(qn("w:id"), str(bookmark_id))
    paragraph._p.append(end)

def add_internal_hyperlink(paragraph, bookmark_name, text, font_size=None, bold=False, color="0563C1"):
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("w:anchor"), bookmark_name)
    new_run = OxmlElement("w:r"); rPr = OxmlElement("w:rPr")
    if font_size:
        sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(int(font_size * 2))); rPr.append(sz)
    if bold:
        b = OxmlElement("w:b"); rPr.append(b)
    col = OxmlElement("w:color"); col.set(qn("w:val"), color); rPr.append(col)
    u = OxmlElement("w:u"); u.set(qn("w:val"), "single"); rPr.append(u)
    new_run.append(rPr)
    t = OxmlElement("w:t"); t.text = text; new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)

def p_bullet_char(p, txt, color=None, bold=False):
    r = p.add_run(txt)
    r.bold = bold
    if color: r.font.color.rgb = RGBColor.from_string(color)
    set_ea(r)
    return r

doc = Document()
style = doc.styles["Normal"]
style.font.name = "Calibri"; style.font.size = Pt(9.5)
style._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

# ── 封面 ──
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("《以异世界迷宫最深处为目标》(web版)"); r.font.size = Pt(20); r.bold = True; set_ea(r)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("事件年表 · 全量版(含伏笔链与反转节点)"); r.font.size = Pt(16); r.bold = True; set_ea(r)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("1568 条事件全量 ｜ 89 条伏笔链 ｜ 181 个反转节点 ｜ 千年双时间线(时间轴序: 原世界→战争期→建造期→千年间→主线)")
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("数据源: final_output/full_event_list.json + foreshadow_chains.json + reversal_nodes.json ｜ 生成 2026-09-01")
doc.add_page_break()

# ── 目录 ──
doc.add_heading("目录(点击跳转)", level=1)
bm_seq = [10000]
def next_bm():
    bm_seq[0] += 1
    return bm_seq[0]

toc = []  # (level, label, bookmark)
toc.append((1, "一、伏笔链总览(89 链)", "SEC_FS"))
toc.append((1, "二、反转轴速查(181 节点)", "SEC_RV"))
for L in ("T0", "T1", "T2", "T4", "T3"):
    name, meta = LAYER_META[L]
    toc.append((1, name, f"SEC_{L}"))
    for seg in agg["layers"][L]:
        if L == "T3":
            toc.append((2, f"{seg['seg_name']} · {seg['seg_desc']}({len(seg['event_ids'])}条)", f"SEG_{L}_{seg['seg_name'][:12]}"))
        else:
            toc.append((2, f"{seg['seg_name']}({len(seg['event_ids'])}条)", f"SEG_{L}_{seg['seg_name'][:12]}"))
        if L == "T3":
            # 主线小目录: 章下话级节(方案第5项)
            from _交付_节映射 import chapter_sec_plan
            for sec in chapter_sec_plan(seg["seg_name"], seg["event_ids"]):
                toc.append((3, f"　└ {sec['sec_name']}({len(sec['event_ids'])}条)",
                            f"SEC3_{L}_{seg['seg_name'][:8]}_{sec['sec_name'][:12]}"))
for lvl, label, bk in toc:
    p = doc.add_paragraph()
    if lvl == 2: p.paragraph_format.left_indent = Cm(0.8)
    if lvl == 3: p.paragraph_format.left_indent = Cm(1.6)
    add_internal_hyperlink(p, bk, label, font_size=(11 if lvl == 1 else (9.5 if lvl == 2 else 8.5)), bold=(lvl == 1))
doc.add_page_break()

# ── 一、伏笔链总览 ──
h = doc.add_heading("一、伏笔链总览(89 链)", level=1); add_bookmark(h, next_bm(), "SEC_FS")
doc.add_paragraph("伏笔→回收闭环;status: closed=已回收, open=悬空。FC 编号可反查正文事件条目中的 ▶ 标注。")
open_n = sum(1 for c in fc if c.get("status") == "open")
doc.add_paragraph(f"合计 {len(fc)} 链: closed {len(fc)-open_n} ｜ open {open_n}")
for c in fc:
    if "chain_id" not in c: continue
    p = doc.add_paragraph()
    r = p.add_run(f"{c['chain_id']} ｜ {c.get('topic','')} ｜ {c.get('status','')}")
    r.bold = True; set_ea(r)
    if c.get("status") == "open":
        r.font.color.rgb = RGBColor.from_string("C00000")
    p2 = doc.add_paragraph(); p2.paragraph_format.left_indent = Cm(0.5)
    p2.add_run(f"伏笔: {c['foreshadow_event_id']}《{c.get('foreshadow_title','')}』 → 回收: {c['callback_event_id']}《{c.get('callback_title','')}》(锚点 {c.get('story_anchor_of_callback','')})")
    if c.get("notes"):
        p3 = doc.add_paragraph(); p3.paragraph_format.left_indent = Cm(0.5)
        p3.add_run("注: " + c["notes"])
doc.add_page_break()

# ── 二、反转轴速查 ──
h = doc.add_heading("二、反转轴速查(181 节点)", level=1); add_bookmark(h, next_bm(), "SEC_RV")
doc.add_paragraph("每条: node_id ｜ event_id《title》｜ axis ｜ before→after。正文事件条目中另有 ⚡ 标注。")
by_axis = {}
for n in rn:
    if "event_id" not in n: continue
    by_axis.setdefault(n.get("axis", 0), []).append(n)
for ax in sorted(by_axis, key=lambda a: (a == 0, a)):
    axname = AXIS_NAME.get(ax, str(ax))
    h2 = doc.add_heading(f"轴{ax} · {axname}({len(by_axis[ax])} 节点)", level=2)
    for n in by_axis[ax]:
        p = doc.add_paragraph(style="List Bullet")
        r = p.add_run(f"{n.get('node_id','')} ｜ {n['event_id']}《{n.get('title','')}》｜ {n.get('confidence','')}")
        r.bold = True; set_ea(r)
        p2 = doc.add_paragraph(); p2.paragraph_format.left_indent = Cm(0.6)
        p2.add_run(f"认知: {n.get('before_belief','')}")
        p3 = doc.add_paragraph(); p3.paragraph_format.left_indent = Cm(0.6)
        r3 = p3.add_run(f"真相: {n.get('after_truth','')}"); r3.font.color.rgb = RGBColor.from_string("C00000")
doc.add_page_break()

# ── 三、全量事件 ──
def safe_str(v):
    if isinstance(v, list):
        return "、".join(str(x) for x in v)
    return str(v) if v is not None else ""

def add_event_entry(e, bm_start):
    """返回该事件消耗的书签数;每条事件不加书签(全量书签过多),伏笔端可加内部链接回总览? 不,保持简单"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    r = p.add_run(f"{e['event_id']} ｜ {e.get('title','')}")
    r.bold = True; set_ea(r); r.font.size = Pt(10.5)
    # 标签行
    tags = []
    if e["event_id"] in fs_map: tags.append("▶伏笔端")
    if e["event_id"] in cb_map: tags.append("◀回收端")
    if e["event_id"] in rv_map: tags.append("⚡反转")
    if tags:
        tr = p.add_run("  [" + " ".join(tags) + "]")
        tr.font.color.rgb = RGBColor.from_string("C00000"); tr.bold = True; set_ea(tr)
    # meta 行
    pm = doc.add_paragraph()
    pm.paragraph_format.left_indent = Cm(0.3)
    rm = pm.add_run(f"时间: {e.get('event_time','')} ｜ 类型: {e.get('event_type','')} ｜ 置信度: {e.get('confidence','')}")
    rm.font.size = Pt(8.5); rm.font.color.rgb = RGBColor.from_string("808080"); set_ea(rm)
    pm2 = doc.add_paragraph()
    pm2.paragraph_format.left_indent = Cm(0.3)
    rm2 = pm2.add_run(f"锚点: {e.get('story_anchor','')}")
    rm2.font.size = Pt(8.5); rm2.font.color.rgb = RGBColor.from_string("808080"); set_ea(rm2)
    # 描述全文
    pd = doc.add_paragraph()
    pd.paragraph_format.left_indent = Cm(0.3)
    pd.add_run("描述: " + safe_str(e.get("description")))
    # quotes
    qs = e.get("quotes") or []
    if qs:
        pq = doc.add_paragraph(); pq.paragraph_format.left_indent = Cm(0.3)
        pq.add_run("台词: ")
        for i, q in enumerate(qs):
            if i: pq.add_run(" ｜ ")
            pq.add_run("「" + safe_str(q).strip('「」') + "」")
    # 人物/地点
    pm3 = doc.add_paragraph()
    pm3.paragraph_format.left_indent = Cm(0.3)
    chs = safe_str(e.get("characters")); loc = safe_str(e.get("location"))
    if chs: pm3.add_run("人物: " + chs + (" ｜ " if loc else ""))
    if loc: pm3.add_run("地点: " + loc)
    # 伏笔链标注
    for c in fs_map.get(e["event_id"], []):
        pv = doc.add_paragraph(); pv.paragraph_format.left_indent = Cm(0.3)
        rv = pv.add_run(f"▶ 伏笔: {c['chain_id']}《{c.get('topic','')}》→ 回收于 {c['callback_event_id']}《{c.get('callback_title','')}》({c.get('status','')})")
        rv.font.color.rgb = RGBColor.from_string("BF8F00"); set_ea(rv)
        if c.get("notes"):
            pvn = doc.add_paragraph(); pvn.paragraph_format.left_indent = Cm(0.3)
            pvn.add_run("　注: " + c["notes"])
    for c in cb_map.get(e["event_id"], []):
        pc = doc.add_paragraph(); pc.paragraph_format.left_indent = Cm(0.3)
        rc = pc.add_run(f"◀ 回收: {c['chain_id']}《{c.get('topic','')}》← 伏笔起于 {c['foreshadow_event_id']}《{c.get('foreshadow_title','')}》")
        rc.font.color.rgb = RGBColor.from_string("2E75B6"); set_ea(rc)
    # 反转标注
    for n in rv_map.get(e["event_id"], []):
        pn = doc.add_paragraph(); pn.paragraph_format.left_indent = Cm(0.3)
        rn1 = pn.add_run(f"⚡ 反转 {n.get('node_id','')} 轴{n.get('axis',0)}: {n.get('before_belief','')} → {n.get('after_truth','')}")
        rn1.font.color.rgb = RGBColor.from_string("C00000"); set_ea(rn1)
        if n.get("notes"):
            pnn = doc.add_paragraph(); pnn.paragraph_format.left_indent = Cm(0.3)
            pnn.add_run("　注: " + n["notes"])

for L in ("T0", "T1", "T2", "T4", "T3"):
    name, meta = LAYER_META[L]
    h = doc.add_heading(name, level=1); add_bookmark(h, next_bm(), f"SEC_{L}")
    doc.add_paragraph(meta)
    for seg in agg["layers"][L]:
        segbk = f"SEG_{L}_{seg['seg_name'][:12]}"
        if L == "T3":
            # 主线章标题: 章名+剧情名(小目录可识别)
            h2 = doc.add_heading(f"{seg['seg_name']} · {seg['seg_desc']}({len(seg['event_ids'])}条)", level=2)
        else:
            h2 = doc.add_heading(f"{seg['seg_name']}({len(seg['event_ids'])}条)", level=2)
        add_bookmark(h2, next_bm(), segbk)
        if L == "T3":
            # 主线小目录: 章内按话组分节(方案第5项)
            from _交付_节映射 import chapter_sec_plan
            for sec in chapter_sec_plan(seg["seg_name"], seg["event_ids"]):
                h3 = doc.add_heading(f"{sec['sec_name']}({len(sec['event_ids'])}条)", level=3)
                add_bookmark(h3, next_bm(), f"SEC3_{L}_{seg['seg_name'][:8]}_{sec['sec_name'][:12]}")
                for i in sec["event_ids"]:
                    add_event_entry(by_id[i], None)
        else:
            for i in seg["event_ids"]:
                add_event_entry(by_id[i], None)
    doc.add_page_break()

outp = os.path.join(DELIVER, "05_事件年表_全量_含伏笔_v5.docx")
doc.save(outp)
print("saved:", outp, os.path.getsize(outp) // 1024, "KB")
