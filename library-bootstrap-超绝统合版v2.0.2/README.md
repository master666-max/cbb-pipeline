# library-bootstrap · 超绝统合版 v2.0.2（三处偏差修正版）

> 128 文件 · 2026-09-05 发布 · 修复源：独立工作区实装发现的「三处偏差修正工单」+ 本包全量检查。
> 旧版 v2.0 / v2.0.1 保留原位；本版为唯一推荐装包。

## v2.0.2 变更记录（vs v2.0.1）
1. **TWIN.md 模板中性化**（v2.0.1 漏修，本次补上）：清除源工作区用户（miza）默认画像——偏好五问答案、预演记录行全部改为【待填充】+ 中性化声明，杜绝给新装库者装"假用户模型"。
2. install.md 引用完整性修复：PENDING.md / ABLATIONS.md / m-core(archive/_INDEX、_cold/.keep、workspace/.keep) 真模板全部补齐；6 处复制源路径歧义修正（L8/L9 共享 scripts 写全路径、agents 模板目录名写实）。
3. broadcast.txt docstring 与行为对齐（PENDING 如实标注"只写不读，回读属机器变异候选"）。
4. vector-search：空库守卫已内置（`--build` 空库 exit 0 不崩）；wrap-up 补装步骤从"已知风险"提升为 install.md **显式第 4 步**（含入链与校验点）。
5. **回归测试 T18-T21**（8 断言）锁定上述全部修复；全套 **38/38 PASS**（含 T1-T17 原有 30 项）。

## 包内自检
```
py -X utf8 run_tests.txt   → 38 PASS / 0 FAIL
```

## 说明
- L0-L9 十档全链 + 10 模块 + 6 特色包 + L7 三实验 + L8 七件 + L9 八件，一个包全装齐。
- L8/L9 直装提示词见「提示词速查.md」第二节（仍会先要求宪章/BCA 公理确认）。
- 逃生舱不变：删对应 experimental-l8|9/ 即回退，主库无损。
