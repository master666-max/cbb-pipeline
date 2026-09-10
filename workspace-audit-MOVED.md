# workspace-audit-MOVED.md — 审计区迁出存根（2026-09-11）

考古产出目录 `workspace-audit/` 已于 2026-09-11 迁出至独立审计区：

**`D:\zcode-workspace-audit`**（独立 git 仓库，BORN commit `886ac73`）

- 迁出时点：本主区 commit `5476d70`（= tag `zero-point-v1`，红队勘误后终态）
- 完整性：298 项文件逐文件 sha256 对账零差异，清单见新家 `出生证明.md`
- 随迁：主区根的 `red-team-report.csv` 与 `red-team-output/`（红队审计全套）→ 新家 `red-team/`
- 历史断言锚点验证：`git show zero-point-v1:<原路径>`（协议见新家 `ANCHOR-PROTOCOL.md`）
- 本存根与 `_meta/` 为元文件，非宇宙成员；增量制图扫描一律跳过
- 主区宇宙新增成员：`大审查-工作包-20260909/`（118,481 文件，冻结期工作回灌）与 `大审查2/`（16 文件核验包）——并入≠入账，语义入账待增量制图（MERGE commit `c781164`）
