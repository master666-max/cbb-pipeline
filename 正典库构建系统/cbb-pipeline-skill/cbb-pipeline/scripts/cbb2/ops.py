# -*- coding: utf-8 -*-
"""cbb2.ops — 运行契约闸（U-A04）：治"凭证在位≠能力接线"（qoder D-26/28/29 三连教训）。

四条件缺一即 BLOCKED：端点在位 / 消费件存在 / 已接线 / 本批有回执。
自检哨 selftest() 打自己——闸自身必须可被验证会响。
考官/外部端点一律 env 注入，禁硬编码（D-004 + 裁①纪律）。
"""
from __future__ import annotations

import json
import os
import urllib.request


def examiner_env(kind: str) -> dict:
    """考官 env 三件套（base/model/key 变量名按编制定）——值不落文件。
    key 回落：EXAMINER_<K>_API_KEY 缺失时回落既定公共变量（QWEN→DASHSCOPE_API_KEY，
    DEEPSEEK→DEEPSEEK_API_KEY，LOCAL→无）；base/model 无默认（BLOCKED 而非硬编码）。"""
    fallback = {"QWEN": "DASHSCOPE_API_KEY", "DEEPSEEK": "DEEPSEEK_API_KEY"}.get(kind, "")
    key = os.environ.get(f"EXAMINER_{kind}_API_KEY") or os.environ.get(fallback, "")
    return {"base": os.environ.get(f"EXAMINER_{kind}_BASE", ""),
            "model": os.environ.get(f"EXAMINER_{kind}_MODEL", ""),
            "key": key,
            "key_source": f"EXAMINER_{kind}_API_KEY" if os.environ.get(f"EXAMINER_{kind}_API_KEY")
                          else (fallback if key else "")}


def capability_gate(capability: str, *, endpoint_alive: bool, artifact_exists: bool,
                    wired: bool, receipt_present: bool) -> dict:
    missing = [name for name, ok in
               (("endpoint_alive", endpoint_alive), ("artifact_exists", artifact_exists),
                ("wired", wired), ("receipt_present", receipt_present)) if not ok]
    return {"capability": capability, "state": "READY" if not missing else "BLOCKED",
            "missing": missing}


def selftest() -> dict:
    """哨兵打自己：全条件=READY，缺一=BLOCKED——闸不会响则数据作废。"""
    full = capability_gate("selftest-full", endpoint_alive=True, artifact_exists=True,
                           wired=True, receipt_present=True)
    broken = capability_gate("selftest-broken", endpoint_alive=True, artifact_exists=True,
                             wired=True, receipt_present=False)
    ok = full["state"] == "READY" and broken["state"] == "BLOCKED" \
        and broken["missing"] == ["receipt_present"]
    return {"ok": ok, "full": full, "broken": broken}


def probe_http(url: str, timeout: float = 4.0) -> bool:
    """端点在位探测（GET，短超时；任何异常=不在位）。"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 500  # 4xx 也是"端点在"
    except Exception:
        return False


def chat_once(base: str, model: str, api_key: str, prompt: str,
              timeout: float = 60.0) -> str:
    """OpenAI 兼容 chat 单发（非流式）。调用方负责系统提示词锚定。"""
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0, "stream": False}).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}" if api_key else ""})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return (data["choices"][0]["message"] or {}).get("content", "")
