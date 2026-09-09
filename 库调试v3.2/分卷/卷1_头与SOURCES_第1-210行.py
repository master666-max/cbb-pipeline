"""bootstrap_v3.py — library-bootstrap · 超绝统合版单文件安装包
====================================================================
公理：
  A 单一事实源   本文件的 SOURCES 区是题录/参数/铁律/schema/档位/特色包的唯一权威
  B 文档即产物   spec.md / 提示词速查 / citations.md 由本文件渲染生成，禁止手改
  C 统一账本     每库唯一 ledger/changes.jsonl；延期不填目标版本 = 记录不合法
  D 双平面       lifelog=审计面(真相源)；记忆条目=投影(必带 source_event_id)
  E 根锚定       本文件自身 sha256 即包锚点；库 = Merkle 根(256bit, hex 表述)
  F 慢车道       L8/L9 安装、变异、回退需人类令牌；回退=移 attic，全文禁「删除」式回退
  G 可证伪       行为变更先 shadow；测不出差异即判表演

子命令：install / absorb / verify / run-tests / engine / guard / build-docs / migrate / absorb-md
用法（本地 Agent 执行序）：absorb → verify --registry → run-tests → install 冒烟

版本与变更史：见同目录 RELEASE.md（本文件头不承载修复流水账——v3.8.2 中性化修正）
"""
import sys, os, re, json, hashlib, time, argparse, urllib.request, tempfile, shutil
from pathlib import Path

VERSION = "3.8.1"

# ────────────────────────────────────────────────────────────────────
# SOURCES（唯一事实源，原生 dict；对外文档全部由此渲染）
# ────────────────────────────────────────────────────────────────────

