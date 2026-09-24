# -*- coding: utf-8 -*-
"""init_project.py — 开书脚手架：读 project.yaml 生成工作区+本体库+BUILD-STATE 骨架
用法：py -X utf8 init_project.py <project.yaml 路径>
零第三方依赖；幂等（已存在即跳过，不覆盖任何文件）。
唯一例外：0 字节的 BUILD-STATE.md 视为「未落地」并回填——它只能是崩在半路的残留。
校验全部前置：参数不齐或语料不存在时一个目录都不建。
"""
import io, os, sys, yaml

# 书名的两个合法键位：assets/project.template.yaml 给的是 project.name，
# 而本件历史实现读的是 proj["book_name"] ⇒ 照 README 三步走会在最后一步 KeyError。
# 两个都收（book_name 优先，向后兼容既有配置），都给不出就明确报错，不让人去猜缺哪个键。
BOOK_KEYS = ("book_name", "name")


def book_name_of(proj):
    for k in BOOK_KEYS:
        v = proj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    raise SystemExit(
        "配置缺书名：project.yaml 的 project 段里 "
        + "／".join(BOOK_KEYS) + " 至少给一个非空值（模板用的是 name）")


def main(cfg_path):
    cfg = yaml.safe_load(io.open(cfg_path, encoding="utf-8"))
    proj = cfg["project"]
    book = book_name_of(proj)
    root = os.path.dirname(os.path.abspath(cfg_path))
    ws = proj.get("workspace_path") or os.path.join(root, "工作区")
    lib = proj.get("library_path") or os.path.join(root, "本体库")
    if not isinstance(proj.get("source_path"), str) or not proj["source_path"].strip():
        raise SystemExit("配置缺语料路径：project.source_path 必须是非空字符串（全文语料的绝对路径）")
    src = proj["source_path"]
    assert os.path.exists(src), f"语料不存在：{src}"
    n = 0
    for line in io.open(src, encoding="utf-8"):
        if "<<<CHAPTER" in line:
            n += 1
    # 校验全过才开始动盘：原实现先 makedirs 再校验，语料路径写错时留下一堆空目录
    for d in (ws, lib,
              os.path.join(ws, "candidates"), os.path.join(ws, "slice"),
              os.path.join(ws, "logs"), os.path.join(ws, "manifest"),
              os.path.join(lib, "libraries"), os.path.join(lib, "quarantine-zone")):
        os.makedirs(d, exist_ok=True)
    state = os.path.join(root, "BUILD-STATE.md")
    body = ("# BUILD-STATE（缓存，事实以磁盘+git为准）\n\n"
            f"> 书：{book}｜语料：{src}｜章数标记：{n}\n"
            "> 目标判据：<开书时填写，全库入库+终审十轮+抽检≥95%>\n\n单位清单：（待填）\n阻塞登记：（无）\n勘误日志：（无）\n")
    # 内容先算好、再开文件：原写法 io.open(state,"w") 排在 f-string 求值之前，
    # 取名/取语料一抛错，文件已被创建并清空；而"已存在即跳过"让下一次正确运行
    # 报「OK 书房就绪」也不回填 ⇒ 一个 0 字节的 STATE 永久沉默地留着。
    # 所以这里放行两种情形：不存在、或存在但 0 字节（崩后残留）。非空 STATE 永不覆盖。
    if (not os.path.exists(state)) or os.path.getsize(state) == 0:
        with io.open(state, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
            f.flush()
        # 写完独立回读断言非零：判定面为空不能读成通过
        assert os.path.getsize(state) > 0, f"STATE 写完回读为 0 字节：{state}"
    print(f"OK 书房就绪：语料标记 {n} 章｜工作区={ws}｜本体库={lib}｜STATE={state}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "project.yaml")
