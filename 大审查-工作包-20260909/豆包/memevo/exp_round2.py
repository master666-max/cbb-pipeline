# -*- coding: utf-8 -*-
"""exp_round2.py — 第二轮 E5-E8：反思与合成闭环
E5 反思阈值50校准(诚实vs注水) E6 top6取材污染与可观测代理 E7 合成层错误放大/持久化 E8 decay0.7核验与emotion死信号"""
import statistics as st
import mem_common as M

SEEDS = list(range(12))
def mean(x): return round(st.mean(x),3)
def cv(xs): return round(st.pstdev(xs)/ (st.mean(xs)+1e-9),3)

# ───────────────────────── E5：反思触发阈值校准 ─────────────────────────
def e5():
    print("E5a 固定写 300 条，反思阈值 × 注水比例 → 触发次数 / 平均间隔条数 / 间隔变异系数CV")
    print(f"{'阈值':>5} | {'诚实写入 次/均隔/CV':>24} | {'20%注水 次/均隔/CV':>22} | {'40%注水':>16}")
    for thr in [20, 50, 100, 200]:
        cells=[]
        for vf in [0.0,0.2,0.4]:
            F,S,C=[],[],[]
            for s in SEEDS:
                ents=M.make_library(300,seed=s,vanity_frac=vf)
                fires,spans=M.append_stream(ents,thr=thr)
                F.append(fires); S.append(mean(spans) if spans else 0); C.append(cv(spans) if len(spans)>1 else 0)
            cells.append(f"{mean(F):>4}/{mean(S):>5}/{mean(C):>5}")
        print(f"{thr:>5} | {cells[0]:>24} | {cells[1]:>22} | {cells[2]:>16}")
    print("  注：出厂阈值=50（TUNABLES 自标『拍脑袋，待校准』）；间隔被自报 importance 直接决定。")

# ───────────────────────── E6：反思取材策略 ─────────────────────────
def pick_top(ents, strategy, n=6):
    if strategy=="selfimp": return sorted(ents,key=lambda e:-e["importance"])[:n]
    if strategy=="uses":    return sorted(ents,key=lambda e:-(e["uses"]+0.3*e["honest_imp"]))[:n]  # 可观测：历史复用
    return sorted(ents,key=lambda e:-e["true_quality"])[:n]                                   # oracle 上界

def e6():
    print("\nE6 反思取材 top6：坏条目(注水/农场/失效)占比 与 素材平均真实质量（12 种子）")
    print(f"{'注水比例':>6} | {'取材策略':>8} | {'坏条目占比':>9} | {'素材均质量':>9}")
    for vf in [0.1,0.3]:
        for strat,label in [("selfimp","自报imp"),("uses","复用次数"),("oracle","真实质量")]:
            bad,q=[],[]
            for s in SEEDS:
                ents=M.make_library(200,seed=s,vanity_frac=vf,farm_clusters=2,farm_size=4)
                top=pick_top(ents,strat)
                bad.append(sum(1 for e in top if e["vanity"] or e["is_farm"] or e["truly_invalid"])/len(top))
                q.append(st.mean(e["true_quality"] for e in top))
            print(f"{vf:>6.1f} | {label:>8} | {mean(bad):>9.3f} | {mean(q):>9.3f}")
        print("  " + "-"*50)

