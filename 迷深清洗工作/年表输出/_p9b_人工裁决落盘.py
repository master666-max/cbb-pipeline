# -*- coding: utf-8 -*-
"""人工裁决落盘(2026-09-01,用户确认):
A2/P9-03 修正(使徒西斯≠始祖涡波等五条);C2 轴4确认;其余按建议执行。
"""
import os, json

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
OUT = os.path.join(BASE, "final_output")

def load(p):
    return json.load(open(p, encoding="utf-8"))

def save(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

# ═══════════ 1. conflict_report: P9-02/03/04 修正 ═══════════
cr = load(os.path.join(OUT, "conflict_report.json"))
for it in cr["items"]:
    if it["issue_id"] == "P9-03":
        it["topic"] = "使徒体系(修正:使徒西斯≠始祖涡波)"
        it["evidence"] = "用户指出原推断错误并给出 docx 参考;原文 grep 证实:①使徒西斯=金发成年女性、独立存在(第五章L7074四人同框『金发的女性是使徒西斯…戴着假面的少年则是始祖涡波』;T1-0010立契两人当面;T1-0122涡波向西斯复仇被捕获;第六章L5658阳滝因西斯过失化怪物)。②缇亚=使徒西斯转世承体/容器(第四章L10941『使徒西斯也利用缇亚的身体复活了』;第三章L10268迪亚布罗·西斯)。③使徒勒伽西=千年前第三位使徒(第7-2章L2415;第五章L4955欺骗建迷宫),帕林库洛·勒伽西为其千年承体(第四章L13238双重记忆)。④西娅·勒迦希=帕林库洛侄女(第四章L6448;第7-2章L7093携缇达魔石),于第120次试炼继承暗之理。⑤『120层暗之理』=第120次试炼(第一百二十之试炼),舞台=迷宫100层(第十章L15766)。"
        it["decision"] = "①缇娅(迪亚布罗·西斯)=千年前使徒西斯的转世承体/容器(反转轴4,保留);②使徒西斯=千年前三使徒之一(金发女使徒),与始祖涡波为契约盟友→后因阳滝异化成仇敌——删除原『使徒西斯=始祖涡波千年前身份』错误推断;③使徒勒伽西=第三位使徒(茶发少年),始祖涡波建迷宫时的欺骗者,帕林库洛·勒伽西(天上七骑士第7位)为其千年承体;④西娅·勒迦希=帕林库洛的侄女,千年后携缇达魔石、于第120之试炼(100层)继承暗之理;⑤『120层』=第120次试炼,非实体120层迷宫。"
        it["confidence"] = "原文明确"
        it["resolved"] = True
        it["data_refs"] = ["T1-0010", "T1-0122", "T3-0411", "第五章L7074/L4953-4955", "第四章L10941/L6448/L13238", "第二章L15100/L17640", "第7-2章L2191/L2415/L7093", "第十章L15766", "第八章L13200", "第九章L4365"]
    elif it["issue_id"] == "P9-02":
        it["decision"] = "帕林库洛 = 吞噬/继承缇达暗之理的继任者(第二章L17640『一口吞下了缇达的魔石』);缇达→帕林库洛→(第120次试炼)西娅·勒迦希的暗之理传承链。P7 已标『缇达→帕林库洛』身份链反转。暗之理第120次试炼舞台=100层,西娅·勒迦希(帕林库洛侄女)为继承者,与使徒勒伽西(帕林库洛之承体源头)为不同角色。"
    elif it["issue_id"] == "P9-04":
        it["decision"] = "涡波并非魔石人类(诺斯菲才是第一个魔石人类,T2-0102/0108 原文明确);『涡波与魔石人类共鸣/认同』是情感线而非身份线。帕林库洛『容器说』(RV-0067/0068)保留为反转中间态,非最终真相。confidence 由 AI推算 升为 合理推断(多原文支撑)。"
        it["confidence"] = "合理推断"
        it["resolved"] = True

# residual_review 裁决
old = cr.get("residual_review", [])
resolved_review = [
    {"event_id": "T3-0019/T3-0020", "issue": "B1 疑似重复(酒馆打工/化名基督)", "verdict": "判重复:保留 T3-0020(描述更长),删除 T3-0019(内容并入 T3-0020)", "executed": True},
    {"event_id": "T3-0118/T3-0199", "issue": "B2 md-0214 同块疑似重复", "verdict": "判不同事件(阿尔缇第十试练 vs 诺文第三十试练),保留两者,移出复核区", "executed": True},
    {"event_id": "T4-0026/T3-0417", "issue": "B3 诺斯菲60层同源锚点", "verdict": "判合理双线拆分(T4千年执念/T3现世决定),保留,加同源 note", "executed": True},
    {"event_id": "T3-0407", "issue": "C1 P7待复核", "verdict": "对齐 before=艾德支配者/利用者 → after=以弟弟身份赎罪(合理推断)", "executed": True},
    {"event_id": "T3-0411", "issue": "C2 P7待复核", "verdict": "确认轴4反转节点(缇亚独立个体价值),标注『缇亚≠西斯,救回即肯定其价值』", "executed": True},
    {"event_id": "T3-0415", "issue": "C3 P7待复核", "verdict": "对齐 before=即使徒承体 → after=缇亚与西斯是不同灵魂(原文明确)", "executed": True},
    {"event_id": "T3-0417", "issue": "C4 P7待复核", "verdict": "判非反转(战后独白决定),从 reversal_nodes 移除", "executed": True},
]
cr["resolved_review"] = resolved_review
cr.pop("residual_review", None)
save(os.path.join(OUT, "conflict_report.json"), cr)
print("conflict_report updated: items=", len(cr["items"]), "resolved_review=", len(resolved_review))

# ═══════════ 2. reversal_nodes: C1-C4 裁决 ═══════════
rvn = load(os.path.join(OUT, "reversal_nodes.json"))
kept = []
for n in rvn:
    eid = n.get("event_id")
    if eid == "T3-0407":  # C1 对齐
        n["before_belief"] = "艾德(木之理·宰相)是缇缇的支配者/利用者,暗中算计扶持她为王"
        n["after_truth"] = "艾德坦白全部算计,以满身伤痕的树人之姿恳求『再一次让我作为你的弟弟陪在身边』,缇缇含泪接纳——以弟弟身份赎罪回归"
        n["reversal"] = True
        n["confidence"] = "合理推断"
        n["axis"] = 0
        n["notes"] = "人工裁决(2026-09-01):C1 按建议对齐 before/after,confidence 合理推断。"
        kept.append(n)
    elif eid == "T3-0411":  # C2 轴4确认
        n["before_belief"] = "缇亚即使徒西斯转世承体,二者争夺身体,缇亚曾落败、将被西斯夺舍"
        n["after_truth"] = "涡波以《Distance Mute》将『不属于缇亚的部分』(使徒西斯)化作魔石取出冰封——转世后的缇亚是拥有独立意志与情感的全新个体,非西斯的简单复刻;救回缇亚即肯定『缇亚本人』的独立价值"
        n["reversal"] = True
        n["confidence"] = "原文明确"
        n["axis"] = 4
        n["notes"] = "人工裁决(2026-09-01):按用户指导思想确认轴4反转节点——缇亚≠西斯,涡波救回缇亚=肯定独立个体价值。原 axis0 修正为 axis4。"
        kept.append(n)
    elif eid == "T3-0415":  # C3 对齐
        n["before_belief"] = "缇亚即使徒西斯的转世承体,可能害了涡波的妹妹(记忆复苏恐惧)"
        n["after_truth"] = "缇亚剖白『西斯和我是不同的……这世界上就不存在完全相同的灵魂』——缇亚是独立个体,请求以『我(私)』自称时被温柔以待"
        n["reversal"] = True
        n["confidence"] = "原文明确"
        n["axis"] = 4
        n["notes"] = "人工裁决(2026-09-01):C3 对齐 before/after,confidence 原文明确,axis 归属轴4。"
        kept.append(n)
    elif eid == "T3-0417":  # C4 移除
        print("C4 removed:", n.get("node_id"), n.get("title"))
        continue
    else:
        kept.append(n)
save(os.path.join(OUT, "reversal_nodes.json"), kept)
print("reversal_nodes updated:", len(kept), "(removed 1)")

# ═══════════ 3. events_all_norm: B1 删除 T3-0019(并入 T3-0020) ═══════════
norm = load(os.path.join(BASE, "_merged", "events_all_norm.json"))
t19 = None
for e in norm:
    if e["event_id"] == "T3-0019":
        t19 = e
    elif e["event_id"] == "T3-0020":
        e.setdefault("merged_from", [])
        e["merged_from"].append({
            "event_id": "T3-0019",
            "title": t19["title"] if t19 else "",
            "reason": "人工裁决 B1:同事件(酒馆打工·化名基督·欧亚)旧/新切法重复,保留描述更长者",
            "absorbed_desc_tail": (t19.get("description", "") or "")[-80:] if t19 else ""
        })
        if t19 and t19.get("quotes"):
            e.setdefault("quotes", [])
            for q in t19["quotes"]:
                if q not in e["quotes"]:
                    e["quotes"].append(q)
norm = [e for e in norm if e["event_id"] != "T3-0019"]
save(os.path.join(BASE, "_merged", "events_all_norm.json"), norm)
print("events_all_norm updated:", len(norm), "(removed T3-0019)")

# 同步 _merged/events_all.json(源)
allsrc = load(os.path.join(BASE, "_merged", "events_all.json"))
allsrc = [e for e in allsrc if e["event_id"] != "T3-0019"]
for e in allsrc:
    if e["event_id"] == "T3-0020":
        e.setdefault("merged_from", [])
        if not any(m.get("event_id") == "T3-0019" for m in e["merged_from"]):
            e["merged_from"].append({"event_id": "T3-0019", "reason": "人工裁决 B1:同事件重复,并入"})
save(os.path.join(BASE, "_merged", "events_all.json"), allsrc)
print("events_all.json synced:", len(allsrc))

# 同步 event_chapter_map
em = load(os.path.join(BASE, "_merged", "event_chapter_map.json"))
em.pop("T3-0019", None)
save(os.path.join(BASE, "_merged", "event_chapter_map.json"), em)
print("event_chapter_map synced:", len(em))
