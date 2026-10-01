# -*- coding: utf-8 -*-
"""init_project.py — 开书脚手架：读 project.yaml 生成工作区+本体库+BUILD-STATE 骨架
用法：py -X utf8 init_project.py <project.yaml 路径>
零第三方依赖（含配置解析——只用标准库读两段式 YAML 子集）；幂等（已存在即跳过，不覆盖任何文件）。
唯一例外：0 字节的 BUILD-STATE.md 视为「未落地」并回填——它只能是崩在半路的残留。
校验全部前置：参数不齐或语料不存在时一个目录都不建。
"""
import io, os, re, sys

# 书名的两个合法键位：assets/project.template.yaml 给的是 project.name，
# 而本件历史实现读的是 proj["book_name"] ⇒ 照 README 三步走会在最后一步 KeyError。
# 两个都收（book_name 优先，向后兼容既有配置），都给不出就明确报错，不让人去猜缺哪个键。
BOOK_KEYS = ("book_name", "name")


_DQ_ESCAPES = {"\\\\": "\\", '\\"': '"', "\\n": "\n", "\\t": "\t", "\\r": "\r", "\\0": "\0"}


def _dq_unescape(s):
    # YAML 双引号串的最小转义还原（\\、\"、\n、\t、\r、\0）；未知转义按原样保留
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            pair = s[i:i + 2]
            if pair in _DQ_ESCAPES:
                out.append(_DQ_ESCAPES[pair])
                i += 2
                continue
        out.append(s[i])
        i += 1
    return "".join(out)


def _scalar(raw):
    # 去行尾注释（引号外的 #），再判型；模板里 init_project 消费的键全是字符串
    s, q, out = raw.strip(), None, []
    for ch in s:
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    s = "".join(out).strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        inner = s[1:-1]
        return _dq_unescape(inner) if s[0] == '"' else inner.replace("''", "'")
    if s == "[]":
        return []
    if s == "{}":
        return {}
    low = s.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    for cast in (int, float):
        try:
            return cast(s)
        except ValueError:
            pass
    return s


def load_project_config(path):
    """解析 assets/project.template.yaml 那一档的两段式 YAML 子集：
    顶层「段名:」+ 缩进「键: 标量」。内联列表/字典等复杂值按原文保留（本件不消费）。"""
    cfg, section = {}, None
    with io.open(path, encoding="utf-8") as f:
        for ln in f:
            line = ln.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line[0].isspace():
                if line.rstrip().endswith(":"):
                    section = line.strip()[:-1].strip()
                    cfg.setdefault(section, {})
                continue
            if not isinstance(cfg.get(section), dict):
                continue
            m = re.match(r"\s+([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
            if m:
                cfg[section][m.group(1)] = _scalar(m.group(2))
    return cfg


def book_name_of(proj):
    for k in BOOK_KEYS:
        v = proj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    raise SystemExit(
        "配置缺书名：project.yaml 的 project 段里 "
        + "／".join(BOOK_KEYS) + " 至少给一个非空值（模板用的是 name）")


def main(cfg_path):
    cfg = load_project_config(cfg_path)
    proj = cfg.get("project")
    if not isinstance(proj, dict):
        raise SystemExit("配置缺 project 段：project.yaml 须有顶层「project:」段（照 assets/project.template.yaml 抄）")
    book = book_name_of(proj)
    root = os.path.dirname(os.path.abspath(cfg_path))
    ws = proj.get("workspace_path") or os.path.join(root, "工作区")
    lib = proj.get("library_path") or os.path.join(root, "本体库")
    if not isinstance(proj.get("source_path"), str) or not proj["source_path"].strip():
        raise SystemExit("配置缺语料路径：project.source_path 必须是非空字符串（全文语料的绝对路径）")
    src = proj["source_path"]
    if not os.path.exists(src):
        raise SystemExit(f"语料不存在：{src}")
    # 单元标记按模板 project.unit_pattern 数；缺省/留空回退历史字面量 <<<CHAPTER
    unit_pattern = proj.get("unit_pattern")
    pat = re.compile(unit_pattern) if isinstance(unit_pattern, str) and unit_pattern.strip() else None
    n = 0
    for line in io.open(src, encoding="utf-8"):
        if (pat.search(line) if pat else "<<<CHAPTER" in line):
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
        if os.path.getsize(state) == 0:
            raise SystemExit(f"STATE 写完回读为 0 字节：{state}")
    print(f"OK 书房就绪：语料标记 {n} 章｜工作区={ws}｜本体库={lib}｜STATE={state}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "project.yaml")
