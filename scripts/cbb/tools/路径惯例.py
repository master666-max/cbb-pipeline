# -*- coding: utf-8 -*-
"""路径惯例.py — 从 store 反推项目根/工作区，替掉散在各件里的"上一项目实例名默认值"

为什么单列一件（2026-09-25 外部审计实测）：发布件里有 19 处功能默认值把**上一个项目的实例名**
（`迷深实战-本体库`／`迷深实战-工作区`／一条仓外绝对路径）写死，另有 7 处把某台机器上的
图库端口 `http://localhost:7695` 当缺省。后果不是一句"不通用"：

  - 检索层旧版默认把查询日志写到 `<项目同级>/迷深实战-工作区/logs/` ⇒ 在别的项目旁边**凭空造出上一项目的目录树**；
  - 批次自检旧版把 STATE 写成 `迷深实战-BUILD-STATE.md` ⇒ 换项目永远读不到，三方对账只对两方还判 PASS；
  - 图库端口当默认 ⇒ "没设 env"被读成"图可用"，而那台机器上在跑的图很可能是别的项目的
    （本包 SKILL 的 Common Mistakes 12 说的就是这件事）。

所以判据统一放这里：**能推的从 store 推，推不出就报错要参数，绝不给共享实例的活端口当缺省。**
"""
from __future__ import annotations

import os
from pathlib import Path

LIB_SUFFIX = "-本体库"
WS_SUFFIX = "-工作区"


def sibling_by_convention(root: Path, suffix: str) -> Path | None:
    """在项目根同级找一个 `*-<suffix>` 目录（惯例命名）；找不到返回 None（不凭空建）。"""
    if not root.exists():
        return None
    hits = sorted(p for p in root.iterdir() if p.is_dir() and p.name.endswith(suffix))
    return hits[0] if hits else None


def project_root(store: str | Path) -> Path:
    """本体库的父目录＝项目根。给到项目根本身（名字不带 `-本体库`）时原样返回。"""
    p = Path(store)
    if p.name.endswith(LIB_SUFFIX) or p.name == "本体库":
        return p.parent
    return p


def workspace_of(store: str | Path, explicit: str | Path | None = None) -> Path:
    """工作区定位：显式参数 > 同级 `*-工作区/` > `<项目根>/工作区` > `<store 同级>/工作区`。

    与旧版的区别：不再把 `迷深实战-工作区` 当默认——新项目没有那个目录时旧代码会
    mkdir 出上一项目的名字（写域凭空扩张，且没人会注意到）。
    """
    if explicit:
        return Path(explicit)
    root = project_root(store)
    hit = sibling_by_convention(root, WS_SUFFIX)
    if hit:
        return hit
    return root / "工作区" if (root / "工作区").exists() else root.parent / "工作区"


def store_of(root: str | Path, explicit: str | Path | None = None) -> Path:
    """反向：从项目根找本体库（显式优先，其次同级惯例名，再退 `<根>/本体库`）。"""
    if explicit:
        return Path(explicit)
    r = Path(root)
    hit = sibling_by_convention(r, LIB_SUFFIX) or (r / "本体库" if (r / "本体库").exists() else None)
    return hit or (r / "本体库")


def graph_base(explicit: str | None = None, env: str = "NEO4J_HTTP") -> str:
    """图库 HTTP 基址：**必须显式给**（参数或 env），不给就抛错。

    旧版到处写 `os.environ.get("NEO4J_HTTP", "http://localhost:7695")`。
    一台机器上在跑的图库不等于本项目可用的图库（community 版单库、跨项目同名实体会互相
    覆盖），把某台机器的活端口当缺省，等于把"没设 env"读成"图可用"。
    """
    b = (explicit or os.environ.get(env) or "").strip()
    if not b:
        raise GraphBaseMissing(
            f"缺图库基址：给 --base 或设 env {env}（例：http://127.0.0.1:7474）。"
            "不给是不给，不许拿别人机器上的活端口当默认。")
    return b.rstrip("/")


class GraphBaseMissing(RuntimeError):
    """图库基址未显式给出——调用方应把它当"未达项"记下来，不许 catch 后当可用。"""
