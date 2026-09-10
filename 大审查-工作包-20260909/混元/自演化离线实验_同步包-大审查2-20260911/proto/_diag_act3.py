"""真正的互补场景：系统会采纳（停摆不触发），但从不产生新配置

构造：变异在【表象维度】上永远变化，但在【有效维度】上不变。
  → child != parent 恒成立 → 我现在的 changed 计数会认为"有变化"
  → 需要更严的定义

更贴近 E149 mutate_dead 的场景其实是：
  mutate 返回父代 → child == parent → 采纳条件里
  judge(child) > judge(champion) 要求严格大于，恒等时不成立 → adopts=0

所以在本内核中 mutate_dead 天然导致 adopts=0，停摆也会触发。
→ 需要一个【只在部分维度失效】的变体：
   有效维度(w_kw/w_content/w_imp/w_age)不变，表象维度乱变
   → child != parent（我会计为变化）
   → 且 judge 分可能上升（表象权重被推高）→ 被采纳
   → 停摆不触发，但系统实际上在有效维度上完全没进步

这才是真正需要【维度级活跃度】的场景。
"""
import sys, random; sys.path.insert(0,'/data/workspace/proto')
import kernel as K
from vk_common import mk

CORE = ("w_kw", "w_content", "w_imp", "w_age")
SURF = ("w_len", "w_fmt", "w_den", "w_cit")

def run(seed, gens=16):
    kk = mk(seed, scale=2.0, activity=True, monitor=True)
    kk.margin = kk.cfg.margin
    orig = K.mutate
    def half_dead(p, rnd, scale):
        # 只在表象维度变异，核心维度冻结
        q = orig(p, rnd, scale)
        d = {k: getattr(q, k) for k in CORE}
        for k in SURF:
            d[k] = round(getattr(p, k) + rnd.choice([-0.5, 0.5]) * scale, 4)
        return K.Policy(**{**{k: getattr(p, k) for k in
                              ("filter_zero", "deep", "writalloc")}, **d})
    K.mutate = half_dead
    try:
        for g in range(1, gens+1):
            kk._step(g)
    finally:
        K.mutate = orig
    return sum(r.adopts for r in kk.reports), sum(kk._activity_hist), kk.activity_alerts

a, c, al = run(1)
print("核心维度冻结 + 表象维度变异：")
print("  总采纳=%d（停摆%s）  总变化=%d（活跃度%s）  告警=%d"
      % (a, "未触发" if a > 0 else "触发", c, "认为有变化" if c > 0 else "认为无变化", al))
