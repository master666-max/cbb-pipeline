# -*- coding: utf-8 -*-
"""build_index_v2.py — U-F07 v2 富文本索引构建（可断点续传：进度落盘 sidecar，重跑跳过已完成）"""
import importlib
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys_path = str(HERE)
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)

m = importlib.import_module("neo4j_export")
STORE = HERE.parent.parent / "迷深实战-本体库"      # cbb/tools → cbb → 项目根
IDX = HERE.parent.parent / "迷深实战-工作区" / "索引" / "lancedb"
PROG = HERE.parent.parent / "迷深实战-工作区" / "索引" / "_embed-progress.jsonl"
EMB = "http://127.0.0.1:8080/v1/embeddings"
BATCH = 8
TIMEOUT = 300


def main() -> int:
    g = m.collect_graph(STORE)
    rows, seen = [], set()
    for n in g["nodes"]:
        if n["record_id"] in seen or not n["name"].strip():
            continue
        seen.add(n["record_id"])
        rows.append({"kind": "entity", "record_id": n["record_id"], "name": n["name"],
                     "library": n["lib"], "status": n["status"], "text": n["name"]})
    for e in g["edges"]:
        if e["record_id"] in seen:
            continue
        seen.add(e["record_id"])
        obs = (e.get("evidence") or [{}])[0].get("quote", "")
        disp = f"{e['subject']} -[{e['rel_type']}]-> {e['object']}"
        rows.append({"kind": "relation", "record_id": e["record_id"], "name": disp,
                     "library": "relation", "status": "provisional",
                     "text": disp + "｜" + (e.get("fact") or "") + "｜" + obs})

    done: dict[str, list[float]] = {}
    if PROG.exists():
        for ln in PROG.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                r = json.loads(ln)
                done[r["rid"]] = r["vec"]
        print(f"续传：已有 {len(done)} 条嵌入")
    todo = [r for r in rows if r["record_id"] not in done]
    print("待嵌入:", len(todo), "/", len(rows))

    PROG.parent.mkdir(parents=True, exist_ok=True)
    with PROG.open("a", encoding="utf-8") as prog:
        for i in range(0, len(todo), BATCH):
            batch = todo[i:i + BATCH]
            payload = json.dumps({"model": "text-embedding-qwen3-embedding-8b@q4_k_m",
                                  "input": [r["text"] for r in batch]},
                                 ensure_ascii=False).encode("utf-8")
            for attempt in range(3):
                try:
                    req = urllib.request.Request(EMB, data=payload,
                                                 headers={"Content-Type": "application/json"})
                    d = json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read().decode("utf-8"))
                    arr = sorted(d["data"], key=lambda x: x["index"])
                    for r, x in zip(batch, arr):
                        vec = x["embedding"]
                        done[r["record_id"]] = vec
                        prog.write(json.dumps({"rid": r["record_id"], "vec": vec},
                                              ensure_ascii=False) + "\n")
                        prog.flush()
                    break
                except (TimeoutError, urllib.error.URLError) as e:
                    print(f"  批 {i} 第 {attempt+1} 次失败: {str(e)[:60]}，重试…")
                    time.sleep(5)
            else:
                raise SystemExit(f"批 {i} 三次失败，中止（已完成的进度已落盘，重跑续传）")
            if (i // BATCH) % 20 == 0:
                print(f"  进度 {i + len(batch)}/{len(todo)}")

    import lancedb
    import pyarrow as pa
    final = [r for r in rows if r["record_id"] in done]
    db = lancedb.connect(str(IDX))
    tbl = db.create_table("records", pa.table({
        "kind": [r["kind"] for r in final],
        "record_id": [r["record_id"] for r in final],
        "name": [r["name"] for r in final],
        "text": [r["text"] for r in final],
        "library": [r["library"] for r in final],
        "status": [r["status"] for r in final],
        "vector": [done[r["record_id"]] for r in final],
    }), mode="overwrite")
    print("v2 索引落盘:", tbl.count_rows(), "行（富文本）")
    PROG.unlink(missing_ok=True)  # 索引建成，进度件清掉
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
