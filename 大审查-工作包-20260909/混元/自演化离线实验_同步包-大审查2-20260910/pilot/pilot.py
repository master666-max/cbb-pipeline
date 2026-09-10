"""自演化试点 · 探针（S0 影子期）

★ 设计目标：零风险、零依赖、可丢进任何 Python 环境。
   - 只用标准库
   - 不改变系统任何行为（只记录）
   - 记录的是【系统本来就有的可观测量】：检索了什么、哪个真被采纳了

为什么先做影子期（实验依据）：
  E32  重要性应【实测】（被检索后是否被采纳），而不是条目自称的数字。
       系统本就有 (shown, adopted) 记录 → 零新增标注成本。
  E64  注意力预算 <150 时自演化终局恒为负 → 必须先算清预算再决定开不开。
  E17  n=10 时假阳性率 42% → 必须先估信号强度，再谈演化。
  E105 把预算全投在审计上是负收益 → 影子期先攒燃料，不花预算。

用法（三行接入）：
    from pilot import Pilot
    P = Pilot("./traces.jsonl")
    result = P.wrap(lambda q: my_retrieve(q, k=5))(query)   # 行为完全不变
    P.adopt(result[0].id)      # 在你的业务代码里，用户/下游真用了它时调一次

也可以手工记：
    P.log(query, [{"id":..,"feat":{...}}], adopted_id=None)
"""
from __future__ import annotations
import json, time, hashlib, os, random, threading
from typing import Any, Dict, List, Optional, Callable


def _hash(x: str, salt: str = "") -> str:
    """条目/查询 id 脱敏（可选）。默认开启，避免把业务数据带出环境。"""
    return hashlib.sha256((salt + str(x)).encode()).hexdigest()[:16]


class Pilot:
    """影子期探针：只记录，不改行为。"""

    VERSION = "1.0"

    def __init__(self, path: str = "./traces.jsonl",
                 salt: str = "", anonymize: bool = True,
                 max_bytes: int = 200 * 1024 * 1024):
        self.path = path
        self.salt = salt
        self.anonymize = anonymize
        self.max_bytes = max_bytes
        self._lock = threading.Lock()
        self._seq = 0
        self._recent: List[int] = []          # 最近未结算的 seq（环形，上限 512）
        self._cand_of: Dict[int, List[dict]] = {}
        self._adopted_seqs: set = set()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    # ── 核心记录 ──
    def log(self, query: str, candidates: List[Dict[str, Any]],
            adopted_id: Optional[str] = None, extra: Optional[dict] = None):
        """记录一次检索及后续采纳情况。

        candidates: [{"id":..., "feat":{特征名:数值}}, ...]  ← 按你的排序给
        adopted_id: 真正被采纳的 id；None = 都没被采纳
        """
        with self._lock:
            self._seq += 1
            rec = {
                "v": self.VERSION,
                "ts": round(time.time(), 3),
                "seq": self._seq,
                "q": _hash(query, self.salt) if self.anonymize else query,
                "cand": [
                    {"id": (_hash(c["id"], self.salt) if self.anonymize else c["id"]),
                     "f": {k: round(float(v), 4) for k, v in (c.get("feat") or {}).items()}}
                    for c in candidates
                ],
                "adopted": (_hash(adopted_id, self.salt)
                            if (adopted_id is not None and self.anonymize)
                            else adopted_id),
            }
            if extra:
                rec["x"] = extra
            self._recent.append(self._seq)
            self._cand_of[self._seq] = rec["cand"]
            if len(self._recent) > 512:
                old = self._recent.pop(0)
                self._cand_of.pop(old, None)
            try:
                if os.path.getsize(self.path) < self.max_bytes:
                    with open(self.path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except OSError:
                pass
        return rec

    def adopt(self, item_id: str, query: Optional[str] = None) -> bool:
        """在业务代码里：确认某条目真被采用了时调用。

        ★ 采纳发生在检索【之后】，所以要回补到刚才那条记录上。
          做法：append-only 地写一条 amend 记录，分析器负责合并。
          （不改写已落盘的行——追加比改写安全，也便于事后审计）

        返回是否成功关联到某次检索。
        """
        key = _hash(item_id, self.salt) if self.anonymize else item_id
        with self._lock:
            seq = None
            for s in reversed(self._recent):
                if any(c["id"] == key for c in self._cand_of.get(s, [])):
                    seq = s
                    break
            if seq is None and self._recent:
                seq = self._recent[-1]        # 兜底：挂到最近一次检索
            if seq is None:
                return False
            rec = {"v": self.VERSION, "ts": round(time.time(), 3),
                   "amend_seq": seq, "adopted": key}
            try:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except OSError:
                return False
            self._adopted_seqs.add(seq)
            return True

    # ── 零改动接入 ──
    def wrap(self, retrieve_fn: Callable[[str], List[Any]],
             id_of=lambda x: getattr(x, "id", None) or str(x),
             feat_of=lambda x: {}):
        """包装你的检索函数，行为完全不变，只旁路记录。"""
        def wrapped(query, *a, **kw):
            t0 = time.time()
            out = retrieve_fn(query, *a, **kw)
            try:
                self.log(query, [{"id": id_of(x), "feat": feat_of(x)} for x in out])
            except Exception:
                pass          # ★ 记录失败绝不能影响业务
            return out
        return wrapped

    # ── 自检 ──
    def stats(self) -> Dict[str, Any]:
        n = 0
        adopted = 0
        feats = set()
        try:
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    if r.get("amend_seq"):
                        adopted += 1
                        continue
                    n += 1
                    if r.get("adopted"):
                        adopted += 1
                    for c in r.get("cand", []):
                        feats |= set((c.get("f") or {}).keys())
        except FileNotFoundError:
            pass
        return {"traces": n, "adopted": adopted,
                "adopt_rate": round(adopted / n, 4) if n else 0.0,
                "features": sorted(feats),
                "path": os.path.abspath(self.path)}
