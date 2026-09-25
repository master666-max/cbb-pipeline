# exp8-constitution · 宪章与卫兵（L8 必装基座）

## 装什么
L8-CONSTITUTION.md（根目录）+ experimental-l8/scripts/l8_guard.txt + lifelog_append.txt（工具）。

## install.md 步骤
1. **前置确认（强制）**：向用户展示宪章全文，取得对六条条的明示确认；未确认即中止 L8 安装。
2. 复制 template/L8-CONSTITUTION.md → 工作区根；复制 experimental-l8/scripts/l8_guard.txt、lifelog_append.txt → tools/（包内共享层，非本模块目录）（E-fallback 沿用 .txt 形态）。
3. 建 mutations/{candidates,}/ 与 mutations/LEDGER.md（空台账：表头+创世哈希行）。
4. 初始化 lifelog：当月文件写入创世行（lifelog_append.txt 'L8-INIT'）。
5. 校验点：`py -X utf8 tools/l8_guard.txt`（无候选时应全绿：integrity/lifelog/ledger 三项 OK）。

## 依赖
L7 全上。本模块必须先于其他 exp8-* 安装。

## 溯源
DGM（arXiv:2505.22954）sandboxing + human oversight + archive 设计；本库 manifest 哈希体系扩展。
