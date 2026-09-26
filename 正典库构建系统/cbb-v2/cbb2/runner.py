# -*- coding: utf-8 -*-
"""cbb2.runner — 章管线编排入口（aux 四件探活降级骨架；实现件按需挂接）。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from . import config


def run_chapter(chapter_no: int, store: Path | None = None, no_aux: bool = False) -> dict:
    """v2 编排骨架：抽取→门→三态→收口 aux（嵌索引/图导出/副本同步/双时序）——全部探活降级。"""
    store = store or config.store_of(Path(__file__).parents[2])
    aux = {"embedding": None, "graph": None, "replica": None, "temporal": None}
    if not no_aux:
        aux_steps = [
            ("embedding", ["py", "-X", "utf8", "cbb/tools/embed_dedup_scan.py"]),
            ("graph", ["py", "-X", "utf8", "cbb/tools/neo4j_export.py"]),
        ]
        for key, cmd in aux_steps:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                   timeout=600, cwd=str(store.parent))
                aux[key] = (json.loads(r.stdout.strip().splitlines()[-1])
                            if r.stdout.strip() else {"status": "blocked"})
            except Exception as e:
                aux[key] = {"status": "error", "stderr": str(e)[-200:]}
    return {"chapter": chapter_no, "aux": aux,
            "口径": "v2 骨架——长尾工具仍由 cbb/ 提供（D1 裁决：增量迁移）"}


if __name__ == "__main__":
    raise SystemExit(run_chapter(int(sys.argv[1]) if len(sys.argv) > 1 else 0) and 0)
