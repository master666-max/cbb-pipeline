# -*- coding: utf-8 -*-
"""exp_round5.py — 第五轮 E17-E19：评测可信度、元层边界、综合治理
E17 golden规模过拟合与显著margin E18 元层冻结必要性(改考题) E19 三治理水平综合压测"""
import statistics as st, random
import mem_common as M

SEEDS=list(range(5))
def mean(x): return round(st.mean(x),3)
def sd(x): return round(st.pstdev(x),3)

# ───────────────────────── E17：golden 规模 / 过拟合 / margin ─────────────────────────
def e17():
    print("E17a 在不同规模 train-golden 上演化 25 代，对比独立大留出集(200题)：过拟合 gap=train-holdout")
    print(f"{'train题数':>8} | {'train终值':>9} | {'独立holdout':>10} | {'过拟合gap':>9}")
    for nt in [5,10,20,40,80]:
        tr,ho=[],[]
        for s in SEEDS:
            ents=M.make_library(220,seed=s,now_day=365)
            qtr=M.make_queries(ents,n_q=nt,seed=1000+s)
            qbig=M.make_queries(ents,n_q=200,seed=9000)
            traj=M.evolve(ents,qtr,qbig,dict(M.FACTORY),n_gen=25,seed=s,mutate_filter=True)
            tr.append(traj[-1][0]);ho.append(traj[-1][1])
        print(f"{nt:>8} | {mean(tr):>9.3f} | {mean(ho):>10.3f} | {round(mean(tr)-mean(ho),3):>9.3f}")
    print("E17b 评测抽样噪声：同一固定检索器，独立抽 m 题评测，重复100次的 recall 标准差与95%半宽")
    ents=M.make_library(220,seed=0,now_day=365); th=dict(M.FACTORY,filter_zero=True)
    print(f"{'抽题数m':>7} | {'recall均值':>9} | {'标准差sd':>8} | {'95%半宽1.96sd':>12} | {'真改进需超过':>10}")
    for m in [10,20,40,80]:
        vals=[]
        for b in range(100):
            q=M.make_queries(ents,n_q=m,seed=5000+b)
            vals.append(M.evaluate(ents,q,th)["recall"])
        s=st.pstdev(vals)
        print(f"{m:>7} | {round(st.mean(vals),3):>9.3f} | {round(s,3):>8.3f} | {round(1.96*s,3):>12.3f} | {round(2*s,3):>10.3f}")

# ───────────────────────── E18：元层冻结必要性（改考题）─────────────────────────
def e18():
    print("\nE18 困难世界(30%注水+4链接农场，正路调参天花板有限)下自演化 40 代：")
    print("    (a)只能调法层、golden冻结；(b)每代变异参数后，可把『错题标准答案改成自己的top1』再决定是否接受")
    print("    hidden=引擎永远看不到、也改不到的独立留出题。机制：标准答案可被自身输出重写时，参数失去梯度→随机漂移")
    def run(can_edit_golden, seed):
        rng=random.Random(seed)
        ents=M.make_library(220,seed=seed,vanity_frac=0.30,farm_clusters=4,farm_size=5,now_day=365)
        def fresh(qs): return [{"query":q["query"],"expected":list(q["expected"])} for q in qs]
        train=fresh(M.make_queries(ents,n_q=40,seed=1000+seed))
        hidden=M.make_queries(ents,n_q=100,seed=9000)
        theta=dict(M.FACTORY); ev=lambda t,qs:M.evaluate(ents,qs,t)["recall"]
        for g in range(40):
            cand=dict(theta); k=rng.choice(["w_kw","w_c","w_imp","w_age","d","fz"])
            if k=="fz": cand["filter_zero"]=not cand.get("filter_zero",False)
            else: cand[k]=max(0,cand[k]+rng.gauss(0,.2)*(abs(cand[k])+.2))
            cand["d"]=min(1,max(0,cand["d"]))
            if can_edit_golden:
                tb=fresh(train)                       # 在候选参数下把错题标准答案改成自己的输出
                for q in tb:
                    top=M.rank(ents,q["query"],cand)
                    if top and top[0][0] not in q["expected"]: q["expected"]=[top[0][0]]
                if ev(cand,tb)>=ev(theta,train): theta,train=cand,tb   # 改题后恒≈满分→任何漂移都被接受
            else:
                if ev(cand,train)>=ev(theta,train): theta=cand          # 只有真提分才接受→参数向好
        return ev(theta,train), ev(theta,hidden)
    print(f"{'权力边界':>30} | {'训练题终值':>9} | {'隐藏题终值':>9} | {'诚信缺口':>8}")
    for edit,label in [(False,"(a)法层可演化,golden冻结"),(True,"(b)法层+golden都可改")]:
        tr,ho=[],[]
        for s in SEEDS:
            a,b=run(edit,s);tr.append(a);ho.append(b)
        print(f"{label:>30} | {mean(tr):>9.3f} | {mean(ho):>9.3f} | {round(mean(tr)-mean(ho),3):>8.3f}")
    print("  → (b)训练分被重写的标准答案抬到接近满分，参数却因失去外部梯度而随机漂移、隐藏题劣化；")
    print("    对应 DGM(Appendix F) Node114：评测题/铁律/验收必须对变异引擎只读不可见、冻结于元层，引擎只收 pass/fail。")

