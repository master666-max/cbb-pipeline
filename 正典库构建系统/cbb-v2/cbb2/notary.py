# -*- coding: utf-8 -*-
"""cbb2.notary — 账本检查点外部发布（Phase F·U-F01；密码学路#1 最高优先）。

形式化依据（RFC 9162 §1.6 + Key Transparency 生产实践：WhatsApp KT / Apple iMessage CKV）：
  防篡改证明成立条件 = ①追加日志 ＋ ②周期性把签名链头检查点发布到【日志存储之外】的追加通道。
  缺 ②，任何链都可被持有者整体重写（split-view）——纯机内账本唯一真弱点，本件堵这一环。

独立复算原则：verify 只读 ledger.jsonl 原文与通道文件，**不 import 任何 store 代码**——
验证器信任面=文件本身，不是生成它的程序。
签名挂点：env CBB_NOTARY_KEY=<ssh key 路径> 时用 `ssh-keygen -Y sign`（namespace=canon-checkpoint）；
未配置=未签名检查点（仍在验证，只是无不可否认性）。
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

LEDGER = "ledger.jsonl"
GENESIS = "genesis"


def ledger_head(store_root: Path) -> dict:
    """独立复算账本头：只读 ledger.jsonl，统计行数与链尾哈希。不信任任何缓存。"""
    p = Path(store_root) / LEDGER
    rows = 0
    last_hash = None
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows += 1
            try:
                last_hash = json.loads(line).get("hash", last_hash)
            except json.JSONDecodeError:
                raise ValueError(f"账本第 {rows} 行撕裂：{line[:60]!r}——先修账本再发检查点")
    return {"rows": rows, "chain_head": last_hash or GENESIS}


def checkpoint_text(origin: str, head: dict, at: str) -> str:
    """C2SP tlog-tiles 风格检查点文本（origin/size/roothash/timestamp）。"""
    return (f"origin: {origin}\n"
            f"size: {head['rows']}\n"
            f"roothash: {head['chain_head']}\n"
            f"timestamp: {at}\n")


def publish(store_root: Path, channel_dir: Path, origin: str, at: str,
            sign_key: str | None = None) -> dict:
    """把账本头检查点原子发布到**库外**通道目录。
    返回 {checkpoint, path, signed}。重复发布同一 size 幂等（同内容覆盖同路径）。"""
    head = ledger_head(store_root)
    text = checkpoint_text(origin, head, at)
    channel_dir = Path(channel_dir)
    channel_dir.mkdir(parents=True, exist_ok=True)
    out = channel_dir / f"{origin}-checkpoint-{head['rows']:07d}.txt"
    tmp = out.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, out)  # 原子写
    signed = False
    if sign_key and Path(sign_key).exists():
        sig = subprocess.run(
            ["ssh-keygen", "-Y", "sign", "-f", sign_key, "-n", "canon-checkpoint", str(out)],
            capture_output=True, timeout=60)
        signed = sig.returncode == 0
    return {"checkpoint": out.name, "rows": head["rows"], "chain_head": head["chain_head"],
            "signed": signed, "path": str(out)}


def verify(channel_dir: Path, store_root: Path, origin: str) -> dict:
    """独立复算：取通道里该 origin 最新的检查点，与账本**全链重放**结果核对。
    重放公式与 cbb2.ledger.line_hash 同源（格式定义）；篡改任意中间行都会使
    重放哈希在断链处偏离 ⇒ 判 FAIL（红队回归：中间行篡改必须可检）。"""
    from .ledger import line_hash
    channel_dir = Path(channel_dir)
    prefix = f"{origin}-checkpoint-"
    cps = sorted(p for p in channel_dir.glob(f"{prefix}*.txt"))
    if not cps:
        return {"ok": False, "errors": [f"通道无 {origin} 检查点"]}
    latest = cps[-1]
    text = latest.read_text(encoding="utf-8")
    fields = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    p = Path(store_root) / LEDGER
    rows = 0
    last_hash = GENESIS
    prev = GENESIS
    errors = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows += 1
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"账本第 {rows} 行撕裂")
                break
            if r.get("prev_hash") != prev:
                errors.append(f"账本第 {rows} 行 prev_hash 断链")
                break
            if line_hash(r) != r.get("hash"):
                errors.append(f"账本第 {rows} 行行哈希不匹配（被篡改？）")
                break
            prev = r.get("hash")
            last_hash = r.get("hash")
    if not errors:
        if int(fields.get("size", -1)) != rows:
            errors.append(f"size 漂移：checkpoint={fields.get('size')} 实际={rows}")
        if fields.get("roothash") != last_hash:
            errors.append(f"roothash 漂移：checkpoint={fields.get('roothash')} 实际={last_hash}")
    return {"ok": not errors, "checkpoint": latest.name, "rows": rows,
            "errors": errors}
