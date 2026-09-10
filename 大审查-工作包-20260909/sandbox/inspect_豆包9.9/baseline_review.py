# -*- coding: utf-8 -*-
"""baseline_review.py — 对朴素自演化记忆库原型做隔离动态探针，逐条复现机制缺口 D0-D8。
运行: python baseline_review.py  （纯标准库，约 1 秒）"""
import mem_common as M
from naive_memory import NaiveMemory

def build():
    ents = M.make_library(n=160, seed=1)
    return ents

def t_D1_importance_no_validate():
    """[D1] importance 无范围校验：自报 999 也被接受并直接进打分"""
    lib = NaiveMemory()
    lib.add({"id":"x","keywords":["召回"],"content":["召回","倒排"],"importance":999,"created_day":300,"links":[]})
    top = lib.search("召回", k=1)
    ok = top and top[0][1][0] > 900
    print(f"[{'CONFIRMED' if ok else 'NOT'}] D1 importance=999 被接受且检索分={top[0][1][0]:.1f}（无范围/类型校验，可注水）")

def t_D2_zero_hit_ranks():
    """[D2] 零词命中条目不过滤：一个词都不沾、仅 importance=10 的新条目能否压过相关条目"""
    lib = NaiveMemory()
    # 真相关：含查询词，但老、诚实 importance=3
    lib.add({"id":"relevant","keywords":["倒排","索引"],"content":["倒排","索引","召回"],"importance":3,"created_day":300,"links":[]})
    # 零命中：关键词/正文完全不含"倒排"，importance 刷满、很新
    lib.add({"id":"spam","keywords":["奖励","策略"],"content":["训练","梯度"],"importance":10,"created_day":360,"links":[]})
    top = [fid for fid,_ in lib.search("倒排 索引", k=2)]
    ok = top[0] == "spam"
    print(f"[{'CONFIRMED' if ok else 'NOT'}] D2 零命中条目 spam 排在真相关 relevant 之前（top2={top}）——importance 霸榜")

def t_D3_link_farm():
    """[D3] links 扩散：零命中条目靠互链簇的传播分上榜"""
    lib = NaiveMemory()
    lib.add({"id":"seed","keywords":["倒排"],"content":["倒排","召回"],"importance":6,"created_day":300,"links":["f1","f2","f3"]})
    for fid in ("f1","f2","f3"):  # 农场成员：词完全不沾，互链回 seed
        lib.add({"id":fid,"keywords":["因果"],"content":["反事实","混杂"],"importance":5,"created_day":300,"links":["seed"]})
    top = [fid for fid,_ in lib.search("倒排", k=4)]
    leaked = [x for x in ("f1","f2","f3") if x in top]
    print(f"[{'CONFIRMED' if leaked else 'NOT'}] D3 零语义相关的互链成员 {leaked} 靠扩散分进入结果（链接农场）")

def t_D4_chinese_split():
    """[D4] 中文无空格 split 退化：同一条目，空格分词 vs 整句，命中数差异"""
    e = {"id":"z","keywords":["记忆","检索","衰减"],"content":["记忆","检索","衰减","复盘"],"importance":3,"created_day":300,"links":[]}
    lib = NaiveMemory(); lib.add(e)
    spaced = lib.search("记忆 检索", k=1)[0][1][0]
    glued = lib.search("记忆检索", k=1)[0][1][0]
    print(f"[{'CONFIRMED' if glued < spaced else 'NOT'}] D4 同查询『记忆检索』空格分={spaced:.1f} vs 无空格整句分={glued:.1f}（split 退化）")

def t_D5_reflect_gamed():
    """[D5] 反思取材被自报 importance 支配：注水条目占据 top6"""
    ents = M.make_library(n=60, seed=2, vanity_frac=0.2)
    lib = NaiveMemory()
    for e in ents: lib.add(e)
    lib.accum = 60
    top = lib.maybe_reflect()
    vanity_in_top = sum(1 for e in top if e["vanity"])
    print(f"[{'CONFIRMED' if vanity_in_top>=4 else 'NOT'}] D5 反思 top6 中注水条目 {vanity_in_top}/6（取材被自报值支配）")

def t_D6_ratchet():
    """[D6] eval 基线棘轮：劣化结果无条件覆盖历史最佳，门限被逐代拉低"""
    lib = NaiveMemory()
    gold = [{"query":"召回 倒排","expected":["a"]}]
    lib.add({"id":"a","keywords":["召回","倒排"],"content":["召回"],"importance":5,"created_day":300,"links":[]})
    b1 = lib.run_eval(gold)                       # 正常：命中=1.0
    # 让目标条目失效 → 召回跌到 0
    lib.ents["a"]["t_invalid"] = 200
    b2 = lib.run_eval(gold)                        # 0.0 覆盖 1.0
    b3 = lib.run_eval(gold)                        # 相对 0.0 "未劣化"即过门
    ok = (b1 == 1.0 and b2 == 0.0 and lib.baseline == 0.0)
    print(f"[{'CONFIRMED' if ok else 'NOT'}] D6 基线 {b1:.2f}→劣化后 {b2:.2f} 被写回，再跑 {b3:.2f} 即'不再劣化'过门（棘轮无下界）")

def t_D7_dead_params():
    """[D7] 死参数：改 broadcast_weights/hot_budget 对检索结果零影响（公理 G：测不出差异=表演）"""
    lib = NaiveMemory(); lib.add({"id":"a","keywords":["召回"],"content":["召回"],"importance":5,"created_day":300,"links":[]})
    r1 = [x[1][0] for x in lib.search("召回")]
    lib.TUNABLES["broadcast_weights"] = [0.9,0.1,0.0]; lib.TUNABLES["index_hot_budget"] = 1
    r2 = [x[1][0] for x in lib.search("召回")]
    print(f"[{'CONFIRMED' if r1==r2 else 'NOT'}] D7 改动两个宣称可调参数，检索分 {r1}→{r2} 零变化（死参数）")

def t_D8_fixed_ttl():
    """[D8] 固定 TTL 只认 t_invalid 标记：错标会误杀/漏放（统计在 E10 展开，此处证机制）"""
    lib = NaiveMemory()
    lib.add({"id":"good_but_mislabeled","keywords":["a"],"content":["a"],"importance":8,"created_day":10,"t_invalid":20,"links":[]})  # 高质量却被错标失效
    lib.add({"id":"bad_no_label","keywords":["b"],"content":["b"],"importance":2,"created_day":10,"links":[]})                      # 低质量不标
    out = lib.retire(now=200, ttl=90)
    killed = [e["id"] for e in out]
    print(f"[{'CONFIRMED' if 'good_but_mislabeled' in killed else 'NOT'}] D8 高质量条目仅因错标被 TTL 出仓（{killed}），低质量无标条目永留")

if __name__ == "__main__":
    print("="*78); print("朴素自演化记忆库原型 · 机制缺口探针（D0-D8）"); print("="*78)
    for fn in [t_D1_importance_no_validate, t_D2_zero_hit_ranks, t_D3_link_farm, t_D4_chinese_split,
               t_D5_reflect_gamed, t_D6_ratchet, t_D7_dead_params, t_D8_fixed_ttl]:
        fn()
    print("-"*78); print("说明：CONFIRMED=缺口在隔离世界模型中复现；这些缺口的【动态后果与治理】由 E1-E19 量化。")
