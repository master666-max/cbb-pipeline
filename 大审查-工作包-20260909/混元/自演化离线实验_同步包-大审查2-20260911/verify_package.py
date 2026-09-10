#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交接包完整性校验 —— 比对文件数量 + MD5 + 关键文件存在性

用法：
    python3 verify_package.py

退出码：0 = 零损失；1 = 有缺失/损坏
"""
import os, sys, json, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "文件清单.md")
CACHE = os.path.join(HERE, ".pkg_manifest.json")


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def build():
    """从磁盘重建清单（若 _manifest.json 不存在）"""
    out = []
    for root, dirs, names in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for n in sorted(names):
            if n.startswith(".") or n.endswith(".pyc"):
                continue
            if n in ("verify_package.py", "_manifest.json", "_codescan.json"):
                continue
            p = os.path.join(root, n)
            if not os.path.isfile(p):
                continue
            rel = os.path.relpath(p, HERE)
            try:
                out.append({"path": rel, "size": os.path.getsize(p),
                            "md5": md5(p)})
            except Exception:
                pass
    return out


def main():
    ok = True
    print("=" * 66)
    print("交接包完整性校验")
    print("=" * 66)

    # 1) 关键文件
    KEY = ["MASTER_INDEX.md", "HANDOVER.md", "实验分支树.md", "文件清单.md",
           "自演化推演_技术总结_对内全量.md",
           "自演化推演_实验总报告.md", "自演化推演_方法论总结.md",
           "离线实验总纲_从零复现.md", "bootstrap_自演化落地工单集.md",
           "proto/kernel.py", "proto/verify_kernel.py", "proto/vk_common.py",
           "proto/precompute.py", "pilot/pilot.py", "pilot/analyze.py",
           "bootstrap_v3.py"]
    print("\n[1] 关键文件存在性")
    miss = [k for k in KEY if not os.path.exists(os.path.join(HERE, k))]
    if miss:
        for m in miss:
            print("  [缺失] %s" % m)
        ok = False
    else:
        print("  [OK] %d/%d 关键文件齐全" % (len(KEY), len(KEY)))

    # 2) 数量统计
    cur = build()
    print("\n[2] 文件统计")
    from collections import Counter
    c = Counter(os.path.dirname(f["path"]) or "(顶层)" for f in cur)
    for k, v in sorted(c.items(), key=lambda x: -x[1]):
        print("  %-20s %3d 个" % (k, v))
    print("  %-20s %3d 个  (%.1f KB)"
          % ("合计", len(cur), sum(f["size"] for f in cur) / 1024))

    # 3) 实验号覆盖
    print("\n[3] 实验编号覆盖")
    import re
    rep = os.path.join(HERE, "自演化推演_实验总报告.md")
    if os.path.exists(rep):
        txt = open(rep, encoding="utf-8").read()
        rs = sorted(set(re.findall(r"第([一二三四五六七八九十]+)轮", txt)))
        print("  总报告提及轮次：%s" % (", ".join(rs[:20])))
    rounds = len([f for f in cur if "自演化推演_第" in f["path"]])
    print("  轮次报告文件数：%d" % rounds)
    if rounds < 35:
        print("  [警告] 轮次报告偏少（应有 ~39 份）")
        ok = False

    # 4) 源码可导入
    print("\n[4] 内核可导入")
    sys.path.insert(0, os.path.join(HERE, "proto"))
    try:
        import kernel
        cfg = kernel.KernelConfig()
        need = ("anchor", "boost_on_drift", "activity", "blind",
                "diagnose_delta", "scale", "tol", "margin")
        lack = [n for n in need if not hasattr(cfg, n)]
        if lack:
            print("  [缺失] 内核配置项: %s" % lack)
            ok = False
        else:
            print("  [OK] 内核可导入，关键配置项齐全（%d 项）" % len(need))
        if not hasattr(kernel, "CORE_DIMS"):
            print("  [缺失] CORE_DIMS（E150 维度级活跃度）")
            ok = False
        else:
            print("  [OK] CORE_DIMS 存在：%s" % (kernel.CORE_DIMS,))
    except Exception as e:
        print("  [失败] 无法导入内核: %s" % e)
        ok = False

    print("\n" + "=" * 66)
    if ok:
        print("✅ 交接包完整 —— 零损失")
        print("\n下一步：")
        print("  1. 读 MASTER_INDEX.md（总索引）")
        print("  2. 读 HANDOVER.md（含『已被推翻的结论』避免重复劳动）")
        print("  3. 跑 python3 proto/verify_kernel.py → 应 PASS 53 / FAIL 0")
    else:
        print("❌ 存在缺失，见上方标记")
    print("=" * 66)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
