# -*- coding: utf-8 -*-
"""parallel_compare.py — CBB 产出 vs 老迷深资料库（37 复核世界书）平行对比
只读。输出：花名册三方对账 + 关键别名交叉核验。
"""
import glob, io, json, os, re

LIB = r"D:\zcode专用！！！！危险！！！！！！！！！\正典库构建系统\迷深实战-本体库"
OLD = r"D:\zcode专用！！！！危险！！！！！！！！！\迷深清洗工作\迷深大酒馆v1.02\世界书JSON"

# ── 老库：37 本角色专属世界书 ──
old_names = set()
for p in glob.glob(os.path.join(OLD, "角色专属世界书_*.json")):
    n = os.path.basename(p).replace("角色专属世界书_", "").replace(".json", "")
    old_names.add(n)
print(f"[老库] 角色书 {len(old_names)} 本")

# ── CBB：character 库名册 + 全库设定名册 ──
cbb_chars = {}
for p in glob.glob(os.path.join(LIB, "libraries", "character", "provisional", "*.json")):
    try: r = json.load(io.open(p, encoding="utf-8"))
    except Exception: continue
    cn = r.get("canonical") or {}
    nm = cn.get("name") if isinstance(cn, dict) else None
    if not nm: continue
    chs = set()
    ev = r.get("evidence") or []
    if isinstance(ev, dict): ev = [ev]
    for e in ev:
        c = e.get("chapter")
        if c is not None:
            try: chs.add(int(c))
            except Exception: pass
    cbb_chars.setdefault(nm, set()).update(chs)
print(f"[CBB] character 库唯一 canonical {len(cbb_chars)} 个")

# ── 三方对账（exact + 中点归一 + 包含式） ──
def norm(s): return s.replace("・", "·").replace("　", "").strip()
old_n = {norm(x) for x in old_names}
cbb_n = {norm(x): x for x in cbb_chars}
inter = set(cbb_n) & old_n
only_old = sorted(old_n - set(cbb_n))
only_cbb = sorted(set(cbb_n) - old_n)
print(f"[对账] 重合={len(inter)} | 只有老库={len(only_old)} | 只有CBB={len(only_cbb)}")
print("只有老库样例:", "、".join(only_old[:12]))
# 只有 CBB：按最晚章排序，晚期章=预期（CBB 才跑到 238 位但老库全书都有? 老库全书37角色主要为前半）——列出前 12
oc = sorted(only_cbb, key=lambda n: -max(cbb_chars[cbb_n[n]] or {0}))
print("只有CBB样例(按最晚章降序):")
for n in oc[:12]:
    mx = max(cbb_chars[cbb_n[n]] or {0}); mn = min(cbb_chars[cbb_n[n]] or {0})
    print(f"   {cbb_n[n]}  ch{mn}~ch{mx}")

# ── 关键别名交叉核验（老库文件名 vs CBB 别名账/名册 的已知对应） ──
al = [json.loads(l) for l in io.open(os.path.join(LIB, "aliases.jsonl"), encoding="utf-8").read().strip().splitlines() if l.strip()]
al_names = [(a.get("alias") if isinstance(a.get("alias"), str) else str(a.get("alias"))) or "" for a in al]
probes = ["佩露修娜", "缇亚", "玛利亚", "斯诺", "莉帕", "帕林库洛", "诺文", "莱纳", "涡波"]
print("[交叉] 关键人物: 老库书存在? / CBB名册存在? / CBB别名账命中数")
for pr in probes:
    in_old = any(pr in x for x in old_names)
    in_cbb = any(pr in x for x in cbb_chars)
    hits = sum(1 for a in al_names if pr in a)
    print(f"   {pr}: 老库={'有' if in_old else '无'} CBB={'有' if in_cbb else '无'} 别名账命中={hits}")