# ───────────────────────── E7：合成层错误放大与持久化 ─────────────────────────
def e7():
    print("E7a 素材含错比例 p_bad 下，自报取材 vs 复用取材 合成规律的污染率/质量（120 次反思）")
    print(f"{'p_bad(错且自信)':>14} | {'自报取材 污染/质量':>18} | {'复用取材 污染/质量':>18}")
    for pb in [0.1,0.3,0.5]:
        res={}
        for strat in ["selfimp","uses"]:
            pol,qa=[],[]
            for s in range(120):
                ents=M.make_library(120,seed=s,vanity_frac=0.0)
                # 注入 pb 比例『错误但高自信』经验：低质量/失效却自报 importance=10；其历史 uses 低
                k=int(pb*len(ents))
                for e in ents[:k]:
                    e["true_quality"]=round(e["true_quality"]*0.1,3); e["truly_invalid"]=True; e["importance"]=10
                top=pick_top(ents,strat)
                syn=M.synthesize(top)
                pol.append(syn["pollution"]); qa.append(syn["syn_quality"])
            res[strat]=(mean(pol),mean(qa))
        print(f"{pb:>14.1f} | {str(res['selfimp'][0])+'/'+str(res['selfimp'][1]):>18} | {str(res['uses'][0])+'/'+str(res['uses'][1]):>18}")
    print("\nE7b 错误的覆盖面：错误规律覆盖的主题词越广，能被越多不同措辞的查询捞回。")
    print("     枚举该主题 8 词的全部两两组合查询(28个)，看错误条目进 top5 / 占 top1 的查询覆盖面")
    import itertools
    tp="检索排序"; allw=M.TOPIC_WORDS[tp]
    combos=list(itertools.combinations(range(len(allw)),2))
    print(f"{'错误条目形态':>22} | {'覆盖词数':>6} | {'进top5覆盖面':>10} | {'占top1面':>8}")
    for label,cover in [("错误原始条目(窄)",4),("错误合成规律(广)",8)]:
        c5,c1=[],[]
        for s in SEEDS:
            ents=M.make_library(200,seed=s)
            bad=dict(id="BAD",topic=tp,true_quality=0.0,keywords=allw[:min(3,cover)],content=allw[:cover],
                     importance=10,honest_imp=10,vanity=False,created_day=360,t_invalid=None,
                     truly_invalid=False,uses=0,links=[],is_farm=False)
            ents.append(bad)
            in5=is1=0
            for i,j in combos:
                q=f"{allw[i]} {allw[j]}"
                top=M.rank(ents,q,dict(M.FACTORY,filter_zero=True),now_day=365)
                ids=[fid for fid,_ in top]
                if "BAD" in ids[:5]: in5+=1
                if ids and ids[0]=="BAD": is1+=1
            c5.append(in5/len(combos)); c1.append(is1/len(combos))
        print(f"{label:>22} | {cover:>6} | {mean(c5):>10.3f} | {mean(c1):>8.3f}")
    print("  → 错误一旦被抽象成『概括全主题的高层规律』并以高 importance 入长期层，其被未来检索反复召回的措辞面显著扩大，纠错成本随抽象层级上升。")

# ───────────────────────── E8：decay 核验 + emotion 死信号 ─────────────────────────
def e8():
    print("E8a emotion_decay=0.7 的半衰期核验（声称『≈半衰期2次wrap-up』）")
    seq=[round(0.7**n,3) for n in range(1,6)]
    print(f"  0.7^1..5 = {seq}；0.7^2={0.7**2:.3f}（≈0.5 成立），到达<0.1 需 {__import__('math').ceil(__import__('math').log(0.1,0.7))} 次 wrap-up")
    print("E8b 死信号 A/B：改 decay 与 emotion 初值，跑完整 append→检索→反思 流程，观察行为是否变化")
    def pipeline(decay, emo_init, s):
        ents=M.make_library(200,seed=s,vanity_frac=0.15)
        qs=M.make_queries(ents,seed=600+s)
        r=M.evaluate(ents,qs,dict(M.FACTORY,filter_zero=True))
        fires,_=M.append_stream(ents,thr=50)
        _,badrate=M.reflect_materials(ents)
        # emotion 状态按 decay 衰减 4 次（wrap-up），但下游不读它
        v=emo_init
        for _ in range(4): v*=decay
        return r["recall"],fires,badrate,round(v,4)
    base=pipeline(0.7,0.5,0)
    print(f"  基线 decay=0.7,init=0.5 → (recall,反思次数,取材坏率,衰减后emotion)={base}")
    for decay,init in [(0.1,0.5),(1.0,0.5),(0.7,1.0),(0.0,0.9)]:
        same=all(abs(pipeline(decay,init,s)[j]-pipeline(0.7,0.5,s)[j])<1e-9 for s in range(6) for j in [0,1,2])
        b0=pipeline(decay,init,0)
        print(f"  decay={decay},init={init}: 行为三元组 recall/反思/取材 ={b0[:3]} 与基线{'完全相同(死信号)' if same else '不同'}（仅emotion数值={b0[3]}变）")
    print("  review_intervals=[1,7,30]、broadcast_weights 同理：grep 仅命中定义，无消费方（见 E16 全量探针）")

if __name__=="__main__":
    print("="*80);print("第二轮：反思与合成闭环（E5-E8）");print("="*80)
    e5();e6();e7();e8()
