# -*- coding: utf-8 -*-
"""cbb2.judging — 判卷产线通用配置层（方法学产品化批次 1·U1）。

目标：判卷五件套（组装/考官腿/合票/上岗考试/中途修复）零书本字面量——
库根、工作目录、考官编制（base/model/key 来源）、契约文本、掺株种子、批大小、
植株捕获门限全部外置到 judging.config.json（书=配置，代码=产线）。

约定：
- 配置内相对路径以**配置文件所在目录**为基准解析（config 放仓库根即以仓库根为基准）。
- 考官 key 解析顺序：env → 注册表（ops.secret_from_registry，D-004 值不落盘）。
  槽位 key 一律排在其平台默认键之前（v1.10 教训：默认键劫持新槽位发错端点 401）。
- 契约文本走文件（contracts/*.txt），不进代码——契约是可校准的仪器参数（PT-026/R-032）。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import ops

REQUIRED = ("version", "book", "store_root", "work_dir", "contract_file", "panel",
            "plants", "batch", "gate")


@dataclass
class Examiner:
    name: str
    base: str = ""
    model: str = ""
    channel: str = "api"
    role: str = "panel"
    key_env: str = ""
    key_registry: list = field(default_factory=list)
    max_tokens: int = 2048
    paced: bool = False

    def key(self) -> str:
        """env 优先 → 注册表逐名回读（槽位键已按优先序排列）。值不落盘不打印（D-004）。"""
        if self.key_env:
            v = os.environ.get(self.key_env)
            if v:
                return v
        for name in self.key_registry:
            v = ops.secret_from_registry(name)
            if v:
                return v
        return ""

    @property
    def audit(self) -> bool:
        return self.role == "audit"


@dataclass
class JudgeConfig:
    path: Path
    version: str
    book: str
    store_root: Path
    work_dir: Path
    contract_file: Path
    contract: str
    panel: dict
    examiners: dict
    plants: dict
    batch: dict
    gate: dict

    def examiner(self, name: str) -> Examiner:
        return self.examiners[name]


def _resolve(base: Path, p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else (base / q)


def load_config(path: str | Path) -> JudgeConfig:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in raw]
    if missing:
        raise ValueError(f"判卷配置缺必填字段: {missing}（{path}）")
    base = path.resolve().parent
    store_root = _resolve(base, raw["store_root"])
    work_dir = _resolve(base, raw["work_dir"])
    contract_file = _resolve(base, raw["contract_file"])
    contract = contract_file.read_text(encoding="utf-8")
    if not contract.strip():
        raise ValueError(f"契约文件为空: {contract_file}")

    examiners = {}
    for name, spec in (raw.get("panel") or {}).items():
        key = spec.get("key") or {}
        examiners[name] = Examiner(
            name=name,
            base=spec.get("base", ""),
            model=spec.get("model", ""),
            channel=spec.get("channel", "api"),
            role=spec.get("role", "panel"),
            key_env=key.get("env", ""),
            key_registry=[k for k in (key.get("registry"), key.get("registry2")) if k],
            max_tokens=int(spec.get("max_tokens", 2048)),
            paced=bool(spec.get("paced", False)),
        )
    if not any(e.role == "panel" for e in examiners.values()):
        raise ValueError("panel 中至少需要一名 role=panel 考官")

    gate = raw["gate"]
    float(gate["capture_min"])  # 类型自检
    return JudgeConfig(path=path.resolve(), version=str(raw["version"]), book=raw["book"],
                       store_root=store_root, work_dir=work_dir, contract_file=contract_file,
                       contract=contract, panel=raw["panel"], examiners=examiners,
                       plants=raw["plants"], batch=raw["batch"], gate=gate)
