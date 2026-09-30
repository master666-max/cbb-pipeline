# -*- coding: utf-8 -*-
"""test_judging_config.py — U1 判卷配置层：加载/校验/解析/契约外置/key 链顺序。"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cbb2 import judging  # noqa: E402


def _write_cfg(tmp: Path, raw: dict, contract="测试契约正文"):
    (tmp / "contracts").mkdir(exist_ok=True)
    (tmp / "contracts" / "judge.txt").write_text(contract, encoding="utf-8")
    raw = {"contract_file": "contracts/judge.txt", **raw}
    p = tmp / "judging.config.json"
    p.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return p


BASE = {"version": "1.0", "book": "测试书", "store_root": "store", "work_dir": "store/work",
        "panel": {"DS": {"base": "https://x", "model": "m", "key": {"env": "K1", "registry": "K1"},
                         "role": "panel"},
                  "THIRD": {"base": "https://y", "model": "m2", "key": {"registry": "K2"},
                            "role": "audit"}},
        "plants": {"pairs": 4, "seed": 7}, "batch": {"chunk": 10},
        "gate": {"correct_min": 5, "capture_min": 0.8334}}


def test_load_ok_and_resolution(tmp_path):
    p = _write_cfg(tmp_path, dict(BASE))
    cfg = judging.load_config(p)
    assert cfg.book == "测试书"
    assert cfg.store_root == tmp_path / "store"          # 相对路径以 config 所在目录为基准
    assert cfg.work_dir == tmp_path / "store" / "work"
    assert cfg.contract == "测试契约正文"                  # 契约外置文件加载
    assert cfg.examiner("DS").role == "panel"
    assert cfg.examiner("THIRD").audit
    assert cfg.examiner("THIRD").key_registry == ["K2"]


def test_missing_required_rejected(tmp_path):
    bad = {k: v for k, v in BASE.items() if k != "gate"}
    p = _write_cfg(tmp_path, bad)
    try:
        judging.load_config(p)
        assert False, "缺必填字段应抛错"
    except ValueError as e:
        assert "gate" in str(e)


def test_empty_contract_rejected(tmp_path):
    p = _write_cfg(tmp_path, dict(BASE), contract="  ")
    try:
        judging.load_config(p)
        assert False, "空契约应抛错"
    except ValueError as e:
        assert "契约文件为空" in str(e)


def test_panel_requires_a_panel_role(tmp_path):
    bad = json.loads(json.dumps(BASE))
    bad["panel"] = {"THIRD": bad["panel"]["THIRD"]}  # 只有 audit 考官
    p = _write_cfg(tmp_path, bad)
    try:
        judging.load_config(p)
        assert False, "无 panel 考官应抛错"
    except ValueError as e:
        assert "panel" in str(e)


def test_key_chain_env_beats_registry(tmp_path, monkeypatch):
    p = _write_cfg(tmp_path, dict(BASE))
    cfg = judging.load_config(p)
    e = cfg.examiner("DS")
    monkeypatch.setenv("K1", "from-env")
    monkeypatch.setattr(judging.ops, "secret_from_registry", lambda name: "from-registry")
    assert e.key() == "from-env"                       # env 优先
    monkeypatch.delenv("K1")
    assert e.key() == "from-registry"                  # env 缺席回落注册表
    monkeypatch.setattr(judging.ops, "secret_from_registry", lambda name: "")
    assert e.key() == ""                               # 全缺席=空（调用方 BLOCKED）
