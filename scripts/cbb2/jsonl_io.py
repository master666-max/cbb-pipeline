"""cbb2.jsonl_io — 共享 JSONL 读面（P-028 修复）。

str.splitlines() / 无参 str.split() 会把 U+0085/U+2028/U+2029 等 Unicode 行分隔符
当行界；JSON 字符串合法包含这些字符时读面被撕裂——json.loads 裸崩或行被静默丢弃。
本模块只按 \\n 切行（容错 \\r\\n），U+2028/2029/U+0085 一律视为普通字符；
解析失败行不静默丢弃：进返回的 skipped 披露列表，同时记入模块级披露缓冲
（iter_skipped 式，disclosed_skips() 可审计，封顶防膨胀）。
"""
from __future__ import annotations

import json

_DISCLOSE_CAP = 1000
_DISCLOSED: list[dict] = []


def read_jsonl_lines(text: str) -> list[str]:
    """P-028 安全切行：只按 \\n 切，剥行尾 \\r；U+2028/2029/U+0085 视为普通字符。"""
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()  # 文件以 \n 收尾产生的空尾（中间空行保留，行号不漂移）
    return [ln[:-1] if ln.endswith("\r") else ln for ln in lines]


def parse_jsonl(text: str, source: str = "<text>",
                skipped: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    """逐行 json.loads。返回 (rows, skipped)；坏行进 skipped（行号/预览/原因），不静默丢弃。
    skipped 同时记入模块级披露缓冲；调用方亦可传自有列表汇聚（iter_skipped 式）。"""
    rows: list[dict] = []
    bad: list[dict] = []
    for i, line in enumerate(read_jsonl_lines(text), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except (ValueError, TypeError) as e:  # JSONDecodeError/UnicodeDecodeError ⊂ ValueError
            entry = {"source": source, "line": i, "reason": str(e)[:120], "preview": line[:80]}
            bad.append(entry)
            _DISCLOSED.append(entry)
            del _DISCLOSED[:-_DISCLOSE_CAP]
            if skipped is not None:
                skipped.append(entry)
    return rows, bad


def disclosed_skips() -> list[dict]:
    """模块级坏行披露缓冲（有界，最新在后）——任何读面坏行在此留痕，供审计。"""
    return list(_DISCLOSED)


def reset_disclosures() -> None:
    """清空披露缓冲（测试隔离用）。"""
    _DISCLOSED.clear()