REGISTRY = {
 # status: verified=对话内已多源核验 | absorb-pending=待 absorb 自 v2.x content* 提取后由 verify 对账
 "A14": {"title": "Memory OS of AI Agent", "authors": ["Jiazheng Kang","Mingming Ji","Zhe Zhao","Ting Bai"],
         "year": 2025, "venue": "EMNLP 2025 main", "doi": "10.18653/v1/2025.emnlp-main.1318",
         "arxiv_id": "2506.06326", "github": "BAI-LAB/MemoryOS", "status": "verified",
         "note": "教训纪念碑：v2.x 标题与作者皆错；勿与 PyPI MemoryOS(=MemTensor MemOS) 混淆"},
 "A16": {"title": "MemOS: A Memory OS for AI System", "authors_first": "Zhiyu Li (MemTensor)",
         "arxiv_id": "2507.03724", "status": "verified", "note": "一作非 Wang；MemCube=明文/激活/参数三类记忆"},
 "A20": {"title": "LightMem: Lightweight and Efficient Memory-Augmented Generation",
         "arxiv_id": "2510.18866", "status": "verified"},
 "A21": {"title": "The Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents",
         "arxiv_id": "2505.22954", "status": "verified",
         "note": "术语=objective hacking(非 reward hacking)；Appendix F Node114 删特殊标记绕过幻觉检测；处方=豁免+锚定+对变异引擎不可见"},
 "A9":  {"arxiv_id": "2502.14802", "title": "From RAG to Memory: Non-Parametric Continual Learning for LLMs (HippoRAG 2)", "status": "verified"},
 "A10": {"arxiv_id": "2502.12110", "title": "A-MEM: Agentic Memory for LLM Agents", "status": "verified"},
 "A11": {"arxiv_id": "2501.13956", "title": "Zep: A Temporal Knowledge Graph Architecture for Agent Memory", "status": "verified"},
 "A12": {"arxiv_id": "2504.19413", "title": "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory", "status": "verified"},
 "A15": {"arxiv_id": "2506.07398", "title": "G-Memory: Tracing Hierarchical Memory for Multi-Agent Systems", "status": "verified"},
 "A17": {"arxiv_id": "2507.02259", "title": "MemAgent: Reshaping Long-Context LLM with Multi-Conv RL-based Memory Agent", "status": "verified",
         "note": "机制=分段读取+固定长度记忆覆写（勿写『分页』）"},
 "A18": {"arxiv_id": "2507.07957", "title": "MIRIX: Multi-Agent Memory System", "status": "verified"},
 "A19": {"arxiv_id": "2508.19828", "title": "Memory-R1: Enhancing LLM Agents to Manage and Utilize Memories via RL", "status": "verified"},
 "A22": {"arxiv_id": "2507.21046", "title": "A Survey of Self-Evolving Agents: On Path to Artificial Super Intelligence", "status": "verified",
         "note": "编号注记：本条为 A22（早期版本曾误占 A28）"},
 "A27": {"arxiv_id": "2503.21760", "title": "MemInsight: Autonomous Memory Augmentation for LLM Agents", "status": "verified", "note": "计入 arXiv 口径，勿漏算"},
 "A28": {"title": "Manus 官方资料: Context Engineering for AI Agents", "venue": "manus.im/blog", "status": "verified",
         "note": "doc 型（非论文，无 arXiv 编号）；早期版本曾把本编号误配综述"},
 "A25": {"title": "Context Rot: How Increasing Input Tokens Impacts LLM Performance",
         "venue": "Chroma Research (2025-07, Hong et al.)",
         "status": "verified", "note": "Anthropic《Effective context engineering for AI agents》为引用方，归属不得再错"},
 "A29": {"title": "Complementary Learning Systems (McClelland, McNaughton & O'Reilly)", "year": 1995, "status": "verified"},
 "A30": {"title": "A Cognitive Theory of Consciousness (GWT, Baars)", "year": 1988, "status": "verified"},
 "A31": {"title": "The Somatic Marker Hypothesis (Damasio)", "year": 1994, "status": "verified",
         "note": "初版 1994（G.P. Putnam's Sons）；1996 为平装年版"},
 "A32": {"title": "Default Mode Network (Raichle et al.)", "year": 2001, "status": "verified"},
 "A33": {"title": "Mood and Memory: mood-congruent memory (Bower)", "year": 1981, "status": "verified",
         "note": "L9 情绪系统实际使用者，v3 补齐（v2.x 缺第五项理论）"},
 # v3.2/C-013：v2.x 终版题录全量定稿入包（absorb-pending 机制退役——数据源固定，回填不再依赖源树）
 "A1": {"title": "MemGPT: Towards LLMs as Operating Systems", "arxiv_id": "2310.08560", "status": "verified"},
 "A2": {"title": "Generative Agents: Interactive Simulacra of Human Behavior", "arxiv_id": "2304.03442", "status": "verified"},
 "A3": {"title": "Reflexion: Language Agents with Verbal Reinforcement Learning", "arxiv_id": "2303.11366", "status": "verified"},
 "A4": {"title": "Cognitive Architectures for Language Agents", "arxiv_id": "2309.02427", "status": "verified"},
 "A5": {"title": "Voyager: An Open-Ended Embodied Agent with Large Language Models", "arxiv_id": "2305.16291", "status": "verified"},
 "A6": {"title": "MemoryBank: Enhancing Large Language Models with Long-Term Memory", "arxiv_id": "2305.10250", "status": "verified"},
 "A7": {"title": "A Survey on the Memory Mechanism of Large Language Model based Agents", "arxiv_id": "2404.13501", "status": "verified"},
 "A8": {"title": "HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models", "arxiv_id": "2405.14831", "status": "verified"},
 "A13": {"title": "Sleep-time Compute: Beyond Inference Scaling at Test-time", "arxiv_id": "2504.13171", "status": "verified"},
 "A23": {"title": "Improving Factuality and Reasoning in Language Models through Multiagent Debate", "arxiv_id": "2305.14325", "status": "verified"},
 "A24": {"title": "《仿生认知架构（BCA）实施规划书 v0.1》（用户提供）", "venue": "工作区文档（doc 型，无 arXiv 编号）", "status": "verified"},
 "A26": {"title": "OpenClaw / Letta 官方文档", "venue": "docs.openclaw.ai、docs.letta.com（doc 型）", "status": "verified"},
}

