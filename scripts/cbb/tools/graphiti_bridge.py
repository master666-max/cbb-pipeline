# -*- coding: utf-8 -*-
"""graphiti_bridge.py — U-C03.7 graphiti 就绪层（工单 v1.8 §0 · 2026-09-18）

用户裁决："接口端口准备好，加个 LLM 就能用"。本件=端口，不含运行时依赖：
- LLMConfig 工厂双预设：DeepSeek 付费档 / LM Studio 本地 GLM-5.3flash 免费档；
  凭证走环境变量（DEEPSEEK_API_KEY / LMSTUDIO_API_KEY），缺失即明确报错（D-004：key 不落盘不输出）。
- 嵌入已知档：qwen3-embedding-8b（q8_0，4096 维）@ http://127.0.0.1:8080/v1/embeddings。
- ingest_candidates()：cbb 候选 → graphiti add_episode，**复用 cbb-extract
  build_episode_kwargs**（Step0 Tier2 已验证形态），禁重造参数组装。
- graphiti 未安装时 import 即明确报错（不静默降级）。

启用三步见同目录 GRAPHITI-READY.md。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CBB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CBB / "cbb-extract"))
sys.path.insert(0, str(CBB / "cbb-anchor"))
import cbb_extract  # noqa: E402  build_episode_kwargs 单一事实源

DEEPSEEK_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-flash"          # 在案名（工单 v1.8 §0 抽检条款同款）
LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
LMSTUDIO_MODEL = "glm-5.3-flash"           # 本地免费档（用户裁决双预设之一）

EMBEDDING_PROFILE = {                       # 嵌入已知档（U-C01 起在案）
    "provider": "lmstudio",
    "model": "qwen3-embedding-8b",
    "quant": "q8_0", "dim": 4096,
    "base_url": "http://127.0.0.1:8080/v1/embeddings",
}


def llm_config(preset: str) -> dict:
    """LLMConfig 工厂双预设。返回 graphiti LLMConfig 构造参数（dict）；
    凭证缺失立即 ValueError（明确指出变量名），绝不返回半配置。"""
    if preset == "deepseek":
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise ValueError("缺环境变量 DEEPSEEK_API_KEY（D-004：凭证只走环境变量，不落盘）")
        return {"api_base": DEEPSEEK_BASE, "api_key": key, "model": DEEPSEEK_MODEL}
    if preset == "lmstudio-flash":
        # LM Studio 本地档无鉴权是常态：key 可选，缺省占位 "lm-studio"（服务端不校验）
        key = os.environ.get("LMSTUDIO_API_KEY") or "lm-studio"
        return {"api_base": LMSTUDIO_BASE, "api_key": key, "model": LMSTUDIO_MODEL}
    raise ValueError(f"未知预设 {preset!r}：合法=deepseek | lmstudio-flash")


def embedding_config() -> dict:
    return dict(EMBEDDING_PROFILE)


def make_graphiti(preset: str, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
    """组装 Graphiti 实例（延迟 import——未安装 graphiti 时此处才报错）。"""
    try:
        from graphiti_core import Graphiti
        from graphiti_core.llm_client import LLMConfig
    except ImportError as e:  # pragma: no cover（离线 stub 不触达）
        raise ImportError(
            "graphiti 未安装：py -m pip install graphiti-core"
            "（启用步骤见 cbb/tools/GRAPHITI-READY.md）") from e
    pw = neo4j_password or os.environ.get("NEO4J_PASSWORD")
    if not pw:
        raise ValueError("缺 Neo4j 密码：参数 neo4j_password 或环境变量 NEO4J_PASSWORD")
    llm = LLMConfig(**llm_config(preset))
    return Graphiti(neo4j_uri, neo4j_user, pw, llm_config=llm)


def episode_body_of(chapter_no: int, records: list[dict]) -> str:
    """一章候选记录 → episode 文本（确定性序列化；实体/关系/事件/伏笔全量）。"""
    parts = [f"CHAPTER {chapter_no:04d} 正典记录"]
    for r in records:
        c = r.get("canonical", {})
        head = c.get("name") or f"{c.get('subject')} --{c.get('rel_type')}--> {c.get('object')}"
        parts.append(f"[{r.get('record_type')}] {head}")
        for o in r.get("observations", []):
            parts.append(f"  - {o.get('text', '')}")
    return "\n".join(parts)


def ingest_candidates(graphiti, chapter_records: dict[int, list[dict]],
                      group_id: str = "mishen-canon") -> dict:
    """候选批量入 graphiti：每章一个 add_episode，kwargs 全部经
    cbb_extract.build_episode_kwargs 组装（已测形态：伪锚点 reference_time+R6 标配）。
    graphiti 参数=任意具备 add_episode(**kwargs) 协议的对象（stub 单测即用此协议）。"""
    results = {}
    for chapter_no in sorted(chapter_records):
        recs = chapter_records[chapter_no]
        kwargs = cbb_extract.build_episode_kwargs(
            order_index=chapter_no,
            episode_body=episode_body_of(chapter_no, recs),
            episode_name=f"ch{chapter_no:04d}",
            group_id=group_id,
            source_description="cbb jsonl 本体库 · <示例项目>",
        )
        results[chapter_no] = graphiti.add_episode(**kwargs)
    return results


def main(argv=None) -> int:  # pragma: no cover（CLI 便捷口）
    import argparse
    ap = argparse.ArgumentParser(description="graphiti 桥（U-C03.7）")
    ap.add_argument("--print-presets", action="store_true")
    ns = ap.parse_args(argv)
    if ns.print_presets:
        print(json.dumps({
            "presets": {"deepseek": {"api_base": DEEPSEEK_BASE, "model": DEEPSEEK_MODEL,
                                     "env": "DEEPSEEK_API_KEY"},
                        "lmstudio-flash": {"api_base": LMSTUDIO_BASE, "model": LMSTUDIO_MODEL,
                                           "env": "LMSTUDIO_API_KEY(可选)"}},
            "embedding": EMBEDDING_PROFILE}, ensure_ascii=False, indent=1))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
