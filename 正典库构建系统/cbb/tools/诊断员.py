# -*- coding: utf-8 -*-
"""诊断员.py — LLM 归因岗位（U-F08 · 黄区 · 量尺已裁 2026-09-23）

裁定组合：A1 主代理 ＋ B2 样本≤30（含经人批准的升级权，每异常最多两批）＋ C2 一次初诊＋一次复诊 ＋ D2 单次≤8K token ＋ E 决策账＋周复盘。

**结构性红区隔离（本模块零执行力——这是设计，不是疏忽）**：
  · 本件只做三件事：**备料**（把异常信号＋有限样本装成诊断任务包）、**记账**（归因结论追加进决策账）、**核引用**（归因里引用的样本必须真实存在）；
  · **没有任何执行函数**：归因/建议永远是文本，动作要由人确认后走各自的正常路径（gate→store 等）；
  · 红区六项（验收/晋升/契约/失效宣告/权限表/量尺）在 validate_attribution 里被显式拒绝——LLM 提议越权 → 拒收并留账。

用法（A1 主代理岗位的接口约定）：
  ①包 = prepare(anomaly, samples)            ← 机械备料，样本自动截到 ≤30
  ②主代理读包 → 产出归因+建议（会话内，≤8K token）
  ③账 = record_decision(账, 包, 归因, 建议)   ← 追加决策账
  ④人确认 → confirm(账, 包id)                ← 追加确认条目
  ⑤复诊 = prepare(同一异常, escalation=True)  ← 仅一次，且须已确认
"""
from __future__ import annotations

import json
from datetime import date as _date
from pathlib import Path

SAMPLE_LIMIT = 30
TOKEN_BUDGET = "≤8K/次"
RED_ZONE = ("验收通过", "晋升", "契约", "失效宣告", "权限表", "量尺")  # 短触发词：误报只会更保守
ESCALATION_MAX = 1  # 每异常升级批次数上限（B2：初诊 1 批 + 升级 1 批）


def _today() -> str:
    return _date.today().isoformat()


def prepare(anomaly: dict, samples: list[dict], escalation: bool = False,
            prior_packages: list[dict] | None = None, today: str | None = None) -> dict:
    """备料：异常信号＋样本（确定性截断 ≤30）→ 诊断任务包。
    anomaly: {"rule":…, "detail":…, "backend":…}（来自巡检/分流/哨兵的 finding）
    samples: [{"record_id":…, "text":…}, …]（调用方圈定；超出 30 自动截断并标注可升级）
    escalation=True 时要求 prior_packages 里该异常已有"已确认"的初诊（C2）。"""
    prior = [p for p in (prior_packages or [])
             if (p.get("anomaly") or {}).get("detail") == anomaly.get("detail")]
    if prior and not escalation:
        raise ValueError("该异常已诊断过（C2：一次初诊；复诊须 escalation=True 且初诊已确认）")
    if escalation:
        if len(prior) >= 1 + ESCALATION_MAX:
            raise ValueError(f"升级批次超限（每异常最多 1+{ESCALATION_MAX} 批）")
        if not any(p.get("status") == "已确认" for p in prior):
            raise ValueError("升级须先有已确认的初诊（人工闸）")
    cut = samples[:SAMPLE_LIMIT]
    pkg = {
        "package_id": f"diag-{anomaly.get('rule', 'x')}-{len(prior) + 1}-{_today()}",
        "anomaly": anomaly,
        "samples": cut[:SAMPLE_LIMIT],
        "sample_count": len(cut),
        "truncated": len(samples) > SAMPLE_LIMIT,
        "量尺": {"色": "黄（提案制）", "样": f"≤{SAMPLE_LIMIT}", "频": "1 初诊+1 复诊",
                "费": TOKEN_BUDGET, "复": "决策账+周复盘"},
        "status": "待诊断",
        "at": today or _today(),
    }
    if escalation:
        pkg["package_id"] += "-esc"
        pkg["escalation"] = True
    return pkg


def validate_attribution(attribution: str, proposals: list[str]) -> None:
    """红区闸（机械）：归因/建议触碰六项红区 → ValueError（拒绝并留账由调用方做）。"""
    for p in proposals or []:
        for rz in RED_ZONE:
            if rz in p:
                raise ValueError(f"建议触碰红区「{rz}」——诊断员无执行权，拒绝留账")


def record_decision(log_path: Path | str, package: dict, attribution: str,
                    proposals: list[str], by: str = "主代理", at: str | None = None) -> dict:
    """归因入账（append-only）。红区提议先过 validate_attribution。"""
    validate_attribution(attribution, proposals)
    entry = {"type": "diagnosis", "package_id": package["package_id"],
             "anomaly": package.get("anomaly"), "color": "黄",
             "sample_refs": [s.get("record_id") for s in package["samples"]][:SAMPLE_LIMIT],
             "attribution": attribution, "proposals": proposals,
             "status": "待人工确认", "by": by, "at": at or _today()}
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def confirm(log_path: Path | str, package_id: str, by: str = "human",
            at: str | None = None, note: str = "") -> dict:
    """人工确认条目（追加）：确认后该异常才允许升级批次（C2 人工闸）。"""
    entry = {"type": "confirm", "package_id": package_id, "by": by,
             "at": at or _today(), "note": note}
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def prior_packages(log_path: Path | str) -> list[dict]:
    """读取账内的诊断包记录（供 prepare 查升级资格）；确认条目按 package_id 并回状态。"""
    p = Path(log_path)
    if not p.exists():
        return []
    entries = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()
               if x.strip()]
    confirmed = {e["package_id"] for e in entries if e.get("type") == "confirm"}
    diags = []
    for e in entries:
        if e.get("type") != "diagnosis":
            continue
        d = dict(e)
        if d["package_id"] in confirmed:
            d["status"] = "已确认"
        diags.append(d)
    return diags
