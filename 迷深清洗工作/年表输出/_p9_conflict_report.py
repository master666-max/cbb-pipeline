# -*- coding: utf-8 -*-
"""P9 冲突消解报告生成：基于 _P9待核查清单 + 合并/提取过程实况。"""
import os, json

BASE = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出"
OUT = os.path.join(BASE, "final_output")
os.makedirs(OUT, exist_ok=True)

report = {
    "report_id": "P9-20260901",
    "generated": "2026-09-01",
    "items": [
        {
            "issue_id": "P9-01",
            "topic": "40层守护者身份",
            "evidence": "第四章提取:艾德=木之理的盗窃者·40层守护者·千年前宰相(guardian_40_艾德);世界观知识库逐层档案未列 40 层(仅 0/10/20/30/50/60/66/70/80/90/100/110/120)。",
            "decision": "以语料实际为准:艾德=木之理·40层。世界观档案缺 40 层属档案不完整,非语料矛盾。",
            "confidence": "原文明确",
            "resolved": True,
            "data_refs": ["T2-0006", "T3-0244", "T3-0245"]
        },
        {
            "issue_id": "P9-02",
            "topic": "帕林库洛=暗之理继任",
            "evidence": "packD:帕林库洛吞缇达魔石·第二十之试练;packB:帕林库洛同化缇达魔石情报(话132);P7 反转清单 axis6/暗线含『帕林库洛=借西娅还魂的千年驻留灵魂』(EV-010-0025 相关)。",
            "decision": "帕林库洛 = 吞噬/继承缇达暗之理的继任者;P7 已标「缇达→帕林库洛」身份链反转。暗之理 20 层与 120 层西娅·勒迦希为不同角色,不混淆。",
            "confidence": "合理推断",
            "resolved": True,
            "data_refs": ["T1-0130", "T1-0131", "T1-0132"]
        },
        {
            "issue_id": "P9-03",
            "topic": "使徒西斯/勒伽西体系",
            "evidence": "T1 提取:使徒西斯置换降临、使徒勒伽西背叛(T2千年前);缇娅=使徒西斯转世(反转轴4);西娅·勒迦希 120层=暗之理(与帕林库洛体系分属不同线)。",
            "decision": "三链分开:①使徒西斯=始祖涡波千年前身份(缇娅=其转世承体);②使徒勒伽西=背叛者,120层西娅·勒迦希为其暗之理线;③帕林库洛=20层暗之理继任(见 P9-02)。",
            "confidence": "合理推断",
            "resolved": True,
            "data_refs": ["T1-0033", "T1-0034", "T1-0120"]
        },
        {
            "issue_id": "P9-04",
            "topic": "涡波是否魔石人类",
            "evidence": "packC 曾提 EV-0011/0015『涡波=魔石人类反转节点』;合并后 T2 线有 7 条『涡波+魔石人类』相关(T2-0080 涡波在魔石人类身上看到自己;T2-0102/0108 诺斯菲诞生为第一个魔石人类)。",
            "decision": "涡波并非魔石人类(诺斯菲才是第一个魔石人类);『涡波与魔石人类共鸣/认同』是情感线而非身份线。该说法与反转轴1(涡波=始祖)相关但非同一事实,不合并。标注为 AI推算结论供人工复核。",
            "confidence": "AI推算",
            "resolved": False,
            "data_refs": ["T2-0080", "T2-0102", "T2-0108"]
        },
        {
            "issue_id": "P9-05",
            "topic": "阳滝死而复生链",
            "evidence": "T1 线:阳滝病恶化/怪物化死亡(T1-0060 化怪物·始祖复仇)→ 世界奉还阵再诞(T1-0068/0069)→ T2 线:阳滝=水之理盗窃者(T2 多条)→ T3 线:100层水之理=阳滝。",
            "decision": "链条成立:T1死→T1世界奉还阵再诞→T2水之理就位→T4千年守护→T3 100层决战。P5 排序已按此时间轴落位;P7 反转轴6(阳滝=水之理)为最终真相。",
            "confidence": "原文明确",
            "resolved": True,
            "data_refs": ["T1-0060", "T1-0068", "T2-0006", "T3-0514"]
        },
        {
            "issue_id": "P9-06",
            "topic": "旧切法 vs 新切法重叠去重",
            "evidence": "第一章 pack01/pack02(旧110KB切法)与 new(1700行切法)重叠;第二章 pack03 与 new/packB 可能重叠。P5 合并 v3 修复跨章 block_id 碰撞:去重键=(章节+block+标题相似度≥0.35,仅跨文件)。",
            "decision": "v3 修复后 1587→1575(合并12组);残留 9 对疑似重复中 4~5 对为真实语义重复(如 T3-0019/T3-0020 第一章迁移者街打工),已记入 conflict_report 复核区。同 block 多事件(同文件)不合并。",
            "confidence": "合理推断",
            "resolved": True,
            "data_refs": ["T3-0019", "T3-0020"]
        },
        {
            "issue_id": "P9-07",
            "topic": "化名/译名双体系",
            "evidence": "一~三章(web_reconstructed)与八~十章(换译者体系)双译名:玛利亚/玛莉亚、缇娅拉/缇亚拉;涡波化名 基督·欧亚 前后章混用。",
            "decision": "按别名表归一:玛利亚(主)+玛莉亚(variant);缇娅拉(主名短称);characters 字段统一输出「相川涡波(化名:基督·欧亚)」双名并存,不替换。",
            "confidence": "原文明确",
            "resolved": True,
            "data_refs": ["001_别名表.md"]
        },
        {
            "issue_id": "P9-08",
            "topic": "章节≈守护者对应",
            "evidence": "合并后验证:1章→10层阿尔缇;2章→20层缇达(圣诞祭高潮);3章→30层诺文;4章→40层艾德;5章→50层庭师(莉帕/罗德);6章→60层诺斯菲;7章→70层(法夫纳系);8章→80层(玛利亚/赛尔德拉);9章→90层(诺伊);10章→100层阳滝。",
            "decision": "与 GUIDE 锚点一致;50/70/80/90 层守护者细名以各章提取正文为准(庭师=莉帕线、70层=法夫纳血之理线、80层=玛利亚、90层=诺伊)。",
            "confidence": "合理推断",
            "resolved": True,
            "data_refs": ["GUIDE 六"]
        },
        {
            "issue_id": "P9-09",
            "topic": "时间线年份锚点",
            "evidence": "T1 境界战争期 T-1000~T-995;T2 建造期 T-995~T-990;T4 千年间;T3 千年后。",
            "decision": "已按 LAYER_ORDER(T0<T1<T2<T4<T3)排序,事件内部保留原文模糊年月(如『T2-约建造期第3年』),不强行精确化;AI推算处已标注。",
            "confidence": "合理推断",
            "resolved": True,
            "data_refs": ["events_all_norm.json"]
        },
        {
            "issue_id": "P9-10",
            "topic": "P5 合并 v1 误吞事件(335 条)",
            "evidence": "初版 _p5c 以纯 block 数字去重,跨章碰撞致 1587→335(79%误删);v3 修复后 1587→1575。",
            "decision": "已用 v3 重跑并重新落盘 events_all.json/events_all_norm.json;原 v1 产物 _merged/events_all.json 已被 v3 覆盖,旧版仅存 _p5c_最终合并_orig.py 备份。",
            "confidence": "原文明确",
            "resolved": True,
            "data_refs": ["_p5c_最终合并.py"]
        },
        {
            "issue_id": "P9-11",
            "topic": "P8 咏唱 unmatched 缺口(562 条)",
            "evidence": "769 关联中 207 matched + 562 unmatched;unmatched 含未入库魔法族(世界炎蛇/耶梦加得系、Sehr・Wind 系、Quartz 水晶系、BlackShift 系、治愈系等)、库结构缺口(guardian_40/50/100 开场白未收录)、非咏唱项(剑技名/人名/书史)。",
            "decision": "unmatched 保留并注明推测;8 大高频魔法族建议后续补录咏唱库;非咏唱项从 incantation_links 中标注 type='非咏唱项' 单列,不计入咏唱关联统计。",
            "confidence": "合理推断",
            "resolved": False,
            "data_refs": ["_p8_links.json"]
        },
        {
            "issue_id": "P9-12",
            "topic": "reversal 字段规范化",
            "evidence": "192 条 reversal 中 5 条小写 true、8 条中文描述值(如『涡波=千年前水之理的盗窃者』)、178 条布尔 True;已由 _p9_规范化.py 统一为布尔+拆出 before_belief/after_truth。",
            "decision": "规范化完成;P7 节点 184 条(axis0=114/axis1=18/axis2=3/axis3=12/axis4=1/axis5=6/axis6=28),待复核 4 条(T3-0407/0411/0415/0417)保留供人工。",
            "confidence": "原文明确",
            "resolved": True,
            "data_refs": ["_p7_nodes.json"]
        },
        {
            "issue_id": "P9-13",
            "topic": "event_type 非法值",
            "evidence": "合并后 3 条『剧情』(T3-0095/0099/0100)、1 条『光环高潮』——非枚举值。",
            "decision": "已由 _p9_规范化.py 统一映射为『剧情高潮』;合并后 event_type 分布校验通过,枚举值全部合法。",
            "confidence": "原文明确",
            "resolved": True,
            "data_refs": ["_p9_规范化.py"]
        }
    ],
    "residual_review": [
        {"event_id": "T3-0019", "note": "第一章『迁移者街·酒馆打工』与 T3-0020 疑似语义重复,标题相似度 0.55"},
        {"event_id": "T3-0020", "note": "同上(旧切法 new vs pack01 重叠残留)"},
        {"event_id": "T3-0118/T3-0199", "note": "md-0214 同块两条千年前魔法统合事件,疑似重复"},
        {"event_id": "T3-0407", "note": "P7 待复核:before/after 无法对齐"},
        {"event_id": "T3-0411", "note": "P7 待复核:before/after 无法对齐"},
        {"event_id": "T3-0415", "note": "P7 待复核:before/after 无法对齐"},
        {"event_id": "T3-0417", "note": "P7 待复核:before/after 无法对齐"},
        {"event_id": "T4-0026", "note": "诺斯菲 60 层千年守望 vs T3-0417 备战,同 block 双事件,疑重复"}
    ]
}

path = os.path.join(OUT, "conflict_report.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
print("written:", path)
print("items:", len(report["items"]), "residual:", len(report["residual_review"]))