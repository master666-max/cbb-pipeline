# -*- coding: utf-8 -*-
"""init_project.py — 一键开新书脚手架（批次 3 收尾件）。

用法：
  py -X utf8 init_project.py --book 书名 --into D:/书库目录 [--dry-run]

生成：
  {into}/{书名}/
    corpus/                          # 放语料（clean_full.txt 或分卷）
    本体库/                          # 三态库根（判卷线写入面）
    工作区/{candidates,manifest,logs,slice}
    contracts/                       # 契约文本（判卷/抽取；PT-026 校准后定稿）
    judging.config.json              # 判卷配置模板（三考官编制占位）
    extraction.config.json           # 抽取配置模板（R-030：types 留空待彩排标定）
    开书清单.md                       # 下一步指引（三章彩排→标定→50 件验证轮→全量）
--dry-run 只打印计划不落盘。已有目录拒绝覆盖（永不删除铁律）。
"""
import argparse
import json
import sys
from pathlib import Path

JUDGE_CFG = {
    "version": "1.0",
    "book": "{book}",
    "store_root": "本体库",
    "work_dir": "工作区/判卷",
    "contract_file": "contracts/judge.txt",
    "_契约说明": "先空跑三章彩排（PT-026 刻度法）定契约档位，再填正式契约文本",
    "panel": {
        "GLM": {"channel": "subagent"},
        "DEEPSEEK": {"base": "https://api.deepseek.com", "model": "deepseek-chat",
                     "key": {"env": "DEEPSEEK_API_KEY", "registry": "DEEPSEEK_API_KEY"}},
        "THIRD": {"base": "__升级票端点__", "model": "__模型名__",
                  "key": {"registry": "__KEY_ENV__"}, "role": "audit", "paced": True},
    },
    "plants": {"pairs": 4, "seed": 0},
    "batch": {"chunk": 10},
    "gate": {"correct_min": 5, "capture_min": 0.8334},
}

EXTRACT_CFG = {
    "version": "1.0",
    "book": "{book}",
    "corpus": {"path": "corpus/"},
    "store_root": "本体库",
    "work_dir": "工作区",
    "panel_concurrency": 3,
    "anchor_check": True,
    "types": {
        "_note": "R-030：libraries 为桶位建议值；entity_type 值必须经三章彩排校准后人工标定，禁止盲抄他书",
        "libraries": ["character", "event", "relation", "foreshadow", "setting"],
        "entity_type_values": [],
        "mutable_fields": [],
    },
}

GUIDE = """# {book} · 开书清单

1. 语料放入 corpus/，跑边界表（build_boundary，需 chapter_marker_regex）。
2. 抽取三章（用你惯用的抽取线），候选 jsonl 交给 calibrate.py → 彩排校准报告。
3. 人审报告：entity_type 值分布标定 → 写入 extraction.config.json types。
4. 植株上岗考试（judge_exam）：考官 ≥5/6 才上岗。
5. 组装 50 件验证轮（judge_assemble → 双腿 → judge_join）：植株门 PASS 再谈全量。
6. 判卷契约档位用 PT-026 刻度法定（v1→v2.2 的教训：条款措辞=支持率刻度）。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--into", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args()

    root = Path(ns.into) / ns.book
    if root.exists():
        print(f"REFUSE：{root} 已存在——永不覆盖（铁律）")
        return 3

    dirs = ([root, root / "corpus", root / "本体库"]
            + [root / "工作区" / s for s in ("candidates", "manifest", "logs", "slice")]
            + [root / "contracts"])
    files = {
        "judging.config.json": json.dumps(json.loads(json.dumps(JUDGE_CFG).replace("{book}", ns.book)),
                                          ensure_ascii=False, indent=1),
        "extraction.config.json": json.dumps(json.loads(json.dumps(EXTRACT_CFG).replace("{book}", ns.book)),
                                             ensure_ascii=False, indent=1),
        "contracts/README.md": "契约文本放此处（judge.txt / extraction-v3.txt）——PT-026 校准后定稿。",
        "开书清单.md": GUIDE.replace("{book}", ns.book),
    }
    print(f"计划：{root}（{len(dirs)} 目录 + {len(files)} 文件）")
    for d in dirs:
        print("  mkdir", d)
    for f in files:
        print("  write", root / f)
    if ns.dry_run:
        print("DRY-RUN 未落盘")
        return 0
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    print(f"完成：{root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
