"""构造：停摆监控失效但活跃度有效 的场景
思路：judge 恒等（子代得分总等于父代）→ d_tr=0 > margin? 
若 margin<0 或噪声使 d_tr 偶尔>0 → 会"采纳"，停摆不触发
但 child != parent 恒假 → 活跃度=0
"""
import sys, random; sys.path.insert(0,'/data/workspace/proto')
import kernel as K
from vk_common import mk

def run(seed, gens=16, margin=-0.5):
    """margin 为负 → 几乎任何子代都被'采纳' → 停摆监控永不触发"""
    kk = mk(seed, scale=2.0, activity=True, margin=margin, monitor=True)
    kk.margin = margin
    # 让变异恒返回父代 → 零变化
    orig = K.mutate
    K.mutate = lambda p, r, s: p
    try:
        for g in range(1, gens+1):
            kk._step(g)
    finally:
        K.mutate = orig
    return sum(r.adopts for r in kk.reports), sum(kk._activity_hist), kk.activity_alerts

a, c, al = run(1)
print("mutate_dead + margin<0（宽松采纳）:")
print("  总采纳=%d  总变化=%d  活跃度告警=%d" % (a, c, al))
print("  → 停摆监控%s触发；活跃度%s触发" % ("未" if a>0 else "已", "已" if al>0 else "未"))
