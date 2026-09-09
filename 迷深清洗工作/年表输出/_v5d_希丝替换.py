# -*- coding: utf-8 -*-
"""全库替换: 希丝 -> 西斯(用户裁决 v5d)
范围: final_output + _merged + 交付四件套 的 json/yaml/md
排除: 原文(04_web版永不改)、P0_决策规范、_backup、_tmp_全、_digest、_packs、_split
"""
import io, os, glob

TARGET_DIRS = [
    r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/final_output",
    r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/_merged",
    r"D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出/交付四件套",
]

total_files = 0
total_repl = 0
for d in TARGET_DIRS:
    for f in glob.glob(d + "/**/*", recursive=True):
        if not os.path.isfile(f): continue
        if not f.endswith((".json", ".yaml", ".md")): continue
        # 跳过 _agg.json 等? 不, 都要替换(它们含事件文本)
        try:
            t = io.open(f, encoding="utf-8").read()
        except Exception:
            continue
        n = t.count("希丝")
        if n:
            t2 = t.replace("希丝", "西斯")
            io.open(f, "w", encoding="utf-8").write(t2)
            total_files += 1
            total_repl += n
            print(f"{os.path.relpath(f, r'D:/DeepSeek Harness专用！危险！！！！！/迷深清洗工作2/年表输出')}: 替换 {n} 处")
print(f"\n合计: {total_files} 文件, {total_repl} 处替换")