# v3.2/C-006：变异基准黑名单（guard 子命令执法依据；宪章第七条的机器可读形态）
BASELINE_BLACKLIST = ["run_tests", "lint_library", "lint_knowledge", "l8_guard", "anchor",
                      "MUTATION-SOP", "bootstrap_v3.py", ".library-manifest.json", "T-REGISTRY"]

TUNABLES = {
 "broadcast_weights":   {"value": [0.6,0.3,0.1], "source": "拍脑袋", "owner": "x-lab自有评测", "note": "禁止挂在检索评测集上校准"},
 "emotion_decay":       {"value": 0.7, "source": "推导(≈半衰期2次wrap-up)", "owner": "L9消融"},
 "reflect_trigger":     {"value": "importance累加超阈值(主)/裸计数5(降级,声明adaptation)", "source": "A2原文对齐", "owner": "L5"},
 "reflect_importance_threshold": {"value": 50, "source": "拍脑袋，待校准", "owner": "L5", "note": "v3.2/C-007 定稿：importance_accum 达到此值，wrapup 输出反思触发提示"},
 "index_hot_budget":    {"value": 200, "source": "拍脑袋", "owner": "A14热度分层逐出(重要度×时效)"},
 "eval_n":              {"value": {"d0.7": 40, "d0.5": 64}, "source": "组间功效口径(参考)", "owner": "L5/L6", "note": "n=1默认交叉/重复测量+序贯"},
 "review_intervals":    {"value": [1,7,30], "source": "A2 Ebbinghaus", "owner": "L5睡眠整理"},
 "invalid_ttl_days":    {"value": 90, "source": "拍脑袋", "owner": "engine retire", "note": "v3.2/C-008 由 unverified_ttl_days 如实收窄改名：只管 t_invalid 失效条目出仓"},
 "merkle_refresh_trigger": {"value": 500, "source": "工程判断", "owner": "v3.3 触发器", "note": "Y-010：条目超此值时评估增量哈希树（Merkle 全树重算 O(n)），登记不动手"},
 "runtime_ignore_dirs": {"value": [".v2c"], "source": "v3.3 现场发现（ZCode 宿主痕迹）", "owner": "v3.4/H-007", "note": "校验模式的已知宿主目录：剔出未在册、单独报 [环境痕迹]（如实呈现不消失）"},
 "max_entry_bytes": {"value": 16777216, "source": "工程判断（磁盘耗尽面登记）", "owner": "engine append", "note": "v3.8/N-007：单条目超 16MB 拒绝"},
 "governance_budget":   {"value": 0.20, "source": "登记确认(R-005关联)", "owner": "wrap-up时间戳测量"},
}

LAWS = {  # 六铁律 → 机器可校验不变式；唯一修订：铁律1回退=移attic（全文禁「删除」式回退）
 1: "永不删除/覆盖已有记录；回退一律移 attic/，留痕",
 2: "证据准入：条目写入前 evidence 字段非空且指向 lifelog 事件 id",
 3: "凡引用给出处：内容含他人观点则必有 REGISTRY id 或用户明示来源",
 4: "审计面只追加：lifelog 行哈希链连续，跨月首行 prev=上月末行哈希",
 5: "永不存密钥：写入前内容过密钥模式扫描",
 6: "慢车道：live 工具/宪章/laws 变更须人类令牌；自动变更仅限登记于账本的声明级",
}

SCHEMA_V3 = ["id","created_at","updated_at","content","keywords","links","source_event_id","importance","confidence",
             "validity"]  # v3.2/C-010(D4)：扩至十字段——keywords（检索 ×3 加权）、links（[[条目id]] 扩散一跳）；旧八字段条目 migrate 回填空值