# ───────────────────────── E19：综合治理压测 ─────────────────────────
def harsh_world(seed):
    return M.make_library(240,seed=seed,vanity_frac=0.20,farm_clusters=4,farm_size=5,
                          mislabel_frac=0.2,now_day=365)

def attack(ents,theta):
    if theta.get("w_imp",1)>0.3:
        for e in [x for x in ents if not x["vanity"]][:8]: e["vanity"]=True;e["importance"]=10
    if theta.get("d",0.5)>0.2:
        free=[e for e in ents if not e["is_farm"]][-4:]; ids=[e["id"] for e in free]
        for e in free: e["is_farm"]=True;e["links"]=ids

def evolve_guarded(ents,theta,rng,lock):
    cand=dict(theta); k=rng.choice(["w_kw","w_c","w_age","d"] if lock else ["w_kw","w_c","w_imp","w_age","d","fz"])
    if k=="fz": cand["filter_zero"]=not cand.get("filter_zero",False)
    else: cand[k]=max(0,cand[k]+rng.gauss(0,.15)*(abs(cand[k])+.2))
    cand["d"]=min(1,max(0,cand["d"]))
    if lock: cand["filter_zero"]=True;cand["w_imp"]=0.0
    q=M.make_queries(ents,n_q=20,seed=1234)
    if M.evaluate(ents,q,cand)["recall"]>=M.evaluate(ents,q,theta)["recall"]:
        if lock: cand["filter_zero"]=True;cand["w_imp"]=0.0
        theta=cand
    return theta

def e19():
    print("\nE19 复合恶劣世界(20%注水+4链接农场+20%错标+仅20题golden)，40代攻防，三治理水平终态对比（5种子）")
    print(f"{'治理水平':>10} | {'holdout':>7} | {'库污染率':>7} | {'长期层纯度':>9} | {'反思取材坏率':>11}")
    for level in ["L0","L1","L2"]:
        H,P,LTP,MB=[],[],[],[]
        for s in SEEDS:
            ents=harsh_world(s); rng=random.Random(s)
            hidden=M.make_queries(ents,n_q=100,seed=8000+s)
            theta=dict(M.FACTORY)
            if level=="L1": theta["filter_zero"]=True
            if level=="L2": theta["filter_zero"]=True; theta["w_imp"]=0.0
            for g in range(41):
                if g%5==0 and g>0: attack(ents,theta)
                if level!="L0": theta=evolve_guarded(ents,theta,rng,lock=(level=="L2"))
            H.append(M.evaluate(ents,hidden,theta)["recall"])
            P.append(sum(1 for e in ents if e["vanity"] or e["is_farm"])/len(ents))
            # 长期层纯度
            if level=="L2":  # 双门 uses>=3
                lt=[e for e in ents if e["importance"]>=7 and e["uses"]>=3]
            else:
                lt=[e for e in ents if e["importance"]>=7]
            LTP.append(sum(e["true_quality"]>=0.6 for e in lt)/max(1,len(lt)))
            # 反思取材坏率
            if level=="L2":
                top=sorted(ents,key=lambda e:-(e["uses"]+0.3*e["honest_imp"]))[:6]
            else:
                top=sorted(ents,key=lambda e:-e["importance"])[:6]
            MB.append(sum(1 for e in top if e["vanity"] or e["is_farm"] or e["truly_invalid"])/6)
        name={"L0":"L0 无治理","L1":"L1 部分(filter+演化)","L2":"L2 全治理(元层锁+uses)"}[level]
        print(f"{name:>10} | {mean(H):>7.3f} | {mean(P):>7.3f} | {mean(LTP):>9.3f} | {mean(MB):>11.3f}")
    print("  L0:出厂固定/零命中不过滤/自报取材/单门  L1:+filter_zero+允许演化  L2:+元层锁安全键+uses取材/双门分层")

if __name__=="__main__":
    print("="*80);print("第五轮：评测可信度、元层边界、综合治理（E17-E19）");print("="*80)
    e17();e18();e19()
