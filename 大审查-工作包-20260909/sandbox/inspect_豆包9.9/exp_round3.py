# -*- coding: utf-8 -*-
"""exp_round3.py — 第三轮 E9-E12：记忆生命周期
E9 长期层阈值7的ROC与被注水刷穿 E10 t_invalid错标与TTL两类错误 E11 hot_budget逐出策略 E12 全扫/索引/Merkle复杂度"""
import statistics as st, time
import mem_common as M

SEEDS=list(range(10))
def mean(x): return round(st.mean(x),3)

# ───────────────────────── E9：长期层阈值 ─────────────────────────
def layer_stats(ents, imp_key, thr, uses_gate=None):
    good=[e for e in ents if e["true_quality"]>=0.6]          # 金标准：真正值得长期
    bad=[e for e in ents if e["true_quality"]<0.6]
    def kept(e):
        if e[imp_key]<thr: return False
        if uses_gate is not None and e["uses"]<uses_gate: return False
        return True
    tpr=sum(kept(e) for e in good)/len(good)                  # 高价值留存率
    fpr=sum(kept(e) for e in bad)/len(bad)                    # 垃圾入库率
    longterm=[e for e in ents if kept(e)]
    prec=sum(e["true_quality"]>=0.6 for e in longterm)/max(1,len(longterm))
    return round(tpr,3),round(fpr,3),round(prec,3),len(longterm)

def e9():
    print("E9a 长期层 importance 阈值扫描（金标准 true_quality>=0.6）：高价值留存率/垃圾入库率/纯度")
    print("  —— 诚实自报 world ——")
    print(f"{'阈值':>4} | {'留存率TPR':>9} | {'垃圾率FPR':>9} | {'长期层纯度':>9} | {'长期条数':>7}")
    ents_h=M.make_library(400,seed=3,vanity_frac=0.0)
    for t in [3,5,7,9]:
        tpr,fpr,prec,n=layer_stats(ents_h,"importance",t)
        print(f"{t:>4} | {tpr:>9.3f} | {fpr:>9.3f} | {prec:>9.3f} | {n:>7}")
    print("  —— 20%注水 world（出厂单门 importance>=7）——")
    ents_v=M.make_library(400,seed=3,vanity_frac=0.20)
    for t in [5,7,9]:
        tpr,fpr,prec,n=layer_stats(ents_v,"importance",t)
        print(f"{t:>4} | {tpr:>9.3f} | {fpr:>9.3f} | {prec:>9.3f} | {n:>7}")
    print("  —— 治理：importance>=7 再加『历史复用 uses>=3』双门（20%注水 world）——")
    for ug in [None,1,3,8]:
        tpr,fpr,prec,n=layer_stats(ents_v,"importance",7,uses_gate=ug)
        print(f"{'双门uses>='+str(ug):>12} | {tpr:>9.3f} | {fpr:>9.3f} | {prec:>9.3f} | {n:>7}")

# ───────────────────────── E10：失效标记与 TTL ─────────────────────────
def e10():
    print("\nE10 t_invalid 错标下，固定TTL=90 vs 动态出仓 的两类错误（误杀真有效/漏放真失效，占总库比例，10种子）")
    print(f"{'错标率':>6} | {'策略':>8} | {'误杀真有效':>9} | {'漏放真失效':>9} | {'净留在库':>7}")
    for mf in [0.0,0.1,0.3]:
        for dyn,label in [(False,"固定TTL"),(True,"动态出仓")]:
            fk,mi,keep=[],[],[]
            for s in SEEDS:
                ents=M.make_library(400,seed=s,mislabel_frac=mf)
                k,out,false_kill,miss_inv=M.retire(ents,now_day=365,ttl=90,dynamic=dyn)
                tot=len(ents)
                fk.append(false_kill/tot); mi.append(miss_inv/tot); keep.append(len(k)/tot)
            print(f"{mf:>6.1f} | {label:>8} | {mean(fk):>9.3f} | {mean(mi):>9.3f} | {mean(keep):>7.3f}")
        print("  "+"-"*56)

