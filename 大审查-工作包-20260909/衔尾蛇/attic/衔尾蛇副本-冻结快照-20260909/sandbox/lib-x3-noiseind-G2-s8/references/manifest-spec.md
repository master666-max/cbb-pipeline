# .library-manifest.json 规范（v1）

> 建库完成时由 bootstrap_verify.txt 生成/校验。它是「装了什么」的唯一事实源，升级/加装都先读它。

```json
{
  "skill": "library-bootstrap",
  "skill_version": "1.0.0",
  "installed_at": "{{SLOT:DATE}}",
  "harness": "{{SLOT:HARNESS_NAME}}",
  "entry_file": "AGENTS.md | CLAUDE.md | .cursorrules",
  "env_tier": "E-full | E-fallback | E-manual",
  "py_runner": "python3 | py | py+txt | none",
  "cron_mode": "auto | manual",
  "preset": "L0..L7 | custom",
  "modules": ["m-core", "m-index", "..."],
  "packs": ["x-rp", "..."],
  "experimental": ["vector-search", "..."],
  "files": [
    {"path": "knowledge/pitfalls.md", "sha1_8": "a1b2c3d4", "module": "m-core"},
    {"path": "knowledge/skills/task-start/SKILL.md", "sha1_8": "...", "module": "m-loop"}
  ]
}
```

## 字段规则
- `files`：所有由模板复制产生的文件 + 内容哈希（前 8 位 sha1）。agent 填槽后哈希即固定，重装校验=复算哈希比对，防走样与误改。
- `experimental`：仅 L7 有值，普通档为空数组。
- 升级流程：新 skill 读旧 manifest → diff modules/files → 只装新增/变更项，已存在且哈希一致则跳过，不一致则报告差异等用户裁决（不自动覆盖，铁律 1）。

## 校验脚本职责（scripts/bootstrap_verify.txt）
1. 目标目录有 manifest → 逐文件存在性 + 哈希比对，输出「一致/漂移/缺失」三态报告。
2. 无 manifest（首次安装收尾）→ 按安装清单生成 manifest。
3. 依赖表校验：modules 展开是否满足 references/decision-tree.md 依赖表（内置同表）。