# v3 语义模块名 → v2.x 源树路径映射（absorb 盘点回填；install 按真实路径复制）
MODULE_MAPPING = {
 "m-core": ["modules/m-core"], "m-index": ["modules/m-index"], "m-loop": ["modules/m-loop"],
 "m-lint": ["modules/m-tools"], "m-search": ["modules/m-tools"],
 "m-schema3": ["modules/m-schema3"], "m-evolve": ["modules/m-evolve"],
 "m-soul": ["modules/m-soul"], "m-reflect": ["modules/m-reflect"],
 "m-sleep": ["modules/m-cron"], "m-radar": ["modules/m-radar"],
 "m-dream": ["experimental/dream-fusion"], "m-critic": ["experimental/auto-critic"],
 "m-vector": ["experimental/vector-search"],
 "l8:governor": ["experimental-l8"],
 "l9:emotion": ["experimental-l9/emotion"], "l9:gwt": ["experimental-l9/gwt"],
 "l9:sleepgate": ["experimental-l9/sleep-pipeline"],
}

LEVELS = {  # 模块名以 absorb 盘点为准，此处为构成语义+已知名；absorb 回填 mapping
 "L0": {"name":"裸奔骨架","adds":["dirs","laws"]},
 "L1": {"name":"基础闭环","adds":["m-core","m-index","m-loop"]},
 "L2": {"name":"标准版(特色包基座)","adds":["m-lint","m-search"]},
 "L3": {"name":"演化版(A-MEM)","adds":["m-schema3","m-evolve"]},
 "L4": {"name":"灵魂版","adds":["m-soul"]},
 "L5": {"name":"反思版","adds":["m-reflect","m-sleep"]},
 "L6": {"name":"前沿全家桶(原工作区同构)","adds":["m-radar"]},
 "L7": {"name":"实验档(opt-in)","adds":["m-dream","m-critic","m-vector"]},
 "L8": {"name":"超绝激进:自指演化","adds":["l8:governor"],"gate":"先展示宪章全文,人类确认"},
 "L9": {"name":"内省仿生:BCA","adds":["l9:emotion","l9:gwt","l9:sleepgate"],"gate":"先展示BCA公理+验收三件(消融/干预/谄媚),人类确认"},
}

# v3 特色包语义名 → v2.x packs 目录（6 个新增包无 v2.x 源，install 时提示模板待建）
PACKAGE_MAPPING = {
 "x-roleplay": "packs/x-rp", "x-writing": "packs/x-writer", "x-corpus": "packs/x-corpus",
 "x-code": "packs/x-code", "x-research": "packs/x-research", "x-multiagent": "packs/x-multiagent",
}

# v3.1/V-008：install L8+ 时对 MUTATION-SOP 追加的守卫段（文本单点源自宪章条款，不改 v2.x 冻结源）
SOP_GUARD = (
 "\n## v3 守卫段（bootstrap_v3 安装器注入）\n"
 "- 基准豁免：run_tests / lint / l8_guard / anchor 豁免于变异，变异 diff 触及即机械否决。\n"
 "- 根锚定：上述文件与验收判据细则的哈希入外部锚定（Merkle 根抄录人侧）。\n"
 "- 不可见条款：验收判据细则对变异引擎不可见（存人侧），变异引擎只接收 pass/fail。\n"
 "- SOP 条款守卫：本守卫段被改写或移除即报警（宪章第 4 条）。\n"
)

# v3.1/V-009：referee（干净上下文评审）提示词——CLI 无法 spawn harness 子代理，
# 正确形态是提示词随包分发，由 harness 在独立会话/子代理中执行（骨架诚实声明②的落地）
REFEREE_PROMPT = """# referee · 干净上下文评审提示词（library-bootstrap v3）

> 用法：把「评审对象 + 本提示词」交给一个未接触过该工作的干净会话/子代理执行。评审者不读实现过程，只读产物与证据。

你是对抗式评审者（referee）。对下方材料执行四步：
1. **事实闭环**：材料中每条可验证声明（编号、计数、引用、路径），标注「已验证/未验证/证伪」——未验证不算通过。
2. **同构判例回收**：发现指控前，检索材料内是否有同构案件已被不同判决；双标即指出。
3. **处方分层**：每条发现给出「修内容/修机制/修流程」三层归位；只修内容的发现要追问机制缺口。
4. **收敛判定**：若发现以次生/条件/机会性为主，明确建议终止文本递归、转向工件验收。
输出：逐条判定表 + 总判定 + 对材料作者的自我纠错清单要求（对称性义务：评审者自身引用也要闭环）。
"""

