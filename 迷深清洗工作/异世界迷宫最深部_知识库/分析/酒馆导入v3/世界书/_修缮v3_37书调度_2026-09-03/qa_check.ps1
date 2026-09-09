param([string]$Dir, [string[]]$Names)
$ErrorActionPreference = 'Continue'
if (!$Dir) { $Dir = 'D:DeepSeek Harness专用！危险！！！！！迷深清洗工作2异世界迷宫最深部_知识库分析酒馆导入v3世界书角色专属世界书' }
$files = if ($Names) { $Names | ForEach-Object { Join-Path $Dir ("角色专属世界书_{0}.json" -f $_) } } else { Get-ChildItem $Dir -File -Filter '*.json' | Where-Object { $_.Name -like '角色专属世界书_*.json' } | Select-Object -ExpandProperty FullName }
foreach ($p in $files) {
  $short = [IO.Path]::GetFileNameWithoutExtension($p)
  try {
    $s = Get-Content -Raw -Encoding UTF8 $p
    if ($s.Length -gt 0 -and $s[0] -eq [char]0xFEFF) { $s = $s.Substring(1) }
    $j = $s | ConvertFrom-Json
    $uids = @($j.entries | ForEach-Object { $_.uid })
    $contig = -not ($uids | Where-Object { $_ -ne $null }) -and ($uids.Count -eq 0 -or (($uids | Measure-Object -Maximum).Maximum -eq $uids.Count - 1 -and $uids[0] -eq 0))
    $dups = @($uids | Group-Object | Where-Object Count -gt 1).Count
    $c0 = $j.entries[0].content
    $coreMeta = $c0 -match '核心元数据（卡外）'
    $uid0len = ($c0 -replace '<!--.*','' ).Length
    $dis = @($j.entries | Where-Object { $_.disable -eq $true -or $_.extensions.disable -eq $true }).Count
    $extPosBad = @($j.entries | Where-Object { $_.extensions.position -ne 4 }).Count
    $uid0cst = $j.entries[0].constant
    $ext0cst = $j.entries[0].extensions.constant
    'PASS? {0} | entries={1} uidContig={2} dupUid={3} uid0.const(root/ext)={4}/{5} uid0核心元数据={6} disable≈{7} extPosBad={8}' -f $short, $j.entries.Count, $contig, $dups, $uid0cst, $ext0cst, $coreMeta, $dis, $extPosBad
  } catch {
    'FAIL {0} :: {1}' -f $short, $_.Exception.Message
  }
}