# ───────────────────────── E11：hot_budget 逐出 ─────────────────────────
def e11():
    print("E11 库=600、热预算=200，四种逐出策略逐出后的 golden recall 保持率（相对不逐出）")
    print(f"{'注水':>5} | {'策略':>14} | {'逐出后recall':>10} | {'被逐高质量':>9} | {'留下注水条':>9}")
    for vf in [0.0,0.2]:
        base_rec={}
        for s in SEEDS:
            e=M.make_library(600,seed=s,vanity_frac=vf); base_rec[s]=M.evaluate(e,M.make_queries(e,seed=700+s),dict(M.FACTORY,filter_zero=True))["recall"]
        for pol,label in [("random","随机"),("lru","LRU(真实复用)"),("imp_time","重要度×时效(自报)"),("quality_oracle","真实质量上界")]:
            rec,killed_good,left_van=[],[],[]
            for s in SEEDS:
                e=M.make_library(600,seed=s,vanity_frac=vf)
                keep,out=M.evict_to_budget(e,200,pol)
                r=M.evaluate(keep,M.make_queries(e,seed=700+s),dict(M.FACTORY,filter_zero=True))["recall"]
                rec.append(r/max(1e-9,base_rec[s]))
                killed_good.append(sum(1 for x in out if x["true_quality"]>=0.6)/max(1,len(out)))
                left_van.append(sum(1 for x in keep if x["vanity"])/max(1,len(keep)))
            print(f"{vf:>5.1f} | {label:>14} | {mean(rec):>10.3f} | {mean(killed_good):>9.3f} | {mean(left_van):>9.3f}")
        print("  "+"-"*60)

# ───────────────────────── E12：规模复杂度 ─────────────────────────
def naive_scan_ms(ents, q, now=365):
    """复刻 _rank_entries：每次查询全扫全库打分（确定性操作量 + 真实计时）"""
    t0=time.perf_counter()
    scored={}
    for e in ents:
        kb=" ".join(e["keywords"]); cb=" ".join(e["content"])
        kw=sum(1 for w in q.split() if w in kb); c=sum(1 for w in q.split() if w in cb)
        if kw:c=max(c,1)
        scored[e["id"]]=3*kw+c+e["importance"]-0.1*(now-e["created_day"])
    sorted(scored.items(),key=lambda kv:-kv[1])
    return (time.perf_counter()-t0)*1000, len(ents)

def inverted_ms(ents,q):
    t0=time.perf_counter()
    # 预建倒排（在真实系统里建一次、增量维护；此处每次重建是为公平对比查询阶段，故分开计时）
    inv={}
    for e in ents:
        for w in set(e["keywords"]+e["content"]): inv.setdefault(w,[]).append(e["id"])
    t1=time.perf_counter()
    cand=set()
    for w in q.split(): cand.update(inv.get(w,()))
    t2=time.perf_counter()
    return (t2-t1)*1000, (t1-t0)*1000, len(cand)

def e12():
    print("E12a 单查询检索成本随库规模：全扫打分 vs 倒排候选（本机 ms，10 次均值；趋势比绝对值重要）")
    print(f"{'条目数':>6} | {'全扫/ms':>8} | {'倒排查询/ms':>10} | {'倒排候选数':>9}")
    q="召回 倒排"
    for n in [200,500,1000,2000,5000,10000]:
        ents=M.make_library(n,seed=5)
        ns=[naive_scan_ms(ents,q)[0] for _ in range(10)]
        iq=[inverted_ms(ents,q)[0] for _ in range(10)]
        cand=inverted_ms(ents,q)[2]
        print(f"{n:>6} | {round(st.mean(ns),3):>8.3f} | {round(st.mean(iq),4):>10.4f} | {cand:>9}")
    print("E12b 每次 append 全量重算 Merkle 的成本（读全库字节做哈希）→ N 次写累计 O(N²)")
    print(f"{'库规模':>6} | {'单次重算/ms':>10} | {'再写100条累计/ms':>14}")
    import hashlib
    for n in [200,1000,5000]:
        ents=M.make_library(n,seed=5)
        blobs=[(" ".join(e["keywords"]+e["content"])).encode() for e in ents]
        def once():
            t0=time.perf_counter()
            h=hashlib.sha256()
            for b in blobs: h.update(hashlib.sha256(b).digest())
            return (time.perf_counter()-t0)*1000
        one=st.mean([once() for _ in range(20)])
        print(f"{n:>6} | {round(one,3):>10.3f} | {round(one*100,2):>14.2f}")
    print("  → merkle_refresh_trigger=500 登记却从不读取(P2-17)：超过该规模应挂根/增量树，否则批量导入 O(N²)。")

if __name__=="__main__":
    print("="*80);print("第三轮：记忆生命周期（E9-E12）");print("="*80)
    e9();e10();e11();e12()