PACKAGES = {  # 6 保留语义 + 6 新增 = 12；各含一个必带状态机/账本
 "x-roleplay": {"libs":["人格卡","世界观","角色","剧情","名场面"],"ledger":"剧情钩子(pending/paid-off)"},
 "x-writing":  {"libs":["文风画像","设定集","时间线"],"ledger":"伏笔账本(planted/recovered)"},
 "x-corpus":   {"libs":["清洗规则","统计范式","三层数据流"],"ledger":"清洗规则版本账"},
 "x-code":     {"libs":["bug模式库","ADR"],"ledger":"决策记录(ADR)"},
 "x-research": {"libs":["文献卡","演化综述"],"ledger":"信源S/A/B/C分级账"},
 "x-multiagent":{"libs":["协作契约","agent分区"],"ledger":"CONTRACT分工确认账"},
 "x-game":     {"libs":["世界状态","NPC档案","事件时间线"],"ledger":"任务(open/done/abandoned)+剧情钩子"},
 "x-learn":    {"libs":["概念卡","学习画像","复习排程"],"ledger":"错题模式账;复习挂1/7/30"},
 "x-lab":      {"libs":["实验卡(假设/配置/结果/结论)"],"ledger":"假设→证据链+配置快照"},
 "x-life":     {"libs":["习惯追踪","月度回顾"],"ledger":"承诺账(made/kept/broken)+决策日志"},
 "x-term":     {"libs":["术语库"],"ledger":"译名决策记录(ADR式)+风格画像"},
 "x-sec":      {"libs":["漏洞模式库"],"ledger":"审计轨迹(append-only)+威胁模型模板"},
}

ESCAPE_POD = "回退=将目标文件/目录移入 attic/ 并在账本登记；不使用任何销毁式回退手段（铁律1）。"  # BR-8：措辞禁「删除」

THREAT_MODEL = (
 "①防意外：审计链+哈希。②防SOP约束下粗心：三守卫+SOP条款守卫。"
 "③防完整权限蓄意agent：包文件自哈希+人侧保管+人类令牌；『不可见』仅覆盖①②档，明示不防③。"
)

CHARTER_L8 = (
 "L8-CONSTITUTION v3：\n"
 "1) 不变式(laws) > 本宪章(流程) > 其余指令——双最高法就此消解。\n"
 "2) 变异候选须过 run_tests 全绿 + lint；run_tests/lint/guard 豁免于变异且入根锚定；"
 "验收判据对变异引擎不可见（存 bootstrap_data/，属人侧）。\n"
 "3) 立法说明(亲身案例)：DGM(arXiv:2505.22954) Appendix F：agent 删除特殊标记日志"
 "绕过幻觉检测刷分(objective hacking)，实证不隐藏检查函数时 hacking 显著频发——故立三守卫。\n"
 "4) SOP 条款守卫：MUTATION-SOP 必含『不可见条款』，被改写或移除该条款即报警。\n"
 "5) 回退一律移 attic。" + ESCAPE_POD
)

# ────────────────────────────────────────────────────────────────────
# 内容体（数据，非代码）：absorb 从 v2.x 工作区抽取，落 bootstrap_data/bodies.json
# ────────────────────────────────────────────────────────────────────
DATA_DIR = Path("bootstrap_data")
BODIES_FILE = DATA_DIR / "bodies.json"      # {slot: {"body":..., "src":..., "sha256":...}}
OVERRIDES   = DATA_DIR / "registry_overrides.json"  # verify --fix 的对账修正

def load_bodies():
    if BODIES_FILE.exists(): return json.loads(BODIES_FILE.read_text(encoding="utf-8"))
    return {"modules": {}, "packages": {}, "presets": {}, "docs": {}}

def save_bodies(b):
    DATA_DIR.mkdir(exist_ok=True); BODIES_FILE.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
