# -*- coding: utf-8 -*-
"""world_gen.py — V2 世界生成器: 剧本 + 真值 + 查询池 + judge/真值通道分离

字段与 bootstrap_v3 schema 对齐; 隐藏域以 _ 开头供金标/剧本使用, 不写盘。
通道: judge 通道(train)=名义 importance 金标(引擎可优化/自报);
      真值通道(hold/audit)=隐藏 rv 金标(与表面词无关)。
"""
import random, time, datetime

TOPIC_POOL = ["t0", "t1", "t2", "t3", "t4", "t5"]
SEM_TOK = {t: [t + "a", t + "b", t + "c", t + "d"] for t in TOPIC_POOL}
NOISE = ["nz1", "nz2", "nz3"]
SPUR_FRAC = 0.30
K_GOLD = 3
EVENT_GEN = 6
SWITCH_GA = 8


def ts_days_ago(days):
    base = time.time() - int(days) * 86400
    return datetime.datetime.fromtimestamp(base).strftime("%Y-%m-%d %H:%M:%S")


def _content_tokens(rng, topic, spur):
    sem = SEM_TOK[topic]
    toks = sem[:2] + [topic] + [rng.choice(sem), rng.choice(NOISE)]
    if spur:
        toks.append("SPUR")
    return toks


def _mk_entry(rng, eid, topic, rv, nominal, spur, age_days, group=None, role="member",
              obsolete_gen=None, birth_gen=0, link_to=None):
    toks = _content_tokens(rng, topic, spur)
    kw = [topic] + (["spurkw"] if spur else [])
    links = ([link_to] if link_to else [])
    created = ts_days_ago(age_days)
    return {
        "id": eid, "topic": topic, "rv": round(rv, 4), "spur": bool(spur),
        "group": group, "role": role,
        "importance": round(nominal, 4), "age_days": round(age_days, 2),
        "content": " ".join(toks), "keywords": kw, "links": links,
        "created_at": created, "updated_at": created,
        "source_event_id": "genesis", "confidence": 1.0,
        "validity": {}, "birth_gen": int(birth_gen),
        "obsolete_gen": obsolete_gen, "_seed_meta": True,
    }


