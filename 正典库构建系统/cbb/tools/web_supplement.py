# -*- coding: utf-8 -*-
"""web_supplement.py — 网络搜索补充层（用户检索面的**低置信度**补充推断材料）。

纪律（本件的存在前提，违反即撤）：
  1. **绝不入正典库**——返回体 `admissible=False` 为硬标记；本件不 import 任何写库模块；
  2. **不参与引文核验**——网络来源不在库内证据池，verify_citations 必然判 unverified；
  3. **不进 RRF/不与 canon 结果混排**——调用方必须将其单列"低置信度补充"区呈现；
  4. 每条带 URL 溯源；无来源的模型转述不在本件产物里。
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
口径 = "网络补充推断材料：低置信度；绝不入正典库、不参与引文核验、不与正典结果混排（单列呈现）"


def _http(url: str, timeout: float = 15.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def search(query: str, n: int = 5, engine: str = "cn.bing") -> dict:
    """web 搜索 → {admissible: False, confidence: "low", results: [{title,url,snippet}]}。
    引擎失败→ results=[] 且 errors 如实披露（不静默、不伪造）。"""
    results: list[dict] = []
    errors: list[str] = []
    try:
        if engine == "cn.bing":
            html = _http("https://cn.bing.com/search?q=" + urllib.parse.quote(query)
                         + "&setlang=zh-hans&count=10")
            for m in re.finditer(r'<li class="b_algo".*?</li>', html, re.S):
                block = m.group(0)
                a = re.search(r'<h2[^>]*><a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
                if not a:
                    continue
                url, title = a.group(1), _strip_tags(a.group(2))
                p = re.search(r'<p[^>]*>(.*?)</p>', block, re.S)
                snippet = _strip_tags(p.group(1)) if p else ""
                results.append({"title": title, "url": url, "snippet": snippet[:300]})
                if len(results) >= n:
                    break
        else:
            errors.append(f"未知引擎 {engine}")
    except Exception as e:  # 网络失败如实披露
        errors.append(f"{type(e).__name__}: {str(e)[:120]}")
    return {"admissible": False, "confidence": "low", "engine": engine,
            "results": results[:n], "errors": errors, "口径": 口径}


def guard_block_admission(item: dict) -> None:
    """准入闸（供调用方显式调用）：任何试图把网络补充材料当正典证据的动作在此拦下。"""
    if not item or not any(k in item for k in ("admissible", "confidence", "record_id", "source")):
        raise ValueError("准入闸收到无来源、无标记的条目：判不了就不放行"                               "（缺席/为空/通过不许同形）")
    if item.get("admissible") is False or item.get("confidence") == "low":
        raise PermissionError("web_supplement 材料不可入正典（admissible=False 硬标记）")


if __name__ == "__main__":  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", required=True)
    ap.add_argument("--n", type=int, default=5)
    ns = ap.parse_args()
    print(json.dumps(search(ns.q, ns.n), ensure_ascii=False, indent=1))
