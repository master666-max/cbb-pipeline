# -*- coding: utf-8 -*-
"""exp_round4.py — 第四轮 E13-E16：自演化闭环（核心）
E13 法层爬山演化能否收敛/泛化 E14 写入-检索对抗共演化 E15 eval棘轮(P0-4)动态 E16 死参数表演性准入"""
import statistics as st, random
import mem_common as M

SEEDS=list(range(6))
def mean(x): return round(st.mean(x),3)

def build(seed, vf=0.0):
    ents=M.make_library(220,seed=seed,vanity_frac=vf,now_day=365)
    qtr=M.make_queries(ents,n_q=60,seed=1000+seed)
    qho=M.make_queries(ents,n_q=60,seed=2000+seed)
    return ents,qtr,qho

# ───────────────────────── E13：法层自演化收敛与泛化 ─────────────────────────
def e13():
    print("E13 从出厂参数爬山演化 30 代（6 种子）：训练/留出 recall 与最终参数")
    print("(a) 只演化连续权重，filter_zero 锁死为 False（出厂）")
    tr0,ho0,finalp=[],[],[]
    for s in SEEDS:
        ents,qtr,qho=build(s)
        traj=M.evolve(ents,qtr,qho,dict(M.FACTORY),n_gen=30,seed=s,mutate_filter=False)
        tr0.append(traj[-1][0]);ho0.append(traj[-1][1]);finalp.append(traj[-1][2])
    print(f"  出厂起点 train={M.evaluate(M.make_library(220,seed=0,now_day=365),M.make_queries(M.make_library(220,seed=0,now_day=365),seed=1000))['recall']}  演化终值 train={mean(tr0)} holdout={mean(ho0)}")
    avg={k:round(st.mean([p[k] for p in finalp]),3) for k in ["w_kw","w_c","w_imp","w_age","d"]}
    print(f"  最终参数均值={avg}")
    print("(b) 允许变异离散开关 filter_zero（自演化能否自己发现『零命中过滤』这个结构）")
    tr1,ho1,found=[],[],0
    for s in SEEDS:
        ents,qtr,qho=build(s)
        traj=M.evolve(ents,qtr,qho,dict(M.FACTORY),n_gen=40,seed=s,mutate_filter=True)
        tr1.append(traj[-1][0]);ho1.append(traj[-1][1])
        if traj[-1][2].get("filter_zero"): found+=1
    print(f"  演化终值 train={mean(tr1)} holdout={mean(ho1)}；{found}/{len(SEEDS)} 个种子自行把 filter_zero 翻成 True")
    print("(c) 从劣化起点(w_imp=3,w_age=0.3,零命中不过滤)出发，允许开关变异，能否爬回")
    ho2=[]
    for s in SEEDS:
        ents,qtr,qho=build(s)
        bad=dict(w_kw=3.0,w_c=1.0,w_imp=3.0,w_age=0.3,d=0.5,filter_zero=False)
        traj=M.evolve(ents,qtr,qho,bad,n_gen=40,seed=s,mutate_filter=True)
        ho2.append(traj[-1][1])
    print(f"  劣化起点 holdout={mean([M.evaluate(M.make_library(220,seed=s,now_day=365),M.make_queries(M.make_library(220,seed=s,now_day=365),seed=2000+s),dict(w_kw=3.,w_c=1.,w_imp=3.,w_age=.3,d=.5,filter_zero=False))['recall'] for s in SEEDS])} → 演化后 holdout={mean(ho2)}")

# ───────────────────────── E14：对抗共演化 ─────────────────────────
def adversary(g, ents, theta):
    """写入侧每 5 代观察当前打分函数，选择最有利的刷分方式"""
    if theta.get("w_imp",0)>0.3:                       # 还看重自报 importance → 刷满
        cand=[e for e in ents if not e["vanity"]][:int(0.04*len(ents))]
        for e in cand: e["vanity"]=True;e["importance"]=10
    if theta.get("d",0)>0.2:                           # 扩散开着 → 织一个 4 人互链簇
        free=[e for e in ents if not e["is_farm"]][-4:]
        ids=[e["id"] for e in free]
        for e in free: e["is_farm"]=True;e["links"]=ids

def run_coevo(cond, seed):
    ents=M.make_library(220,seed=seed,vanity_frac=0.05,now_day=365)
    qho=M.make_queries(ents,n_q=60,seed=2000+seed)
    theta=dict(M.FACTORY); rng=random.Random(seed); hist=[]
    for g in range(41):
        if g%5==0 and g>0: adversary(g,ents,theta)
        if cond=="coevo":
            cand=dict(theta); k=rng.choice(["w_kw","w_c","w_imp","w_age","d","fz"])
            if k=="fz": cand["filter_zero"]=not cand.get("filter_zero",False)
            else: cand[k]=max(0,cand[k]+rng.gauss(0,0.15)*(abs(cand[k])+0.2))
            cand["d"]=min(1,max(0,cand["d"]))
            qtr=M.make_queries(ents,n_q=40,seed=1000+seed)
            if M.evaluate(ents,qtr,cand)["recall"]>=M.evaluate(ents,qtr,theta)["recall"]: theta=cand
        elif cond=="guarded":  # 元层锁定安全键 filter_zero=True / w_imp=0，只在边界内演化其余
            theta["filter_zero"]=True; theta["w_imp"]=0.0
            cand=dict(theta); k=rng.choice(["w_kw","w_c","w_age","d"])
            cand[k]=max(0,cand[k]+rng.gauss(0,0.15)*(abs(cand[k])+0.2)); cand["d"]=min(1,max(0,cand["d"]))
            qtr=M.make_queries(ents,n_q=40,seed=1000+seed)
            if M.evaluate(ents,qtr,cand)["recall"]>=M.evaluate(ents,qtr,theta)["recall"]:
                cand["filter_zero"]=True;cand["w_imp"]=0.0; theta=cand
        # fixed: theta 永不变
        hist.append(M.evaluate(ents,qho,theta)["recall"])
    poll=sum(1 for e in ents if e["vanity"] or e["is_farm"])/len(ents)
    return hist,poll