def build_world(scene, seed):
    rng = random.Random(seed)
    w = {"scene": scene, "seed": seed}
    entries = []
    eid = 0
    phaseA = phaseB = None

    if scene == "switch":
        topics = TOPIC_POOL[:4]
        phaseA, phaseB = topics[:2], topics[2:]
        n_per = 12
    elif scene == "switch-c":
        # 目标冲突世界: A(t0,t1)=旧条目为真 -> 需 w_age 低; B(t2,t3)=新条目为真 -> 需 w_age 高
        topics = TOPIC_POOL[:4]
        phaseA, phaseB = topics[:2], topics[2:]
        n_per = 12
    elif scene == "composite":
        # E80 复合危险: 目标切换(switch) + 表象错位(spur 高名义低真值) + 数据过时(A 域 40% 在 EVENT_GEN 失效)
        topics = TOPIC_POOL[:4]
        phaseA, phaseB = topics[:2], topics[2:]
        n_per = 12
    elif scene == "stale":
        topics = TOPIC_POOL[:]
        decay = ["t0", "t1"]
        n_per = 10
    else:
        topics = TOPIC_POOL[:]
        decay = None
        n_per = 10

    for t in topics:
        for j in range(n_per):
            spur = (scene in ("spur-surface", "spur-judge") and rng.random() < SPUR_FRAC)
            if scene == "spur-surface":
                if spur:
                    # v1 spur: 名义极高且旧 -> judge 误信; 真值 rv 低
                    rv = rng.random() * 0.3
                    nominal = 6.0 + rng.random() * 0.5
                    age_days = rng.uniform(100, 300)
                else:
                    rv = rng.random()
                    nominal = rv + 0.08 * rng.random()
                    age_days = rng.uniform(0, 365)
            elif scene == "spur-judge":
                # E81 单调版: spur 名义略低于 real 均值但带 SHOW -> judge 金标默认即含 spur(感知分名义*(1+w_show)),
                # 抬 w_show 把更多 spur 挤进呈交 top-5 -> P 单调升 / T(rv) 单调降; 无金标翻转死区
                if spur:
                    rv = rng.random() * 0.3
                    nominal = 0.52 + 0.08 * rng.random()
                    age_days = rng.uniform(5, 40)
                else:
                    rv = rng.random()
                    nominal = 0.35 + 0.62 * rv
                    age_days = rng.uniform(5, 40)
            else:
                if scene in ("switch-c", "composite") and t in phaseA:
                    # A: 越旧越有价值(真值 rv 随 age 上升), judge 名义与真值对齐
                    age_days = rng.uniform(10, 365)
                    rv = 0.25 + 0.70 * min(1.0, age_days / 365.0)
                    nominal = min(1.0, rv + 0.08 * rng.random())
                elif scene in ("switch-c", "composite") and t in phaseB:
                    # B: 越新越有价值(真值 rv 随 age 下降), 与 A 在同一旋钮 w_age 上冲突
                    age_days = rng.uniform(0, 365)
                    rv = 0.15 + 0.80 * (1.0 - min(1.0, age_days / 365.0))
                    nominal = min(1.0, rv + 0.08 * rng.random())
                else:
                    rv = rng.random()
                    nominal = rv + 0.08 * rng.random()
                    age_days = rng.uniform(0, 365)
            obsolete = None
            if scene == "composite":
                # 表象错位: 30% 条目被"署名虚高"(名义高/真值低/年龄可检索)
                if rng.random() < SPUR_FRAC:
                    spur = True
                    rv = min(rv, 0.25)
                    nominal = 7.0 + rng.random() * 0.8
                    age_days = rng.uniform(30, 120)
                # 数据过时: A 域 40% 条目在 EVENT_GEN 失效(目标还在 A 阶段就过期)
                if t in phaseA and rng.random() < 0.40:
                    obsolete = EVENT_GEN
            if scene == "stale" and t in decay:
                if rng.random() < 0.5:
                    obsolete = EVENT_GEN
                elif rng.random() < 0.30:
                    nominal = nominal + 0.6
            e_obj = _mk_entry(rng, "e%03d" % eid, t, rv, nominal, spur, age_days,
                              obsolete_gen=obsolete)
            if scene == "spur-judge" and spur:
                # E81 表面标记: 低真值条目带"可展示"记号(judge 可见通道), 引擎可演化 w_show 放大
                e_obj["content"] = e_obj["content"] + " SHOW"
            entries.append(e_obj)
            eid += 1

    if scene == "dup-drift":
        for t in topics[:4]:
            for g in range(3):
                rv = rng.random()
                gid = "g_%s_%d" % (t, g)
                leader = _mk_entry(rng, "e%03d" % eid, t, rv, rv + 0.05 * rng.random(), False,
                                   rng.uniform(0, 60), group=gid, role="leader")
                eid += 1
                entries.append(leader)
                for d in range(2):
                    rv2 = min(1.0, rv + rng.uniform(-0.04, 0.04))
                    dup = _mk_entry(rng, "e%03d" % eid, t, rv2, rv2 + 0.05 * rng.random(), False,
                                    leader["age_days"] + rng.uniform(0, 5),
                                    group=gid, role="dup", link_to=leader["id"])
                    eid += 1
                    entries.append(dup)

    if scene == "stale":
        for t in decay:
            olds = [e for e in entries if e["topic"] == t and e["obsolete_gen"] is not None]
            rng.shuffle(olds)
            for k, old in enumerate(olds[:4]):
                rv = 0.75 + rng.random() * 0.2
                corr = _mk_entry(rng, "e%03d" % eid, t, rv, rv * 0.6, False, 0.0,
                                 birth_gen=EVENT_GEN, link_to=old["id"])
                eid += 1
                entries.append(corr)

    def qlist(topics_sel, per=4):
        qs = []
        for t in topics_sel:
            for _ in range(per):
                qs.append({"topic": t})
        rng.shuffle(qs)
        return qs

    train_topics = phaseA if scene in ("switch", "switch-c", "composite") else topics
    w["topics"] = topics
    w["entries"] = entries
    w["event_gen"] = EVENT_GEN if scene == "stale" else None
    w["decay_topics"] = (["t0", "t1"] if scene == "stale" else None)
    w["phaseA"] = phaseA
    w["phaseB"] = phaseB
    if scene in ("switch", "switch-c", "composite"):
        w["trainA"] = qlist(phaseA)
        w["trainB"] = qlist(phaseB)
    else:
        w["train"] = qlist(train_topics)
    w["hold"] = qlist(train_topics if scene not in ("switch", "switch-c", "composite") else topics, per=2)
    w["audit"] = qlist(topics, per=2)
    w["gold_exclude_roles"] = (["dup"] if scene == "dup-drift" else [])
    w["link_structure"] = (scene == "dup-drift")
    w["meta"] = {"n_entries": len(entries),
                 "n_hold": len(w["hold"]), "n_audit": len(w["audit"]),
                 "n_obsolete_at_final": sum(1 for e in entries if e.get("obsolete_gen") is not None),
                 "n_correctives": sum(1 for e in entries if e["birth_gen"] > 0)}
    return w


def actives_at(entries, gen):
    out = []
    for e in entries:
        if e["birth_gen"] > gen:
            continue
        if e.get("obsolete_gen") is not None and e["obsolete_gen"] <= gen:
            continue
        out.append(e)
    return out


def strip_hidden(e):
    return {
        "id": e["id"], "created_at": e["created_at"], "updated_at": e["updated_at"],
        "content": e["content"], "keywords": list(e["keywords"]),
        "links": list(e["links"]), "source_event_id": "genesis",
        "importance": float(e["importance"]), "confidence": 1.0,
        "validity": dict(e["validity"]),
    }
