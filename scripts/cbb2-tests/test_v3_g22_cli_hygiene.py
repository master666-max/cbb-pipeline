# -*- coding: utf-8 -*-
"""test_v3_g22_cli_hygiene.py — G22 CLI 卫生批（D-27）。
运行：py -X utf8 -m pytest cbb-v2/tests/test_v3_g22_cli_hygiene.py -q
判据：退役件清单 `--help` 全部 exit 0；`--dry-run` 盘点口可用（build_index_v2 零写盘）。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent.parent / "cbb" / "tools"

# G22 清单：build_index_v2 / web_console / graphiti 系退役件（详见 cbb/tools/legacy-退役说明.md）
CLI_LIST = ["build_index_v2.py", "web_console.py", "graphiti_bridge.py",
            "graphiti_dump.py", "graphiti_ingest.py", "graphiti_ready.py", "graphiti_spike.py"]

# skill 包只携带在役件、不含退役件——包内执行时整体跳过（工作区副本正常跑）
if not (TOOLS / "web_console.py").exists():
    pytest.skip("退役件清单为工作区战役面板，skill 包不含退役件", allow_module_level=True)


def _run(tool, *args):
    return subprocess.run([sys.executable, "-X", "utf8", str(TOOLS / tool), *args],
                          capture_output=True, timeout=120)


def test_g22_help_exits_zero_for_all():
    for tool in CLI_LIST:
        r = _run(tool, "--help")
        assert r.returncode == 0, f"{tool} --help 退出码 {r.returncode}：{r.stderr.decode('utf-8', 'replace')[:200]}"


def test_g22_dry_run_available():
    # ingest 的 --dry-run 语义是"只抽取不喂入"（需活端点），不入零依赖 smoke；
    # 其余退役件 --dry-run 均为零网络盘点口。
    for tool in CLI_LIST:
        if tool == "graphiti_ingest.py":
            assert "--dry-run" in _run(tool, "--help").stdout.decode("utf-8", "replace")
            continue
        r = _run(tool, "--dry-run")
        assert r.returncode == 0, f"{tool} --dry-run 退出码 {r.returncode}：{r.stderr.decode('utf-8', 'replace')[:200]}"


def test_g22_build_index_dry_run_zero_write(tmp_path):
    """D-27 反例转绿：--dry-run 对不存在库只盘点（0 行），且**不创建任何目录/进度盘**。"""
    ghost = tmp_path / "ghost-store"   # 不预建——历史缺陷路径会在只读目录 mkdir+写盘
    r = _run("build_index_v2.py", "--dry-run", "--store", str(ghost))
    assert r.returncode == 0
    rep = json.loads(r.stdout.decode("utf-8").strip().splitlines()[-1])
    assert rep["dry_run"] is True and rep["rows"] == 0
    assert not ghost.exists()          # 零写盘判据
    assert not (tmp_path / "索引").exists()


def test_g22_retirement_readme_exists():
    md = TOOLS / "legacy-退役说明.md"
    assert md.exists()
    body = md.read_text(encoding="utf-8")
    for tool in CLI_LIST:              # 每件都登记状态与替代路径
        assert tool.split(".")[0] in body, f"{tool} 未登记进 legacy-退役说明.md"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"OK {fn.__name__}")
    print(f"{len(fns)} tests PASS")
