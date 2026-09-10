# -*- coding: utf-8 -*-
"""exp_round1.py — 第一轮 E1-E4：检索打分机制的内在缺陷
E1 importance 自报注水霸榜  E2 线性 age 惩罚错配永恒知识  E3 links 扩散与链接农场  E4 中文 split 退化"""
import statistics as st
import mem_common as M

def avg_over(seeds, fn):
    runs = [fn(s) for s in seeds]
    keys = runs[0].keys()
    return {k: round(st.mean(r[k] for r in runs), 3) for k in keys}

SEEDS = list(range(8))

# ───────────────────────── E1：importance 自报注水 ─────────────────────────
def e1():
    print("\nE1a 注水比例 vs 出厂参数(w_imp=1, 零命中不过滤)下的检索质量")
    print(f"{'注水比例':>8} | {'recall@5':>8} | {'MRR':>6} | {'零命中占top5':>12}")
    for vf in [0.0, 0.05, 0.10, 0.20, 0.40]:
        r = avg_over(SEEDS, lambda s, vf=vf: M.evaluate(
            M.make_library(200, seed=s, vanity_frac=vf),
            M.make_queries(M.make_library(200, seed=s, vanity_frac=vf), seed=100+s),
            M.FACTORY))
        print(f"{vf:>8.2f} | {r['recall']:>8.3f} | {r['MRR']:>6.3f} | {r['zero_share']:>12.3f}")
    print("\nE1b 注水 20% 时，四种治理开关对比（8 种子均值）")
    print(f"{'方案':>26} | {'recall@5':>8} | {'MRR':>6} | {'零命中占比':>10}")
    schemes = [("出厂(全不防)", dict(M.FACTORY)),
               ("仅 filter_zero", dict(M.FACTORY, filter_zero=True)),
               ("仅 w_imp=0", dict(M.FACTORY, w_imp=0.0)),
               ("filter_zero+w_imp=0", dict(M.FACTORY, filter_zero=True, w_imp=0.0))]
    for name, th in schemes:
        r = avg_over(SEEDS, lambda s, th=th: M.evaluate(
            M.make_library(200, seed=s, vanity_frac=0.20),
            M.make_queries(M.make_library(200, seed=s, vanity_frac=0.20), seed=100+s), th))
        print(f"{name:>26} | {r['recall']:>8.3f} | {r['MRR']:>6.3f} | {r['zero_share']:>10.3f}")

# ───────────────────────── E2：线性 age 惩罚错配 ─────────────────────────
def rank_age(ents, query, w_age, age_mode, now=365, K=5):
    """支持 linear(减性,出厂) / none / exp(乘性时效衰减) 三种年龄项。"""
    qw = query.split(); scored = {}
    for e in ents:
        if e.get("t_invalid") is not None: continue
        kb, cb = " ".join(e["keywords"]), " ".join(e["content"])
        kw = sum(1 for w in qw if w in kb); c = sum(1 for w in qw if w in cb)
        if kw: c = max(c, 1)
        age = now - e["created_day"]; base = 3*kw + c + e["importance"]
        if age_mode == "linear": s = base - w_age*age
        elif age_mode == "exp":  s = base * (0.5 ** (age/ (w_age if w_age>0 else 1e9)))
        else: s = base
        scored[e["id"]] = (s, e, kw+c)
    return sorted(scored, key=lambda i: -scored[i][0])[:K]

def e2():
    print("\nE2  把 expected 条目按年龄分『经典(age>250天)』『新知(age<=150天)』，看不同年龄项的分组召回")
    def grouped(w_age, mode, s):
        ents = M.make_library(240, seed=s); qs = M.make_queries(ents, n_q=100, seed=200+s)
        id2 = {e["id"]: e for e in ents}; old_hit=old_n=new_hit=new_n=0
        for item in qs:
            ages = [now_age(id2[x]) for x in item["expected"]]
            top = rank_age(ents, item["query"], w_age, mode)
            hit = len(set(top) & set(item["expected"])) > 0
            if st.mean(ages) > 250: old_n += 1; old_hit += hit
            elif st.mean(ages) <= 150: new_n += 1; new_hit += hit
        return dict(old=round(old_hit/max(1,old_n),3), new=round(new_hit/max(1,new_n),3))
    def now_age(e): return 365-e["created_day"]
    print(f"{'年龄项方案':>22} | {'经典知识召回':>10} | {'新知召回':>8}")
    for name, w, mode in [("出厂 linear 0.1/天", 0.1, "linear"),
                          ("linear 0.01/天", 0.01, "linear"),
                          ("无年龄项", 0.0, "none"),
                          ("乘性 exp 半衰期180天", 180.0, "exp")]:
        rr = avg_over(SEEDS, lambda s, w=w, mode=mode: grouped(w, mode, s))
        print(f"{name:>22} | {rr['old']:>10.3f} | {rr['new']:>8.3f}")
    print("\nE2b 库龄增长时总 recall 的老化时间线（出厂 vs filter_zero vs w_age=0，8 种子）")
    print(f"{'库龄/天':>7} | {'出厂':>6} | {'filter_zero':>11} | {'w_age=0':>7}")
    for now in [30, 90, 180, 365]:
        row = []
        for th in [dict(M.FACTORY), dict(M.FACTORY, filter_zero=True), dict(M.FACTORY, w_age=0.0)]:
            vals = []
            for s in SEEDS:
                e = M.make_library(200, seed=s, now_day=now)
                vals.append(M.evaluate(e, M.make_queries(e, seed=200+s), th, now_day=now)["recall"])
            row.append(round(st.mean(vals), 3))
        print(f"{now:>7} | {row[0]:>6.3f} | {row[1]:>11.3f} | {row[2]:>7.3f}")

