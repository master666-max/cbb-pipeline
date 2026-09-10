# MEM-EVOLVE-SANDBOX · 一键复现脚本（Windows / PowerShell）
# 用法：在仓库根目录执行  .\reproduce.ps1
# 全部命令使用 stdlib，无第三方依赖。结果写入 runs\<name>\

$ErrorActionPreference = "Continue"
$PY = "py -3.14"

# 0) 被测源码位置（改成你的 bootstrap_v3.py 路径）
$env:BS3_PATH = "D:\zcode专用！！！！危险！！！！！！！！！\library-bootstrap-v3.0\bootstrap_v3.py"

Write-Host "=== 0/8 门禁（不通过则后续全部作废） ===" -ForegroundColor Cyan
& $PY harness/run.py selftest

Write-Host "=== 1/8 一致性探针 C1-C5（真实源码） ===" -ForegroundColor Cyan
& $PY harness/run.py consistency --procs 12
& $PY harness/run.py concurrency --procs 12

Write-Host "=== 2/8 主实验：clean / pseudo / deceptive（24 种子 x 60 代） ===" -ForegroundColor Cyan
& $PY harness/run.py evolve --terrain clean --cfgs static none two-tier random --seeds 24 --gens 60
& $PY harness/run.py evolve --terrain pseudo --cfgs static none two-tier --seeds 24 --gens 60
& $PY harness/run.py evolve --terrain deceptive --cfgs strict-admit two-tier --seeds 24 --gens 60 --genes w_kw filter_zero

Write-Host "=== 3/8 专项：更新(H2) / 重组(H4) / 遗忘(H3) ===" -ForegroundColor Cyan
& $PY harness/run.py importance --seeds 12 --warmup 6
& $PY harness/run.py reorg      --seeds 12
& $PY harness/run.py forget     --seeds 12 --gens 60

Write-Host "=== 4/8 漂移：先标定阈值，再扫 alpha ===" -ForegroundColor Cyan
& $PY harness/run.py calibrate --alphas 0.0 0.10 --seeds 8 --gens 40
$env:ANCHOR_THRESHOLD = "0.95"          # ← 用 calibrate 输出的标定值替换
& $PY harness/run.py sweep --alphas 0.0 0.05 0.10 0.20 0.30 --seeds 12 --gens 40
& $PY harness/run.py sweep --alphas 0.20 --cfgs two-tier two-tier+anchor two-tier+reanchor --seeds 12 --gens 40
& $PY harness/run.py sweep-show

Write-Host "=== 5/8 消融：哪条护栏在赚钱 ===" -ForegroundColor Cyan
& $PY harness/run.py ablate --terrains pseudo    --seeds 12 --gens 25
& $PY harness/run.py ablate --terrains deceptive --seeds 12 --gens 40 --genes w_kw filter_zero

Write-Host "=== 6/8 金标噪声：独立 vs 相关（E52/E57） ===" -ForegroundColor Cyan
& $PY harness/run.py noise --terrain clean --seeds 24 --gens 25 --ps 0.3
& $PY harness/run.py noise --terrain clean --seeds 12 --gens 25 --ps 0.3 0.7

Write-Host "=== 7/8 注意力预算：门控判决可靠性门槛（E17+E64） ===" -ForegroundColor Cyan
& $PY harness/run.py gate-budget --terrain pseudo --seeds 12 --gens 25
& $PY harness/run.py budget      --seeds 8 --budgets 40 60 100 150 300 600

Write-Host "=== 8/8 全场景矩阵 ===" -ForegroundColor Cyan
& $PY harness/run.py matrix --cfgs static none two-tier --seeds 12 --gens 60

Write-Host "完成。结果在 runs\ 下；用  py -3.14 harness/run.py show --path <关键字>  查看汇总。" -ForegroundColor Green
