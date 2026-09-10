import sys; sys.path.insert(0,'/data/workspace/proto')
import run_e148 as R
import statistics
# 逐对比：baseline vs 三个"无差异"故障，逐个 seed 打印
for f in ("baseline", "audit_always", "audit_never", "budget_halve", "admit_always", "scale_spike"):
    v = R.res if hasattr(R,'res') else None
import json
r = json.load(open('/data/workspace/res_e148.json'))
for f in ("baseline","audit_always","audit_never","budget_halve","admit_always","scale_spike"):
    d = r[f+"_def"][:10]
    print("%-14s %s" % (f, " ".join("%+.3f"%x for x in d)))