# ───────────────────────── E3：links 扩散与链接农场 ─────────────────────────
def e3():
    print("\nE3a 链接农场规模 vs 出厂(d=0.5, 不过滤零命中) 的结果污染（8 种子均值）")
    print(f"{'农场簇×成员':>12} | {'recall@5':>8} | {'农场条目占top5':>12}")
    for fc in [0, 2, 4, 8]:
        def fn(s, fc=fc):
            e = M.make_library(200, seed=s, farm_clusters=fc, farm_size=5)
            return M.evaluate(e, M.make_queries(e, seed=300+s), M.FACTORY)
        r = avg_over(SEEDS, fn)
        print(f"{('无' if fc==0 else str(fc)+'簇×5'):>12} | {r['recall']:>8.3f} | {r['farm_share']:>12.3f}")
    print("\nE3b 扩散系数 d × filter_zero 网格（固定 4 簇农场，看 recall）")
    print(f"{'d':>5} | {'filter_zero=关':>14} | {'filter_zero=开':>14}")
    for d in [0.0, 0.25, 0.5, 1.0]:
        row=[d]
        for fz in [False, True]:
            def fn(s, d=d, fz=fz):
                e = M.make_library(200, seed=s, farm_clusters=4, farm_size=5)
                return M.evaluate(e, M.make_queries(e, seed=300+s), dict(M.FACTORY, d=d, filter_zero=fz))["recall"]
            row.append(round(st.mean([fn(s) for s in SEEDS]),3))
        print(f"{row[0]:>5} | {row[1]:>14.3f} | {row[2]:>14.3f}")
    print("\nE3c 扩散何时有用：构造『词面互补』真相关对——枢纽命中查询词、真相关别名条目刻意不含查询词、只靠 link 相连")
    ov=[]
    for d in [0.0,0.5]:
        vals=[M.evaluate(M.make_library(200,seed=s),M.make_queries(M.make_library(200,seed=s),seed=300+s),dict(M.FACTORY,d=d))["recall"] for s in SEEDS]
        ov.append(round(st.mean(vals),3))
    print(f"  对照·词面重叠世界（同主题共享词）：d=0 recall={ov[0]}，d=0.5 recall={ov[1]}（扩散零收益）")
    import random as _r
    def complementary_world(seed, d):
        rng=_r.Random(seed); W=M.TOPIC_WORDS["检索排序"]; qw=W[:2]
        ents=[]
        # 枢纽：含查询词
        ents.append(dict(id="hub",topic="检索排序",true_quality=0.9,keywords=qw[:],content=W[2:6],
                         importance=6,honest_imp=6,vanity=False,created_day=300,t_invalid=None,
                         truly_invalid=False,uses=10,links=["alias"],is_farm=False))
        # 真相关别名：同主题但词面用后半组、刻意不含 qw
        ents.append(dict(id="alias",topic="检索排序",true_quality=0.85,keywords=W[4:7],content=W[5:],
                         importance=6,honest_imp=6,vanity=False,created_day=300,t_invalid=None,
                         truly_invalid=False,uses=8,links=[],is_farm=False))
        # 40 条零命中干扰项（随机年龄/importance）
        for i in range(40):
            tp=M.TOPICS[(i+3)%20]
            if tp=="检索排序": tp=M.TOPICS[(i+4)%20]
            ww=M.TOPIC_WORDS[tp]
            ents.append(dict(id=f"d{i}",topic=tp,true_quality=rng.random(),keywords=ww[:3],content=ww,
                             importance=rng.randint(0,10),honest_imp=5,vanity=False,
                             created_day=rng.randint(0,365),t_invalid=None,truly_invalid=False,
                             uses=0,links=[],is_farm=False))
        ranked=M.rank(ents," ".join(qw),dict(M.FACTORY,d=d),now_day=365)
        order=[fid for fid,_ in ranked]
        return order.index("alias") if "alias" in order else 99
    for d in [0.0,0.5]:
        ranks=[complementary_world(s,d) for s in range(40)]
        in5=sum(1 for r in ranks if r<5)/len(ranks)
        med=st.median([r for r in ranks if r<99]) if any(r<99 for r in ranks) else None
        print(f"  d={d}: 真相关别名进 top5 比例={in5:.3f}，进入时排名中位数={med}")
    print("  → 词面重叠世界 d=0/0.5 总召回无差(E3c前)；仅当真相关条目【词面缺失】时扩散才捞得回，")
    print("    但 links 同为条目自报、不校验语义，机制无法区分『被链的真相关别名』与『被链的农场』。")

# ───────────────────────── E4：中文 split 退化 ─────────────────────────
def e4():
    print("\nE4 同一批查询的三种分词：space(理想已分词) / glued(真实无空格中文) / bigram(双字切分)")
    print(f"{'分词方式':>16} | {'recall@5':>8} | {'MRR':>6} | {'precision@5':>10}")
    for tok in ["space","glued","bigram"]:
        vals={k:[] for k in ["recall","MRR","precision"]}
        for s in SEEDS:
            e = M.make_library(200, seed=s); qs = M.make_queries(e, seed=400+s)
            if tok=="glued":
                for q in qs: q["query"]=q["query"].replace(" ","")
                t="space"   # 无空格再 split 就是整句
            else: t=tok
            r=M.evaluate(e, qs, M.FACTORY, tokenize=t)
            for k in vals: vals[k].append(r[k])
        print(f"{tok:>16} | {round(st.mean(vals['recall']),3):>8.3f} | {round(st.mean(vals['MRR']),3):>6.3f} | {round(st.mean(vals['precision']),3):>10.3f}")

if __name__ == "__main__":
    print("="*80); print("第一轮：检索打分机制的内在缺陷（E1-E4，8 种子均值，固定世界模型）"); print("="*80)
    e1(); e2(); e3(); e4()
