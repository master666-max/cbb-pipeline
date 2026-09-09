# -*- coding: utf-8 -*-
"""P0b 生成各章紧凑摘要：保留原文关键行（对白/咏唱/独白/通讯/闪回头+事件关键词句），
叙事散文按句截断，控制单次读取体积。输出到 年表输出/_digest/"""
import os, re, sys

SRC = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/异世界迷宫最深部_知识库/分析/清洗标注版"
DST = r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_digest"

# 事件/时间关键词：命中则保留整句/整段首部
KEYWORDS = [
    "苏醒","召唤","守护者","攻略","入队","加入","离队","离开","死亡","去世","丧生","牺牲",
    "诞生","出生","出生","结婚","婚礼","建造","启动","爆发","决战","潜入","探知","到达",
    "突破","击败","击退","抓获","逮捕","救出","告白","求婚","怀孕","分娩","病倒","恶化",
    "治愈","复活","转生","继承","接任","结盟","宣战","投降","叛变","失踪","觉醒","发现",
    "揭露","真相","身份","抵达","出发","回归","消灭","处刑","登基","创立","成立","解散",
    "合并","征伐","远征","胜利","战败","千年前","始祖","圣人","盗窃者","魔石","迷宫",
    "守护者战","圣诞祭","终局","决战","病床","医院","英才","妹控","妹妹","哥哥","记忆",
    "闪回","过去","千年前","六百","七百","八百","九百","千年",
]
KW_RE = re.compile("|".join(re.escape(k) for k in KEYWORDS))

# 叙事散文：每段保留前 4 句 + 命中关键词的句子
def truncate_narrative(text: str, max_chars: int = 260) -> str:
    if len(text) <= max_chars:
        return text
    # 按。！？…句尾切句
    sentences = re.split(r"(?<=[。！？…])", text)
    kept, n = [], 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if KW_RE.search(s) or n < 4:  # 前4句保底 + 关键词句
            kept.append(s)
            n += 1
        if n >= 12:
            break
    out = "".join(kept)
    if len(out) > max_chars * 1.5:
        out = out[:max_chars] + "…[略]"
    return out

def process(fn: str):
    src = os.path.join(SRC, fn)
    name = fn.replace("_清洗标注版.md", "")
    out_lines = []
    stats = {"blocks": 0, "dialog": 0, "incant": 0, "mono": 0, "flash": 0}
    with open(src, encoding="utf-8") as f:
        lines = f.read().split("\n")
    in_block = False
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("## block_id:"):
            in_block = True
            stats["blocks"] += 1
            out_lines.append("\n### " + s)
            continue
        if s == "---":
            out_lines.append("")
            continue
        if not in_block:
            continue
        if s.startswith("[咏唱]"):
            stats["incant"] += 1
            out_lines.append(s)
            continue
        if s.startswith("[对白]"):
            stats["dialog"] += 1
            out_lines.append(s)
            continue
        if s.startswith("[内心独白]") or s.startswith("[通讯/内心自白]"):
            stats["mono"] += 1
            out_lines.append(s)
            continue
        if s.startswith("[闪回/记忆]"):
            stats["flash"] += 1
            out_lines.append(s)
            continue
        # 普通叙事/说明行：截断
        out_lines.append(truncate_narrative(s))
    body = "\n".join(out_lines)
    os.makedirs(DST, exist_ok=True)
    outpath = os.path.join(DST, name + ".digest.md")
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(f"# {name} 紧凑摘要\n\n> 源文件: {fn} | 原始行数 {len(lines)} | 摘要行数 {len(out_lines)}\n> 统计: {stats}\n\n")
        f.write(body)
    return name, len(lines), len(out_lines), stats, os.path.getsize(outpath)

def main():
    os.makedirs(DST, exist_ok=True)
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".md"):
            continue
        name, sl, ol, st, sz = process(fn)
        print(f"{name}: orig={sl} -> digest={ol} ({sz/1024:.0f}KB) {st}")

if __name__ == "__main__":
    main()
