# -*- coding: utf-8 -*-
"""test_dl_models.py — B1/B4 依赖模型下载与冒烟（串行）。
①Erlangshen-110M-NLI（hf-mirror）→ 一发蕴含冒烟
②HanLP 核指模型 → 一句零指代冒烟
任一失败不抛死——打印状态供主会话定 B4/B1 走向。
"""
import os
import traceback

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

print("== ① Erlangshen-110M-NLI ==")
try:
    from transformers import pipeline
    nli = pipeline("text-classification",
                   model="IDEA-CCNL/Erlangshen-RoBERTa-330M-NLI",
                   truncation=True)
    out = nli({"text": "我将要去 Université Canadiens-Français 学习艺术。",
               "text_pair": "我将去上学。"})[0]
    print("冒烟:", out)
    print("ERLANGSHEN OK")
except Exception as e:  # noqa: BLE001 — 依赖探针面
    print("ERLANGSHEN FAIL:", str(e)[:200])
    traceback.print_exc()

print()
print("== ② HanLP 核指 ==")
try:
    import hanlp
    HanLP = hanlp.load(hanlp.pretrained.coref.COREF_CONV_20211101, devices=-1)
    doc = HanLP(["我从小就很喜欢吃苹果。", "它对我的健康很有帮助。"])
    print("冒烟 clusters:", doc["coref"])
    print("HANLP OK")
except Exception as e:  # noqa: BLE001 — 依赖探针面
    print("HANLP FAIL:", str(e)[:200])
    traceback.print_exc()
