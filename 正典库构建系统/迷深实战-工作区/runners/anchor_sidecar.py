# -*- coding: utf-8 -*-
"""anchor_sidecar.py — 段收口锚归一旁车（U-C03 段收口 · 2026-09-19）。

背景：批11-17 部分子代理把 verified_against 锚到切片文件+内容哈希（582/2794），
偏离 U-C00 固化决议（path=clean_full.txt+git blob sha）。B5 旧件字节不动→旁车归一：
①机械验证：每个切片文件内容=边界表切行（语料子串）→ 切片哈希可信等价于语料锚；
②产出 anchor-normalization.jsonl：record_id → canonical 锚（corpus path+e1a96061），
保留原切片锚留痕。drift_check/R1 消费方按旁车视图对账。
用法：py -X utf8 anchor_sidecar.py [--verify-only]
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
ROOT = WORK.parent
CORPUS = ROOT.parent / "语料分析" / "corpus" / "clean_full.txt"
BT = WORK / "manifest" / "boundary-table-v1.json"
STORE = ROOT / "迷深实战-本体库"
OUT = WORK / "manifest" / "anchor-normalization.jsonl"
sys.path.insert(0, str(ROOT / "cbb" / "contracts"))
sys.path.insert(0, str(ROOT / "cbb" / "cbb-store"))
import cbb_store  # noqa: E402

CORPUS_CANONICAL = {"path": "语料分析/corpus/clean_full.txt",
                    "sha": "e1a96061d25b0016094dd8daec82769ee80fc3bb"}


def main(verify_only: bool = False) -> int:
    bt = json.loads(BT.read_text(encoding="utf-8"))
    by_no = {c["chapter_no"]: c for c in bt["chapters"]}
    corpus_lines = CORPUS.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # ① 收集切片锚记录与其所用切片文件
    store = cbb_store.ThreeStateStore(STORE)
    need, files = [], set()
    for r in store.iter_records():
        va = r.get("verified_against") or {}
        p = va.get("path") or ""
        if "clean_full" not in p and p:
            need.append({"record_id": r["record_id"], "orig_path": p, "orig_sha": va.get("sha")})
            files.add(p)
    # 切片路径两种形态：绝对（含 :\\）与相对（迷深实战-工作区/slice/chNNNN.txt）
    slice_root = WORK / "slice"
    resolved, unverifiable = {}, []
    for p in sorted(files):
        name = Path(p).name
        cand = slice_root / name
        if not cand.exists():
            unverifiable.append(p)
            continue
        resolved[p] = cand
    # ② 机械验证：切片内容 == 边界表行段（语料子串）
    verified, failed = {}, []
    for p, f in resolved.items():
        stem = f.stem
        ch_no = int("".join(ch for ch in stem if ch.isdigit()))
        ch = by_no.get(ch_no)
        if not ch:
            failed.append((p, "boundary_miss"))
            continue
        expect = "\n".join(corpus_lines[ch["marker_line"] - 1:ch["line_end"]])
        got = f.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
        if got == expect.rstrip("\n"):
            verified[p] = ch_no
        else:
            failed.append((p, f"content_mismatch_ch{ch_no:04d}"))
    report = {"n_records_offspec": len(need), "n_slice_files": len(files),
              "n_verified": len(verified), "n_unverifiable": unverifiable, "n_failed": failed,
              "corpus_canonical": CORPUS_CANONICAL}
    print(json.dumps({k: v for k, v in report.items() if k != "corpus_canonical"},
                     ensure_ascii=False, indent=1))
    if verify_only or failed or unverifiable:
        return 0 if not (failed or unverifiable) else 1
    # ③ 旁车落盘（幂等：重跑覆盖旁车=快照型产物，非 append-only 库件）
    rows = [{"record_id": n["record_id"],
             "orig": {"path": n["orig_path"], "sha": n["orig_sha"]},
             "canonical": dict(CORPUS_CANONICAL),
             "verified_via": f"slice⊂corpus@ch{verified.get(n['orig_path'], '?'):04d}"}
            for n in need if n["orig_path"] in verified]
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                           for r in rows), encoding="utf-8")
    print(json.dumps({"out": str(OUT), "n_rows": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(verify_only="--verify-only" in sys.argv))
