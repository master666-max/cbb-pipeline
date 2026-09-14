# -*- coding: utf-8 -*-
"""adversarial_gold_review.py — 金标 DeepSeek 对抗性自审 ×5 轮
用法: DEEPSEEK_API_KEY=sk-xxx <venv312>/python.exe -X utf8 adversarial_gold_review.py
每轮独立存盘（崩溃不丢轮）；挑战带原文行号引文，裁决权在审核线。
"""
import json, os, sys, time, re
import httpx

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
OUTDIR = os.path.join(ROOT, "结果", "adversarial")
os.makedirs(OUTDIR, exist_ok=True)

API = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"
KEY = os.environ.get("DEEPSEEK_API_KEY")
if not KEY:
    sys.exit("FATAL: DEEPSEEK_API_KEY not set")

EXCERPTS = {
    "excerpt1": "excerpt1-CHAPTER0014.md",
    "excerpt2": "excerpt2-CHAPTER0038.md",
    "excerpt3": "excerpt3-CHAPTER0114.md",
    "excerpt4": "excerpt4-CHAPTER0001-序章型.md",
}

THEMES = {
    1: ("漏标攻击", "逐字对照原文，找出金标遗漏的一切应抽项：实体（人物/地点/组织/物品/技能魔法/概念）、关系、时间表述。特别注意：对话中提到但金标没有的人名地名、被别名掩盖的两个不同存在、金标实体有提及行却没有任何关系边覆盖的情况、无具名但有明确指称对象的重要事物。"),
    2: ("错标攻击", "逐条检查金标已标注项：实体名称是否与原文用字完全一致、type 是否恰当、aliases 归并是否把两个不同存在错并成一个、evidence 行号是否真的支持该标注；关系的方向是否与原文谓词方向一致、claim 标记是否正确、遗漏了金标实体间应有的关系。"),
    3: ("口径与规则攻击", "检查金标是否违反其自身声明规则：未具名角色不立实体？迷宫层级单列是否一致？claim 口径执行是否一致？噪声（图片文件名/论坛吐槽/译注/现实日期）是否被误当正文标注？各册排除备案是否有站不住脚的？你也可以直接质疑规则本身——但必须给出理由和替代方案。"),
    4: ("时间口径攻击", "逐条检查时间表述：有无漏收的时间词？kind 类型判定对不对？anchorable 该不该 true？年龄/等级/层数/倍率有没有被误当时间或漏收？相对锚指向的事件是否说清？excerpt4 的现实日期处理是否符合其'该抽零'口径？"),
    5: ("红队终局复核", "综合前四轮：a) 复核此前挑战里被一带而过的次级问题；b) 对金标做'最强抗辩'测试——如果你要为这份金标的错误负全责，你最担心哪一条被推翻？为什么？c) 给出整份金标的置信度评分(0-100)与最脆弱的三处。"),
}

SCHEMA = """{"round": N, "challenges": [{"type": "漏标实体|错标实体|漏标关系|错标关系|漏标时间|错标时间|口径质疑",
"target": "针对的金标项或'全局'", "claim": "挑战内容一句话", "evidence": "L行号:\\"原文引文\\"",
"proposed_fix": "建议修正", "severity": "high|medium|low"}], "confidence_score": 0-100}"""

def call(client, messages, max_tokens=32768):
    payload = {"model": MODEL, "messages": messages, "temperature": 0.3,
               "max_tokens": max_tokens, "response_format": {"type": "json_object"}}
    r = client.post(API, json=payload, headers={"Authorization": f"Bearer {KEY}"}, timeout=480)
    if r.status_code in (429, 500, 502, 503):
        time.sleep(20)
        r = client.post(API, json=payload, headers={"Authorization": f"Bearer {KEY}"}, timeout=480)
    r.raise_for_status()
    data = r.json()
    ch = data["choices"][0]
    content = (ch["message"].get("content") or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", content, re.S)
    if m:
        content = m.group(1).strip()
    return content, data.get("usage", {}), ch.get("finish_reason")

def main():
    client = httpx.Client()
    total_challenges = 0
    for gname, ef in EXCERPTS.items():
        text = open(os.path.join(ROOT, "材料", ef), encoding="utf-8").read()
        gold = json.load(open(os.path.join(ROOT, "金标", f"gold-{gname}.json"), encoding="utf-8"))
        gold_str = json.dumps(gold, ensure_ascii=False)
        prior = []
        for rnd in range(1, 6):
            out_path = os.path.join(OUTDIR, f"{gname}_R{rnd}.json")
            if os.path.exists(out_path):
                old = json.load(open(out_path, encoding="utf-8"))
                prior.append({"round": rnd, "challenges": old.get("challenges", [])})
                total_challenges += len(old.get("challenges", []))
                print(f"[skip] {gname} R{rnd} 已存在 ({len(old.get('challenges', []))} 条)", flush=True)
                continue
            theme_name, theme_body = THEMES[rnd]
            sys_p = "你是对抗性审计员，任务是攻击一份小说金标答案册。宁可多挑战也不放过，但每条挑战必须给出原文行号+引文证据；没有证据的挑战等于零。输出严格 JSON。"
            user_p = f"""# 原文（切样，行号=L文件行号）
{text}

# 金标答案册（你要攻击的对象）
{gold_str}

# 金标声明规则（攻击时以此为基准，亦可质疑规则本身）
R1 未具名角色不立实体；R2 迷宫层级单列；R3 虚构声称（信件/传闻/谎言）抽为 claim=true 边；R4 否定性事实记实体 note 不建边；R5 国/势力单标地点不拆；噪声（图片文件名/论坛吐槽/译注/现实日期）不标注。excerpt4 为元文本，口径=零故事实体。

# 本轮攻击主题：{theme_name}
{theme_body}

# 此前轮次挑战摘要（不要重复，应深化、反驳或补刀）
{json.dumps(prior, ensure_ascii=False) if prior else "（首轮，无）"}

# 输出格式
{SCHEMA}"""
            msgs = [{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}]
            txt, usage, fin = call(client, msgs)
            if fin == "length":
                txt, usage, fin = call(client, msgs, max_tokens=65536)
            try:
                parsed = json.loads(txt)
            except Exception as e:
                open(out_path + ".bad", "w", encoding="utf-8").write(txt)
                print(f"[FAIL] {gname} R{rnd} JSON解析失败: {e}", flush=True)
                continue
            parsed.setdefault("challenges", [])
            parsed["usage"] = usage
            parsed["finish"] = fin
            json.dump(parsed, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            prior.append({"round": rnd, "challenges": parsed["challenges"]})
            total_challenges += len(parsed["challenges"])
            print(f"[ok] {gname} R{rnd}: {len(parsed['challenges'])} 条挑战, 置信度={parsed.get('confidence_score', '-')}, usage={usage.get('total_tokens')}", flush=True)
    print(f"[ALL DONE] 总挑战数={total_challenges}", flush=True)

if __name__ == "__main__":
    main()
