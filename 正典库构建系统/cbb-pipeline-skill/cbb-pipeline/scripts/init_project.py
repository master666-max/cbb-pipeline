# -*- coding: utf-8 -*-
"""init_project.py — 开书脚手架：读 project.yaml 生成工作区+本体库+BUILD-STATE 骨架
用法：py -X utf8 init_project.py <project.yaml 路径>
零第三方依赖；幂等（已存在即跳过，不覆盖任何文件）。
"""
import io, os, sys, yaml

def main(cfg_path):
    cfg = yaml.safe_load(io.open(cfg_path, encoding="utf-8"))
    proj = cfg["project"]
    root = os.path.dirname(os.path.abspath(cfg_path))
    ws = proj.get("workspace_path") or os.path.join(root, "工作区")
    lib = proj.get("library_path") or os.path.join(root, "本体库")
    for d in (ws, lib,
              os.path.join(ws, "candidates"), os.path.join(ws, "slice"),
              os.path.join(ws, "logs"), os.path.join(ws, "manifest"),
              os.path.join(lib, "libraries"), os.path.join(lib, "quarantine-zone")):
        os.makedirs(d, exist_ok=True)
    src = proj["source_path"]
    assert os.path.exists(src), f"语料不存在：{src}"
    n = 0
    for line in io.open(src, encoding="utf-8"):
        if "<<<CHAPTER" in line:
            n += 1
    state = os.path.join(root, "BUILD-STATE.md")
    if not os.path.exists(state):
        io.open(state, "w", encoding="utf-8", newline="\n").write(
            "# BUILD-STATE（缓存，事实以磁盘+git为准）\n\n"
            f"> 书：{proj['book_name']}｜语料：{src}｜章数标记：{n}\n"
            "> 目标判据：<开书时填写，全库入库+终审十轮+抽检≥95%>\n\n单位清单：（待填）\n阻塞登记：（无）\n勘误日志：（无）\n")
    print(f"OK 书房就绪：语料标记 {n} 章｜工作区={ws}｜本体库={lib}｜STATE={state}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "project.yaml")