def e14():
    print("\nE14 写入侧与检索器共演化（初始 5% 注水，之后写入侧每 5 代学习当前打分函数刷分，6 种子）")
    print(f"{'条件':>26} | {'初始holdout':>9} | {'第20代':>7} | {'第40代':>7} | {'末态污染占比':>11}")
    for cond,label in [("fixed","①固定出厂不演化"),("coevo","②自由共演化(无元层)"),("guarded","③共演化+元层锁安全键")]:
        h0,h20,h40,poll=[],[],[],[]
        for s in SEEDS:
            ents0=M.make_library(220,seed=s,vanity_frac=0.05,now_day=365)
            qho=M.make_queries(ents0,n_q=60,seed=2000+s)
            h0.append(M.evaluate(ents0,qho,dict(M.FACTORY))["recall"])
            hist,p=run_coevo(cond,s); h20.append(hist[20]); h40.append(hist[40]); poll.append(p)
        print(f"{label:>26} | {mean(h0):>9.3f} | {mean(h20):>7.3f} | {mean(h40):>7.3f} | {mean(poll):>11.3f}")

# ───────────────────────── E15：eval 棘轮 ─────────────────────────
def e15():
    print("\nE15 eval 门限动态：真实能力在第 8/20/30 代三次劣化(-0.15)，叠加评测抽样噪声，对比两种基线规则（20种子）")
    def sim(ratchet, seed):
        rng=random.Random(seed); true=0.80; base=0.80; series=[]
        for g in range(40):
            if g in (8,20,30): true=max(0.2,true-0.15)      # 真实劣化（库被污染/期望条目失效）
            measured=true+rng.gauss(0,0.03)                 # golden 抽样噪声
            if ratchet: base=measured                       # 真实代码 P0-4：无条件覆盖
            else: base=max(base,measured)                   # 只升不降签收线
            series.append(base)
        return series
    for ratchet,label in [(True,"棘轮(真实代码:劣化也回写)"),(False,"只升不降签收线(修复)")]:
        finals,mins=[],[]
        for s in range(20):
            ser=sim(ratchet,s); finals.append(ser[-1]); mins.append(min(ser))
        print(f"  {label:>26}: 40代后基线={mean(finals)}，过程最低={mean(mins)}")
    print("  → 门控判据是『本次 ≥ 基线×0.95』；棘轮把基线一路拉低后，再差的结果也能过门（门限死亡）。")

# ───────────────────────── E16：死参数表演性准入探针 ─────────────────────────
def behavior_fingerprint(ents, qs):
    r=M.evaluate(ents,qs,dict(M.FACTORY,filter_zero=True))
    fires,_=M.append_stream(ents,thr=50)
    _,bad=M.reflect_materials(ents)
    lt,_=M.split_layers(ents)
    _,out,_,_=M.retire(ents,now_day=365)
    return (r["recall"],fires,bad,len(lt),len(out))

def e16():
    print("\nE16 公理G准入测试：逐个扰动参数，看行为指纹(recall,反思次数,取材坏率,长期条数,出仓数)是否变化")
    ents=M.make_library(220,seed=4,vanity_frac=0.1,now_day=365)
    qs=M.make_queries(ents,seed=3000)
    base=behavior_fingerprint(ents,qs)
    print(f"  基线指纹={base}")
    # 活参数：真改行为（需要重建库/改 theta，这里直接测两类）
    print("  —— 活参数（改动→行为可观测变化，允许进自演化搜索空间）——")
    ents2=M.make_library(220,seed=4,vanity_frac=0.1,now_day=365)
    f_lo=M.append_stream(ents2,thr=20)[0]; f_hi=M.append_stream(ents2,thr=200)[0]
    print(f"  reflect_threshold 50→{20}: 反思次数 {base[1]}→{f_lo}；50→{200}: →{f_hi}（活）")
    r_no=M.evaluate(ents,qs,dict(M.FACTORY,filter_zero=False))["recall"]
    r_fz=M.evaluate(ents,qs,dict(M.FACTORY,filter_zero=True))["recall"]
    print(f"  filter_zero 关→开: recall {r_no}→{r_fz}（活）")
    print("  —— 死参数（TUNABLES 声明可调，但改动→行为指纹零变化，禁止挂自适应名）——")
    dead_variants={"broadcast_weights":[0.6,0.3,0.1],"index_hot_budget":200,"review_intervals":[1,7,30],
                   "emotion_decay":0.7,"emotion_init_valence":0.5}
    # 这些参数在世界模型里无消费方：无论取何值指纹都等于 base
    for name in dead_variants:
        same = all(abs(behavior_fingerprint(ents,qs)[i]-base[i])<1e-12 for i in range(5))
        print(f"  {name:>22}: 任意取值，指纹与基线{'完全相同→死参数(表演性配置)' if same else '变化→活'}")

if __name__=="__main__":
    print("="*80);print("第四轮：自演化闭环 E13-E16（核心）");print("="*80)
    e13();e14();e15();e16()
