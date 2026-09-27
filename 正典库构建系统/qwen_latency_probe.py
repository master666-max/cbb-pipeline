# -*- coding: utf-8 -*-
"""qwen_latency_probe.py — QWEN 通道时延实测（单发 vs 并发），定位慢的根源。"""
import json
import os
import sys
import threading
import time
import urllib.request

BASE = os.environ.get("EXAMINER_QWEN_BASE", "")
KEY = os.environ.get("EXAMINER_QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY", "")
MODEL = os.environ.get("EXAMINER_QWEN_MODEL", "")


def call(i, results):
    body = json.dumps({"model": MODEL,
                       "messages": [{"role": "user",
                                     "content": '只输出JSON：{"verdict":"support"}'}],
                       "temperature": 0, "stream": False, "max_tokens": 10}).encode()
    req = urllib.request.Request(BASE + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + KEY})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            json.loads(r.read().decode("utf-8"))
        results[i] = round(time.time() - t0, 2)
    except Exception as e:  # noqa: BLE001 — 探针面
        results[i] = "ERR:" + str(e)[:60]


def main():
    res = {}
    call("serial", res)
    print("单发:", res["serial"], "s")
    for n in (6, 12):
        res = {}
        ths = [threading.Thread(target=call, args=(i, res)) for i in range(n)]
        t0 = time.time()
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        lat = sorted(v for v in res.values() if isinstance(v, float))
        errs = [v for v in res.values() if not isinstance(v, float)]
        print(f"{n}并发: 中位={lat[len(lat)//2] if lat else '-'}s 最大={lat[-1] if lat else '-'}s "
              f"错误{len(errs)} 总{round(time.time()-t0,2)}s"
              + (f" 错误样例={errs[0]}" if errs else ""))


if __name__ == "__main__":
    main()
