# -*- coding: utf-8 -*-
"""cbb2.config — 包级唯一配置源（env-first，无实例默认；吸收 路径惯例.py 判据）。

v1 的头号债务：46 个模块各自 sys.path.insert + 散落 19 处实例名默认 + 7 处写死端口。
v2：全部经此件推导——能推的从 store 推，推不出报错要参数。
"""
from __future__ import annotations

import os
from pathlib import Path

LIB_SUFFIX = "-本体库"
WS_SUFFIX = "-工作区"


def sibling_by_convention(root: Path, suffix: str) -> Path | None:
    if not root.exists():
        return None
    hits = sorted(p for p in root.iterdir() if p.is_dir() and p.name.endswith(suffix))
    return hits[0] if hits else None


def store_of(root: Path) -> Path:
    """从任意上级目录按惯例名推 store；env CBB_STORE 优先；推不出报错。"""
    env = os.environ.get("CBB_STORE")
    if env:
        return Path(env)
    d = root
    for _ in range(6):
        hit = sibling_by_convention(d, LIB_SUFFIX)
        if hit:
            return hit
        nxt = d.parent
        if nxt == d:
            break
        d = nxt
    raise RuntimeError("推不出 store：设 CBB_STORE 或在项目根旁放 *-本体库/（惯例命名）")


def workspace_of(store: Path) -> Path:
    hit = sibling_by_convention(store.parent, WS_SUFFIX)
    if hit:
        return hit
    raise RuntimeError("推不出 workspace：store 同级应有 *-工作区/（惯例命名）")


def neo4j_http() -> str:
    return os.environ.get("NEO4J_HTTP", "http://localhost:7474")  # 出厂默认；实例端口走 env


def namespace() -> str:
    ns = (os.environ.get("CBB_NAMESPACE") or "").strip()
    if not ns:
        raise RuntimeError("缺命名空间：设 CBB_NAMESPACE（同机共图防串图）")
    return ns


def embed_endpoint() -> str:
    return os.environ.get("EMBED_HTTP", "http://127.0.0.1:8080/v1/embeddings")
